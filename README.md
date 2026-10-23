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
