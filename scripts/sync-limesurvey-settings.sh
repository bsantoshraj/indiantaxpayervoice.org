#!/usr/bin/env bash
# Local and staging: keep LimeSurvey's admin contact settings in step with .env
# (they are otherwise set only at install). Idempotent; run on every deploy.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a

email=${LS_ADMIN_EMAIL:?LS_ADMIN_EMAIL is not set}
[[ "$email" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]] || { echo "LS_ADMIN_EMAIL is not an email address" >&2; exit 1; }
[[ "$LS_ADMIN_USER" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "unexpected LS_ADMIN_USER" >&2; exit 1; }

if [[ "${LS_DB_HOST:-ls-db}" == "host.docker.internal" ]]; then
  sql() { sudo mariadb -N "$LS_DB_NAME"; }   # staging: MariaDB on the host
else
  sql() { docker compose exec -T ls-db sh -c 'MYSQL_PWD=$MARIADB_ROOT_PASSWORD mariadb -uroot -N limesurvey'; }
fi

sql <<SQL
UPDATE lime_users SET email = '${email}' WHERE users_name = '${LS_ADMIN_USER}';
INSERT INTO lime_settings_global (stg_name, stg_value) VALUES
  ('siteadminemail', '${email}'), ('siteadminbounce', '${email}'), ('siteadminname', 'Indian Taxpayer Voice')
  ON DUPLICATE KEY UPDATE stg_value = VALUES(stg_value);
SQL
echo "LimeSurvey admin contact: ${email}"
