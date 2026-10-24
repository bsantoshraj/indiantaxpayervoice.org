# Indian Taxpayer Voice — Phase 0 report: audit, architecture and plan

*Prepared 2026-10-23 as the Phase 0 audit and plan. Sections 1–7 record the audit as it
was; the status, decisions and plan below are kept current.*

> **Status update, 2026-10-24 (evening).** Staging runs on DigitalOcean (`blr1`) behind
> Cloudflare, deployed by CI/CD on every merge to `main`.
> **Phase 1:** complete except owner items (legal review, page content, Search Console,
> an analytics permission); monitoring and alerting moved out by owner decision.
> **Phase 2:** statistics API, differencing protection, tile-grid map and five heat maps
> live on staging; trends, filters, a screen-reader test and the privacy review remain.
> **Production:** being prepared on the same layout (owner request, 2026-10-24).
> Details: [Phase 1 report](phase-1-report.md), [Phase 2 report](phase-2-report.md),
> [owner backlog](owner-backlog.md), [how it works](how-it-works.md),
> [operations](operations.md).

This report covers the first deliverable in `claude.md` §14. Each finding is marked **[Verified]** (observed or tested in this environment) or **[Assumption]** (to be confirmed). Costs are planning estimates, not quotes.

---

## 1. Existing-state findings

| Area | Finding | Basis |
|---|---|---|
| Repository | The folder contained only `claude.md`. It was not a git repository, and there was no code, CI/CD or deployment configuration. | [Verified] |
| WordPress | No existing installation, hosting or content. | [Verified] |
| Domains | `indiantaxpayervoice.org`, `indiantaxpayervoice.in` and `indiantaxpayer.org` all return NXDOMAIN from their TLD servers, and `.org` RDAP returns 404, so **they appear to be unregistered**. There is no DNS, TLS or CDN yet. | [Verified] public DNS/RDAP, 2026-10-23 |
| DigitalOcean | The `doctl` CLI on this VM has a stored token that the DigitalOcean API rejects (`401 Unable to authenticate`), so no existing resources could be listed. | [Verified] |
| Credentials hygiene | `~/do_token`, `~/ghcr_token` and `~/do_staging.json` are world-readable (mode 664). **Recommend `chmod 600`.** These files were not read or used. | [Verified] |
| Analytics | None configured. | [Verified] |
| Local tooling | Docker 29.4, Compose 5.1, Python 3.12, Node 20, Terraform 1.9.8, doctl 1.115 and gh are available. | [Verified] |

**Built locally since the audit (Phase 1/2 groundwork, local only):** a Docker Compose stack with WordPress 7.1.3, LimeSurvey 7.5.1 (upgraded from 6.17.18, which its admin UI reports as out of support) and two MariaDB 11.8 databases; a custom theme; the v1 questionnaire; the aggregator; static statistics publishing; and the survey gate. Details are in §9.

---

## 2. Proposed target architecture (DigitalOcean)

```
                         Internet (mostly mobile)
                                  │
                ┌─────────────────▼──────────────────┐
                │ Cloudflare: DNS · CDN · WAF · DDoS │
                │ Turnstile (survey only) · TLS      │
                └──┬──────────────┬───────────────┬──┘
     www.          │   survey.    │      stats.   │
                   ▼              ▼               ▼
        ┌────────────────┐ ┌──────────────────┐ ┌───────────────────┐
        │ WordPress      │ │ DO Load Balancer │ │ DO Spaces + CDN   │
        │ droplet(s)     │ └────────┬─────────┘ │ static JSON/CSV   │
        │ page cache     │          ▼           │ /v1/statistics/*  │
        └──────┬─────────┘ ┌──────────────────┐ └────────▲──────────┘
               │           │ survey droplets  │          │ publish
               │           │ (1..N, identical)│          │ (atomic)
               │           │ nginx proxy      │ ┌────────┴──────────┐
               │           │ → gate (ALTCHA)  │ │ Aggregator job    │
               │           │ → LimeSurvey 7   │ │ hourly            │
               │           └────────┬─────────┘ │ RemoteControl     │
               ▼                    ▼           │ export (read-only)│
     ┌──────────────────┐ ┌──────────────────┐  └────────┬──────────┘
     │ WP database      │ │ Managed MySQL    │◄──────────┘ (via LimeSurvey
     │ (no survey data) │ │ LimeSurvey only  │              API, not SQL)
     └──────────────────┘ │ private VPC      │
                          └──────────────────┘
   Backups: managed-DB daily backups + PITR, plus weekly encrypted dumps to a
   separate Spaces bucket. Staging is a scaled-down copy with no real data.
```

