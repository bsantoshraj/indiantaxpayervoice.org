# Operating staging and production

Staging (`itv-staging-1`, 134.209.157.144) and production (`itv-prod-1`, 64.227.176.80)
are each one DigitalOcean droplet (Premium AMD 2 GB, `blr1`) behind Cloudflare, built
from the same Terraform module. Staging holds test data only. Every difference is in
[environments.md](environments.md). Manual deploys: `scripts/deploy.sh <env>`; smoke
tests: `scripts/smoke.sh <env>`; key sync: `scripts/sync-staging-keys.sh <env>`.

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
| `~/itv-backups/staging/`, `~/itv-backups/production/` | Encrypted copies of each droplet's backups (pulled daily at 08:30 and 08:35 IST by cron; 30 days kept) |

All of these should be mode 600. SSH: `ssh deploy@134.209.157.144` (staging) or
`ssh deploy@64.227.176.80` (production); key-only, no passwords, no root.

## Terraform

Two configurations, applied by hand from the admin machine after the change has been
reviewed in a PR:

| Directory | Manages |
|---|---|
| `infra/terraform/modules/droplet` | Shared: droplet, firewall (HTTPS from Cloudflare only, SSH key-only), project |
| `infra/terraform/staging`, `infra/terraform/production` | Each environment's module call: name, size, keys (compare the two files to see every difference) |
| `infra/terraform/cloudflare` | Zone-wide: cache rules, browser cache TTL, tiered cache, WAF and rate limiting, and the admins (DNS, Access applications, policy, email-code login). Shared by staging and production because a zone has one cache ruleset |

```bash
export DIGITALOCEAN_TOKEN="$(cat ~/.config/itv/do_token)"
export CLOUDFLARE_API_TOKEN="$(cat ~/.config/itv/cf_token)"
terraform -chdir=infra/terraform/staging plan       # review, then apply (saved plan file)
terraform -chdir=infra/terraform/production plan
terraform -chdir=infra/terraform/cloudflare plan
```

