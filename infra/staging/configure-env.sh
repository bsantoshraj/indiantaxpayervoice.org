#!/usr/bin/env bash
# Run on the staging droplet after scripts/init-local-env.sh: turns the freshly
# generated .env (random secrets) into a staging configuration.
set -euo pipefail
cd "$(dirname "$0")/../.."
ip="${1:?usage: configure-env.sh <public-ip> [domain]}"
domain="${2:-}"
dashed="${ip//./-}"
# With a domain: staging., survey-staging., stats-staging. (one level deep, so a
# Cloudflare Universal SSL certificate can cover them if proxied later).
# Without one: sslip.io names that resolve to the IP.
if [[ -n "$domain" ]]; then
  wp_host="staging.${domain}"; survey_host="survey-staging.${domain}"; stats_host="stats-staging.${domain}"
else
  wp_host="wp.${dashed}.sslip.io"; survey_host="survey.${dashed}.sslip.io"; stats_host="stats.${dashed}.sslip.io"
fi
set_var() { if grep -q "^$1=" .env; then sed -i "s#^$1=.*#$1=$2#" .env; else echo "$1=$2" >> .env; fi; }

set_var ITV_ENV staging
set_var COMPOSE_FILE compose.yaml:compose.staging.yaml
set_var COMPOSE_PROFILES ""
set_var BIND_ADDR 127.0.0.1
set_var WP_DB_HOST host.docker.internal
set_var LS_DB_HOST host.docker.internal
set_var WP_HOST "$wp_host"
set_var SURVEY_HOST "$survey_host"
set_var STATS_HOST "$stats_host"
set_var WP_URL "https://${wp_host}"
set_var LS_PUBLIC_URL "https://${survey_host}"
# A real domain is proxied by Cloudflare and uses its Origin CA certificate.
if [[ -n "$domain" ]]; then set_var CADDYFILE Caddyfile.origin-ca; else set_var CADDYFILE Caddyfile; fi
set_var ITV_GATE_ENABLED 1
set_var ITV_GATE_SECURE_COOKIE 1
chmod 600 .env
echo "Staging .env configured: ${wp_host}, ${survey_host}, ${stats_host} (secrets not printed)."