**Key properties**

- **Two independent scaling domains** (claude.md §5): the website is served almost entirely from the CDN, while the survey scales by adding identical droplets behind the load balancer. The survey never depends on WordPress.
- **WordPress never sees survey data.** It has no LimeSurvey credentials and no network path to the survey database. It reads only the public statistics JSON.
- **Public statistics are static files** on Spaces/CDN, so visitors cannot trigger database queries. This replaces a live API: the endpoints in claude.md §4D are kept as file paths (`/v1/statistics/summary` and so on), and health is reported by the publisher job.
- **No Kubernetes, queues or microservices.** LimeSurvey writes directly to MySQL, and a response is accepted only once LimeSurvey has committed it.

Alternatives considered: DO App Platform for WordPress (rejected for now because WordPress needs a writable filesystem and plugins; revisit with a Spaces media offload); Lightsail/Hetzner (cheaper, but weaker managed DB and VPC features).

---

## 3. Component-by-component deployment plan

| Component | Local (built) | Staging / production on DigitalOcean |
|---|---|---|
| CDN/WAF | — | Cloudflare (Free → Pro during campaigns): WAF managed rules, bot fight mode, rate rules on `survey.`, Turnstile site key |
| WordPress | `wordpress:7.1.3-php8.3-apache` + child theme + must-use plugin (always loaded) | Droplet (Docker Compose), full-page cache, media on Spaces, `DISALLOW_FILE_EDIT`, admin MFA, admin restricted by Cloudflare Access |
| WP database | MariaDB 11.8 container | DB on the WP droplet (pilot), or managed MySQL from the Growth scenario |
| Survey proxy + gate | nginx 1.30.6 + `gate/` (ALTCHA 3.2.4 / altcha-py 2.2.0) | On every survey droplet; gate **always on** (refuses to start disabled) |
| LimeSurvey | `martialblog/limesurvey:7.5.1-261021-apache` (PHP 8.4), DB sessions, encryption keys from env | Same image, 1..N droplets behind LB; `/admin` reachable only via Cloudflare Access/VPN |
| Survey database | MariaDB 11.8 container, internal network | DO Managed MySQL 8, private VPC, trusted sources = survey droplets + aggregator only |
| Aggregator | `aggregator/`, 5-minute loop container | Cron on a small droplet (or App Platform job), publishing to Spaces |
| Stats hosting | nginx serving a volume | Spaces bucket + CDN, `Cache-Control: max-age=300` |
| Secrets | `.env` (mode 600, gitignored) | DO droplet env from a secrets manager / sops-encrypted files; never in git |
| IaC | Compose | Terraform (DO provider) for droplets, LB, DB, Spaces, firewall, VPC; Compose on droplets |
| CI/CD | — | GitHub Actions: tests → build images → push to registry → deploy to staging → manual promotion to production |

---

## 4. LimeSurvey hosting model and persistent storage

- **Edition:** LimeSurvey Community Edition **7.x** (7.5.1 locally), licensed **GPL-2.0-or-later** [Verified: LICENSE in image]. *Correction:* this report originally proposed 6.x; the LimeSurvey 6 admin UI states that version 6 is out of support, so the stack was upgraded to 7.5.1 on 2026-10-23. The DB migrated from schema 651 to 717 with no data loss [Verified: the existing response was preserved and exported].
- **Upgrade notes found during 6 → 7:** the response table is renamed `lime_responses_<sid>` (was `lime_survey_<sid>`); survey pages now change without a full page reload; checkbox field names use internal IDs (`Q35_S40`). The export API and code headings are unchanged, so the aggregator needed no change for these.
- **Upgrade step learned the hard way:** after a major upgrade, **clear the `lime_sessions` table**. Sessions started before the upgrade still reference the old column names, and a respondent resuming one gets a 500 error on their next page [Verified locally 2026-10-23]. In production, schedule major upgrades in a maintenance window with the survey paused. Self-hosting unmodified is permitted. If we modify LimeSurvey and *distribute* it, GPL obligations apply; we currently make no code changes, and the gate is a separate service.
- **Runtime:** PHP 8.4, Apache [Verified]. Supported databases: MySQL/MariaDB, PostgreSQL and MSSQL. Recommendation: **DO Managed MySQL 8** (InnoDB).
- **Persistent state and how each is handled:**

