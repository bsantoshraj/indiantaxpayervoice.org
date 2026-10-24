# Indian Taxpayer Voice: Phase 1 status report

**Status on 2026-10-24:** the staging platform is built, secured and deployed
automatically. **Phase 1 is not complete.** The remaining work is mostly not
engineering: website content, legal review of privacy and terms, retention rules,
billing alerts and a phone test. See [Remaining work](#remaining-work-to-close-phase-1).

Phase 1 in [`claude.md`](../claude.md) §12 is "Secure public website and survey pilot".
The architecture and plan are in the [Phase 0 report](phase-0-report.md). How the
system works is described in [how-it-works.md](how-it-works.md).

Markers: ✅ done and verified · ◐ partly done · ❌ not done.

## 1. Phase 1 scope (claude.md §12)

| Item | Status | State on staging |
|---|---|---|
| Configure the WordPress site | ◐ | Theme, navigation and 14 published pages. Contact address published. **All page text is still placeholder or draft** |
| Deploy and harden LimeSurvey | ✅ | LimeSurvey 7.5.1, anonymised (no IP, no tokens, no dates), behind the proof-of-work gate and per-IP rate limits. Admin only on its own Cloudflare Access hostname, with the token re-verified at the origin; every admin route returns 404 on the public host |
| Domain, TLS and CDN/WAF | ◐ | Domain on Cloudflare; Full (strict) with an Origin CA certificate; Always Use HTTPS; firewall accepts HTTPS from Cloudflare only; cache rules and tiered cache in Terraform. **No Cloudflare WAF or rate-limiting rules yet** |
| Build the first questionnaire | ✅ | v1: consent plus 11 questions (3 required), live and active. Methodologist review pending |
| Define retention and consent practices | ◐ | Consent question in the survey. **Retention periods and deletion procedure not defined** |
| Establish database backups and monitoring | ◐ | Backups done (below). **Monitoring and alerts deferred** to production (#5) |
| Methodology, privacy and terms pages | ❌ | Pages exist as drafts. **Privacy and terms need legal review** |
| Test the entire response-collection workflow | ◐ | One completed submission in a desktop browser through Cloudflare and the gate (response 3, 2026-10-24 morning) is counted in the published statistics. An owner test at 13:05 IST opened the survey from the LimeSurvey admin but **submitted no answers** (none reached the server). **Not yet done on a phone** |

## 2. Acceptance criteria (Phase 0 report §9)

| Criterion | Status | Evidence |
|---|---|---|
| A tester completes the survey on a phone over HTTPS through the gate | ❌ | Desktop browser only (response 3). The 13:05 IST attempt recorded no answers. Use the public link (`survey-staging…/index.php/735139`), not the admin's run/preview button, so the gate is part of the test |
| The response appears in the statistics within 15 minutes | ✅ | Response 3 is published (`valid_responses = 1`). The aggregator runs every 5 minutes and statistics are cached for 5; the smoke tests fail if statistics are older than 15 minutes. Staging holds 2 responses: 1 completed, 1 abandoned (not counted) |
| A database restore into a scratch database succeeds | ✅ | `restore-test.sh`: PASS on 5 consecutive runs (about 2 s), byte-identical re-dump |
| Cloudflare and billing alerts are configured | ❌ | Deferred with monitoring (#5). **A billing alert is still required to close Phase 1** |
| Legal sign-off on the privacy notice | ❌ | Draft outline only |

## 3. What was built

### Platform
| Component | Version / detail |
|---|---|
| Droplet | `itv-staging-1`, DigitalOcean `blr1`, Premium AMD 1 vCPU / 2 GB / 50 GB, US$14 a month |
| Website | WordPress 7.1.3 (PHP 8.3), block theme `itv`, statistics plugin |
| Survey | LimeSurvey 7.5.1 (PHP 8.4) behind an nginx 1.30 proxy and the gate (ALTCHA proof-of-work) |
| Databases | Host MariaDB 10.11: two databases, one user each, reachable only from the Docker networks |
| Statistics | Aggregator every 5 minutes; static JSON/CSV with small-cell suppression (k = 20) |
| HTTPS | Caddy 2.11 with a Cloudflare Origin CA certificate |
| Edge | Cloudflare Free: DNS, CDN, Full (strict) TLS, Zero Trust Access (free tier) |

### Security controls
- **Network:** HTTPS accepted only from Cloudflare's published ranges; port 80 closed (Cloudflare redirects to HTTPS); SSH key-only. MariaDB is not exposed.
- **Admin access:** Cloudflare Access with email one-time codes for `hello@indiantaxpayervoice.org` (8-hour sessions). The origin verifies the signed token (signature, application, issuer, expiry, email) and refuses if it can't, with 13 tests covering forged, expired, wrong-app and wrong-algorithm tokens.
- **Survey integrity:** the bot-check pass is signed, lasts 2 hours and covers 60 requests; answer submissions are rate-limited per visitor IP, which arrives through Cloudflare and Caddy.
- **Secrets:** generated on the droplet and never copied off it (`.env`, mode 600). Rotation is scripted (`rotate-secrets.sh`).
- **Repository:** public, with `main` protected (PR plus passing CI; no force-push or deletion; only the owner can bypass). Secret scanning with push protection and Dependabot security alerts are on. History scanned with gitleaks: no leaks.
- **CI key:** restricted on the droplet to code sync and `deploy <sha>`. Shell, PTY, port forwarding and paths outside `/opt/itv` are refused (tested).

### Backups
Daily at 02:17 UTC: consistent dumps of both databases plus a separate copy of `.env`
(LimeSurvey's encryption keys), encrypted with age to a public key. The droplet
cannot decrypt them. 14 days are kept on the droplet, and a daily cron copies them to
the admin machine.

### Delivery
- **CI/CD:** every PR runs the tests, lint and image builds. Merging to `main` builds the images once on GitHub (GHCR, tagged by commit), deploys staging, purges its CDN cache and runs 18 smoke checks. Rollback redeploys an earlier commit. Details: [ci-cd.md](ci-cd.md).
- **Infrastructure as code:** Terraform for the droplet, firewall and keys (`infra/terraform/staging`) and for Cloudflare cache rules, settings and Access (`infra/terraform/cloudflare`).
- **Dependencies:** Dependabot opens weekly grouped update PRs.
- **Documentation:** [how-it-works](how-it-works.md), [development](development.md), [ci-cd](ci-cd.md), [operations](operations.md).

## 4. Verified test results (2026-10-24)

| Suite | Result |
|---|---|
| Aggregator unit and integration tests | 55 passed |
| Gate tests (bot check and Access token verification) | 34 passed |
| Staging smoke tests through Cloudflare (`scripts/smoke-staging.sh`) | 18/18 passed |
| Backup restore test on staging | PASS |
| Public-host admin blocking | 10 URL variants refused locally (case, `?r=`, encoding, double slash); 5 on staging |
| Direct-to-origin admin requests with no, junk or unsigned tokens | 403 |
| shellcheck, Terraform fmt/validate, `nginx -t`, actionlint | Clean |
| Responsive layout (14 pages × 7 widths) | 98/98, local, from Phase 0. **Not re-run on staging** |
| End-to-end survey submission | Passed locally (Phase 0) and once in a desktop browser on staging (response 3). The 13:05 IST owner attempt submitted no answers. **Not yet on a phone** |

## 5. Incidents and corrections

- **Staging secrets exposed in a session transcript (2026-10-24).** A debugging trace printed the staging `.env`. Every secret was rotated, including LimeSurvey's encryption keys; none had encrypted data yet. Backups holding the old values were deleted, and a fresh backup passed the restore test. There was no real data on staging. Prevention: secrets are now only compared on the server, never printed.
- **Privacy page returned 404.** The bootstrap updated WordPress's own draft privacy page but never published it. Fixed.
- **Cloudflare SSL mode was Full, not Full (strict).** Switched to strict.
- **Browser cache TTL overrode the 5-minute statistics headers** (Cloudflare's 4-hour default). Now set to respect the origin.
- **Deploys waited 5 minutes for no reason** after the admin lockdown, because they polled an admin URL that now returns 404. Fixed.
- **Image builds on the droplet time out downloading from PyPI.** Images are now built in CI.
- **Email addresses showed as "[email protected]"** without JavaScript (Cloudflare obfuscation). Turned off.
- **Survey setting changed in the admin (2026-10-24, 13:06 IST):** Assessments was switched on. It has no rules, so respondents see no difference, but it no longer matches the survey as built from `survey/questionnaire-v1.json`. The survey is still active and anonymised, with no IP storage and no participant table. **Owner to confirm or revert.**

## 6. Decisions still needed from the owner

Carried over from Phase 0 §8, with today's status:

| # | Decision | Status |
|---|---|---|
| 1 | Register the domains | `.org` registered and on Cloudflare; `.in` not checked |
| 2 | Data fiduciary, privacy contact, grievance officer | **Open.** The contact address exists; roles not named |
| 3 | Trademark search for the name and logo | **Open** |
| 4 | DigitalOcean API access | Done |
| 5 | Cloudflare account; Turnstile on staging | Account done. Turnstile not configured (proof-of-work only) |
| 6 | Email for administration notifications | Mailbox exists (Google Workspace). LimeSurvey has no outgoing mail configured, and its default "your answers were emailed" text is unresolved |
| 7 | Quality-flag rules (speeders, bursts) | **Open**, after the pilot |
| 8 | Methodologist review of questions and income bands | **Open** |
| 9 | Survey timestamps (keep anonymisation or not) | **Open.** Recommendation (a) stands: keep it, derive trends from run-to-run totals |

## 7. Remaining work to close Phase 1

**Owner / editorial / legal**
- [ ] Write the website content (all 14 pages are drafts), especially methodology
- [ ] Privacy notice and terms: legal review and sign-off. This needs decision 2
- [ ] Define retention periods and the deletion procedure (survey responses, backups, logs, admin accounts)
- [ ] Complete the survey on a phone over HTTPS through the gate, using the public link rather than the admin's run button, and confirm it appears in the statistics (response IDs and published counts are checked on the server)
- [ ] Confirm or revert the Assessments setting switched on in the admin

**Engineering**
- [ ] Billing alert on the DigitalOcean account (part of #5; required by the acceptance criteria)
- [ ] Cloudflare WAF and rate-limiting rules in front of the survey (the token already has the permission)
- [ ] Decide Turnstile on or off for staging and production; if on, create keys in Terraform
- [ ] Re-run the responsive check against staging
- [ ] Resolve LimeSurvey's outgoing-mail behaviour (decision 6)

**Open pull requests:** Dependabot #7 (DigitalOcean provider), #8 (nginx 1.31), #10 (altcha 2.3), and #9 (MariaDB 11.8 → 13.0, a major version that needs a local migration test first).

**Backlog (after Phase 1):** monitoring and alerts beyond billing (#5), remote Terraform state (#12), on-demand end-to-end survey test (#13).
