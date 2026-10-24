#!/usr/bin/env bash
# Purge Cloudflare's cache for the given hostnames only (other environments keep
# theirs). Token from CLOUDFLARE_API_TOKEN or ~/.config/itv/cf_token; needs
# Zone > Cache Purge (+ Zone > Read unless ITV_CF_ZONE_ID is set). Usage: scripts/purge-cdn.sh <hostname>...
set -euo pipefail
(( $# )) || { echo "usage: purge-cdn.sh <hostname>..." >&2; exit 2; }
token=${CLOUDFLARE_API_TOKEN:-$(cat ~/.config/itv/cf_token 2>/dev/null || true)}
[[ -n "$token" ]] || { echo "No Cloudflare token; cache not purged." >&2; exit 1; }
zone=${ITV_CF_ZONE:-indiantaxpayervoice.org}
api() { curl -fsS -H "Authorization: Bearer $token" -H "Content-Type: application/json" "$@"; }
# A purge-only token (CI) cannot look zones up: pass ITV_CF_ZONE_ID instead.
zone_id=${ITV_CF_ZONE_ID:-$(api "https://api.cloudflare.com/client/v4/zones?name=$zone" | python3 -c 'import sys,json; print(json.load(sys.stdin)["result"][0]["id"])')}
hosts=$(python3 -c 'import sys,json; print(json.dumps({"hosts": sys.argv[1:]}))' "$@")
api -X POST "https://api.cloudflare.com/client/v4/zones/$zone_id/purge_cache" -d "$hosts" \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); sys.exit(0 if d["success"] else d["errors"])'
echo "Purged Cloudflare cache for: $*"
