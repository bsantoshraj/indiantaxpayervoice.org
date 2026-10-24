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

echo "Importing and activating survey…"
sid=$(REPLACE_SID="${ITV_LS_SURVEY_ID:-}" LS_URL="http://127.0.0.1:${LS_PORT}/index.php/admin/remotecontrol" \
      STRUCTURE="$structure" python3 scripts/limesurvey_rpc.py import-and-activate)
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
echo "Done. Survey URL: ${LS_PUBLIC_URL}/index.php/${sid}?lang=en"
