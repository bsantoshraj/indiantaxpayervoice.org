#!/usr/bin/env bash
# Deploy this repository to the staging droplet created by
# infra/terraform/staging. Idempotent: secrets are generated on the droplet on
# first run and never copied off it. Usage: scripts/deploy-staging.sh <ip>
set -euo pipefail
cd "$(dirname "$0")/.."
ip="${1:?usage: deploy-staging.sh <droplet-ip>}"
target="deploy@${ip}"
ssh_opts=(-o StrictHostKeyChecking=accept-new)

echo "Waiting for cloud-init on ${ip}…"
ssh "${ssh_opts[@]}" "$target" 'cloud-init status --wait >/dev/null; docker --version'

echo "Syncing code…"
rsync -az --delete -e "ssh ${ssh_opts[*]}" \
  --exclude .git --exclude .env --exclude 'var/' --exclude node_modules \
  --exclude '.terraform/' --exclude '*.tfstate*' --exclude terraform.tfvars \
  --exclude __pycache__ --exclude .pytest_cache --exclude public-stats \
  ./ "$target:/opt/itv/"

ssh "${ssh_opts[@]}" "$target" bash -s -- "$ip" <<'REMOTE'
set -euo pipefail
ip="$1"
cd /opt/itv
if [[ ! -f .env ]]; then
  ./scripts/init-local-env.sh
  ./infra/staging/configure-env.sh "$ip"
fi
sudo ./infra/staging/setup-host-db.sh
command -v age >/dev/null || sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq age >/dev/null
sudo install -m 644 infra/staging/itv-backup.cron /etc/cron.d/itv-backup   # daily encrypted DB backup
[[ -f var/certs/server.crt ]] || ./scripts/make-local-certs.sh "$ip" >/dev/null   # nginx's optional :8443 listener
docker compose build -q
docker compose up -d
echo "Waiting for LimeSurvey…"
for _ in $(seq 1 60); do curl -fs -o /dev/null http://127.0.0.1:8081/index.php/admin/authentication/sa/login && break; sleep 5; done
set -a; . ./.env; set +a
[[ -n "${ITV_LS_SURVEY_ID:-}" ]] || ./scripts/setup-local-survey.sh
set -a; . ./.env; set +a
docker compose up -d   # pick up ITV_LS_SURVEY_ID
docker compose run --rm wpcli bash /bootstrap.sh | tail -1
docker compose ps --format '{{.Service}}: {{.Status}}'
REMOTE
