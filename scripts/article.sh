#!/usr/bin/env bash
# Articles from the command line, on the admin machine: review, publish on staging,
# and publish to / unpublish from production through the approved workflow.
# Guide: docs/articles.md.
#
#   scripts/article.sh list                   every article: number, status on staging and production
#   scripts/article.sh status  <NN|slug>      both sites' status and whether the text matches the repo
#   scripts/article.sh show    <NN|slug>      print the article (Markdown) for review
#   scripts/article.sh preview <NN|slug>      staging preview link (open it in your browser)
#   scripts/article.sh stage   <NN|slug>      publish on staging: you have reviewed it
#   scripts/article.sh unstage <NN|slug>      back to draft on staging
#   scripts/article.sh publish   <NN|slug>    ask GitHub to publish it on production
#   scripts/article.sh unpublish <NN|slug>    ask GitHub to take it off production
#   scripts/article.sh approve [run-id]       approve a waiting production run (asks first)
#   scripts/article.sh watch   [run-id]       follow a run to the end and show its result
#
# Needs: gh (signed in as the owner), SSH access as deploy to both droplets.
set -euo pipefail
cd "$(dirname "$0")/.."

STAGING=${ITV_STAGING_SSH:-deploy@134.209.157.144}
PRODUCTION=${ITV_PRODUCTION_SSH:-deploy@64.227.176.80}
REPO=bsantoshraj/indiantaxpayervoice.org
WORKFLOW=publish-article.yml

die() { echo "article: $*" >&2; exit 1; }
remote() { ssh -o BatchMode=yes "$1" "cd /opt/itv && $2"; }
json_field() { python3 -I -c 'import json,sys; print(json.load(sys.stdin)[sys.argv[1]])' "$1"; }

