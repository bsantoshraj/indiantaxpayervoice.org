#!/usr/bin/env bash
# Copy the staging droplet's encrypted backups (age, see infra/staging/backup-db.sh)
# to this machine. Files stay encrypted; nothing is decrypted here.
# Usage: scripts/pull-staging-backups.sh <droplet-ip> [dest-dir]
set -euo pipefail
ip="${1:?usage: pull-staging-backups.sh <droplet-ip> [dest-dir]}"
dest="${2:-$HOME/itv-backups/staging}"
umask 077
mkdir -p "$dest"
rsync -a --chmod=F600 --rsync-path="sudo rsync" -e "ssh -o BatchMode=yes" \
  --include='*.age' --exclude='*' "deploy@${ip}:/var/backups/itv/" "$dest/"
# Keep 30 days here (the privacy notice states this); the droplet keeps 14.
find "$dest" -name '*.age' -mtime +30 -delete
echo "Backups in $dest:"; ls -l "$dest"
