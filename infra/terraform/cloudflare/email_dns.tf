# Email authentication and certificate issuance for the zone.

# SPF: only Google Workspace sends mail as @indiantaxpayervoice.org (the servers
# send none), so anything else fails hard. Created by hand originally; imported.
resource "cloudflare_dns_record" "spf" {
  zone_id = local.zone_id
  name    = var.zone_name
  type    = "TXT"
  content = "\"v=spf1 include:_spf.google.com -all\""
  ttl     = 1
  comment = "SPF: Google Workspace only; managed by infra/terraform/cloudflare"
}

import {
  to = cloudflare_dns_record.spf
  id = "b89e9d6516c6eeea34e4a2572677ed22/589a4d496e817c5b7950d6254e799418"
}

# DMARC: start with p=none and aggregate reports to the contact mailbox; after
# about two weeks of clean reports, move to p=quarantine (docs/operations.md).
resource "cloudflare_dns_record" "dmarc" {
  zone_id = local.zone_id
  name    = "_dmarc.${var.zone_name}"
  type    = "TXT"
  content = "\"v=DMARC1; p=${var.dmarc_policy}; rua=mailto:${var.dmarc_reports}; adkim=s; aspf=s; fo=1\""
  ttl     = 1
  comment = "DMARC; managed by infra/terraform/cloudflare"
}

# CAA: only the CAs Cloudflare uses for edge certificates may issue for this
# domain. (The origin certificate comes from Cloudflare's private Origin CA,
# which CAA does not cover.) Violations are reported to the contact mailbox.
locals {
  caa = merge(
    { for ca in ["letsencrypt.org", "pki.goog", "ssl.com", "digicert.com", "sectigo.com", "comodoca.com"] : "issue ${ca}" => { tag = "issue", value = ca } },
    { for ca in ["letsencrypt.org", "pki.goog", "ssl.com", "digicert.com", "sectigo.com", "comodoca.com"] : "issuewild ${ca}" => { tag = "issuewild", value = ca } },
    { "iodef" = { tag = "iodef", value = "mailto:${var.dmarc_reports}" } },
  )
}

resource "cloudflare_dns_record" "caa" {
  for_each = local.caa
  zone_id  = local.zone_id
  name     = var.zone_name
  type     = "CAA"
  ttl      = 1
  data     = { flags = 0, tag = each.value.tag, value = each.value.value }
  comment  = "CAA; managed by infra/terraform/cloudflare"
}
