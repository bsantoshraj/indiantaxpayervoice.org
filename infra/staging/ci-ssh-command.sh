#!/usr/bin/env bash
# Forced command for the CI deploy key (authorized_keys "command=…,restrict").
# Installed to /usr/local/bin by remote-deploy.sh, outside /opt/itv, so a code
# sync cannot replace it. The key can do exactly two things:
#   rsync into /opt/itv only (rrsync), and
#   "deploy <40-hex git sha>" with a short-lived GHCR token on stdin.
# Anything that can deploy code can run code on this host; this limits the key
# to the deploy path, it does not make a compromised CI harmless.
set -euo pipefail
cmd=${SSH_ORIGINAL_COMMAND:-}
case "$cmd" in
  "rsync --server "*)
    exec rrsync /opt/itv ;;
  deploy\ *)
    sha=${cmd#deploy }
    [[ "$sha" =~ ^[0-9a-f]{40}$ ]] || { echo "deploy: expected a 40-character git SHA" >&2; exit 2; }
    exec /opt/itv/infra/staging/remote-deploy.sh --image-tag "$sha" ;;
  *)
    echo "This key may only sync code and deploy." >&2; exit 1 ;;
esac
