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
# Admin email follows .env (set at install only otherwise). Set directly: the CLI
# skips WordPress's confirmation email, which local/staging cannot receive reliably.
wp option update admin_email "$WP_ADMIN_EMAIL"
wp user update "$WP_ADMIN_USER" --user_email="$WP_ADMIN_EMAIL" --skip-email >/dev/null
wp option update blogdescription "We contribute. We deserve a voice."
# Only production is indexed by search engines (staging also sends X-Robots-Tag).
if [[ "${ITV_ENV:-local}" == "production" ]]; then wp option update blog_public 1; else wp option update blog_public 0; fi
wp option update default_comment_status closed
wp option update default_ping_status closed
wp option update users_can_register 0
wp option update timezone_string "Asia/Kolkata"
wp theme activate itv
wp rewrite structure '/%postname%/' --hard

# Remove sample content.
wp post delete 1 2 --force 2>/dev/null || true
wp plugin delete akismet hello 2>/dev/null || true

# slug|title|content file|description (meta description, under 160 characters)
pages=(
  "home|Indian Taxpayer Voice|home.html|An independent, non-partisan initiative. Take a short anonymous survey and see privacy-protected results from Indian taxpayers."
  "mission|Mission and principles|mission.html|Why Indian Taxpayer Voice exists, the principles it follows, and what it will and will not do with taxpayers' views."
  "participate|Participate in the survey|participate.html|Take the anonymous five-minute survey on job-loss protection, health costs and public spending. No name, PAN, Aadhaar or contact details."
  "job-loss-protection|Job-loss protection research|job-loss.html|Research on how Indian taxpayers would cope with losing their job, and the protection they think the system should offer."
  "health-financial-protection|Health-related financial protection research|health.html|Research on medical costs, health cover and the financial risk of illness for Indian taxpayers and their families."
  "public-spending|Public spending and accountability research|spending.html|Research on how taxpayers see public spending and accountability, and what they want their taxes to deliver."
  "research|Research and articles|research.html|Articles and research from Indian Taxpayer Voice, based on survey results and public data."
  "survey-methodology|Survey methodology|methodology.html|How the survey works: who can take part, how responses are checked, and how small groups are protected before results are published."
  "statistics|Public statistics|statistics.html|Privacy-protected totals from the Indian Taxpayer Voice survey: responses, states and union territories, industries and top concerns."
  "faq|Frequently asked questions|faq.html|Answers to common questions about the survey, privacy, how results are published and who runs Indian Taxpayer Voice."
  "contact|Contact|contact.html|Contact Indian Taxpayer Voice at hello@indiantaxpayervoice.org. Please do not send financial or medical details, PAN or Aadhaar numbers."
  "privacy-policy|Privacy policy|privacy.html|How Indian Taxpayer Voice handles survey answers and other data: what is collected, what is never collected, and how to contact us."
  "terms|Terms of use|terms.html|Terms of use for the Indian Taxpayer Voice website, survey and published statistics."
  "accessibility|Accessibility statement|accessibility.html|The accessibility standard Indian Taxpayer Voice aims for, accessible alternatives, and how to report a problem."
)

for entry in "${pages[@]}"; do
  IFS='|' read -r slug title file description <<<"$entry"
  content=$(mktemp)
  survey_url="${LS_PUBLIC_URL}/index.php/${ITV_LS_SURVEY_ID}?lang=en"
  sed "s#{{SURVEY_URL}}#${survey_url}#g" "/content/$file" >"$content"
  id=$(wp post list --post_type=page --name="$slug" --post_status=any --field=ID --format=ids)
  if [[ -z "$id" ]]; then
    id=$(wp post create "$content" --post_type=page --post_status=publish \
      --post_name="$slug" --post_title="$title" --post_excerpt="$description" --porcelain)
    echo "created $slug ($id)"
  else
    # Publish too: WordPress installs a draft privacy-policy page of its own.
    wp post update "$id" "$content" --post_title="$title" --post_excerpt="$description" --post_status=publish >/dev/null
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
