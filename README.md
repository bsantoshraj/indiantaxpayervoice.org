# Indian Taxpayer Voice — local platform

Local build of the stack described in `claude.md`, before moving to DigitalOcean.

| Component | Local URL | Notes |
|---|---|---|
| WordPress (public site) | `http://<BIND_ADDR host>:8080` | Own MariaDB; no survey data, no route to LimeSurvey |
| LimeSurvey 6 (survey) | `:8081`, admin at `/admin/` | Own MariaDB on an internal-only network; DB sessions on |
| Public statistics | `:8082/v1/statistics/{summary,states,industries,trends}` | Static JSON written by the aggregator |

## First run

```bash
./scripts/init-local-env.sh          # writes .env (mode 600) with random secrets
docker compose up -d
docker compose run --rm wpcli bash /bootstrap.sh   # idempotent: pages, menu, settings
```

`BIND_ADDR` in `.env` controls exposure: `127.0.0.1` (this machine only) or
`0.0.0.0` (local network, plain HTTP). When it is `0.0.0.0`, set `WP_URL` and
`LS_PUBLIC_URL` to this machine's LAN address and re-run the bootstrap.

## Aggregator (survey export → public statistics)

```bash
cd aggregator && python3 -m pytest -q             # unit/integration tests
docker compose run --rm aggregator                 # via LimeSurvey RemoteControl API
docker compose run --rm -v "$PWD/export.csv:/in/export.csv:ro" aggregator --csv /in/export.csv
```

The API route needs, in LimeSurvey: RemoteControl enabled (JSON-RPC), a survey
whose question codes match `survey/questionnaire-v1.json`, a `stats-exporter`
user with response-export permission on that survey only, and
`ITV_LS_SURVEY_ID` set in `.env`.

Privacy rules applied before anything is published: completed + consented
responses only, unknown codes rejected, duplicate response IDs counted once,
cells under 20 suppressed with complementary suppression, no IDs, timestamps
or free text in output. A failed or suspicious run (missing columns, >10 % drop
in valid responses, LimeSurvey unreachable) keeps the previous release.

## Staging (DigitalOcean)

One Premium AMD (NVMe) 2 GB droplet in `blr1`. WordPress and the survey stack run
in Docker; MariaDB runs on the host (two databases, one user each, reachable
only from the Docker networks). The bot gate is always on.

Hostnames (`staging`, `survey-staging`, `stats-staging` under
`indiantaxpayervoice.org`) are proxied by Cloudflare in Full (strict) mode. Caddy
terminates HTTPS with a Cloudflare Origin CA certificate (`CADDYFILE=Caddyfile.origin-ca`
in `/opt/itv/.env`; key and cert in `/opt/itv/var/origin-tls`, never in git).
`infra/staging/Caddyfile` is the Let's Encrypt / `sslip.io` fallback.

```bash
export DIGITALOCEAN_TOKEN="$(cat ~/.config/itv/do_token)"   # never commit tokens
cd infra/terraform/staging && terraform init && terraform apply
cd - && scripts/deploy-staging.sh "$(terraform -chdir=infra/terraform/staging output -raw ip)"
scripts/sync-staging-keys.sh        # push the SSH keys declared in Terraform to the live droplet
```

Secrets are generated on the droplet (`/opt/itv/.env`, mode 600) and never leave
it. SSH is key-only (no passwords, no root) from any address; `extra_ssh_key_names`
lists the DigitalOcean account keys allowed in. A single host MariaDB is weaker
isolation than separate servers — acceptable for staging (no real data); use a
managed database for the survey in production.

### Backups and restore test (staging)

