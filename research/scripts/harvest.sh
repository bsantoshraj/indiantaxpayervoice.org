#!/usr/bin/env bash
# Download every source in research/sources.csv and record its SHA-256.
#
# store=repo  -> research/sources/        (official/open data, committed)
# store=local -> research/sources/local/  (third-party pages, gitignored: kept
#                                          as evidence, not republished)
#
# A source that refuses the download (many Indian government sites block
# scripts) is fetched from its latest Internet Archive snapshot instead; the
# manifest records which.  Existing files are kept, so a re-run never
# overwrites what was captured earlier; delete a file to capture it again.
#
# Usage: research/scripts/harvest.sh
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
ua="Mozilla/5.0 (X11; Linux x86_64) indiantaxpayervoice.org research"
log="$root/sources/harvest-log.csv"
mkdir -p "$root/sources/local"
[[ -f "$log" ]] || echo "id,file,via,retrieved_utc,sha256" >"$log"

ext_for() {
  case "$1" in
    *pdf*) echo pdf ;;
    *json*) echo json ;;
    *) echo html ;;
  esac
}

fetch() { # url out -> prints content type, fails on HTTP error
  curl -sSL --fail --max-time 120 -A "$ua" -o "$2" -w '%{content_type}' "$1"
}

tail -n +2 "$root/sources.csv" | while IFS= read -r line; do
  # Columns: id,article,store,...,url (the url is the last field; titles may hold commas)
  id="${line%%,*}"
  rest="${line#*,}"; rest="${rest#*,}"
  store="${rest%%,*}"
  url="${line##*,}"
  dir="$root/sources"; [[ "$store" == local ]] && dir="$root/sources/local"

  if compgen -G "$dir/$id.*" >/dev/null; then
    echo "keep   $id"
    continue
  fi

  tmp="$(mktemp)"
  via=direct
  if ! ctype="$(fetch "$url" "$tmp" 2>/dev/null)"; then
    via=wayback
    if ! ctype="$(fetch "https://web.archive.org/web/2026id_/$url" "$tmp" 2>/dev/null)"; then
      echo "FAILED $id"
      rm -f "$tmp"
      continue
    fi
  fi
  out="$dir/$id.$(ext_for "$ctype")"
  mv "$tmp" "$out"
  sum="$(sha256sum "$out" | cut -d' ' -f1)"
  echo "$id,${out#"$root"/},$via,$(date -u +%FT%TZ),$sum" >>"$log"
  echo "saved  $id ($via)"
  sleep 2
done

# Checksums for everything captured, committed or not.
(cd "$root" && find sources -type f ! -name harvest-log.csv | sort | xargs sha256sum >SHA256SUMS)
echo "wrote research/SHA256SUMS"
