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
