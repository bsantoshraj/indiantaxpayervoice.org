#!/usr/bin/env bash
# Replace the deploy user's authorized_keys on staging with the keys declared
# in infra/terraform/staging (this machine's key + extra_ssh_key_names), plus the
# restricted CI deploy key (~/.config/itv/ci-deploy-key.pub) when present.
# Usage: scripts/sync-staging-keys.sh [staging|production]   (default staging)
set -euo pipefail
env="${1:-staging}"
cd "$(dirname "$0")/../infra/terraform/$env"
ip=$(terraform output -raw ip)
keys=$(terraform output -raw authorized_keys)
[[ $(grep -c '^ssh-' <<<"$keys") -ge 1 ]] || { echo "no keys from terraform output" >&2; exit 1; }
# CI deploy key: may only sync code and deploy (infra/staging/ci-ssh-command.sh,
# installed to /usr/local/bin by remote-deploy.sh). "restrict" disables pty,
# forwarding and agent access.
if [[ "$env" == staging ]]; then default_key=ci-deploy-key.pub; else default_key=ci-deploy-key-$env.pub; fi
ci_key=${ITV_CI_PUBKEY:-$HOME/.config/itv/$default_key}   # kept out of the repo; one key per environment
[[ -f "$ci_key" ]] && keys+=$'\n'"command=\"/usr/local/bin/itv-ci-ssh-command\",restrict $(cat "$ci_key")"
# Write to a temp file and move into place so a failed copy never empties the file.
printf '%s\n' "$keys" | ssh -o BatchMode=yes "deploy@${ip}" \
  'umask 077; cat > ~/.ssh/authorized_keys.new && mv ~/.ssh/authorized_keys.new ~/.ssh/authorized_keys && wc -l < ~/.ssh/authorized_keys'
