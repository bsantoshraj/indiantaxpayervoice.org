# Operating staging

Staging is one DigitalOcean droplet (Premium AMD 2 GB, `blr1`, `itv-staging-1`)
behind Cloudflare. It holds no real data. Production does not exist yet; it will
reuse this layout with managed databases (see the [Phase 0 report](phase-0-report.md)).

## Admin machine

Infrastructure is changed from one admin machine, which holds credentials that never
go to CI or the repository:

| Path | What |
|---|---|
| `~/.config/itv/do_token` | DigitalOcean API token (Terraform) |
| `~/.config/itv/cf_token` | Cloudflare admin token (Terraform, settings) |
| `~/.config/itv/cf-cache-purge.token` | Cloudflare cache-purge token (also the `CF_PURGE_TOKEN` CI secret) |
| `~/.config/itv/backup-age.key` | **Backup private key.** Without it backups are unreadable. Keep an offline copy |
| `~/.config/itv/ci-deploy-key.pub` | Public half of the CI deploy key |
| `~/itv/itv.{crt,key}` | Cloudflare Origin CA certificate and key (copied to `/opt/itv/var/origin-tls` on the droplet) |
| `infra/terraform/*/terraform.tfstate` | Terraform state (gitignored; only copy) |
| `~/itv-backups/staging/` | Encrypted copies of the droplet's backups (pulled daily at 08:30 IST by cron) |

All of these should be mode 600. SSH to the droplet: `ssh deploy@134.209.157.144`
(key-only; no passwords, no root).

## Terraform

Two configurations, applied by hand from the admin machine after the change has been
reviewed in a PR:

| Directory | Manages |
|---|---|
| `infra/terraform/staging` | Droplet, firewall (HTTPS from Cloudflare only, SSH key-only), SSH keys, project |
| `infra/terraform/cloudflare` | Zone-wide: cache rules, browser cache TTL, tiered cache, and the LimeSurvey admin (DNS, Access application, policy, email-code login). Shared by staging and production because a zone has one cache ruleset |

```bash
export DIGITALOCEAN_TOKEN="$(cat ~/.config/itv/do_token)"
export CLOUDFLARE_API_TOKEN="$(cat ~/.config/itv/cf_token)"
terraform -chdir=infra/terraform/staging plan       # review, then apply
terraform -chdir=infra/terraform/cloudflare plan
```

The droplet ignores changes to `ssh_keys` and `user_data` so it is never rebuilt by
accident. Its DNS records for `staging`, `survey-staging` and `stats-staging` were
created by hand in Cloudflare; `survey-admin-staging` is in Terraform.

## Cloudflare

- **SSL/TLS:** Full (strict), Always Use HTTPS on, origin uses a Cloudflare Origin CA
  certificate (valid only behind Cloudflare, so these names must stay proxied).
- **Caching:** see [how-it-works.md](how-it-works.md#hostnames-staging). Purge one
  environment only: `scripts/purge-cdn.sh <hostname>...`.
- **Email address obfuscation** is on (Cloudflare default): addresses in pages are
  rewritten and decoded by a small script in the browser. Visitors without JavaScript
  see "[email protected]".

**Add a LimeSurvey administrator.** Add the address to `survey_admin_emails` in
`infra/terraform/cloudflare/variables.tf`, open a PR, then
`terraform -chdir=infra/terraform/cloudflare apply` and deploy (the deploy writes the
allowlist into the droplet's `.env`, which the origin check uses). They also need a
LimeSurvey account.

## Backups and restore

`infra/staging/backup-db.sh` runs daily at 02:17 UTC (`/etc/cron.d/itv-backup`, log
`/var/log/itv-backup.log`). Each run writes a consistent dump of both databases plus a
separate copy of `.env` (it holds LimeSurvey's encryption keys) to `/var/backups/itv`,
encrypted with [age](https://age-encryption.org) to `infra/staging/backup-recipient.txt`
(a public key: it can only encrypt). Fourteen days are kept. The droplet cannot read
its own backups.

```bash
# Restore test (monthly, and after any database or backup change)
ssh deploy@134.209.157.144 'sudo /opt/itv/infra/staging/restore-test.sh /dev/stdin' < ~/.config/itv/backup-age.key
# Copy backups here now (cron does this daily)
scripts/pull-staging-backups.sh 134.209.157.144
```

The restore test restores the newest complete set into scratch databases (decrypted
data and the key stay in memory), requires a byte-identical re-dump, checks WordPress
and the active survey, checks the set's `.env` holds all five LimeSurvey keys, and
drops the scratch databases. Last run: PASS in about 2 seconds.

## Rotating secrets

```bash
ssh deploy@134.209.157.144 '/opt/itv/infra/staging/rotate-secrets.sh'                     # passwords, gate secret
ssh deploy@134.209.157.144 '/opt/itv/infra/staging/rotate-secrets.sh --encryption-keys'   # also LimeSurvey keys
```
It regenerates every secret in `/opt/itv/.env`, applies it to the database users, the
LimeSurvey and WordPress accounts and the containers, logs every admin out, checks the
aggregator still exports, and takes a fresh backup. `--encryption-keys` is refused while
any data is encrypted with the current keys. If the rotation was because of exposure,
delete the older backups too (they contain the old secrets). Admin passwords are read
on the droplet, never printed: `grep '^LS_ADMIN_PASSWORD=' /opt/itv/.env | cut -d= -f2`.

## SSH keys

`scripts/sync-staging-keys.sh` replaces the `deploy` user's `authorized_keys` with the
keys in Terraform (this machine's key plus `extra_ssh_key_names`) and the restricted CI
deploy key. Run it after changing either.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Browser says `DNS_PROBE_FINISHED_NXDOMAIN` for a new hostname | Your resolver cached "not found" from before the record existed (up to 30 min). Clear `chrome://net-internals/#dns`, flush the OS cache, or wait |
| Page still shows old content after a deploy | Browser cache (hard refresh), or the CDN cache if the deploy's purge step warned. `curl -sI <url> \| grep -i cf-cache-status` shows what Cloudflare served |
| "[email protected]" instead of an address | Cloudflare email obfuscation and JavaScript blocked in that browser |
| Cloudflare error 526 / 525 | Origin certificate invalid or Caddy not serving that hostname: check `docker compose logs caddy` and that the host is in the Caddyfile |
| "Unable to find your Access application" | A truncated or old login link: always start at the app's address |
| Image builds on the droplet time out | Downloads from PyPI are unreliable from `blr1`; deploy through CI (images are built on GitHub) |
| The LimeSurvey admin returns 403 | Missing or wrong `ITV_ACCESS_*` in `/opt/itv/.env` (the deploy writes them from Terraform outputs), or the email is not in the allowlist |

## Not set up yet

Tracked as GitHub issues with the `backlog` label: monitoring and alerts (#5, deferred
until production work starts, though a billing alert is required before Phase 1 is
complete), remote Terraform state, and a manually triggered end-to-end survey test.