| State | Where | Multi-replica handling |
|---|---|---|
| Responses, survey structure, users, permissions | Database | Shared managed DB |
| PHP sessions | Database (`TABLE_SESSION`) [Verified enabled] | Any replica can serve any page |
| Encryption keys (`security.php`) | Env vars, identical on every replica [Verified] | **Back up separately**: losing them makes encrypted fields unreadable |
| `upload/` (themes, survey resources, uploaded files) | Volume | v1 has no file-upload questions; bake the theme into the image so replicas are stateless. If file uploads are added, use shared storage. |

- **Concurrency [Assumption, must load-test]:** LimeSurvey writes one row per response and updates it page by page. Multiple app replicas sharing one DB with DB sessions is a supported pattern, but throughput per vCPU must be measured (§7).
- **Upgrades:** pin the image tag, test in staging against a production-structure copy with synthetic data, back up the DB, then upgrade production in a maintenance window. The `updatedb` migration runs on container start.

---

## 5. WordPress-to-survey integration design

```
Respondent ──► WordPress /participate/ ──link──► survey.…/index.php/<sid>
                                                  │ gate → LimeSurvey → MySQL
Aggregator (cron) ──RemoteControl export_responses (least-privilege user)──┘
     │ validate → dedupe → aggregate → suppress → publish (atomic swap)
     ▼
Spaces/CDN /v1/statistics/*.json ◄── WordPress shortcodes (server fetch, 60 s cache)
```

- **Integration point:** LimeSurvey's documented RemoteControl JSON-RPC API (`export_responses`, CSV with code headings). The aggregator never queries LimeSurvey's database schema directly, per claude.md §4B.
- **Least privilege [Verified]:** the `stats-exporter` account has only `auth_db` login rights plus `responses: read, export` on the one survey.
- **Single source of truth:** `survey/questionnaire-v1.json` generates the LimeSurvey structure (`survey/build_structure.py`) *and* drives aggregator validation, so codes cannot drift.
- **Public endpoints** (static): `summary`, `states`, `industries`, `breakdowns`, `distributions`, `trends` (JSON), plus `states.csv`.
- **Failure behaviour [Verified by tests]:** if LimeSurvey is unreachable, the export is malformed, or valid responses drop more than 10%, nothing is published and the previous release stays live. Only one run can execute at a time.

---

## 6. Security and privacy threat model

**Assets:** raw responses (especially free text), LimeSurvey admin accounts, DB credentials, encryption keys, the integrity of the published statistics, the gate secret, and respondents' trust.

| # | Threat (STRIDE) | Mitigation | Status |
|---|---|---|---|
| T1 | Ballot stuffing by bots or scripts (Tampering) | ALTCHA proof-of-work gate with single-use challenges and bounded passes; Turnstile + Cloudflare WAF in production; rate limits; quality flags (speeders, bursts, honeypot) | Gate + rate limits built; flags pending pilot data |
| T2 | Re-identification from published statistics (Info disclosure) | Small-cohort threshold of 20 + complementary suppression; demographics never crossed with state or each other; no free text, IDs or times; weekly trends only | Built + 53 aggregator tests |
| T3 | Differencing across successive releases | Refresh on a schedule (not per response); cumulative counts only; review before launch | **Residual risk**: needs privacy review |
| T4 | Free text containing personal data | Never published; on-screen warning; redaction process before any quoted use; restricted export access | Process to be written |
| T5 | LimeSurvey admin takeover (Spoofing / Elevation) | `/admin` behind Cloudflare Access/VPN, MFA, unique admin accounts, no shared logins, audit log of exports | Production config |
| T6 | DB exposure | Managed DB in private VPC, trusted sources only, TLS, no public endpoint; WP has no route to it | Mirrored locally (internal network) |
| T7 | Secret leakage | `.env` gitignored (mode 600); secrets never logged (tested); production secrets in a secrets store | Built |
| T8 | Spreadsheet formula injection in exports | Public CSV cells sanitised (tested). LimeSurvey's own exports must be opened safely by staff | Built / staff guidance |
| T9 | Loss of encryption keys or data | Keys backed up separately from DB backups; PITR; restore test monthly | Production runbook |
| T10 | Open redirect / XSS on the gate | `next` restricted to `/index.php/…`; output escaped; CSP with `frame-ancestors 'none'` (tested) | Built |
| T11 | DoS / viral surge | CDN-cached site; static statistics; LB + horizontal survey replicas; Cloudflare DDoS | Design |
| T12 | Third-party processors seeing personal data | Cloudflare (IP addresses) listed in the privacy notice; no analytics until consent design is done | Legal review |

