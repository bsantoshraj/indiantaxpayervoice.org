#!/usr/bin/env bash
# Run on the staging droplet as deploy, after the code is synced to /opt/itv.
# Shared by scripts/deploy-staging.sh (manual) and CI (.github/workflows/ci.yml).
#   remote-deploy.sh [--image-tag <git-sha>] [KEY=VALUE ...]
# --image-tag: pull the gate and aggregator images built by CI from GHCR instead
#   of building here; a short-lived registry token is read from stdin and
#   discarded after the pull. KEY=VALUE pairs (never secrets) are written to .env.
set -euo pipefail
cd "$(dirname "$0")/../.."

image_tag=""
if [[ "${1:-}" == "--image-tag" ]]; then image_tag=${2:?missing tag}; shift 2; fi
ip=$(curl -fsS --max-time 5 http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address)

set_var() { if grep -q "^$1=" .env; then sed -i "s#^$1=.*#$1=$2#" .env; else echo "$1=$2" >> .env; fi; }
if [[ ! -f .env ]]; then
  ./scripts/init-local-env.sh
  ./infra/staging/configure-env.sh "$ip"
fi
for kv in "$@"; do set_var "${kv%%=*}" "${kv#*=}"; done
# The project's contact address replaces the original placeholders (not secret).
for var in WP_ADMIN_EMAIL LS_ADMIN_EMAIL; do
  if grep -q "^$var=admin@example.invalid$" .env; then set_var "$var" hello@indiantaxpayervoice.org; fi
done

sudo ./infra/staging/setup-host-db.sh
command -v age >/dev/null || sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq age >/dev/null
sudo install -m 644 infra/staging/itv-backup.cron /etc/cron.d/itv-backup   # daily encrypted DB backup
sudo install -m 755 infra/staging/ci-ssh-command.sh /usr/local/bin/itv-ci-ssh-command   # outside /opt/itv: CI cannot replace it
[[ -f var/certs/server.crt ]] || ./scripts/make-local-certs.sh "$ip" >/dev/null   # nginx's optional :8443 listener

if [[ -n "$image_tag" ]]; then
  set_var ITV_IMAGE_REPO ghcr.io/bsantoshraj/itv
  set_var ITV_IMAGE_TAG "$image_tag"
  DOCKER_CONFIG=$(mktemp -d); export DOCKER_CONFIG
  trap 'rm -rf "$DOCKER_CONFIG"' EXIT
  docker login ghcr.io -u ci --password-stdin >/dev/null 2>&1 || { echo "GHCR login failed" >&2; exit 1; }
  docker compose pull -q gate aggregator-cron
  docker compose --profile jobs pull -q aggregator
  docker logout ghcr.io >/dev/null 2>&1 || true
  docker compose up -d --no-build --remove-orphans
else
  set_var ITV_IMAGE_REPO itv
  set_var ITV_IMAGE_TAG local
  docker compose build -q
  docker compose up -d --remove-orphans
fi

# Config files are bind-mounted as single files. rsync replaces them with new
# files, but a running container keeps reading the old one until it restarts, so
# restart only the services whose config changed since the last deploy.
caddyfile=$(sed -n 's/^CADDYFILE=//p' .env); caddyfile=${caddyfile:-Caddyfile}
declare -A config=(
  [survey-proxy]="infra/nginx/survey.conf infra/nginx/survey-locations.inc"
  [stats]="infra/nginx/stats.conf"
  [caddy]="infra/staging/$caddyfile"
  [wordpress]="infra/php/zz-itv-hardening.ini"
  [limesurvey]="infra/php/zz-itv-hardening.ini"
)
mkdir -p var; touch var/deployed-config.sha256
for svc in "${!config[@]}"; do
  # shellcheck disable=SC2086  # word-split the file list on purpose
  sum=$(cat ${config[$svc]} | sha256sum | cut -c1-64)
  if ! grep -qx "$svc $sum" var/deployed-config.sha256; then
    echo "Config changed for $svc: restarting it"
    docker compose restart "$svc" >/dev/null
    sed -i "/^$svc /d" var/deployed-config.sha256; echo "$svc $sum" >> var/deployed-config.sha256
  fi
done

echo "Waiting for LimeSurvey…"   # the public proxy serves / ; admin routes are refused there
for _ in $(seq 1 60); do curl -fs -o /dev/null http://127.0.0.1:8081/ && break; sleep 5; done
set -a; . ./.env; set +a
# The survey is built from survey/questionnaire-v1.json. LimeSurvey cannot change
# answer options or questions of an active survey, so a changed questionnaire means
# replacing the survey, which deletes its responses: automatic on staging (test
# data only), refused anywhere else.
survey_hash=$(sha256sum survey/questionnaire-v1.json | cut -c1-64)
survey_replaced=0
if [[ -z "${ITV_LS_SURVEY_ID:-}" ]]; then
  ./scripts/setup-local-survey.sh; survey_replaced=1
elif [[ "${ITV_LS_SURVEY_HASH:-}" != "$survey_hash" ]]; then
  if [[ "${ITV_ENV:-}" != "staging" ]]; then
    echo "The questionnaire changed, but replacing the survey would delete its responses in ${ITV_ENV:-this environment}. Plan a migration; not replacing." >&2
    exit 1
  fi
  echo "Questionnaire changed: replacing staging survey ${ITV_LS_SURVEY_ID} (its test responses are deleted)…"
  ./scripts/setup-local-survey.sh; survey_replaced=1
fi
set -a; . ./.env; set +a
docker compose up -d --no-build   # pick up ITV_LS_SURVEY_ID
./scripts/sync-limesurvey-settings.sh
if (( survey_replaced )); then
  # The new survey starts empty; publish that instead of keeping the old counts.
  docker compose run --rm aggregator --allow-drop 2>&1 | grep -E "INFO rows|ERROR" | sed 's/.*INFO //' || true
fi
docker compose run --rm wpcli bash /bootstrap.sh | tail -1
docker compose ps --format '{{.Service}}: {{.Status}}'