The droplets ignore changes to `ssh_keys` and `user_data` and have `prevent_destroy`,
so neither is rebuilt or deleted by accident. All DNS records for both environments
are in Terraform (staging's first records were imported), as are SPF, DMARC, CAA and
the Bot Fight Mode setting (off).

## Cloudflare

- **SSL/TLS:** Full (strict), Always Use HTTPS on, origin uses a Cloudflare Origin CA
  certificate (valid only behind Cloudflare, so these names must stay proxied).
- **Caching:** see [how-it-works.md](how-it-works.md#hostnames). Purge one
  environment only: `scripts/purge-cdn.sh <hostname>...`.
- **WAF** (`infra/terraform/cloudflare/waf.tf`): Cloudflare Managed Free Ruleset on
  every host; custom rules block `/xmlrpc.php`, LimeSurvey admin routes on the public
  survey host, and methods a host does not need (statistics are read-only).
- **Rate limiting:** survey POSTs (answers and bot-check verifications) over
  `survey_posts_per_10s` (50) per IP per 10 s are blocked for 10 s at the edge; nginx
  limits again at the origin. Indian mobile carriers share IPs (CGNAT): revisit both
  limits against real traffic before production.
- **WordPress admin** (`/wp-admin`, `/wp-login.php`) is behind Cloudflare Access with
  the same policy as the LimeSurvey admin; Caddy re-checks the token (`forward_auth`
  to the gate). `ITV_ACCESS_AUD` lists both applications.
- **Email address obfuscation** is off (Terraform), so addresses are shown as written,
  including to visitors without JavaScript.

**Add a LimeSurvey administrator.** Add the address to `survey_admin_emails` in
`infra/terraform/cloudflare/variables.tf`, open a PR, then
`terraform -chdir=infra/terraform/cloudflare apply` and deploy (the deploy writes the
allowlist into the droplet's `.env`, which the origin check uses). They also need a
LimeSurvey account.

## Email and certificate DNS

`infra/terraform/cloudflare/email_dns.tf`: SPF allows only Google Workspace (`-all`);
DMARC starts at `p=none` with aggregate reports to `hello@indiantaxpayervoice.org`;
CAA limits certificate issuance to the CAs Cloudflare uses (violation reports to the
same mailbox). **After about two weeks of clean DMARC reports** (only Google sending,
all passing), set `dmarc_policy = "quarantine"` in `variables.tf` and apply; later
`reject`. If anything else ever needs to send mail as the domain (for example
LimeSurvey or a newsletter), add it to SPF first.

## SEO and analytics

- `wordpress/mu-plugins/itv-seo.php` adds meta descriptions (each page's excerpt, set
  from the description column in `wordpress/bootstrap.sh`), Open Graph and Twitter tags
  with `themes/itv/assets/share.png`, Organization/WebSite structured data, `en-IN` and
  sitemaps (`/wp-sitemap.xml`). Only production is indexable: `bootstrap.sh` sets
  "discourage search engines" unless `ITV_ENV=production`, and staging also sends
  `X-Robots-Tag: noindex`.
- **Search Console:** add a *Domain* property for `indiantaxpayervoice.org` in Google
  Search Console, copy the `google-site-verification=…` TXT value, and add it as a TXT
  record (in `infra/terraform/cloudflare`), then verify and submit
  `https://indiantaxpayervoice.org/wp-sitemap.xml` once production exists.
- **Cloudflare Web Analytics** (cookieless; website only, never the survey): set
  `ITV_CF_BEACON_TOKEN` in the droplet's `.env` to the site's beacon token. Creating the
  site via Terraform needs the token permission *Account › Account Web Analytics › Edit*.

## Backups and restore

`infra/staging/backup-db.sh` runs daily at 02:17 UTC (`/etc/cron.d/itv-backup`, log
`/var/log/itv-backup.log`). Each run writes a consistent dump of both databases plus a
separate copy of `.env` (it holds LimeSurvey's encryption keys) to `/var/backups/itv`,
encrypted with [age](https://age-encryption.org) to `infra/staging/backup-recipient.txt`
(a public key: it can only encrypt). Fourteen days are kept. The droplet cannot read
its own backups.

```bash
# Restore test (monthly, and after any database or backup change)
IP=134.209.157.144   # staging; production: 64.227.176.80
ssh deploy@$IP 'sudo /opt/itv/infra/staging/restore-test.sh /dev/stdin' < ~/.config/itv/backup-age.key
# Copy backups here now (cron does this daily; production into ~/itv-backups/production)
scripts/pull-staging-backups.sh $IP [~/itv-backups/production]
```

The restore test restores the newest complete set into scratch databases (decrypted
data and the key stay in memory), requires a byte-identical re-dump, checks WordPress
and the active survey, checks the set's `.env` holds all five LimeSurvey keys, and
drops the scratch databases. Last runs (2026-10-24): PASS on staging and on production.

## Deleting survey responses (retention)

The privacy notice promises survey responses are kept **2 years from the close of
their survey round**. Responses carry no dates, so deletion is per round:

1. When a round closes, record its close date in the methodology page and in the
   survey's LimeSurvey settings (expiry date).
2. Two years later, delete that round's survey in the LimeSurvey admin (which deletes
   its responses and comments), or replace it as described in ci-cd.md.
3. Published statistics hold no personal data and can stay. Backups containing the
   deleted responses expire within 14 days (server) and 30 days (admin copy).

## Rotating secrets

```bash
ssh deploy@$IP '/opt/itv/infra/staging/rotate-secrets.sh'                     # passwords, gate secret
ssh deploy@$IP '/opt/itv/infra/staging/rotate-secrets.sh --encryption-keys'   # also LimeSurvey keys (refused while encrypted data exists)
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
| "[email protected]" instead of an address | Cloudflare email obfuscation was switched back on; it is `off` in `infra/terraform/cloudflare/main.tf` |
| Cloudflare error 526 / 525 | Origin certificate invalid or Caddy not serving that hostname: check `docker compose logs caddy` and that the host is in the Caddyfile |
| "Unable to find your Access application" | A truncated or old login link: always start at the app's address |
| Image builds on the droplet time out | Downloads from PyPI are unreliable from `blr1`; deploy through CI (images are built on GitHub) |
| The LimeSurvey admin returns 403 | Missing or wrong `ITV_ACCESS_*` in `/opt/itv/.env` (the deploy writes them from Terraform outputs), or the email is not in the allowlist |

## Not set up yet

Tracked as GitHub issues with the `backlog` label: monitoring and alerts (#5, deferred
until production work starts, though a billing alert is required before Phase 1 is
complete), remote Terraform state (#12), and a manually triggered end-to-end survey
test (#13).
