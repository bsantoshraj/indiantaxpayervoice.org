output "zone_id" {
  value = local.zone_id
}

# Not secret: the gate checks Access tokens against these (ITV_ACCESS_* in .env).
output "access_team_domain" {
  value = local.team_domain
}

# Every Access application the origin accepts tokens for (ITV_ACCESS_AUD).
output "staging_access_audiences" {
  value = join(",", [
    cloudflare_zero_trust_access_application.staging_survey_admin.aud,
    cloudflare_zero_trust_access_application.staging_wordpress_admin.aud,
  ])
}

output "staging_survey_admin_aud" {
  value = cloudflare_zero_trust_access_application.staging_survey_admin.aud
}

output "staging_survey_admin_host" {
  value = var.staging_survey_admin_host
}

output "survey_admin_emails" {
  value = join(",", var.survey_admin_emails)
}
