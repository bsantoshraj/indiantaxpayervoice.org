# Owner backlog

Action items that need the owner: decisions, accounts, content and reviews that
cannot be done in code. Engineering work is tracked in GitHub issues (label
`backlog`) and in the phase reports. Last updated: 2026-10-25.

## Blocking Phase 1 sign-off

| # | Item | What is needed | Notes |
|---|---|---|---|
| 1 | **Legal review** of the privacy notice and terms | A lawyer's review of `/privacy-policy/` and `/terms/` | Both are written to match the system; they make commitments (7-working-day replies, publishing breach details) |
| 2 | **Who is responsible for the data** (data fiduciary, grievance officer) | Name a person or legal entity | The privacy notice currently names the initiative and `hello@indiantaxpayervoice.org` |
| 3 | **Website content** | Fuller text for job-loss, health, public spending, research, mission and FAQ pages (about 140–230 words each today) | Edit `wordpress/content/*.html` or send text; each page also has a meta description in `wordpress/bootstrap.sh` |

## Accounts and access

| # | Item | What is needed |
|---|---|---|
| 4 | **Search Console** | A `google-site-verification` TXT record is already on the domain. In Search Console, click **Verify** for the *Domain* property, then submit `https://indiantaxpayervoice.org/wp-sitemap.xml` |
| 20 | **Bing Webmaster Tools** | At https://www.bing.com/webmasters, import the site from Google Search Console (after item 4). IndexNow submissions already run on every production deploy |
| 5 | **Cloudflare Web Analytics** | Add *Account › Account Web Analytics › Edit* to the existing Cloudflare token (its value does not change) |
| 6 | **Backup private key** | Keep an offline copy of `~/.config/itv/backup-age.key` (for example in a password manager); without it, backups are unreadable |
| 7 | **Old credential files** | `~/do_token`, `~/ghcr_token` and `~/do_staging.json` are readable by every user on the admin machine: `chmod 600` them or delete them |
| 18 | **DNSSEC** | Cloudflare dashboard → DNS → Settings → *Enable DNSSEC*, then add the DS record it shows at your domain registrar |
| 21 | **Article publish token** | Create a fine-grained GitHub token: this repository only, permission *Actions: read and write*, nothing else. Add it to the staging `/opt/itv/.env` as `ITV_PUBLISH_DISPATCH_TOKEN=…` and redeploy staging. Until then, staging's "Publish to production" / "Unpublish from production" links explain how to run the workflow by hand ([ci-cd.md](ci-cd.md#publish-an-article-controlled-release)) |
| 22 | **Renew staging's CI Access token by 2027-10-25** | It is valid for a year. Renew as in [operations.md](operations.md#renew-the-ci-access-token-for-staging); otherwise the staging smoke tests fail |
| 19 | **DMARC to quarantine** | Around 7 November 2026, if DMARC reports to `hello@` show only Google sending and passing: ask to set `dmarc_policy = "quarantine"` |

## Decisions

| # | Decision | Recommendation |
|---|---|---|
| 8 | Turnstile on or off (in addition to the proof-of-work gate) | Off for now; revisit if automated submissions appear |
| 9 | LimeSurvey outgoing email (administration notices; the default "your answers were emailed" text) | No respondent email at all; admin notices only if needed |
| 10 | Methodologist review of the questions and income bands | Before the survey opens to the public |
| 11 | Trademark search for the name and logo | Before public launch |
| 12 | Register or check `indiantaxpayervoice.in` (to redirect to `.org`) | Optional |
| 13 | Quality-flag rules (speeders, bursts) | After the pilot |

## Reviews and approvals

| # | Item |
|---|---|
| 14 | Merge approvals for open pull requests (the pipeline deploys `main` to staging) |
| 23 | **Article review before publishing**: each article's "Owner check" notes in the drafts doc; a tax professional's check of the tax tables in articles 7, 11 and 12 |
| 24 | **Older CBDT return statistics (AY 2012-13 to 2021-22)** for the 10-year picture: incometaxindia.gov.in refuses scripted downloads. Download them in a browser into `research/sources/` as `a11-cbdt-itr-stats-ayYYYY-YY.pdf` ([research/README.md](../research/README.md)) |
| 25 | **RTI questions** (optional): CBDT, number of returns with a house-property loss above ₹2 lakh and the tax effect of the cap; salaried filers with house-property losses |
| 15 | Dependabot updates: #7 DigitalOcean provider, #8 nginx 1.31, #10 altcha 2.3 (small); #9 MariaDB 11.8 → 13.0 (major; needs a migration test first) |

## Production

| # | Item | What is needed |
|---|---|---|
| 16 | **Survey controlled release** | Opened 2026-10-24 (PR #33). To close it again: `ITV_SURVEY_OPEN=0` in `infra/env/production.env`, then promote and approve ([ci-cd.md](ci-cd.md#open-or-close-the-production-survey-controlled-release)) |
| 17 | **Approve production deployments** | Each "Run workflow → production" waits for your approval in GitHub |

## Deferred by owner decision

- Monitoring and alerting, including the billing alert: until production work starts (#5).

## Done

- 2026-10-25: staging made private (Cloudflare Access on every staging host; CI uses a service token).
- 2026-10-25: reviewed article publishing: drafts on staging, "Publish to production" / "Unpublish from production" with approval; Research page lists published articles.
- 2026-10-25: research evidence folder (`research/`): 12 articles, sources, checksums, scripts, charts.
- 2026-10-25: daily backup copies to the admin machine via anacron (catch up after sleep).
- 2026-10-24: external security review; fixes live (account names and version hidden, framing protection, SPF/DMARC/CAA, Bot Fight Mode off).
- 2026-10-24: production live on indiantaxpayervoice.org; survey opened by controlled release (before the legal, privacy and methodologist reviews, by owner decision).

- 2026-10-24: survey-response retention set to 2 years from the close of each round.
- 2026-10-24: income bands extended (₹24–50 lakh, ₹50 lakh–₹1 crore, above ₹1 crore).
- 2026-10-24: Phase 2 decisions: hourly, rounded statistics; tile-grid map; server-rendered charts.
- 2026-10-24: phone test of the survey through the gate.
- 2026-10-24: Cloudflare token for Zero Trust, WAF and cache; purge-only token for CI.
