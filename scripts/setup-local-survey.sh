#!/usr/bin/env bash
# Local and staging: import and activate the v1 survey in LimeSurvey, enable the
# RemoteControl API, and create a least-privilege "stats-exporter" account for
# the aggregator. Writes ITV_LS_SURVEY_ID into .env. Secrets are never printed.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a

if [[ "${LS_DB_HOST:-ls-db}" == "host.docker.internal" ]]; then
  sql() { sudo mariadb -N "$LS_DB_NAME"; }   # staging: MariaDB on the host
else
  sql() { docker compose exec -T ls-db sh -c 'MYSQL_PWD=$MARIADB_ROOT_PASSWORD mariadb -uroot -N limesurvey'; }
fi

echo "Enabling RemoteControl (JSON-RPC)…"
sql <<'SQL'
INSERT INTO lime_settings_global (stg_name, stg_value) VALUES ('RPCInterface', 'json')
  ON DUPLICATE KEY UPDATE stg_value = 'json';
SQL

structure=$(mktemp)
trap 'rm -f "$structure"' EXIT
python3 survey/build_structure.py survey/questionnaire-v1.json >"$structure"
chmod 644 "$structure"   # survey structure only (no secrets); read by the container user

# RemoteControl is an admin route, which the public survey proxy refuses, so call
# LimeSurvey directly on the internal network from the aggregator image (it has
# Python and the route the aggregator already uses). Credentials come from .env.
echo "Importing and activating survey…"
sid=$(docker compose run --rm --no-deps -T \
      -v "$PWD/scripts/limesurvey_rpc.py:/rpc.py:ro" -v "$structure:/structure.txt:ro" \
      -e LS_URL=http://limesurvey:8080/index.php/admin/remotecontrol -e STRUCTURE=/structure.txt \
      -e REPLACE_SID="${ITV_LS_SURVEY_ID:-}" -e LS_ADMIN_USER -e LS_ADMIN_PASSWORD \
      --entrypoint python aggregator /rpc.py import-and-activate)
echo "Survey ID: $sid"

echo "Creating stats-exporter account (export permission on survey $sid only)…"
hash=$(printf '%s' "$ITV_LS_PASSWORD" | docker compose exec -T limesurvey \
  php -r 'echo password_hash(stream_get_contents(STDIN), PASSWORD_DEFAULT);')
sql <<SQL
DELETE p FROM lime_permissions p JOIN lime_users u ON u.uid = p.uid WHERE u.users_name = '${ITV_LS_USER}';
DELETE FROM lime_users WHERE users_name = '${ITV_LS_USER}';
INSERT INTO lime_users (users_name, password, full_name, parent_id, lang, email, created, modified, user_status)
  VALUES ('${ITV_LS_USER}', '${hash}', 'Statistics exporter', 1, 'en', '', NOW(), NOW(), 1);
SET @uid = LAST_INSERT_ID();
INSERT INTO lime_permissions (entity, entity_id, uid, permission, create_p, read_p, update_p, delete_p, import_p, export_p)
  VALUES ('global', 0, @uid, 'auth_db', 0, 1, 0, 0, 0, 0),
         ('survey', ${sid}, @uid, 'responses', 0, 1, 0, 0, 0, 1);
SQL

sed -i "s/^ITV_LS_SURVEY_ID=.*/ITV_LS_SURVEY_ID=${sid}/" .env
# Fingerprint of the questionnaire this survey was built from (deploys compare it).
hash=$(sha256sum survey/questionnaire-v1.json | cut -c1-64)
if grep -q '^ITV_LS_SURVEY_HASH=' .env; then sed -i "s/^ITV_LS_SURVEY_HASH=.*/ITV_LS_SURVEY_HASH=${hash}/" .env; else echo "ITV_LS_SURVEY_HASH=${hash}" >> .env; fi
./scripts/sync-limesurvey-settings.sh
echo "Done. Survey URL: ${LS_PUBLIC_URL}/index.php/${sid}?lang=en"
