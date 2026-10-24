# Indian Taxpayer Voice: Phase 1 status report

**Status on 2026-10-24:** the staging platform is built, secured, documented and
deployed automatically, and the survey has been tested end to end on a phone. The
website pages are published without draft notices, and methodology, privacy and terms
describe what the system actually does. **What remains is mostly owner work:** formal
legal review, fuller research content, and two small account steps for analytics. See
[Remaining work](#7-remaining-work-to-close-phase-1).

Phase 1 in [`claude.md`](../claude.md) §12 is "Secure public website and survey pilot".
The architecture and plan are in the [Phase 0 report](phase-0-report.md). How the
system works is described in [how-it-works.md](how-it-works.md).

Markers: ✅ done and verified · ◐ partly done · ❌ not done · — out of scope (owner decision).

## 1. Phase 1 scope (claude.md §12)

| Item | Status | State on staging |
|---|---|---|
| Configure the WordPress site | ✅ | Theme, navigation and 14 published pages, no draft notices. Per-page meta descriptions, Open Graph and Twitter cards with a share image, Organization/WebSite structured data, `en-IN`, XML sitemap, icons. Research and topic pages are still short (about 140–230 words) |
| Deploy and harden LimeSurvey | ✅ | LimeSurvey 7.5.1, anonymised (no IP, no tokens, no dates), behind the proof-of-work gate and rate limits at the edge and origin. Admin only on its own Cloudflare Access hostname, token re-verified at the origin; admin routes blocked on the public host by the WAF (403) and nginx (404) |
| Domain, TLS and CDN/WAF | ✅ | Full (strict) TLS with an Origin CA certificate, minimum TLS 1.2, Always Use HTTPS; origin accepts HTTPS from Cloudflare only. Cache rules and tiered cache; Cloudflare Managed Free Ruleset and custom WAF rules; edge rate limiting on survey submissions. All in Terraform |
| Build the first questionnaire | ✅ | v1: consent plus 11 questions (3 required). Income bands extended on 2026-10-24 to ₹24–50 lakh, ₹50 lakh–₹1 crore and above ₹1 crore (surcharge thresholds); the pipeline rebuilt the staging survey from the JSON |
| Define retention and consent practices | ✅ | Consent (18+, privacy notice, aggregate use) in the survey. Retention published in the privacy notice: survey responses 2 years from the close of their round, backups 14 days (server) and 30 days (copy), logs size-rotated, emails until dealt with. Deletion procedure in operations.md |
| Establish database backups and monitoring | ✅ / — | Backups ✅ (below). Monitoring and alerting — **out of Phase 1 scope by owner decision**; tracked in #5 |
| Methodology, privacy and terms pages | ◐ | Written to match the system (anonymity, what is and is not collected, cookies, logs, processors, retention, DPDP Act rights, corrections). **Formal legal review not done** |
| Test the entire response-collection workflow | ✅ | Completed on a phone through Cloudflare and the gate, and in a desktop browser; both reached the published statistics |

## 2. Acceptance criteria (Phase 0 report §9)

| Criterion | Status | Evidence |
|---|---|---|
| A tester completes the survey on a phone over HTTPS through the gate | ✅ | Response 5, 2026-10-24: public link at 14:13:56 IST; the phone solved the bot check in about 3 s (`/gate/verify` 303); 5 answer pages submitted by 14:14:59 IST |
| The response appears in the statistics within 15 minutes | ✅ (criterion relaxed) | Response 5 reached the public statistics **2 min 32 s** after submission, seen through Cloudflare (`valid_responses` 1 → 2), under the original 5-minute refresh. Since Phase 2's differencing protection, statistics refresh **hourly** with counts rounded to 5, so the criterion is now "within about 75 minutes"; the smoke tests fail if statistics are older than that |
| A database restore into a scratch database succeeds | ✅ | `restore-test.sh`: PASS on 5 consecutive runs (about 2 s), byte-identical re-dump |
| Cloudflare and billing alerts are configured | — | Out of Phase 1 scope by owner decision (monitoring and alerting deferred to production, #5) |
| Legal sign-off on the privacy notice | ◐ | Notice written to match the system's actual behaviour; formal legal review not yet done |

The test responses (3 and 5) were deleted when the questionnaire changed and the
pipeline rebuilt the staging survey; the evidence above was recorded before that.

## 3. What was built

### Platform
| Component | Version / detail |
|---|---|
| Droplet | `itv-staging-1`, DigitalOcean `blr1`, Premium AMD 1 vCPU / 2 GB / 50 GB, US$14 a month |
| Website | WordPress 7.1.3 (PHP 8.3.36), block theme `itv`, statistics and SEO must-use plugins |
| Survey | LimeSurvey 7.5.1 (PHP 8.4.27) behind an nginx 1.30 proxy and the gate (ALTCHA proof-of-work) |
| Databases | Host MariaDB 10.11: two databases, one user each, reachable only from the Docker networks |
| Statistics | Aggregator every 5 minutes; static JSON/CSV with small-cell suppression (k = 20) |
| HTTPS | Caddy 2.11 with a Cloudflare Origin CA certificate |
| Edge | Cloudflare Free: DNS, CDN, WAF, rate limiting, Full (strict) TLS, Zero Trust Access (free tier) |

### Security controls
- **Network:** HTTPS accepted only from Cloudflare's published ranges; port 80 closed; SSH key-only. MariaDB is not exposed.
- **Edge:** Cloudflare Managed Free Ruleset; custom rules block `/xmlrpc.php`, LimeSurvey admin routes on the public survey host, and methods a host does not need (statistics are read-only); survey POSTs over 50 per IP per 10 s are blocked.
- **Admins:** the LimeSurvey admin and the WordPress admin (`/wp-admin`, `/wp-login.php`) are behind Cloudflare Access with email one-time codes for `hello@indiantaxpayervoice.org` (8-hour sessions). The origin re-verifies the signed token for both (signature, application, issuer, expiry, email), with 13 tests covering forged, expired, wrong-app and wrong-algorithm tokens.
- **Survey integrity:** the bot-check pass is signed, lasts 2 hours and covers 60 requests; submissions are rate-limited at the edge and again per visitor IP at the origin.
- **PHP:** both runtimes include the PHP2Shell fixes (CVE-2026-109618/109619). CVE-2026-115560 (no fixed release yet) is mitigated with `session.upload_progress.enabled = 0`; neither app changes its session serializer at runtime. `expose_php` is off.
- **Secrets:** generated on the droplet and never copied off it (`.env`, mode 600). Rotation is scripted (`rotate-secrets.sh`).
- **Repository:** public, with `main` protected (PR plus passing CI; no force-push or deletion; only the owner can bypass). Secret scanning with push protection and Dependabot security alerts are on. History scanned with gitleaks: no leaks.
- **CI key:** restricted on the droplet to code sync and `deploy <sha>`. Shell, PTY, port forwarding and paths outside `/opt/itv` are refused (tested).

### Privacy by design
No name, contact details, PAN, Aadhaar, exact income, IP address or timestamp is
stored with a response. The website sets no cookies; analytics (when enabled) are
cookieless and never run on the survey. Server logs hold IP addresses for security
only and are size-rotated. Published statistics suppress groups under 20.

### Backups
Daily at 02:17 UTC: consistent dumps of both databases plus a separate copy of `.env`
(LimeSurvey's encryption keys), encrypted with age to a public key. The droplet
cannot decrypt them. 14 days are kept on the droplet; a daily cron copies them to the
admin machine, which keeps 30 days.

### Delivery
- **CI/CD:** every PR runs tests, lint and image builds. Merging to `main` builds images once on GitHub (GHCR, tagged by commit), deploys staging, restarts only services whose configuration changed, purges the staging CDN cache and runs 21 smoke checks. A changed questionnaire rebuilds the staging survey automatically (refused anywhere else). Rollback redeploys an earlier commit. Details: [ci-cd.md](ci-cd.md).
- **Infrastructure as code:** Terraform for the droplet, firewall and keys (`infra/terraform/staging`) and for Cloudflare cache, WAF, rate limiting, settings and Access (`infra/terraform/cloudflare`).
- **Dependencies:** Dependabot opens weekly grouped update PRs.
- **Documentation:** [how-it-works](how-it-works.md), [development](development.md), [ci-cd](ci-cd.md), [operations](operations.md).

## 4. Verified test results (2026-10-24)

| Suite | Result |
|---|---|
| Aggregator unit and integration tests | 57 passed |
| Gate tests (bot check and Access token verification) | 34 passed |
| Staging smoke tests through Cloudflare (`scripts/smoke-staging.sh`) | 21/21 passed |
| Backup restore test on staging | PASS |
| Admin blocking on the public survey host | 10 URL variants refused locally (case, `?r=`, encoding, double slash); WAF 403 on staging |
| Direct-to-origin admin requests with no, junk or unsigned tokens | 403 |
| Survey proxy after upstream containers get new IPs | Keeps working without a restart (tested by forcing a new IP) |
| SEO output, all 14 pages (local) | Meta description, 10 Open Graph and 4 Twitter tags, one H1, `en-IN`; structured data on the home page; all 14 pages in the sitemap; no author sitemap |
| shellcheck, Terraform fmt/validate, `nginx -t`, Caddy adapt, actionlint | Clean |
| Responsive layout (14 pages × 7 widths) | 98/98 PASS, re-run locally on 2026-10-24 after the content, SEO and map changes |
| End-to-end survey submission | Passed locally; on staging in a desktop browser and on a phone through the gate |

## 5. Incidents and corrections

- **Staging secrets exposed in a session transcript.** A debugging trace printed the staging `.env`. Every secret was rotated, including LimeSurvey's encryption keys (no encrypted data existed). Backups holding the old values were deleted; a fresh backup passed the restore test. No real data was on staging. Prevention: secrets are only compared on the server, never printed.
- **Survey outage on staging after a deploy.** Recreated containers got new IPs, and nginx kept proxying to the old ones (gate 502, survey 500). The deploy's smoke tests caught it; service was restored by restarting the proxy. Fixed permanently: nginx re-resolves upstream names through Docker's DNS.
- **Configuration changes did not always take effect.** Config files are bind-mounted, and running containers kept the old files until recreated (the nginx fix above was on disk but not running). Deploys now restart only the services whose configuration changed.
- **CI deploy lost its SSH connection** during a quiet wait. SSH keepalives added.
- **Privacy page returned 404.** The bootstrap updated WordPress's own draft privacy page but never published it. Fixed.
- **Cloudflare SSL mode was Full, not Full (strict).** Switched to strict.
- **Browser cache TTL overrode the 5-minute statistics headers** (Cloudflare's 4-hour default). Now respects the origin.
- **Survey setup broke after the admin lockdown** (it called the admin API through the public proxy) and **deploys waited 5 minutes** polling an admin URL. Both now use internal routes.
- **Image builds on the droplet timed out downloading from PyPI.** Images are built in CI.
- **Email addresses showed as "[email protected]"** without JavaScript. Cloudflare email obfuscation turned off.
- **Assessments was switched on by hand in the LimeSurvey admin.** Reverted when the pipeline rebuilt the survey from the JSON; lasting survey changes go in the JSON.
- **The privacy outline promised "optional email for updates".** No such feature exists; the published notice describes only what is built.

## 6. Decisions still needed from the owner

| # | Decision | Status |
|---|---|---|
| 1 | Register the domains | `.org` registered and on Cloudflare; `.in` not checked |
| 2 | Data fiduciary and grievance officer | **Open.** The privacy notice names the initiative and `hello@indiantaxpayervoice.org`; a named person or legal entity is not stated |
| 3 | Trademark search for the name and logo | **Open** |
| 4 | DigitalOcean API access | Done |
| 5 | Cloudflare account; Turnstile | Account done. Turnstile not configured (proof-of-work gate only) |
| 6 | Email for administration notifications | Mailbox exists (Google Workspace). LimeSurvey has no outgoing mail, and its default "your answers were emailed" text is unresolved |
| 7 | Quality-flag rules (speeders, bursts) | **Open**, after the pilot |
| 8 | Methodologist review of questions and income bands | **Open** (bands extended at the owner's request) |
| 9 | Survey timestamps | **Open.** Recommendation stands: keep anonymisation; trends from run-to-run totals (not built yet) |
| 10 | Survey-response retention period | **Decided:** 2 years from the close of each survey round (published in the privacy notice) |
| 11 | Production canonical hostname | Apex `indiantaxpayervoice.org`, with `www` redirecting (recommended, adopted for SEO defaults) |

## 7. Remaining work to close Phase 1

**Owner / editorial / legal**
- [ ] Formal legal review of the privacy notice and terms, and decision 2 (who is responsible)
- [ ] Fuller content for the research and topic pages (job loss, health, public spending, research, mission, FAQ)
- [ ] Search Console: create the property and send the DNS verification code (it goes into Cloudflare via Terraform)
- [ ] Cloudflare token: add *Account › Account Web Analytics › Edit* so cookieless page-view analytics can be switched on

**Engineering**
- [ ] Enable Cloudflare Web Analytics (beacon on the website only) once the token permission is added
- [x] Re-run the responsive check (14 pages × 7 widths) after the content changes: 98/98 PASS (local)
- [ ] Decide Turnstile on or off; if on, create keys in Terraform
- [ ] Resolve LimeSurvey's outgoing-mail behaviour (decision 6)
- [ ] Review the Dependabot PRs: #7 (DigitalOcean provider), #8 (nginx 1.31), #10 (altcha 2.3), #9 (MariaDB 11.8 → 13.0, a major version needing a local migration test)

**Out of Phase 1 scope:** monitoring and alerting, including the billing alert (#5);
remote Terraform state (#12); on-demand end-to-end survey test (#13).
