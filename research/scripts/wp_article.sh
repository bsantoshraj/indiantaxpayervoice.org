#!/usr/bin/env bash
# Put articles from research/articles/ into WordPress. Run from the directory that
# holds the Docker Compose stack (the repository locally, /opt/itv on a droplet).
#
#   wp_article.sh drafts           every article as a draft. New articles are created
#                                  as drafts; existing posts get the repository text
#                                  but keep their status. Staging runs this on every
#                                  deploy, so it always holds the latest text.
#   wp_article.sh publish <slug>   publish one article from research/articles here
#                                  (create or update). For the local site.
#   wp_article.sh receive <slug>   publish the article sent on stdin, as JSON from
#                                  article_to_wp.py. Production runs this only from the
#                                  "Publish article" workflow, after the owner's
#                                  approval, so an article goes live without a code deploy.
#   wp_article.sh unpublish <slug> take the article off this site: back to draft (kept,
#                                  not deleted). Production runs this from the workflow.
#   wp_article.sh status <slug>    "<status> <fingerprint>" of that post here (read-only;
#                                  the workflow asks staging before publishing).
#   wp_article.sh fingerprint <slug>  fingerprint of the repository's version.
#
# The repository is the source of truth: text edited in wp-admin is replaced on the
# next run. Charts come from research/charts/manifest.json.
set -euo pipefail
cd "$(dirname "$0")/../.."

usage() { echo "usage: $0 drafts | publish <slug> | receive <slug> < article.json | unpublish <slug> | status <slug> | fingerprint <slug>" >&2; exit 2; }

# fingerprint <json>: SHA-256 of the article's title and content, as stored with the
# post (_itv_source_sha256). Production publishes only an article whose fingerprint
# matches the one published on staging, i.e. exactly the text that was reviewed.
fingerprint() {
  python3 -I -c 'import hashlib,json,sys; d=json.loads(sys.argv[1]); print(hashlib.sha256((d["title"]+"\n"+d["content"]).encode()).hexdigest())' "$1"
}

# upsert <json> <publish|keep>: create or update the post with this slug.
#   publish: create or update as published.
#   keep:    create as a draft; on update keep the status, except that a published
#            post whose text changed goes back to draft, to be reviewed again.
upsert() {
  local json=$1 mode=$2 title64 slug sha
  title64=$(python3 -I -c 'import json,sys,base64; print(base64.b64encode(json.loads(sys.argv[1])["title"].encode()).decode())' "$json")
  slug=$(python3 -I -c 'import json,sys; print(json.loads(sys.argv[1])["slug"])' "$json")
  sha=$(fingerprint "$json")
  python3 -I -c 'import json,sys; sys.stdout.write(json.loads(sys.argv[1])["content"])' "$json" |
    docker compose run --rm -T -e "T64=$title64" -e "SLUG=$slug" -e "MODE=$mode" -e "SHA=$sha" wpcli sh -c '
      title=$(printf %s "$T64" | base64 -d)
      id=$(wp post list --post_type=post --name="$SLUG" --post_status=any --field=ID --format=ids)
      note=""
      if [ -n "$id" ]; then
        old=$(wp post meta get "$id" _itv_source_sha256 2>/dev/null || true)
        set -- --post_title="$title"
        if [ "$MODE" = publish ]; then
          set -- "$@" --post_status=publish
        elif [ "$old" != "$SHA" ] && [ "$(wp post get "$id" --field=post_status)" = publish ]; then
          set -- "$@" --post_status=draft; note=", text changed: back to draft for review"
        fi
        wp post update "$id" - "$@" --user="$WP_ADMIN_USER" >/dev/null
      else
        status=draft; [ "$MODE" = publish ] && status=publish
        id=$(wp post create - --post_type=post --post_status=$status --post_name="$SLUG" --post_title="$title" --user="$WP_ADMIN_USER" --porcelain)
      fi
      wp post meta update "$id" _itv_source_sha256 "$SHA" >/dev/null
      echo "$SLUG: post $id, $(wp post get "$id" --field=post_status)$note"' 2>&1 | grep -E "^[a-z0-9-]+: post |Error"
}

# status <slug>: "<status> <fingerprint>" of the post here, or "missing -".
status() {
  docker compose run --rm -T -e "SLUG=$1" wpcli sh -c '
    id=$(wp post list --post_type=post --name="$SLUG" --post_status=any --field=ID --format=ids)
    if [ -z "$id" ]; then echo "missing -"; exit 0; fi
    echo "$(wp post get "$id" --field=post_status) $(wp post meta get "$id" _itv_source_sha256 2>/dev/null || echo -)"' 2>/dev/null | tail -1
}

convert() { python3 -I research/scripts/article_to_wp.py "$1"; }

case "${1:-}" in
  drafts)
    for f in research/articles/[0-9][0-9]-*.md; do
      [[ "$(basename "$f")" == 00-* ]] && continue
      upsert "$(convert "$f")" keep
    done ;;
  publish)
    slug=${2:-}; [[ "$slug" =~ ^[a-z0-9-]{1,100}$ ]] || usage
    json=$(python3 -I research/scripts/article_to_wp.py --slug "$slug")
    upsert "$json" publish ;;
  receive)
    slug=${2:-}; [[ "$slug" =~ ^[a-z0-9-]{1,100}$ ]] || usage
    json=$(head -c 4000000)   # an article with inline charts is well under 1 MB
    python3 -I -c '
import json, sys
try:
    d = json.loads(sys.argv[1])
except ValueError:
    d = None
ok = isinstance(d, dict) and d.get("slug") == sys.argv[2] and all(isinstance(d.get(k), str) and d[k] for k in ("title", "content"))
sys.exit(0 if ok else "receive: stdin is not the article " + sys.argv[2])' "$json" "$slug"
    upsert "$json" publish ;;
  unpublish)
    slug=${2:-}; [[ "$slug" =~ ^[a-z0-9-]{1,100}$ ]] || usage
    docker compose run --rm -T -e "SLUG=$slug" wpcli sh -c '
      id=$(wp post list --post_type=post --name="$SLUG" --post_status=any --field=ID --format=ids)
      if [ -z "$id" ]; then echo "$SLUG: not on this site"; exit 0; fi
      wp post update "$id" --post_status=draft >/dev/null
      echo "$SLUG: post $id, $(wp post get "$id" --field=post_status) (unpublished)"' 2>&1 | grep -E "^[a-z0-9-]+: |Error" ;;
  status)
    slug=${2:-}; [[ "$slug" =~ ^[a-z0-9-]{1,100}$ ]] || usage
    status "$slug" ;;
  fingerprint)
    slug=${2:-}; [[ "$slug" =~ ^[a-z0-9-]{1,100}$ ]] || usage
    fingerprint "$(python3 -I research/scripts/article_to_wp.py --slug "$slug")" ;;
  *) usage ;;
esac