`infra/staging/backup-db.sh` runs daily at 02:17 UTC (`/etc/cron.d/itv-backup`,
log `/var/log/itv-backup.log`). It writes a consistent dump of each database plus
a separate copy of `.env` (LimeSurvey's encryption keys) to `/var/backups/itv`,
encrypted with [age](https://age-encryption.org) to `infra/staging/backup-recipient.txt`,
and keeps 14 days. The private key is **not** on the droplet (it cannot read its
own backups); it lives at `~/.config/itv/backup-age.key` on the admin machine and
must also be kept somewhere offline — without it the backups are unreadable.

Restore test (monthly, and after any DB or backup change):

```bash
ssh deploy@<ip> 'sudo /opt/itv/infra/staging/restore-test.sh /dev/stdin' < ~/.config/itv/backup-age.key
```

It restores the newest backups into scratch databases (decrypted data and key
stay in `/dev/shm`), re-dumps them and requires a byte-identical match, checks
WordPress and the active survey, confirms the secrets backup holds the current
LimeSurvey keys, and drops the scratch databases.

Restore tests use the newest *complete* set (both databases and `.env` from the
same run) and check that its `.env` holds all five LimeSurvey keys, since those
keys, not the running ones, decrypt that set.

### Rotating staging secrets

```bash
ssh deploy@<ip> '/opt/itv/infra/staging/rotate-secrets.sh'                     # passwords + gate secret
ssh deploy@<ip> '/opt/itv/infra/staging/rotate-secrets.sh --encryption-keys'   # also LimeSurvey keys
```

Replaces every generated secret in `/opt/itv/.env`, applies it to the host DB
users, the LimeSurvey and WordPress accounts and the containers, logs all admins
out, and takes a fresh backup. Values are never printed. `--encryption-keys` is
refused while any data is encrypted with the current keys. Backups taken before a
rotation still hold the old secrets: delete them if the rotation was because of
exposure.

`scripts/pull-staging-backups.sh <ip>` copies the encrypted files to
`~/itv-backups/staging` on the admin machine (still encrypted). Planned: a
separate Spaces bucket as the off-site copy.

## Cloudflare (zone-wide, shared by staging and production)

`infra/terraform/cloudflare` manages the cache rules, browser-cache setting and
tiered cache for `indiantaxpayervoice.org` (one cache ruleset per zone, so it is
separate from the per-environment Terraform). Hostnames are listed per role in
`variables.tf`; add production's there.

```bash
export CLOUDFLARE_API_TOKEN="$(cat ~/.config/itv/cf_token)"
cd infra/terraform/cloudflare && terraform init && terraform plan
```

- **Statistics:** cached at the edge per the origin's `Cache-Control` (5 minutes).
- **WordPress pages:** cached 10 minutes for anonymous visitors. Admin, login,
  `wp-json`, previews and logged-in/comment/password cookies always reach the origin.
  404s are cached for 60 s and 5xx are never cached.
- **Survey, gate and LimeSurvey admin:** never cached.
- `scripts/purge-cdn.sh <host>...` purges only the named hostnames; the staging
  deploy runs it at the end. Content edited in wp-admin can take up to 10 minutes
  to appear for visitors unless purged.

## LimeSurvey admin (Cloudflare Access)

The admin is served only on its own hostname, `survey-admin-staging.indiantaxpayervoice.org`
(local: http://localhost:8083). Defined in `infra/terraform/cloudflare/access.tf`.

- **Cloudflare Access** in front: a one-time code is emailed to an allowed address
  (`survey_admin_emails`, default `hello@indiantaxpayervoice.org`); sessions last 8 h.
- **The origin re-checks** every request: nginx (`:8090`) asks the gate's
  `/access/check`, which verifies the `Cf-Access-Jwt-Assertion` token (Cloudflare's
  signature, this app's `aud`, issuer, expiry, allowed email). Without valid
  `ITV_ACCESS_*` settings it refuses everyone in staging and production.
- **The public survey hostname refuses every admin route** (`/index.php/admin`, `/admin`,
  `?r=admin`, REST API, installer) with 404.
- The staging deploy writes `SURVEY_ADMIN_HOST` and `ITV_ACCESS_*` (not secret) into
  `/opt/itv/.env` from the Cloudflare Terraform outputs. To add an administrator,
  extend `survey_admin_emails` and re-run `terraform apply` and the deploy.

## CI/CD (GitHub Actions)

`.github/workflows/ci.yml`:

- **Every PR:** aggregator and gate tests, shellcheck, Terraform fmt/validate, compose
  config and `nginx -t`; both images are built (not pushed).
- **Merge to `main`:** the gate and aggregator images are built once and pushed to
  `ghcr.io/bsantoshraj/itv-{gate,aggregator}:<commit sha>`, then deployed to staging:
  code is synced, the droplet pulls those images (it never builds), the staging CDN
  cache is purged, and `scripts/smoke-staging.sh` runs.
- **Rollback:** Actions → CI → Run workflow with an earlier `main` commit SHA.
- **Not in CI:** `terraform apply` (state lives on the admin machine), the backup
  restore test (needs the backup key) and the full survey e2e test.

The CI deploy key is restricted on the droplet to syncing into `/opt/itv` and
`deploy <sha>` (`infra/staging/ci-ssh-command.sh`, installed to `/usr/local/bin`); its
public half is kept at `~/.config/itv/ci-deploy-key.pub` (not in the repo) and installed
by `scripts/sync-staging-keys.sh`. Registry access uses each run's short-lived
`GITHUB_TOKEN`; no registry credential is stored on the droplet.

| GitHub setting | Kind | Value |
|---|---|---|
| `STAGING_SSH_KEY` | secret | CI deploy private key |
| `CF_PURGE_TOKEN` | secret | Cloudflare token with Zone > Cache Purge only |
| `STAGING_HOST`, `STAGING_SSH_KNOWN_HOSTS`, `CF_ZONE_ID` | variables | droplet IP, its pinned host keys, zone ID |

`scripts/deploy-staging.sh` remains as a manual fallback (builds images on the droplet).
Dependabot (`.github/dependabot.yml`) opens weekly update PRs.
