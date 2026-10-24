#!/usr/bin/env bash
# Tell IndexNow search engines (Bing and others) which production pages exist.
# Reads the page URLs from the site's sitemap. Run by CI after production deploys.
# Usage: INDEXNOW_ID=<32 hex> scripts/indexnow.sh [host]   (default indiantaxpayervoice.org)
set -euo pipefail
host=${1:-indiantaxpayervoice.org}
id=${INDEXNOW_ID:?set INDEXNOW_ID}
[[ "$id" =~ ^[a-f0-9]{32}$ ]] || { echo "INDEXNOW_ID must be 32 lowercase hex characters" >&2; exit 2; }

# The verification file must be served before engines will accept submissions.
served=$(curl -fsS --max-time 20 "https://$host/$id.txt" || true)
[[ "$served" == "$id" ]] || { echo "https://$host/$id.txt does not serve the id; set ITV_INDEXNOW_ID on the server" >&2; exit 1; }

urls=$(curl -fsS --max-time 20 "https://$host/wp-sitemap-posts-page-1.xml" | grep -oE '<loc>[^<]+' | sed 's/<loc>//')
[[ -n "$urls" ]] || { echo "no URLs in the sitemap" >&2; exit 1; }
body=$(python3 -c 'import json, sys; h, k = sys.argv[1], sys.argv[2]; print(json.dumps({"host": h, "key": k, "keyLocation": f"https://{h}/{k}.txt", "urlList": sys.stdin.read().split()}))' "$host" "$id" <<<"$urls")
status=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 30 -X POST https://api.indexnow.org/indexnow \
  -H 'Content-Type: application/json; charset=utf-8' -d "$body")
echo "IndexNow: submitted $(wc -l <<<"$urls") URLs for $host (HTTP $status)"
[[ "$status" == 200 || "$status" == 202 ]]