**Privacy baseline:** no PAN, Aadhaar, exact salary, employer or address; IP addresses not stored (`ipaddr=N`); anonymised survey (no tokens); optional demographics with "Prefer not to say"; contact sign-up (when built) kept separate from responses. A **legal review of the Digital Personal Data Protection Act, 2023 and its Rules (including commencement dates)** is required before launch.

---

## 7. Capacity and monthly cost estimates

**Assumptions [all to be validated by load testing]:**

- **Peak hour:** 15% of daily traffic (25% for the viral "Major campaign"). Peak second = 3× the peak-hour average.
- **Website:** 3 pages per visitor; CDN cache-hit rate 90–95% for HTML and ~100% for assets, so only misses reach WordPress.
- **Survey:** about 10 HTTP requests per completed survey (gate + 5 pages + assets misses), over about 5 minutes.
- **LimeSurvey:** about 10–15 dynamic requests per second per vCPU [unmeasured].
- **Storage:** each response row is about 1–2 KB.
- **Money:** USD→INR at ₹88. DigitalOcean list prices as known at writing; **verify current pricing**. Each cost range includes a small staging environment.

| | Pilot | Initial traction | Growth | Major campaign |
|---|---:|---:|---:|---:|
| Daily visitors / submissions | 1k / 100 | 10k / 1k | 100k / 10k | 1M / 100k |
| Peak site req/s (edge) | ~0.4 | ~4 | ~38 | ~625 |
| Peak req/s reaching WordPress | <0.1 | ~0.4 | ~4 | ~30 |
| Concurrent survey sessions (peak) | ~2 | ~13 | ~125 | ~2,100 |
| Peak survey req/s (uncached) | ~0.05 | ~1.3 | ~13 | ~210 |
| Survey app capacity | 1 × 2 GB/1 vCPU | 1 × 4 GB/2 vCPU | 2 × 4 GB/2 vCPU + LB | 4–6 × 8 GB/4 vCPU + LB |
| Survey DB | Managed 1 GB | Managed 2 GB | Managed 4 GB + standby | Managed 8 GB/4 vCPU + standby |
| DB connections (peak) | <10 | ~20 | ~60 | ~300 (needs pooling/limits) |
| Response data growth | ~0.2 MB/day | ~2 MB/day | ~20 MB/day | ~200 MB/day |
| Edge bandwidth/day | ~0.5 GB | ~5 GB | ~45 GB | ~450 GB (CDN) |
| **Monthly cost (INR)** | **₹6,000–9,000** | **₹9,000–12,000** | **₹25,000–31,000** | **₹53,000–97,000** |

**Likely bottlenecks, in order:**
1. LimeSurvey PHP CPU. Fix: add droplets.
2. Survey DB writes and connections. Fix: scale the DB vertically and cap per-replica PHP workers.
3. Gate memory state with many replicas. Fix: move the pass and replay store to Redis/Valkey.
4. Admin exports during surges. Fix: schedule exports off-peak.

The DB and LB do not autoscale on DigitalOcean; plan resizes ahead of announced campaigns. Droplets bill hourly, so surge capacity can be added for days and removed afterwards. Configure **DO billing alerts** at 50%, 80% and 100% of the monthly budget.

**Graceful degradation:**
- Static statistics keep serving if the aggregator stops.
- The website keeps serving from the CDN if WordPress is down.
- Under survey overload, Cloudflare queues or challenges rather than LimeSurvey dropping writes.
- Aggregator frequency can be reduced to free DB capacity.

---

## 8. Risks, assumptions and unresolved decisions

**Decisions needed from the owner**
1. Register `indiantaxpayervoice.org` and `.in` (they appear available), and decide who holds the registrar account.
  *Update 2026-10-24: `.org` registered and on Cloudflare; `.in` not checked.*
2. Who the legal data fiduciary is (person or entity), the contact details in the privacy notice, and the grievance officer.
  *Update: open. The privacy notice names the initiative and `hello@indiantaxpayervoice.org`.*
3. A trademark search and clearance for the name and logo (IP India public search; ideally a lawyer).
  *Update: open.*
4. DigitalOcean account access: a fresh API token for staging, scoped to the project. The current one is invalid.
  *Update: done (new token, kept in `~/.config/itv`, mode 600). The old `~/do_token`, `~/ghcr_token` and `~/do_staging.json` from §1 are still world-readable: run `chmod 600` on them or delete them.*
