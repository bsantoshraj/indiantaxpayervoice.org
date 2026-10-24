# Indian Taxpayer Voice — Website, Survey Platform, Security and Elastic Infrastructure

## 1. Your role

Act as a principal cloud architect, senior WordPress engineer, survey-platform specialist, security engineer, DevOps engineer, SEO strategist and privacy-conscious data architect.

Design and implement a production-ready digital platform for **Indian Taxpayer Voice**, a public-interest initiative intended to collect evidence about Indian taxpayers' concerns, understand gaps in employment and health-related financial protection, and publish transparent, evidence-based research.

The platform must be secure, responsive, accessible, SEO-optimized, measurable, privacy-conscious and capable of scaling as public participation grows.

Do not start by building a custom survey engine. We have selected **LimeSurvey** for survey creation and response collection.

## 2. Confirmed product decisions

Use these as fixed decisions unless a technical incompatibility is identified:

- Initiative name: Indian Taxpayer Voice.
- Tagline: “We contribute. We deserve a voice.”
- Primary domain: `indiantaxpayervoice.org`.
- Secondary domain: `indiantaxpayervoice.in`, intended to redirect to the primary domain after registration and configuration.
- Public website: WordPress.
- Survey platform: LimeSurvey, preferably self-hosted initially.
- Survey data: Stored separately from WordPress content and WordPress's database.
- Survey analytics: A separate, privacy-preserving aggregation and reporting layer.
- Hosting preference: Evaluate DigitalOcean first, but compare suitable managed alternatives where they materially improve resilience, security or cost.
- Environments (confirmed by the owner): **local** (Docker Compose on the owner's development VM, built first), **staging** on DigitalOcean, and **production** on DigitalOcean. Staging must not contain real survey data. Production-only protections, such as the survey bot challenge (section 4F), must also be enabled in staging, so that they are tested before release. Only local development may disable them.
- Infrastructure principle: Elasticity and the ability to increase or reduce capacity without redesigning the system.
- Initial deployment principle: Avoid Kubernetes, Kafka and unnecessary microservices until measurable demand justifies them.
- Governance principle: Non-partisan, democratic, transparent and evidence-based.
- Research principle: Do not present a voluntary online survey as statistically representative of India's population unless a defensible sampling design supports that conclusion.
- Funding principle: Do not claim to provide insurance or underwrite risk. Any future insurance arrangement must involve appropriately licensed entities and be legally reviewed.

Do not claim that the initiative is a registered NGO, has members, has achieved survey participation targets or has secured benefits unless verified facts are supplied.

## 3. Begin by inspecting the existing environment

Before changing files or deploying anything:

1. Inspect the repository, current WordPress installation if accessible, existing hosting configuration, domain setup, DNS, TLS, reverse proxy/CDN, CI/CD, environment variables and existing analytics.
2. Identify which components already exist and which are only planned.
3. Identify existing DigitalOcean resources and avoid unnecessary duplication.
4. Inspect the repository's structure, deployment procedures, existing code, security posture and documentation.
5. Never print secrets, private keys, access tokens, passwords or database credentials into logs or reports.
6. Never change production DNS, delete resources, overwrite production data or deploy a breaking change without explicit authorization.
7. Produce an architecture proposal, data-flow diagram, security assessment, cost assumptions and phased implementation plan before making material changes.
8. Clearly separate verified observations from assumptions.

If access to an environment is unavailable, explain what cannot be inspected and provide reproducible commands or configuration examples for the owner to run.

## 4. Target architecture

Design the following logical components.

### A. Public website — WordPress

Responsibilities:

- Homepage and initiative introduction.
- Mission, principles and methodology.
- Research reports, articles and policy analysis.
- Survey landing pages and calls to action.
- Frequently asked questions.
- Contact and volunteer-interest forms, if implemented.
- Privacy notice, terms and accessibility statement.
- Public statistics and heat-map visualizations.
- SEO, editorial workflows and campaign landing pages.

Requirements:

- Responsive design, mobile-first. Many participants will arrive on phones from social media, so every page, the survey and every statistic must work fully on small screens — not as a reduced version of the desktop site. Specifically:
  - Support viewport widths from 320px (small phones) to 1920px (large desktops), including tablets in both orientations.
  - No page may scroll horizontally at any supported width. Wide content, such as data tables, scrolls inside its own labelled, keyboard-focusable container instead of widening the page.
  - Interactive targets are at least 24×24 CSS pixels (WCAG 2.2 SC 2.5.8); primary actions, such as "Take the survey", should be larger.
  - Body text is at least 16px and no visible text is smaller than 12px; text reflows at 400% zoom without loss of content (WCAG SC 1.4.10).
  - The primary survey call to action remains reachable on every screen size, including inside the mobile navigation menu.
  - Maps, heat maps and charts adapt to narrow screens and always offer an equivalent table.
  - Respect `prefers-reduced-motion`; do not rely on hover for any information or function.
  - Verify responsiveness with an automated check across the supported widths before each release, in addition to manual testing on real devices.
- Semantic HTML and accessible navigation.
- Gutenberg compatibility.
- Fast page delivery using CDN caching.
- Minimal, trusted plugins and a documented update process.
- Separate administrative accounts, MFA and least-privilege permissions.
- No survey response database credentials in WordPress.
- No unrestricted access from WordPress to individual survey responses.
- Persistent media storage where required by the hosting architecture.
- A staging environment that does not contain real survey data.

### B. Survey platform — LimeSurvey

Use LimeSurvey rather than writing a new survey engine.

Evaluate the currently supported LimeSurvey Community Edition deployment model, PHP/runtime requirements, supported database engines, license, update policy and persistent-storage requirements.

Responsibilities:

- Questionnaire creation and versioning.
- Anonymous or appropriately pseudonymous survey responses.
- Question validation and conditional logic.
- Survey consent and introductory text.
- Response exports for authorized research staff.
- Survey closure and version-specific methodology records.

Requirements:

- Deploy LimeSurvey separately from WordPress.
- Prefer a dedicated survey subdomain, such as `survey.indiantaxpayervoice.org`, subject to final security and hosting decisions.
- Do not assume the survey service is fully serverless.
- Assess whether the selected platform supports multiple replicas, shared persistent storage, session handling and concurrent response writes.
- Ensure all application instances use compatible configuration and persistent data.
- Keep database credentials, application secrets and private exports out of source control.
- Restrict administrative access.
- Test upgrades, backups, restoration and concurrent survey submissions.
- Verify that the selected license permits the intended use and any planned modifications.
- Protect the survey against automated or programmatic stuffing as described in section 4F.

Do not assume LimeSurvey's database schema is a stable public integration API. Prefer supported exports, documented APIs or a controlled read-only integration.

### C. Separate analytics and aggregation layer

Create a small, independently deployable service or scheduled processing job for generating public statistics.

Responsibilities:

- Count valid survey submissions.
- Count represented states and union territories.
- Aggregate concerns by state and industry.
- Calculate response percentages and time-based trends.
- Generate approved public datasets.
- Record survey versions and aggregation timestamps.
- Provide public counters and heat-map data without exposing individual records.

The aggregation service must not require WordPress to read raw survey records.

Prefer a read-only integration or a restricted database account with access only to the necessary tables and fields. If the required LimeSurvey integration is not supported directly, use an approved export or API workflow.

### D. Public statistics API

Implement a separate read-only API, or an equivalent static-data publishing mechanism, for approved aggregates.

Proposed endpoints:

- `GET /v1/statistics/summary`
- `GET /v1/statistics/states`
- `GET /v1/statistics/industries`
- `GET /v1/statistics/trends`
- `GET /health/live`
- `GET /health/ready`

Adapt the design to the chosen implementation and avoid exposing sensitive operational information in health endpoints.

Requirements:

- No public endpoint may return raw survey responses, contact information, precise timestamps that identify respondents, internal record identifiers or unreviewed free text.
- Validate parameters and restrict expensive queries.
- Use caching and precomputed aggregates.
- Support API versioning and rate limiting.
- Do not expose database credentials or direct database connectivity.
- Suppress small groups and combinations that could identify individuals.
- Do not treat a minimum group size alone as a guarantee of anonymity.

### E. Infrastructure

Evaluate these components:

- CDN and WAF.
- DDoS and bot protection.
- WordPress hosting.
- LimeSurvey application hosting.
- Managed relational database.
- Persistent object storage or supported persistent volumes.
- Background job processing.
- Public statistics caching.
- Centralized logs and security monitoring.
- Encrypted backups and a recovery environment.

Start with the simplest architecture that meets tested requirements. Do not introduce Kubernetes, Kafka, a service mesh or a distributed database unless measured workload or reliability requirements justify them.

### F. Survey integrity and anti-stuffing

*Added after initial scoping, at the owner's request: responses must not be stuffed or programmatically influenced.*

No single control can prove that a respondent is a unique human without collecting identity, which conflicts with anonymity. Use layered controls that raise the cost of automated submissions, and say so publicly:

1. **Bot challenge before the survey (both layers confirmed):**
   - **ALTCHA**, self-hosted, open-source proof of work. This runs in a small gate service in front of LimeSurvey, so LimeSurvey's code is not modified. A solved challenge issues a signed, short-lived, HttpOnly pass that allows only a bounded number of survey requests, so each further automated submission needs a new proof of work. Challenges are single-use, and the gate fails closed.
   - **Cloudflare Turnstile** at the edge in production, when Cloudflare is the CDN/WAF, verified server-side by the same gate. List Cloudflare as a data processor in the privacy notice, because it sees visitor IP addresses.
   - Do not use LimeSurvey's built-in image CAPTCHA. It has no accessible alternative, and bots read it easily.
2. **Rate limiting** of survey requests per network address at the reverse proxy or edge. Set limits generously, because Indian mobile carriers place many users behind shared IP addresses (CGNAT).
3. **Response-quality flags in the aggregator:** implausibly fast completion, bursts of identical answer patterns, and a hidden honeypot field. **Decision: flag and log only during the pilot.** Choose exclusion rules once real completion-time data exists. Any rule that later excludes responses must be published on the methodology page, together with the number of responses excluded.
4. **Escalation option, if stuffing is detected:** one-time survey links sent after email or phone verification, with responses kept anonymised and unlinkable to the invitation. This adds friction and requires collecting contact data, so it needs a separate decision and a privacy review.

The challenge must remain keyboard- and screen-reader-accessible and must work on low-end phones. Monitor gate failure rates and survey drop-off at the gate.

**Per environment:** the gate is controlled by `ITV_GATE_ENABLED`. It may be `0` only when `ITV_ENV=local`, and it refuses to start disabled in staging or production. The proof-of-work check needs a browser secure context (HTTPS), which the DigitalOcean load balancer or Cloudflare provides in staging and production. Locally, test the gate over HTTPS using `scripts/make-local-certs.sh`.

## 5. Elasticity and capacity planning

The platform must accommodate organic growth and sudden surges caused by news coverage, social media campaigns, search visibility or public interest.

Design for two independent scaling domains:

1. Public website delivery.
2. Survey ingestion and survey administration.

The survey application must not depend on WordPress being available.

Requirements:

- CDN-cache public articles, images, scripts and other cacheable assets.
- Use stateless application instances wherever the software supports that model.
- Define configurable minimum and maximum application instance counts.
- Use autoscaling only on hosting plans and workloads that actually support it.
- Document scaling triggers, cooldowns and maximum capacity.
- Identify components that do not scale automatically, especially the database and persistent storage.
- Use database connection pooling or another tested connection-management strategy.
- Set connection limits, query timeouts and resource safeguards.
- Precompute heat maps and statistics rather than calculating them for every visitor.
- Use a durable queue only where it is needed and supported.
- If a queue is introduced, implement retries, idempotency, back-pressure and dead-letter handling.
- Do not confirm a survey response as accepted until it has been durably stored according to the chosen design.
- Never silently discard accepted responses during an overload.
- Protect survey submissions from duplicate records caused by retries or network timeouts.
- Configure provider spending alerts and resource limits.
- Document graceful degradation when traffic exceeds tested capacity.
- Keep the submission pathway functional where possible while temporarily reducing nonessential analytics work.

Produce capacity estimates for these illustrative scenarios:

| Scenario | Daily visitors | Daily survey submissions |
|---|---:|---:|
| Pilot | 1,000 | 100 |
| Initial traction | 10,000 | 1,000 |
| Growth | 100,000 | 10,000 |
| Major campaign | 1,000,000 | 100,000 |

These are planning scenarios, not traffic forecasts or performance guarantees.

For each scenario, estimate:

- Peak requests per second.
- Expected concurrent sessions and submissions.
- Application instances and memory/CPU assumptions.
- Database connection requirements.
- Database and backup storage growth.
- Network and bandwidth requirements.
- Cache hit-rate assumptions.
- Monthly infrastructure cost ranges in INR.
- Likely bottlenecks and scaling actions.

State the assumptions clearly. Validate the model through load testing instead of presenting theoretical capacity as guaranteed performance.

Do not multiply average daily traffic into peak load without explaining the assumed peak factor. Consider both gradual traffic ramps and abrupt viral surges.

## 6. Survey content and methodology

Design an initial questionnaire that measures concerns without assuming the initiative's conclusions.

Potential questions:

- State or union territory.
- Broad industry or employment sector.
- Main concern or concerns.
- Perceived gaps in job-loss protection.
- Concerns about access to health insurance or medical-expense protection.
- Availability of emergency savings, using broad ranges only if justified.
- Top three improvements respondents would prioritize.
- Optional free-text comments.
- Optional and separately consented interest in receiving updates.

*Added after initial scoping, at the owner's request:* income and gender may influence which concerns people report, so the questionnaire also includes these optional demographic questions. Each uses broad bands and offers "Prefer not to say":

- Annual individual income band, before tax, using broad ranges aligned to tax thresholds (currently up to ₹4 lakh, ₹4–12 lakh, ₹12–24 lakh, ₹24–50 lakh, ₹50 lakh–₹1 crore, and above ₹1 crore; ₹50 lakh and ₹1 crore are the income-tax surcharge thresholds, added at the owner's request on 2026-10-24). Re-check the bands against the slabs in force before each survey version.
- Gender: woman, man, another gender identity, or prefer not to say.
- Age band.
- Employment type, such as salaried private, salaried government, self-employed, or contract/gig. This bears directly on job-loss protection.

Publish each demographic question only on its own, against the concern list. Never cross demographic questions with state/UT or with each other, and apply the same small-cohort suppression to them. An unanswered optional question is published as "Not answered", which is distinct from "Prefer not to say". Before launch, re-validate the full question set with a methodologist, so that every question is justified by the research purpose and nothing is needlessly intrusive.

Do not require respondents to disclose:

- PAN or Aadhaar.
- Tax returns.
- Exact salary.
- Bank account information.
- Employer name.
- Medical records.
- Precise home address.
- Other information that is unnecessary for the research purpose.

Make clear that participation is voluntary, the questionnaire is not an official government survey, and participation does not guarantee financial or insurance benefits.

Include a survey methodology page describing:

- Survey purpose and dates.
- Questionnaire version.
- Recruitment channels.
- Eligibility and validation rules.
- Response cleaning and duplicate-handling methodology.
- Limitations and potential selection bias.
- How percentages are calculated.
- How invalid or incomplete submissions are treated.
- When aggregated data was last refreshed.

Do not claim that survey findings represent all Indian taxpayers merely because participation is high.

## 7. Public engagement and analytics

The homepage should help visitors understand the initiative and participate without making unsupported claims.

Potential public counters:

- Valid survey responses.
- States and union territories represented.
- Industries represented.
- Reports published.
- Volunteers expressing interest, if that workflow is implemented and the metric can be reliably verified.

Every counter must have a defined data source, calculation method and refresh interval. Display zero or unavailable states honestly. Do not use fabricated numbers or simulated production data.

Private analytics should measure:

- Search impressions and clicks through Search Console.
- Website sessions and landing-page traffic.
- Referrals and campaign attribution.
- Survey starts and completions where technically measurable.
- CTA click-through rates.
- Drop-off points.
- Response volume by date.
- Traffic and conversion trends.

Use platform-native analytics or documented integrations where appropriate. Do not claim that Google Analytics automatically supplies organic social-platform impressions. Respect consent and applicable privacy requirements for tracking technologies.

For every metric, distinguish website engagement from actual survey submissions.

## 8. State and industry heat maps

Build an accessible India state/UT map and an industry-versus-concern heat map.

Requirements:

- Use a properly licensed map asset.
- Make the map keyboard-accessible and provide a tabular alternative.
- Provide filters and explanatory tooltips.
- Allow users to understand counts, percentages and denominators.
- Distinguish respondent-reported state from approximate analytics geolocation.
- Do not infer respondents' states from IP addresses when they can select their own state.
- Clearly label the survey's voluntary nature and limitations.
- Configure a minimum cohort threshold, initially 20 responses, with a privacy review before launch.
- Suppress or combine small groups where needed.
- Consider differencing risks from successive filter combinations and updates.
- Avoid displaying precise respondent-level locations.
- Document how multi-select questions affect percentage totals.
- Never invent data for a map or fill missing regions with fabricated values.
- Show insufficient data distinctly from zero responses.

Use cached, precomputed aggregates. Public visitors must never trigger unrestricted raw-data queries.

## 9. Security and privacy baseline

Treat the collected information as potentially sensitive, particularly free-text responses and contact details.

Implement and document:

- HTTPS and secure cookie settings.
- Secrets management.
- Encryption at rest where supported and TLS in transit.
- Least-privilege accounts.
- MFA for administrative access.
- Restricted database connectivity.
- Input validation and output encoding.
- CSRF protection where applicable.
- Rate limiting and abuse detection.
- Secure session handling.
- Dependency and vulnerability scanning.
- WordPress plugin and theme review.
- Audit logging for administrative access and data exports.
- Restricted access to raw responses.
- Separation of survey responses from contact subscriptions.
- Protection against spreadsheet formula injection in CSV exports.
- Data retention and deletion procedures.
- Encrypted, isolated backups.
- Periodic restoration tests.
- Incident response and escalation procedures.
- Development, staging and production separation.
- A process for reviewing and redacting identifying information in free-text responses.

Do not log full survey payloads, secrets, contact details or unnecessary personal information.

Use a recognized application security verification framework such as OWASP ASVS as a starting point for testing custom application code.

Create a privacy notice, consent flow where required, data inventory, retention schedule, processor/vendor inventory and breach-response procedure. Obtain appropriate legal review of applicable Indian data-protection requirements and their commencement dates before launch.

Do not assume a hashed identifier is anonymous or that collecting consent alone makes unnecessary data collection acceptable.

## 10. WordPress design and SEO

Create a modern, professional and trustworthy civic-research design.

The visual identity should be neutral, accessible and non-partisan. Avoid party symbols, inflammatory claims, fabricated endorsements and misleading social-proof counters.

Build or configure:

- Homepage.
- Mission and principles.
- Participate in the survey.
- Job-loss protection research.
- Health-related financial protection research.
- Public spending and accountability research.
- Research and articles.
- Survey methodology.
- Public statistics.
- Frequently asked questions.
- Contact.
- Privacy policy.
- Terms of use.
- Accessibility statement.

Implement:

- Responsive, mobile-first layouts meeting the requirements in section 4A.
- Semantic HTML.
- WCAG 2.2 AA-oriented accessibility testing.
- Fast loading and image optimization.
- Canonical URLs.
- XML sitemap and robots directives.
- Appropriate structured data only where truthful and applicable.
- Internal linking and useful metadata.
- Search Console verification instructions.
- Open Graph metadata.
- Clear editorial authorship and source references.
- A process for correcting or updating published research.

Do not keyword-stuff or make claims unsupported by published evidence.

## 11. Operational readiness

Produce:

- Architecture diagram.
- Data-flow diagram.
- Threat model.
- Component and dependency inventory.
- Infrastructure-as-code or reproducible deployment instructions.
- Environment variable template containing placeholders only.
- CI/CD workflow.
- Database backup and recovery procedure.
- Application and dependency update procedure.
- Monitoring dashboard specification.
- Alert thresholds.
- Incident response runbook.
- Rollback procedure.
- Cost estimate and scaling guide.
- Administrator documentation.
- Survey operator documentation.
- Public methodology and privacy documentation.

Implement automated tests for the survey/statistics integration and any custom code.

Include tests for:

- Invalid and oversized survey submissions.
- Concurrent submissions.
- Retry and duplicate behavior.
- Authorization boundaries.
- Attempts to retrieve raw data through public endpoints.
- Survey-integrity controls: bypassing the bot challenge, replaying a solved challenge, forged or expired passes, open redirects from the gate, and rate limits.
- Small-cohort suppression.
- Aggregation correctness.
- Database failures.
- Cache invalidation.
- Backup restoration.
- Traffic spikes and resource exhaustion.
- Accessibility and mobile usability, including horizontal-overflow, tap-target and minimum-font-size checks at 320, 375, 414, 768, 1024, 1366 and 1920px widths for every public page and the survey.
- SEO basics.

## 12. Implementation phases

### Phase 0 — Audit and architecture

Inspect the existing repository and infrastructure. Identify decisions requiring confirmation, estimate costs, and provide the architecture and threat model.

Do not deploy or modify production resources during this phase without authorization.

### Phase 1 — Secure public website and survey pilot

- Configure the WordPress site.
- Deploy and harden LimeSurvey.
- Configure domain, TLS and CDN/WAF.
- Build the first questionnaire.
- Define retention and consent practices.
- Establish database backups and monitoring.
- Create methodology, privacy and terms pages.
- Test the entire response-collection workflow.

### Phase 2 — Aggregation and public statistics

- Implement a controlled LimeSurvey integration.
- Generate precomputed aggregate statistics.
- Build the public statistics API or static data publishing mechanism.
- Add public counters and heat maps.
- Implement suppression and privacy tests.
- Document metric definitions and refresh intervals.

### Phase 3 — Elasticity and resilience

- Configure autoscaling where supported.
- Test connection pooling and database capacity.
- Implement queueing only where justified.
- Load-test all major workloads.
- Validate cost alerts, maximum capacity, recovery and graceful degradation.

### Phase 4 — Growth and research operations

- Improve search visibility and editorial workflows.
- Add campaign attribution and survey conversion analysis.
- Improve research reporting.
- Review capacity, privacy and security using actual traffic and survey data.

## 13. How to work

Work incrementally and show your reasoning through concise, documented engineering decisions—not hidden assumptions.

For each phase:

1. Explain the design and important trade-offs.
2. Identify what you inspected and what remains unknown.
3. Provide the relevant implementation or configuration.
4. Run available tests and report actual results.
5. Document security implications and operational costs.
6. Identify anything requiring manual action, credentials, approval or external account setup.

Do not claim tests, scans, backups, deployments or security checks succeeded unless they were actually executed and their results verified.

Do not place credentials in source code or commit real `.env` files.

Do not create fake survey responses, public metrics or testimonials.

Do not provision paid infrastructure or change production resources without explicit approval.

## 14. First deliverable

Start with the repository and environment audit, then provide:

1. Existing-state findings.
2. Proposed target architecture.
3. Component-by-component deployment plan.
4. Recommended LimeSurvey hosting model and its persistent-storage requirements.
5. WordPress-to-survey integration design.
6. Security and privacy threat model.
7. Capacity and monthly cost estimates for all four traffic scenarios.
8. Main risks, assumptions and unresolved decisions.
9. A phased implementation plan with acceptance criteria.

Wait for approval before making material production changes. Once approved, implement the first phase and verify it before proceeding.
