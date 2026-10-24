#!/usr/bin/env bash
# Run on the staging droplet (sudo). Creates two databases on the host MariaDB,
# each with its own user that can reach only its own database, and only from
# the Docker networks. Passwords come from /opt/itv/.env and are never printed.
set -euo pipefail
cd "$(dirname "$0")/../.."
set -a; . ./.env; set +a

mariadb <<SQL
CREATE DATABASE IF NOT EXISTS \`${WP_DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS \`${LS_DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${WP_DB_USER}'@'172.%' IDENTIFIED BY '${WP_DB_PASSWORD}';
CREATE USER IF NOT EXISTS '${LS_DB_USER}'@'172.%' IDENTIFIED BY '${LS_DB_PASSWORD}';
ALTER USER '${WP_DB_USER}'@'172.%' IDENTIFIED BY '${WP_DB_PASSWORD}';
ALTER USER '${LS_DB_USER}'@'172.%' IDENTIFIED BY '${LS_DB_PASSWORD}';
GRANT ALL PRIVILEGES ON \`${WP_DB_NAME}\`.* TO '${WP_DB_USER}'@'172.%';
GRANT ALL PRIVILEGES ON \`${LS_DB_NAME}\`.* TO '${LS_DB_USER}'@'172.%';
DELETE FROM mysql.user WHERE User = '';
DROP DATABASE IF EXISTS test;
FLUSH PRIVILEGES;
SQL
echo "Host databases ready: ${WP_DB_NAME} (user ${WP_DB_USER}), ${LS_DB_NAME} (user ${LS_DB_USER})."