5. A Cloudflare account, and whether to use Turnstile in staging with test keys.
  *Update: account, Zero Trust and Terraform-managed zone in place. Turnstile not configured (proof-of-work gate only).*
6. Email provider for administration notifications. LimeSurvey's default "your answers were emailed" error text must be fixed or email configured.
  *Update: Google Workspace mailbox `hello@indiantaxpayervoice.org`. LimeSurvey outgoing mail still unconfigured.*
7. Quality-flag rules after the pilot (speeder threshold, bursts).
  *Update: open, after the pilot.*
8. A methodologist's review of the question set and income bands (re-check against the tax slabs in force).
  *Update: open. Income bands extended on 2026-10-24 (₹24–50 lakh, ₹50 lakh–₹1 crore, above ₹1 crore) at the owner's request.*
9. **Survey timestamps.** In LimeSurvey 7, an anonymised survey stores every date as `1980-01-01` [Verified 2026-10-23]. As a result:
   - Weekly trends cannot come from response dates. The aggregator now reports such responses as `date_not_recorded` and never invents a date.
   - The "completed implausibly fast" quality flag (claude.md §4F) is not possible without durations.

   The options are:
   - **(a)** Keep anonymisation (recommended). It is also what keeps one-time invitation links unlinkable if stuffing ever forces that escalation. Derive daily or weekly trends from the change in the total between scheduled aggregator runs, and evaluate LimeSurvey's `savetimings` (per-page durations, not timestamps) for speeder detection.
   - **(b)** Turn anonymisation off while still storing no tokens or IP addresses. This gives real dates, but weakens that guarantee.

   *Update: (a) kept; run-to-run trends are part of Phase 2.*
10. **Retention.** *Decided 2026-10-24: survey responses are kept 2 years from the close of their round (privacy notice).*

**Key risks**
- **Selection bias** is inherent: the results cannot represent all taxpayers. Mitigated by honest labelling everywhere [Built].
- **Determined, human-powered stuffing** cannot be fully prevented without identity checks. The escalation path is documented in claude.md §4F.
- **Map legality:** the Phase 2 India map must follow Survey of India boundaries; a generic map dataset is a legal risk.
- **LimeSurvey throughput** is unmeasured. Capacity numbers are estimates until load-tested.
- **Small-cohort differencing** across releases (T3) needs a privacy review before launch.

**Recorded scope changes** (in claude.md): concrete responsive requirements (§4A), the survey-integrity layer (§4F), optional demographic questions (§6), and the environments (local VM; staging and production on DigitalOcean).

---

## 9. Phased plan with acceptance criteria

### Phase 0 — Audit and architecture *(this document)*
- [x] Existing-state audit, architecture, threat model, costs, risks
- **Acceptance:** owner approves this report and answers the §8 decisions needed to start staging.

