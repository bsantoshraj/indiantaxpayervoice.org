# Zone-wide Cloudflare configuration shared by staging and production. It lives
# apart from infra/terraform/staging because a zone has exactly one cache-rules
# ruleset and one browser-cache setting.

data "cloudflare_zone" "itv" {
  filter = { name = var.zone_name }
}

locals {
  zone_id = data.cloudflare_zone.itv.zone_id
  hosts   = { for role, list in { wp = var.wordpress_hosts, stats = var.stats_hosts, survey = var.survey_hosts } : role => join(" ", [for h in list : "\"${h}\""]) }

  # WordPress requests that must always reach the origin: admin, login, API,
  # previews, and anyone logged in or holding a password/comment cookie.
  wordpress_uncached = join(" or ", [
    "starts_with(http.request.uri.path, \"/wp-admin\")",
    "http.request.uri.path in {\"/wp-login.php\" \"/xmlrpc.php\" \"/wp-cron.php\"}",
    "starts_with(http.request.uri.path, \"/wp-json\")",
    "http.request.uri.query contains \"preview=\"",
    "http.cookie contains \"wordpress_logged_in_\"",
    "http.cookie contains \"wp-postpass_\"",
    "http.cookie contains \"comment_author_\"",
  ])
}

# Browsers follow the origin's Cache-Control (5 minutes for statistics) instead
# of Cloudflare's 4-hour default.
resource "cloudflare_zone_setting" "browser_cache_ttl" {
  zone_id    = local.zone_id
  setting_id = "browser_cache_ttl"
  value      = 0 # 0 = respect existing headers
}

# Show email addresses as written. Cloudflare's default obfuscation replaces them
# with "[email protected]" for visitors without JavaScript (an accessibility
# problem); the published contact address is meant to be read.
resource "cloudflare_zone_setting" "email_obfuscation" {
  zone_id    = local.zone_id
  setting_id = "email_obfuscation"
  value      = "off"
}

# Cloudflare data centres fetch from each other before the origin (free plan).
resource "cloudflare_tiered_cache" "smart" {
  zone_id = local.zone_id
  value   = "on"
}

# Later rules override earlier ones where they match the same request.
resource "cloudflare_ruleset" "cache" {
  zone_id     = local.zone_id
  name        = "itv cache rules"
  description = "Managed by infra/terraform/cloudflare"
  kind        = "zone"
  phase       = "http_request_cache_settings"

  rules = [
    {
      ref         = "stats_respect_origin"
      description = "Public statistics: cache everything, for as long as the origin says"
      expression  = "(http.host in {${local.hosts.stats}})"
      action      = "set_cache_settings"
      action_parameters = {
        cache       = true
        edge_ttl    = { mode = "respect_origin" }
        browser_ttl = { mode = "respect_origin" }
      }
    },
    {
      ref         = "wordpress_anonymous_html"
      description = "WordPress pages for anonymous visitors; errors are never cached"
      expression  = "(http.host in {${local.hosts.wp}}) and not (${local.wordpress_uncached})"
      action      = "set_cache_settings"
      action_parameters = {
        cache = true
        edge_ttl = {
          mode    = "override_origin"
          default = var.wordpress_edge_ttl
          status_code_ttl = [
            { status_code = 404, value = 60 },
            { status_code_range = { from = 500, to = 599 }, value = -1 },
          ]
        }
        browser_ttl = { mode = "respect_origin" }
      }
    },
    {
      ref               = "wordpress_bypass"
      description       = "WordPress admin, login, API, previews and logged-in visitors: never cached"
      expression        = "(http.host in {${local.hosts.wp}}) and (${local.wordpress_uncached})"
      action            = "set_cache_settings"
      action_parameters = { cache = false }
    },
    {
      ref               = "survey_bypass"
      description       = "Survey, gate and admin: per-respondent, never cached"
      expression        = "(http.host in {${local.hosts.survey}})"
      action            = "set_cache_settings"
      action_parameters = { cache = false }
    },
  ]
}
