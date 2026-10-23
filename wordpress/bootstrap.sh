#!/usr/bin/env bash
# Idempotent local WordPress setup. Run via: docker compose run --rm wpcli bash /bootstrap.sh
set -euo pipefail

if ! wp core is-installed 2>/dev/null; then
  wp core install --url="$WP_URL" --title="Indian Taxpayer Voice" \
    --admin_user="$WP_ADMIN_USER" --admin_password="$WP_ADMIN_PASSWORD" \
    --admin_email="$WP_ADMIN_EMAIL" --skip-email
fi

# Keep URLs in step with .env (e.g. after changing BIND_ADDR / host IP).
wp option update home "$WP_URL"
wp option update siteurl "$WP_URL"
wp option update blogdescription "We contribute. We deserve a voice."
wp option update blog_public 0            # local/staging: discourage indexing
wp option update default_comment_status closed
wp option update default_ping_status closed
wp option update users_can_register 0
wp option update timezone_string "Asia/Kolkata"
wp theme activate itv
wp rewrite structure '/%postname%/' --hard

# Remove sample content.
wp post delete 1 2 --force 2>/dev/null || true
wp plugin delete akismet hello 2>/dev/null || true

# slug|title|content file
pages=(
  "home|Indian Taxpayer Voice|home.html"
  "mission|Mission and principles|mission.html"
  "participate|Participate in the survey|participate.html"
  "job-loss-protection|Job-loss protection research|job-loss.html"
  "health-financial-protection|Health-related financial protection research|health.html"
  "public-spending|Public spending and accountability research|spending.html"
  "research|Research and articles|research.html"
  "survey-methodology|Survey methodology|methodology.html"
  "statistics|Public statistics|statistics.html"
  "faq|Frequently asked questions|faq.html"
  "contact|Contact|contact.html"
  "privacy-policy|Privacy policy|privacy.html"
  "terms|Terms of use|terms.html"
  "accessibility|Accessibility statement|accessibility.html"
)

for entry in "${pages[@]}"; do
  IFS='|' read -r slug title file <<<"$entry"
  content=$(mktemp)
  survey_url="${LS_PUBLIC_URL}/index.php/${ITV_LS_SURVEY_ID}?lang=en"
  sed "s#{{SURVEY_URL}}#${survey_url}#g" "/content/$file" >"$content"
  id=$(wp post list --post_type=page --name="$slug" --post_status=any --field=ID --format=ids)
  if [[ -z "$id" ]]; then
    id=$(wp post create "$content" --post_type=page --post_status=publish \
      --post_name="$slug" --post_title="$title" --porcelain)
    echo "created $slug ($id)"
  else
    wp post update "$id" "$content" --post_title="$title" >/dev/null
    echo "updated $slug ($id)"
  fi
  rm -f "$content"
done

home_id=$(wp post list --post_type=page --name=home --field=ID --format=ids)
privacy_id=$(wp post list --post_type=page --name=privacy-policy --field=ID --format=ids)
wp option update show_on_front page
wp option update page_on_front "$home_id"
wp option update wp_page_for_privacy_policy "$privacy_id"

# Block-theme navigation with relative links, so it works on any host/IP.
# (A classic menu gets converted with absolute URLs frozen at first render.)
nav=""
for item in "mission|Mission" "research|Research" \
            "survey-methodology|Methodology" "statistics|Statistics" "faq|FAQ" "contact|Contact"; do
  IFS='|' read -r slug label <<<"$item"
  pid=$(wp post list --post_type=page --name="$slug" --field=ID --format=ids)
  nav+="<!-- wp:navigation-link {\"label\":\"$label\",\"type\":\"page\",\"id\":$pid,\"url\":\"/$slug/\",\"kind\":\"post-type\"} /-->"
done
# Survey CTA inside the mobile menu only (the header button is hidden on phones).
pid=$(wp post list --post_type=page --name=participate --field=ID --format=ids)
nav+="<!-- wp:navigation-link {\"label\":\"Take the survey\",\"type\":\"page\",\"id\":$pid,\"url\":\"/participate/\",\"kind\":\"post-type\",\"className\":\"itv-nav-cta\"} /-->"
for old in $(wp post list --post_type=wp_navigation --post_status=any --field=ID --format=ids); do
  wp post delete "$old" --force >/dev/null
done
wp menu delete Primary >/dev/null 2>&1 || true
wp post create --post_type=wp_navigation --post_status=publish --post_title="Primary" \
  --post_content="$nav" --porcelain >/dev/null
echo "navigation updated"

echo "WordPress bootstrap complete."
