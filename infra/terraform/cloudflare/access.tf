# Admins behind Cloudflare Access, per environment: the LimeSurvey admin on its
# own hostname (Access matches paths, not query strings, and LimeSurvey also
# routes admin via ?r=admin/...), and WordPress /wp-admin and /wp-login.php.
# The origin re-verifies the Access token (gate /access/check), so a
# misconfigured policy alone cannot open either admin.

locals {
  account_id  = data.cloudflare_zone.itv.account.id
  team_domain = "indiantaxpayervoice.cloudflareaccess.com"
}

resource "cloudflare_zero_trust_access_identity_provider" "email_otp" {
  account_id = local.account_id
  name       = "Email one-time code"
  type       = "onetimepin"
  config     = {}
}

resource "cloudflare_zero_trust_access_policy" "survey_admins" {
  account_id       = local.account_id
  name             = "Site administrators (LimeSurvey and WordPress)"
  decision         = "allow"
  include          = [for e in var.survey_admin_emails : { email = { email = e } }]
  session_duration = "8h"
}

resource "cloudflare_zero_trust_access_application" "survey_admin" {
  for_each                   = local.envs
  account_id                 = local.account_id
  name                       = "LimeSurvey admin (${each.key})"
  type                       = "self_hosted"
  domain                     = each.value.survey_admin
  session_duration           = "8h"
  allowed_idps               = [cloudflare_zero_trust_access_identity_provider.email_otp.id]
  auto_redirect_to_identity  = true
  app_launcher_visible       = false
  http_only_cookie_attribute = true
  same_site_cookie_attribute = "lax"
  policies                   = [{ id = cloudflare_zero_trust_access_policy.survey_admins.id, precedence = 1 }]
}

# Nothing public uses admin-ajax.php (checked), so all of /wp-admin is covered.
resource "cloudflare_zero_trust_access_application" "wordpress_admin" {
  for_each   = local.envs
  account_id = local.account_id
  name       = "WordPress admin (${each.key})"
  type       = "self_hosted"
  destinations = [
    { type = "public", uri = "${each.value.website}/wp-admin" },
    { type = "public", uri = "${each.value.website}/wp-login.php" },
  ]
  session_duration           = "8h"
  allowed_idps               = [cloudflare_zero_trust_access_identity_provider.email_otp.id]
  auto_redirect_to_identity  = true
  app_launcher_visible       = false
  http_only_cookie_attribute = true
  same_site_cookie_attribute = "lax"
  policies                   = [{ id = cloudflare_zero_trust_access_policy.survey_admins.id, precedence = 1 }]
}

moved {
  from = cloudflare_zero_trust_access_application.staging_survey_admin
  to   = cloudflare_zero_trust_access_application.survey_admin["staging"]
}
moved {
  from = cloudflare_zero_trust_access_application.staging_wordpress_admin
  to   = cloudflare_zero_trust_access_application.wordpress_admin["staging"]
}

# Private environments (staging): the whole site, survey and statistics need
# Access, so drafts and test data are never public. Admins sign in with the
# email code; CI's smoke tests present a service token (CF-Access-Client-Id /
# CF-Access-Client-Secret headers). The admin applications above still apply to
# their paths and hostname, and they do not accept the service token.
locals {
  private_envs = { for env, e in local.envs : env => e if e.private }
}

resource "cloudflare_zero_trust_access_service_token" "ci" {
  for_each   = local.private_envs
  account_id = local.account_id
  name       = "CI smoke tests (${each.key})"
  duration   = "8760h"
}

resource "cloudflare_zero_trust_access_policy" "ci" {
  for_each   = local.private_envs
  account_id = local.account_id
  name       = "CI service token (${each.key})"
  decision   = "non_identity"
  include    = [{ service_token = { token_id = cloudflare_zero_trust_access_service_token.ci[each.key].id } }]
}

resource "cloudflare_zero_trust_access_application" "private_site" {
  for_each   = local.private_envs
  account_id = local.account_id
  name       = "Private environment (${each.key})"
  type       = "self_hosted"
  destinations = [
    { type = "public", uri = each.value.website },
    { type = "public", uri = each.value.survey },
    { type = "public", uri = each.value.stats },
  ]
  session_duration           = "8h"
  allowed_idps               = [cloudflare_zero_trust_access_identity_provider.email_otp.id]
  auto_redirect_to_identity  = true
  app_launcher_visible       = false
  http_only_cookie_attribute = true
  same_site_cookie_attribute = "lax"
  policies = [
    { id = cloudflare_zero_trust_access_policy.survey_admins.id, precedence = 1 },
    { id = cloudflare_zero_trust_access_policy.ci[each.key].id, precedence = 2 },
  ]
}
