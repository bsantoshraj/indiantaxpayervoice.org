#!/usr/bin/env bash
# Forced command for the CI deploy key (authorized_keys "command=…,restrict").
# Installed to /usr/local/bin by remote-deploy.sh, outside /opt/itv, so a code
# sync cannot replace it. The key can do exactly five things:
#   rsync into /opt/itv only (rrsync),
#   "deploy <40-hex git sha>" with a short-lived GHCR token on stdin, and
#   "publish <article slug>" with the converted article (JSON) on stdin: the
#   Publish article workflow, after the owner's approval,
#   "unpublish <article slug>": take that article off the site (back to draft), and
#   "status <article slug>": read-only, that post's status and text fingerprint
#   (the workflow checks the article was published on staging first).
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
  publish\ *)
    slug=${cmd#publish }
    [[ "$slug" =~ ^[a-z0-9-]{1,100}$ ]] || { echo "publish: expected an article slug" >&2; exit 2; }
    cd /opt/itv && exec research/scripts/wp_article.sh receive "$slug" ;;
  unpublish\ *)
    slug=${cmd#unpublish }
    [[ "$slug" =~ ^[a-z0-9-]{1,100}$ ]] || { echo "unpublish: expected an article slug" >&2; exit 2; }
    cd /opt/itv && exec research/scripts/wp_article.sh unpublish "$slug" ;;
  status\ *)
    slug=${cmd#status }
    [[ "$slug" =~ ^[a-z0-9-]{1,100}$ ]] || { echo "status: expected an article slug" >&2; exit 2; }
    cd /opt/itv && exec research/scripts/wp_article.sh status "$slug" ;;
  *)
    echo "This key may only sync code, deploy, and publish, unpublish or check articles." >&2; exit 1 ;;
esac