# resolve <NN|slug>: sets FILE and SLUG for an article in research/articles.
resolve() {
  local want=${1:?article number or slug}
  local f
  for f in research/articles/[0-9][0-9]-*.md; do
    [[ "$(basename "$f")" == 00-* ]] && continue
    if [[ "$want" =~ ^[0-9]{1,2}$ ]]; then
      [[ "$(basename "$f" | cut -c1-2)" == "$(printf %02d "$((10#$want))")" ]] || continue
    fi
    SLUG=$(python3 -I research/scripts/article_to_wp.py "$f" | json_field slug)
    if [[ "$want" =~ ^[0-9]{1,2}$ || "$SLUG" == "$want" ]]; then FILE=$f; return; fi
  done
  die "no article '$want' in research/articles"
}

# site_status <host> <slug>: "<status> <fingerprint>" or "missing -"
site_status() { remote "$1" "research/scripts/wp_article.sh status $2"; }

# Statuses of every post on a site, as "slug status" lines.
site_posts() {
  remote "$1" "docker compose run --rm -T wpcli wp post list --post_type=post --post_status=any --fields=post_name,post_status --format=csv 2>/dev/null" | tail -n +2 | tr ',' ' '
}

# find_run <action> <slug> <since>: id of the run started for this request.
find_run() {
  local id i
  for i in $(seq 1 20); do
    id=$(gh run list -R "$REPO" --workflow "$WORKFLOW" --limit 10 --json databaseId,displayTitle,createdAt \
      -q ".[] | select(.createdAt >= \"$3\" and .displayTitle == \"$1 $2\") | .databaseId" | head -1)
    [[ -n "$id" ]] && { echo "$id"; return; }
    [[ $i -lt 20 ]] && sleep 3
  done
  die "GitHub did not show the run; check: gh run list -R $REPO --workflow $WORKFLOW"
}

waiting_run() {
  gh run list -R "$REPO" --status waiting --limit 10 --json databaseId -q '.[0].databaseId'
}

cmd=${1:-}; shift || true
case "$cmd" in
  list)
    declare -A staged live
    while read -r slug st; do staged[$slug]=$st; done < <(site_posts "$STAGING")
    while read -r slug st; do live[$slug]=$st; done < <(site_posts "$PRODUCTION")
    printf '%-3s  %-9s  %-10s  %s\n' NN staging production slug
    for f in research/articles/[0-9][0-9]-*.md; do
      [[ "$(basename "$f")" == 00-* ]] && continue
      slug=$(python3 -I research/scripts/article_to_wp.py "$f" | json_field slug)
      printf '%-3s  %-9s  %-10s  %s\n' "$(basename "$f" | cut -c1-2)" "${staged[$slug]:--}" "${live[$slug]:--}" "$slug"
    done ;;

  status)
    resolve "${1:-}"
    repo_sha=$(research/scripts/wp_article.sh fingerprint "$SLUG")
    read -r s_st s_sha < <(site_status "$STAGING" "$SLUG")
    read -r p_st p_sha < <(site_status "$PRODUCTION" "$SLUG")
    echo "$FILE"
    echo "  slug:        $SLUG"
    echo "  staging:     $s_st$([[ "$s_sha" == "$repo_sha" ]] && echo ", text matches the repo" || echo ", text differs from the repo (staging not yet redeployed?)")"
    echo "  production:  $p_st$([[ "$p_st" == missing ]] || { [[ "$p_sha" == "$repo_sha" ]] && echo ", text matches the repo" || echo ", text differs from the repo (republish to update)"; })"
    if [[ "$p_st" == publish && "$p_sha" == "$repo_sha" ]]; then
      echo "  → live on production and up to date"
    elif [[ "$s_st" == publish && "$s_sha" == "$repo_sha" ]]; then
      echo "  → can be published to production: scripts/article.sh publish $SLUG"
    else
      echo "  → review it, then: scripts/article.sh stage $SLUG"
    fi ;;

  show)
    resolve "${1:-}"
    ${PAGER:-less} "$FILE" ;;

  preview)
    resolve "${1:-}"
    id=$(remote "$STAGING" "docker compose run --rm -T wpcli wp post list --post_type=post --name=$SLUG --post_status=any --field=ID --format=ids 2>/dev/null")
    [[ -n "$id" ]] || die "$SLUG is not on staging yet (merge it, then wait for the staging deploy)"
    echo "https://staging.indiantaxpayervoice.org/?p=$id&preview=true"
    echo "(Opens after the Cloudflare email code and the WordPress login.)" ;;

  stage)
    resolve "${1:-}"
    remote "$STAGING" "research/scripts/wp_article.sh publish $SLUG" ;;

  unstage)
    resolve "${1:-}"
    remote "$STAGING" "research/scripts/wp_article.sh unpublish $SLUG" ;;

  publish|unpublish)
    resolve "${1:-}"
    if [[ "$cmd" == publish ]]; then
      read -r s_st s_sha < <(site_status "$STAGING" "$SLUG")
      [[ "$s_st" == publish ]] || die "$SLUG is $s_st on staging: review it and run 'scripts/article.sh stage $SLUG' first"
      [[ "$s_sha" == "$(research/scripts/wp_article.sh fingerprint "$SLUG")" ]] \
        || die "staging shows different text from your repository: pull main, or wait for the staging deploy, and review again"
    fi
    since=$(date -u +%FT%TZ)
    gh workflow run "$WORKFLOW" -R "$REPO" --ref main -f action="$cmd" -f slug="$SLUG"
    id=$(find_run "$cmd" "$SLUG" "$since")
    echo "Run $id: https://github.com/$REPO/actions/runs/$id"
    echo "It waits for your approval: scripts/article.sh approve $id" ;;

  approve)
    id=${1:-$(waiting_run)}
    [[ -n "$id" ]] || die "no run is waiting for approval"
    gh run view "$id" -R "$REPO" --json workflowName,displayTitle,status \
      -q '"\(.workflowName): \(.displayTitle) (\(.status))"'
    env_ids=$(gh api "repos/$REPO/actions/runs/$id/pending_deployments" -q '.[].environment.id')
    [[ -n "$env_ids" ]] || die "run $id is not waiting for approval"
    read -r -p "Approve this run for production? [y/N] " answer </dev/tty
    [[ "$answer" == [yY] ]] || die "not approved"
    args=()
    for e in $env_ids; do args+=(-F "environment_ids[]=$e"); done
    gh api -X POST "repos/$REPO/actions/runs/$id/pending_deployments" "${args[@]}" \
      -f state=approved -f comment="Approved from scripts/article.sh" -q '.[0].environment' >/dev/null
    echo "Approved. Following the run…"
    exec "$0" watch "$id" ;;

  watch)
    id=${1:-$(gh run list -R "$REPO" --workflow "$WORKFLOW" --limit 1 --json databaseId -q '.[0].databaseId')}
    gh run watch "$id" -R "$REPO" --exit-status >/dev/null && result=succeeded || result=failed
    gh run view "$id" -R "$REPO" --log 2>/dev/null \
      | grep -E "staging: |post [0-9]+, |not on this site|-> [0-9]{3}|::error::" | sed -E 's/^.*Z //' || true
    echo "Run $id $result: https://github.com/$REPO/actions/runs/$id"
    [[ "$result" == succeeded ]] ;;

  *)
    sed -n '2,19p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
