#!/usr/bin/env bash
# Post-deploy checks through Cloudflare, as a visitor sees it. Run by CI after
# every deploy; safe to run by hand. Exits non-zero on failure.
# Usage: scripts/smoke.sh <staging|production>
set -uo pipefail
shopt -s extglob
cd "$(dirname "$0")/.." || exit 2
env=${1:?usage: smoke.sh <staging|production>}
domain=indiantaxpayervoice.org
case "$env" in
  staging)    wp="https://staging.$domain"; survey="https://survey-staging.$domain"
              admin="https://survey-admin-staging.$domain"; stats="https://stats-staging.$domain" ;;
  production) wp="https://$domain"; survey="https://survey.$domain"
              admin="https://survey-admin.$domain"; stats="https://stats.$domain" ;;
  *) echo "environment must be staging or production" >&2; exit 2 ;;
esac
survey_open=$(sed -n 's/^ITV_SURVEY_OPEN=//p' "infra/env/$env.env")
failures=0
# Private environments (staging) sit behind Cloudflare Access: CI passes a service
# token in CF_ACCESS_CLIENT_ID / CF_ACCESS_CLIENT_SECRET, sent with every request.
auth=()
if [[ -n "${CF_ACCESS_CLIENT_ID:-}" ]]; then
  auth=(-H "CF-Access-Client-Id: $CF_ACCESS_CLIENT_ID" -H "CF-Access-Client-Secret: ${CF_ACCESS_CLIENT_SECRET:?}")
fi

check() {  # check <description> <expected glob> <actual>
  # shellcheck disable=SC2053  # $2 is a pattern on purpose
  if [[ "$3" == $2 ]]; then printf 'ok    %-58s %s\n' "$1" "$3"
  else printf 'FAIL  %-58s got %s, want %s\n' "$1" "$3" "$2"; failures=$((failures + 1)); fi
}
code() { curl "${auth[@]}" -s -o /dev/null -w '%{http_code}' --max-time 20 "$@"; }
cache() { curl "${auth[@]}" -s -o /dev/null -D - --max-time 20 "$1" | tr -d '\r' | awk -F': ' 'tolower($1)=="cf-cache-status"{print $2}'; }

for path in / /participate/ /survey-methodology/ /privacy-policy/ /terms/; do check "website $path" 200 "$(code "$wp$path")"; done
check "http redirects to https" 301 "$(code "http://${wp#https://}/")"
check "gate health" 200 "$(code "$survey/gate/health")"
check "survey sends visitors through the gate" 302 "$(code "$survey/index.php/1?lang=en")"
if [[ "$survey_open" == 1 ]]; then
  check "survey open: gate shows the bot check" 200 "$(code "$survey/gate/")"
else
  check "survey closed: gate says not open yet" "503 yes" \
    "$(code "$survey/gate/") $(curl "${auth[@]}" -s --max-time 20 "$survey/gate/" | grep -q 'not open yet' && echo yes || echo no)"
fi
robots=$(curl "${auth[@]}" -s -o /dev/null -D - --max-time 20 "$wp/" | tr -d '\r' | awk -F': ' 'tolower($1)=="x-robots-tag"{print $2}')
if [[ "$env" == production ]]; then
  check "website indexable (no X-Robots-Tag)" "" "$robots"
  check "www redirects to the website" "301 $wp/faq/?a=1" "$(curl "${auth[@]}" -s -o /dev/null -w '%{http_code} %{redirect_url}' --max-time 20 "https://www.$domain/faq/?a=1")"
else
  check "website kept out of search engines" "noindex*" "$robots"
  # Once CI holds the service token the environment is private: prove the token is needed.
  (( ${#auth[@]} )) && for host in "$wp" "$survey" "$stats"; do
    check "without a token, ${host#https://} requires Cloudflare Access" "302 *.cloudflareaccess.com" \
      "$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' --max-time 20 "$host/" | sed -E 's#https://([^/]+)/.*#\1#')"
  done
fi
for path in /index.php/admin /admin "/index.php?r=admin/authentication/sa/login" /index.php/rest/v1/survey; do
  # 403: blocked by the Cloudflare WAF; 404: refused by the origin's nginx.
  check "public survey host refuses $path" "@(403|404)" "$(code "$survey$path")"
done
check "admin host requires Cloudflare Access" "302 *.cloudflareaccess.com" \
  "$(curl "${auth[@]}" -s -o /dev/null -w '%{http_code} %{redirect_url}' --max-time 20 "$admin/" | sed -E 's#https://([^/]+)/.*#\1#')"
check "WordPress admin requires Cloudflare Access" "302 *.cloudflareaccess.com" \
  "$(curl "${auth[@]}" -s -o /dev/null -w '%{http_code} %{redirect_url}' --max-time 20 "$wp/wp-login.php" | sed -E 's#https://([^/]+)/.*#\1#')"
check "WAF blocks /xmlrpc.php" 403 "$(code -X POST "$wp/xmlrpc.php")"
# Security hardening (account names, version, framing)
check "users API hidden from visitors" 404 "$(code "$wp/wp-json/wp/v2/users")"
check "?author=1 does not reveal a username" "301 $wp/" "$(curl "${auth[@]}" -s -o /dev/null -w '%{http_code} %{redirect_url}' --max-time 20 "$wp/?author=1")"
check "readme.html hidden" 404 "$(code "$wp/readme.html")"
check "no WordPress generator tag" 0 "$(curl "${auth[@]}" -s --max-time 20 "$wp/" | grep -c 'name="generator"')"
check "website refuses framing (X-Frame-Options)" SAMEORIGIN "$(curl "${auth[@]}" -s -o /dev/null -D - --max-time 20 "$wp/" | tr -d '\r' | awk -F': ' 'tolower($1)=="x-frame-options"{print $2}')"
check "WAF blocks writes to statistics" 403 "$(code -X POST "$stats/v1/statistics/summary")"
check "stats summary" 200 "$(code "$stats/v1/statistics/summary")"

generated=$(curl "${auth[@]}" -s --max-time 20 "$stats/v1/statistics/summary" | python3 -c 'import sys,json; print(json.load(sys.stdin)["meta"]["generated_at"])' 2>/dev/null)
age=$(( $(date -u +%s) - $(date -u -d "${generated:-1970-01-01}" +%s) ))
# Statistics refresh hourly (differencing protection): allow one interval plus 15 minutes.
check "stats generated within 75 minutes (${age}s ago)" "yes" "$([[ $age -lt 4500 ]] && echo yes || echo no)"

for url in "$survey/gate/health" "$survey/index.php/1?lang=en" "$wp/wp-login.php"; do
  cache "$url" >/dev/null
  check "never cached: ${url#https://}" "!(HIT)" "$(s=$(cache "$url"); echo "${s:-none}")"
done

echo
(( failures == 0 )) && echo "Smoke tests passed." || echo "$failures smoke test(s) failed."
exit $(( failures > 0 ))
