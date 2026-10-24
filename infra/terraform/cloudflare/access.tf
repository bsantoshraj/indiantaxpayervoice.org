# LimeSurvey admin behind Cloudflare Access. The admin has its own hostname so
# Access can cover all of it (Access matches paths, not query strings, and
# LimeSurvey also routes admin via ?r=admin/...). The public survey hostname
# refuses every admin route at nginx, and the origin re-verifies the Access
# token (gate /access/check), so a misconfigured policy alone cannot open it.

data "terraform_remote_state" "staging" {
  backend = "local"
  config  = { path = "${path.module}/../staging/terraform.tfstate" }
}

locals {
  account_id  = data.cloudflare_zone.itv.account.id
  team_domain = "indiantaxpayervoice.cloudflareaccess.com"
}

resource "cloudflare_dns_record" "staging_survey_admin" {
  zone_id = local.zone_id
  name    = var.staging_survey_admin_host
  type    = "A"
  content = data.terraform_remote_state.staging.outputs.ip
  proxied = true # required: the origin accepts only Cloudflare, and Access runs at the edge
  ttl     = 1
  comment = "LimeSurvey admin (staging), behind Cloudflare Access"
}

resource "cloudflare_zero_trust_access_identity_provider" "email_otp" {
  account_id = local.account_id
  name       = "Email one-time code"
  type       = "onetimepin"
  config     = {}
}

resource "cloudflare_zero_trust_access_policy" "survey_admins" {
  account_id       = local.account_id
  name             = "LimeSurvey administrators"
  decision         = "allow"
  include          = [for e in var.survey_admin_emails : { email = { email = e } }]
  session_duration = "8h"
}

resource "cloudflare_zero_trust_access_application" "staging_survey_admin" {
  account_id                 = local.account_id
  name                       = "LimeSurvey admin (staging)"
  type                       = "self_hosted"
  domain                     = var.staging_survey_admin_host
  session_duration           = "8h"
  allowed_idps               = [cloudflare_zero_trust_access_identity_provider.email_otp.id]
  auto_redirect_to_identity  = true
  app_launcher_visible       = false
  http_only_cookie_attribute = true
  same_site_cookie_attribute = "lax"
  policies                   = [{ id = cloudflare_zero_trust_access_policy.survey_admins.id, precedence = 1 }]
}
