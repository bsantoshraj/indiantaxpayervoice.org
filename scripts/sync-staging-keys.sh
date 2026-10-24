#!/usr/bin/env bash
# Replace the deploy user's authorized_keys on staging with the keys declared
# in infra/terraform/staging (this machine's key + extra_ssh_key_names).
# Usage: DIGITALOCEAN_TOKEN=… scripts/sync-staging-keys.sh
set -euo pipefail
cd "$(dirname "$0")/../infra/terraform/staging"
ip=$(terraform output -raw ip)
keys=$(terraform output -raw authorized_keys)
[[ $(grep -c '^ssh-' <<<"$keys") -ge 1 ]] || { echo "no keys from terraform output" >&2; exit 1; }
# Write to a temp file and move into place so a failed copy never empties the file.
printf '%s\n' "$keys" | ssh -o BatchMode=yes "deploy@${ip}" \
  'umask 077; cat > ~/.ssh/authorized_keys.new && mv ~/.ssh/authorized_keys.new ~/.ssh/authorized_keys && wc -l < ~/.ssh/authorized_keys'
