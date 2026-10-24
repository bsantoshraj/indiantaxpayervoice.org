# Owner backlog

Action items that need the owner: decisions, accounts, content and reviews that
cannot be done in code. Engineering work is tracked in GitHub issues (label
`backlog`) and in the phase reports. Last updated: 2026-10-24.

## Blocking Phase 1 sign-off

| # | Item | What is needed | Notes |
|---|---|---|---|
| 1 | **Legal review** of the privacy notice and terms | A lawyer's review of `/privacy-policy/` and `/terms/` | Both are written to match the system; they make commitments (7-working-day replies, publishing breach details) |
| 2 | **Who is responsible for the data** (data fiduciary, grievance officer) | Name a person or legal entity | The privacy notice currently names the initiative and `hello@indiantaxpayervoice.org` |
| 3 | **Website content** | Fuller text for job-loss, health, public spending, research, mission and FAQ pages (about 140–230 words each today) | Edit `wordpress/content/*.html` or send text; each page also has a meta description in `wordpress/bootstrap.sh` |

## Accounts and access

| # | Item | What is needed |
|---|---|---|
| 4 | **Search Console** | Create a *Domain* property for `indiantaxpayervoice.org` and send the `google-site-verification=…` value; it is added as a DNS record through Terraform |
| 5 | **Cloudflare Web Analytics** | Add *Account › Account Web Analytics › Edit* to the existing Cloudflare token (its value does not change) |
| 6 | **Backup private key** | Keep an offline copy of `~/.config/itv/backup-age.key` (for example in a password manager); without it, backups are unreadable |
| 7 | **Old credential files** | `~/do_token`, `~/ghcr_token` and `~/do_staging.json` are readable by every user on the admin machine: `chmod 600` them or delete them |

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
| 15 | Dependabot updates: #7 DigitalOcean provider, #8 nginx 1.31, #10 altcha 2.3 (small); #9 MariaDB 11.8 → 13.0 (major; needs a migration test first) |

## Deferred by owner decision

- Monitoring and alerting, including the billing alert: until production work starts (#5).

## Done

- 2026-10-24: survey-response retention set to 2 years from the close of each round.
- 2026-10-24: income bands extended (₹24–50 lakh, ₹50 lakh–₹1 crore, above ₹1 crore).
- 2026-10-24: Phase 2 decisions: hourly, rounded statistics; tile-grid map; server-rendered charts.
- 2026-10-24: phone test of the survey through the gate.
- 2026-10-24: Cloudflare token for Zero Trust, WAF and cache; purge-only token for CI.
