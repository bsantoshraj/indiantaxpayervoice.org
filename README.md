# Indian Taxpayer Voice

An independent initiative that gives Indian taxpayers a voice: a public website, an
anonymous voluntary survey, and **aggregated, privacy-protected statistics** built from
it. Results describe the people who chose to respond; they are not statistically
representative of all taxpayers.

## Documentation

| Document | Read it to… |
|---|---|
| [Environments](docs/environments.md) | see every deliberate difference between dev, staging and production, and how to open the survey |
| [How it works](docs/how-it-works.md) | understand the components, how a survey response becomes a public statistic, and the privacy guarantees |
| [Development](docs/development.md) | run everything locally, run the tests, edit pages or the survey, and open a pull request |
| [CI/CD](docs/ci-cd.md) | ship a change, roll back, and understand what the pipeline can and cannot do |
| [Operating staging](docs/operations.md) | change infrastructure, manage Cloudflare and admins, back up and restore, rotate secrets, troubleshoot |
| [Phase 0 report](docs/phase-0-report.md) | see the architecture decisions, threat model, cost estimates and phase plan |
| [Owner backlog](docs/owner-backlog.md) | see the decisions, accounts, content and reviews waiting on the owner |
| [Phase 1 report](docs/phase-1-report.md) | see what is done, what was verified, and what remains before Phase 1 is complete |
| [Phase 2 report](docs/phase-2-report.md) | see the public statistics, map and heat maps, and what remains in Phase 2 |
| `claude.md` (private, not in this repository) | the full project brief and requirements, kept by the owner |

## Environments

| | Website | Survey | Statistics | LimeSurvey admin |
|---|---|---|---|---|
| **Local** | http://localhost:8080 | http://localhost:8081 | http://localhost:8082 | http://localhost:8083 |
| **Staging** | https://staging.indiantaxpayervoice.org | https://survey-staging.indiantaxpayervoice.org | https://stats-staging.indiantaxpayervoice.org | https://survey-admin-staging.indiantaxpayervoice.org (Cloudflare Access) |
| **Production** | https://indiantaxpayervoice.org | https://survey.indiantaxpayervoice.org (controlled release) | https://stats.indiantaxpayervoice.org | https://survey-admin.indiantaxpayervoice.org (Cloudflare Access) |

Staging deploys automatically when a pull request is merged into `main`; production is promoted from staging by a manual, approved CI run ([CI/CD](docs/ci-cd.md)).

## Quick start

```bash
./scripts/init-local-env.sh                        # .env with random secrets (never commit it)
docker compose up -d
docker compose run --rm wpcli bash /bootstrap.sh   # website pages and settings
./scripts/setup-local-survey.sh && docker compose up -d
```

Details, ports and tests: [docs/development.md](docs/development.md).

## Repository map

| Path | Contents |
|---|---|
| `wordpress/` | Theme (`themes/itv`), must-use plugins (`mu-plugins/`: statistics, SEO, hardening, publish relay), page content (`content/*.html`), `bootstrap.sh` |
| `research/` | Articles (one Markdown file each), their sources with checksums, extraction and chart scripts ([research/README.md](research/README.md)) |
| `survey/` | Questionnaire definition (`questionnaire-v1.json`, the single source of truth) and the LimeSurvey import builder |
| `aggregator/` | Export → validate → suppress → publish statistics (Python, standard library only) |
| `gate/` | Survey bot check and Cloudflare Access token verification (Python) |
| `infra/nginx/` | Survey proxy and statistics server configuration |
| `infra/staging/` | Caddy configuration and the on-droplet scripts: deploy, backups, restore test, secret rotation |
| `infra/terraform/` | `staging/` (droplet, firewall, keys) and `cloudflare/` (CDN rules, Access) |
| `scripts/` | Local setup, deploy fallback, smoke tests, CDN purge, key sync, backup pull, articles (`article.sh`, guide in [docs/articles.md](docs/articles.md)) |
| `tests/` | Browser tests: responsive layout and end-to-end survey submission |
| `.github/` | CI/CD workflow and Dependabot configuration |

## Contact

hello@indiantaxpayervoice.org
