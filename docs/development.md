# Development

Everything runs locally in Docker Compose, the same images as staging, with
MariaDB in containers instead of on the host.

## Prerequisites
Docker with Compose v2, Python 3.12 (for running tests outside Docker), and `gh`
for pull requests. Node 20 is only needed for the browser tests in `tests/`.

## First run

```bash
./scripts/init-local-env.sh                          # writes .env (mode 600) with random secrets; never commit it
docker compose up -d
docker compose run --rm wpcli bash /bootstrap.sh     # pages, menu, settings (idempotent)
./scripts/setup-local-survey.sh                      # import + activate the survey, create stats-exporter
docker compose up -d                                 # pick up ITV_LS_SURVEY_ID
```

| Service | Local address | Notes |
|---|---|---|
| Website | http://localhost:8080 | WordPress admin at `/wp-admin` (`WP_ADMIN_USER` / `WP_ADMIN_PASSWORD` in `.env`) |
| Survey (public proxy) | http://localhost:8081/index.php/&lt;survey id&gt; | The gate is off locally (`ITV_GATE_ENABLED=0`) |
| Survey over HTTPS | https://localhost:8443 | Needed to test the gate (browsers run the proof-of-work only in a secure context); certificates from `scripts/make-local-certs.sh` |
| LimeSurvey admin | http://localhost:8083 | Open locally (no Cloudflare Access); `LS_ADMIN_USER` / `LS_ADMIN_PASSWORD` |
| Statistics | http://localhost:8082/v1/statistics/summary | Refreshed every 5 minutes locally (`ITV_AGG_INTERVAL=300`; hourly on staging and production) |

`BIND_ADDR` in `.env` is `127.0.0.1` (this machine only) or `0.0.0.0` (your LAN,
plain HTTP). With `0.0.0.0`, set `WP_URL` and `LS_PUBLIC_URL` to the machine's LAN
address and re-run the bootstrap.

## Tests

```bash
(cd aggregator && python3 -m pytest -q)                                  # 67 tests, no dependencies
(cd gate && pip install -r requirements.txt pytest && python3 -m pytest -q)   # 38 tests
docker run --rm -v "$PWD:/mnt" -w /mnt koalaman/shellcheck:v0.10.0 -S warning scripts/*.sh infra/staging/*.sh
terraform fmt -check -recursive infra/terraform
```
CI runs all of these on every pull request (see [ci-cd.md](ci-cd.md)). Browser
tests: `tests/responsive` (14 pages × 7 widths) and `tests/e2e/survey_submit.mjs`
(fills in and submits the survey); see the comments at the top of each.

## Common tasks

**Edit a website page.** Page content lives in `wordpress/content/*.html` (block
markup) and is loaded by `wordpress/bootstrap.sh`; editing in wp-admin works too but
is overwritten by the next bootstrap. After editing a file:
`docker compose run --rm wpcli bash /bootstrap.sh`. New pages also need an entry in
the `pages` list in `bootstrap.sh`. The theme is `wordpress/themes/itv`.

**Articles.** Articles live in `research/articles/` (exported from the drafts doc with
`research/scripts/split_articles.py`). Load them into the local site as drafts with
`research/scripts/wp_article.sh drafts`; preview them under wp-admin › Posts. The
release flow to staging and production is in [ci-cd.md](ci-cd.md#publish-an-article-controlled-release).

**Change the survey.** The questionnaire is `survey/questionnaire-v1.json`; the
aggregator validates exports against it, so question and option codes must match
LimeSurvey's. `survey/build_structure.py` builds the LimeSurvey import from it.
Changing codes or adding questions needs aggregator test updates; follow the
methodology notes in `claude.md`. LimeSurvey cannot change an active survey's
questions or answer options, so a changed questionnaire means **replacing** the
survey, which deletes its responses. Locally: `./scripts/setup-local-survey.sh`
(replaces it), then `docker compose up -d`, the bootstrap, and
`docker compose run --rm aggregator --allow-drop`. On staging the pipeline does this
automatically (see [ci-cd.md](ci-cd.md#survey-changes)).

**Run the aggregator by hand.** `docker compose run --rm aggregator` (from LimeSurvey)
or with a CSV export: `docker compose run --rm -v "$PWD/export.csv:/in/export.csv:ro" aggregator --csv /in/export.csv`.

**Contact and admin emails.** `WP_ADMIN_EMAIL` and `LS_ADMIN_EMAIL` in `.env` are
applied on every bootstrap / `scripts/sync-limesurvey-settings.sh`.

## Making a change

`main` is protected: changes go through a pull request, and CI (tests, lint, both
image builds) must pass before merging. Merging deploys to staging automatically.

```bash
git switch -c my-change
# … edit, test locally …
git commit -am "Explain what and why"
git push -u origin my-change
gh pr create --fill          # CI runs; merge when green → staging deploy
```

Never commit secrets or keys. `.env`, Terraform state and certificates are
gitignored, and GitHub push protection blocks pushes that contain recognisable
secrets.