### Phase 1 — Secure website and survey pilot
| Item | Local | Staging (DigitalOcean) |
|---|---|---|
| WordPress pages, theme, logo, responsive (98/98 width checks pass locally) | ✅ | ✅ 14 pages, no draft notices, SEO metadata; responsive re-check pending |
| LimeSurvey deployed, hardened (anonymised, no IP, DB sessions, encryption keys, admin behind Cloudflare Access) | ✅ | ✅ |
| v1 questionnaire (consent + 11 questions incl. optional income, gender, age, employment) | ✅ | ✅ income bands extended 2026-10-24 |
| Bot gate + rate limits (on in staging/prod; off locally) | ✅ built, 34 tests | ✅ verified in a phone browser over HTTPS; edge rate limit too |
| End-to-end survey submission | ✅ | ✅ phone and desktop; reached public statistics in 2 min 32 s |
| Domain, TLS, Cloudflare CDN and WAF | — | ✅ Full (strict), managed + custom WAF rules, cache rules (Terraform) |
| Backups + restore test | — | ✅ daily age-encrypted dumps; restore test PASS; 30-day copy off the droplet |
| Monitoring, billing alerts | — | — out of Phase 1 scope (owner decision, #5) |
| Privacy notice, terms, methodology | ✅ written to match the system | ◐ formal legal review pending |
- **Acceptance:** phone test through the gate ✅; response in statistics ✅; restore into a scratch DB ✅; Cloudflare and billing alerts — moved out of scope; legal sign-off ◐. With Phase 2's differencing protection, statistics update **hourly**, so "within 15 minutes" becomes "within about 75 minutes". Full status: [Phase 1 report](phase-1-report.md).

### Phase 2 — Aggregation and public statistics
- [x] Controlled LimeSurvey integration (RemoteControl, least-privilege `stats-exporter`)
- [x] Aggregator with validation, dedupe, suppression, atomic publish (57 tests)
- [x] Static statistics API on its own host, cached by Cloudflare; metric definitions and refresh on the methodology page
- [x] Counters + state table in WordPress (honest zero and suppressed states)
- [x] **Differencing protection**: hourly releases, counts rounded to the nearest 5, whole percentages from rounded figures; synthetic-data tests (#26)
- [x] **Accessible state/UT map**: tile-grid map (`[itv_state_map]`), one equal tile per state/UT, no boundaries; each tile focusable with a tooltip and a screen-reader description; distinct "not shown" and "no responses" tiles; the state table remains the text alternative. Text contrast at least 5.2:1
- [x] **Sector, income, gender, age and employment × concern heat maps** (`[itv_heatmap question=…]`): server-rendered tables shaded by percentage, so each is its own text alternative; no third-party JavaScript; each question shown alone, never crossed with state or another question
- [ ] Filters and explanatory tooltips (progressive enhancement)
- [ ] Trends from the change in totals between releases (responses carry no dates)
- [ ] Publish to Spaces/CDN (only if production load needs it; Cloudflare already caches the static files)
- **Acceptance:** no public file contains IDs, timestamps finer than a week, or free text (tested); suppression and rounding verified on synthetic data in staging; the map and charts pass keyboard and screen-reader checks. Status: [Phase 2 report](phase-2-report.md).

### Production rollout (owner request, 2026-10-24)
- [x] QA on staging: test suites, smoke tests, restore test PASS, responsive check 98/98 against staging
- [x] Production droplet `itv-prod-1` and firewall from the shared Terraform module (`infra/terraform/modules/droplet`)
- [x] Cloudflare for production hosts (one `environments` map): DNS, Access, WAF, rate limiting, cache rules; `www` → apex redirect at the origin
- [x] CI/CD promotion job: the images that passed staging are pulled from GHCR (no rebuild), deployed after owner approval
- [x] Production `.env` generated on the droplet; first deploy with the GHCR images of `afb7437`; smoke tests
- [x] Survey opened by controlled release on 2026-10-24 (`ITV_SURVEY_OPEN=1`, PR #33, promoted with owner approval; production smoke tests pass)
- [x] Production backups: daily encrypted dumps on the droplet, daily copy to the admin machine (`~/itv-backups/production`); restore test PASS
- Open before real respondents are invited: legal review, privacy review (Phase 2), a methodologist's review; monitoring and alerting deferred by owner decision

### Phase 3 — Elasticity and resilience
- [ ] Load tests (k6/Locust) for the Growth and Major-campaign profiles; measure LimeSurvey req/s per vCPU
- [ ] Horizontal survey replicas behind the LB; shared gate store
- [ ] Failure drills: DB failover, aggregator outage, restore from backup (*partly done: the backup restore test passes on staging in about 2 s*)
- [x] Edge protection groundwork: Cloudflare cache rules, tiered cache, managed and custom WAF rules, edge rate limiting (Terraform)
- **Acceptance:** the Growth profile sustains its target with p95 page time under 1.5 s and zero lost submissions; restore time measured and documented.

### Phase 4 — Growth and research operations
- Search Console, consented analytics, campaign attribution, editorial workflow, quarterly privacy and security review.
- *Groundwork done:* SEO metadata, sitemaps and structured data; cookieless analytics code (needs a token permission); Search Console instructions (needs the owner's verification code); Dependabot weekly update PRs; CI/CD with smoke tests; secret scanning with push protection.

---

## Verified test results at the time of writing

*These are the Phase 0 results (2026-10-23). Current results: [Phase 1 report §4](phase-1-report.md), [Phase 2 report §5](phase-2-report.md).*

| Suite | Result |
|---|---|
| Aggregator (`aggregator/tests`) | **55 passed** |
| Gate (`gate/tests`, run in `python:3.12-slim`) | **21 passed** |
| Responsive check (`tests/responsive`, 14 pages × 7 widths) | **PASS, 98/98** |
| End-to-end survey submission (`tests/e2e`, local, gate off) | **PASS** on LimeSurvey 7.5.1 |
| Gate in a real browser, HTTPS, full flow | *Update 2026-10-24:* passed on staging on a phone (response 5, bot check solved in about 3 s). Originally: not yet run; the widget was verified solving a challenge in a secure context; the full flow will be confirmed in staging. |
