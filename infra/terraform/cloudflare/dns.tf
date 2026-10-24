# DNS for every environment's hostnames, pointing at that environment's droplet
# (IP from its Terraform state). All proxied: the origins accept only Cloudflare,
# and their Origin CA certificate is trusted only by Cloudflare.

data "terraform_remote_state" "env" {
  for_each = local.envs
  backend  = "local"
  config   = { path = "${path.module}/../${each.key}/terraform.tfstate" }
}

locals {
  dns_records = merge([for env, e in local.envs : merge(
    { for role in ["website", "survey", "survey_admin", "stats"] : "${env}/${role}" => { env = env, name = e[role] } },
    e.www_redirect ? { "${env}/www" = { env = env, name = "www.${e.website}" } } : {}
  )]...)
}

resource "cloudflare_dns_record" "host" {
  for_each = local.dns_records
  zone_id  = local.zone_id
  name     = each.value.name
  type     = "A"
  content  = data.terraform_remote_state.env[each.value.env].outputs.ip
  proxied  = true
  ttl      = 1
  comment  = "${each.value.env}: managed by infra/terraform/cloudflare"
}

# Staging's first three records were created by hand before this file existed.
import {
  to = cloudflare_dns_record.host["staging/website"]
  id = "b89e9d6516c6eeea34e4a2572677ed22/11bb3f92a21a343d3e6d581302393669"
}
import {
  to = cloudflare_dns_record.host["staging/stats"]
  id = "b89e9d6516c6eeea34e4a2572677ed22/d0fffa381978ecc50ab770631a6de8c8"
}
import {
  to = cloudflare_dns_record.host["staging/survey"]
  id = "b89e9d6516c6eeea34e4a2572677ed22/9ed6a4afa257265f8e365d832efe80e6"
}
moved {
  from = cloudflare_dns_record.staging_survey_admin
  to   = cloudflare_dns_record.host["staging/survey_admin"]
}

# The www -> website redirect is served by Caddy at the origin (the API token has
# no Redirect Rules permission); the DNS record above routes www through Cloudflare.
