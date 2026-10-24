#!/usr/bin/env bash
# Post-deploy checks against staging through Cloudflare, as a visitor sees it.
# Run by CI after every deploy; safe to run by hand. Exits non-zero on failure.
# Usage: scripts/smoke-staging.sh [domain]   (default indiantaxpayervoice.org)
set -uo pipefail
shopt -s extglob
domain=${1:-indiantaxpayervoice.org}
wp="https://staging.$domain"; survey="https://survey-staging.$domain"
admin="https://survey-admin-staging.$domain"; stats="https://stats-staging.$domain"
failures=0

check() {  # check <description> <expected glob> <actual>
  # shellcheck disable=SC2053  # $2 is a pattern on purpose
  if [[ "$3" == $2 ]]; then printf 'ok    %-58s %s\n' "$1" "$3"
  else printf 'FAIL  %-58s got %s, want %s\n' "$1" "$3" "$2"; failures=$((failures + 1)); fi
}
code() { curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$@"; }
cache() { curl -s -o /dev/null -D - --max-time 20 "$1" | tr -d '\r' | awk -F': ' 'tolower($1)=="cf-cache-status"{print $2}'; }

for path in / /participate/ /survey-methodology/ /privacy-policy/ /terms/; do check "website $path" 200 "$(code "$wp$path")"; done
check "http redirects to https" 301 "$(code "http://staging.$domain/")"
check "gate health" 200 "$(code "$survey/gate/health")"
check "survey sends visitors through the gate" 302 "$(code "$survey/index.php/1?lang=en")"
for path in /index.php/admin /admin "/index.php?r=admin/authentication/sa/login" /index.php/rest/v1/survey; do
  check "public survey host refuses $path" 404 "$(code "$survey$path")"
done
check "admin host requires Cloudflare Access" "302 *.cloudflareaccess.com" \
  "$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' --max-time 20 "$admin/" | sed -E 's#https://([^/]+)/.*#\1#')"
check "stats summary" 200 "$(code "$stats/v1/statistics/summary")"

generated=$(curl -s --max-time 20 "$stats/v1/statistics/summary" | python3 -c 'import sys,json; print(json.load(sys.stdin)["meta"]["generated_at"])' 2>/dev/null)
age=$(( $(date -u +%s) - $(date -u -d "${generated:-1970-01-01}" +%s) ))
check "stats generated within 15 minutes (${age}s ago)" "yes" "$([[ $age -lt 900 ]] && echo yes || echo no)"

for url in "$survey/gate/health" "$survey/index.php/1?lang=en" "$wp/wp-login.php"; do
  cache "$url" >/dev/null
  check "never cached: ${url#https://}" "!(HIT)" "$(s=$(cache "$url"); echo "${s:-none}")"
done

echo
(( failures == 0 )) && echo "Smoke tests passed." || echo "$failures smoke test(s) failed."
exit $(( failures > 0 ))
