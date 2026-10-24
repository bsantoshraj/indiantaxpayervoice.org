#!/usr/bin/env bash
# Replace the deploy user's authorized_keys on staging with the keys declared
# in infra/terraform/staging (this machine's key + extra_ssh_key_names), plus the
# restricted CI deploy key (~/.config/itv/ci-deploy-key.pub) when present.
# Usage: DIGITALOCEAN_TOKEN=… scripts/sync-staging-keys.sh
set -euo pipefail
cd "$(dirname "$0")/../infra/terraform/staging"
ip=$(terraform output -raw ip)
keys=$(terraform output -raw authorized_keys)
[[ $(grep -c '^ssh-' <<<"$keys") -ge 1 ]] || { echo "no keys from terraform output" >&2; exit 1; }
# CI deploy key: may only sync code and deploy (infra/staging/ci-ssh-command.sh,
# installed to /usr/local/bin by remote-deploy.sh). "restrict" disables pty,
# forwarding and agent access.
ci_key=${ITV_CI_PUBKEY:-$HOME/.config/itv/ci-deploy-key.pub}   # kept out of the repo
[[ -f "$ci_key" ]] && keys+=$'\n'"command=\"/usr/local/bin/itv-ci-ssh-command\",restrict $(cat "$ci_key")"
# Write to a temp file and move into place so a failed copy never empties the file.
printf '%s\n' "$keys" | ssh -o BatchMode=yes "deploy@${ip}" \
  'umask 077; cat > ~/.ssh/authorized_keys.new && mv ~/.ssh/authorized_keys.new ~/.ssh/authorized_keys && wc -l < ~/.ssh/authorized_keys'
