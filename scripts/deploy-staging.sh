#!/usr/bin/env bash
# Deploy this repository to the staging droplet created by
# infra/terraform/staging, building images on the droplet. Normally CI deploys
# (.github/workflows/ci.yml); this is the manual path. Idempotent: secrets are
# generated on the droplet on first run and never copied off it.
# Usage: scripts/deploy-staging.sh <ip>
set -euo pipefail
cd "$(dirname "$0")/.."
ip="${1:?usage: deploy-staging.sh <droplet-ip>}"
target="deploy@${ip}"
ssh_opts=(-o StrictHostKeyChecking=accept-new)

# Cloudflare Access settings for the LimeSurvey admin (not secret), from
# infra/terraform/cloudflare. Without them the admin hostname refuses everyone.
cf_tf=infra/terraform/cloudflare
access_vars=()
if [[ -f "$cf_tf/terraform.tfstate" ]]; then
  out() { terraform -chdir="$cf_tf" output -raw "$1"; }
  access_vars=("SURVEY_ADMIN_HOST=$(out staging_survey_admin_host)" "ITV_ACCESS_TEAM_DOMAIN=$(out access_team_domain)"
               "ITV_ACCESS_AUD=$(out staging_access_audiences)" "ITV_ACCESS_ALLOWED_EMAILS=$(out survey_admin_emails)")
else
  echo "Warning: no Cloudflare Terraform state; the LimeSurvey admin will refuse all requests." >&2
fi

echo "Waiting for cloud-init on ${ip}…"
ssh "${ssh_opts[@]}" "$target" 'cloud-init status --wait >/dev/null; docker --version'

echo "Syncing code…"
rsync -az --delete -e "ssh ${ssh_opts[*]}" --exclude-from=infra/staging/rsync-excludes.txt ./ "$target:/opt/itv/"

# Builds the images on the droplet; CI instead pulls images it built (--image-tag).
ssh "${ssh_opts[@]}" "$target" /opt/itv/infra/staging/remote-deploy.sh "${access_vars[@]}"

# New content must not wait for the edge cache (10 min for pages, 5 for stats).
hosts=$(ssh "${ssh_opts[@]}" "$target" "grep -E '^(WP_HOST|STATS_HOST)=' /opt/itv/.env | cut -d= -f2 | tr '\n' ' '")
# shellcheck disable=SC2086
./scripts/purge-cdn.sh $hosts || echo "Warning: Cloudflare cache not purged; pages may be up to 10 minutes stale." >&2
