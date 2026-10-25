output "zone_id" {
  value = local.zone_id
}

# Not secret: the gate checks Access tokens against these (ITV_ACCESS_* in .env).
output "access_team_domain" {
  value = local.team_domain
}

# Per environment: every Access application the origin accepts tokens for (ITV_ACCESS_AUD).
output "access_audiences" {
  value = { for env in keys(local.envs) : env => join(",", [
    cloudflare_zero_trust_access_application.survey_admin[env].aud,
    cloudflare_zero_trust_access_application.wordpress_admin[env].aud,
  ]) }
}

output "hosts" {
  value = local.envs
}

output "survey_admin_emails" {
  value = join(",", var.survey_admin_emails)
}

# CI service tokens for private environments: the id is not secret; read the
# secret straight into GitHub, never onto the screen, e.g.
#   terraform output -json ci_access_tokens | jq -r .staging.client_secret | gh secret set STAGING_ACCESS_CLIENT_SECRET
output "ci_access_tokens" {
  sensitive = true
  value = { for env, t in cloudflare_zero_trust_access_service_token.ci : env => {
    client_id     = t.client_id
    client_secret = t.client_secret
  } }
}
