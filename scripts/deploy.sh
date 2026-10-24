#!/usr/bin/env bash
# Deploy this working tree to an environment's droplet from the admin machine.
# Normally CI deploys (.github/workflows/ci.yml); this is the manual path and the
# first-time setup of a new droplet. Secrets are generated on the droplet on the
# first run and never copied off it.
#   scripts/deploy.sh <staging|production>
#   IMAGE_TAG=<main commit sha> scripts/deploy.sh production   # pull CI images from GHCR
# Without IMAGE_TAG the images are built on the droplet (slow; PyPI is unreliable
# from blr1).
set -euo pipefail
cd "$(dirname "$0")/.."
env="${1:?usage: deploy.sh <staging|production>}"
[[ "$env" == staging || "$env" == production ]] || { echo "environment must be staging or production" >&2; exit 2; }
domain=indiantaxpayervoice.org
ip=$(terraform -chdir="infra/terraform/$env" output -raw ip)
target="deploy@${ip}"
ssh_opts=(-o StrictHostKeyChecking=accept-new -o ServerAliveInterval=15)

# Cloudflare Access settings for this environment's admins (not secret).
cf=infra/terraform/cloudflare
access_vars=()
if [[ -f "$cf/terraform.tfstate" ]]; then
  read -r admin_host audiences < <(terraform -chdir="$cf" output -json | python3 -c '
import json, sys; o = json.load(sys.stdin); e = sys.argv[1]
print(o["hosts"]["value"][e]["survey_admin"], o["access_audiences"]["value"][e])' "$env")
  access_vars=("SURVEY_ADMIN_HOST=$admin_host" "ITV_ACCESS_AUD=$audiences"
               "ITV_ACCESS_TEAM_DOMAIN=$(terraform -chdir="$cf" output -raw access_team_domain)"
               "ITV_ACCESS_ALLOWED_EMAILS=$(terraform -chdir="$cf" output -raw survey_admin_emails)")
else
  echo "Warning: no Cloudflare Terraform state; the admins will refuse all requests." >&2
fi

echo "Deploying to $env ($ip)…"
ssh "${ssh_opts[@]}" "$target" 'cloud-init status --wait >/dev/null; docker --version'

# Origin certificate (Cloudflare Origin CA, *.domain + apex), kept on the admin
# machine in ~/itv and on each droplet in var/origin-tls; never in git.
ssh "${ssh_opts[@]}" "$target" 'test -s /opt/itv/var/origin-tls/origin.pem' 2>/dev/null || {
  echo "Installing the origin certificate…"
  ssh "${ssh_opts[@]}" "$target" 'sudo install -d -o deploy -g deploy -m 755 /opt/itv && install -d -m 700 /opt/itv/var/origin-tls'
  scp -q "${ssh_opts[@]}" ~/itv/itv.crt "$target:/opt/itv/var/origin-tls/origin.pem"
  scp -q "${ssh_opts[@]}" ~/itv/itv.key "$target:/opt/itv/var/origin-tls/origin.key"
  ssh "${ssh_opts[@]}" "$target" 'chmod 644 /opt/itv/var/origin-tls/origin.pem; chmod 600 /opt/itv/var/origin-tls/origin.key'
}

echo "Syncing code…"
rsync -az --delete -e "ssh ${ssh_opts[*]}" --exclude-from=infra/staging/rsync-excludes.txt ./ "$target:/opt/itv/"

bootstrap="ITV_BOOTSTRAP_ENV=$env ITV_BOOTSTRAP_DOMAIN=$domain"
if [[ -n "${IMAGE_TAG:-}" ]]; then
  [[ "$IMAGE_TAG" =~ ^[0-9a-f]{40}$ ]] || { echo "IMAGE_TAG must be a full commit SHA" >&2; exit 2; }
  # Short-lived use of your GitHub CLI token to pull from GHCR; not stored on the droplet.
  gh auth token | ssh "${ssh_opts[@]}" "$target" "$bootstrap /opt/itv/infra/staging/remote-deploy.sh --image-tag $IMAGE_TAG ${access_vars[*]}"
else
  ssh "${ssh_opts[@]}" "$target" "$bootstrap /opt/itv/infra/staging/remote-deploy.sh ${access_vars[*]}"
fi

hosts=$(ssh "${ssh_opts[@]}" "$target" "grep -E '^(WP_HOST|STATS_HOST)=' /opt/itv/.env | cut -d= -f2 | tr '\n' ' '")
# shellcheck disable=SC2086
./scripts/purge-cdn.sh $hosts || echo "Warning: Cloudflare cache not purged." >&2
