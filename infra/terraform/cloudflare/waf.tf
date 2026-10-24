# Edge protection (Cloudflare Free plan: managed free ruleset, 5 custom rules,
# 1 rate-limiting rule with a 10 s window). The origin enforces the same limits
# again (nginx rate limits, admin 404s), so these rules reduce load and noise;
# they are not the only control.

locals {
  public_survey_hosts = join(" ", [for h in var.public_survey_hosts : "\"${h}\""])
}

resource "cloudflare_ruleset" "managed_waf" {
  zone_id     = local.zone_id
  name        = "itv managed WAF"
  description = "Managed by infra/terraform/cloudflare"
  kind        = "zone"
  phase       = "http_request_firewall_managed"
  rules = [{
    ref               = "cloudflare_free_managed"
    description       = "Cloudflare Managed Free Ruleset (high-impact, widely exploited vulnerabilities)"
    expression        = "true"
    action            = "execute"
    action_parameters = { id = "77454fe2d30c4220b5701f6fdfb893ba" }
  }]
}

resource "cloudflare_ruleset" "custom_waf" {
  zone_id     = local.zone_id
  name        = "itv custom WAF"
  description = "Managed by infra/terraform/cloudflare"
  kind        = "zone"
  phase       = "http_request_firewall_custom"
  rules = [
    {
      ref         = "block_xmlrpc"
      description = "WordPress XML-RPC: unused, and a common brute-force and amplification target"
      expression  = "(http.host in {${local.hosts.wp}} and http.request.uri.path eq \"/xmlrpc.php\")"
      action      = "block"
    },
    {
      ref         = "block_public_survey_admin"
      description = "LimeSurvey admin routes on the public survey host (the admin has its own Access host; the origin also returns 404)"
      expression = join(" ", [
        "(http.host in {${local.public_survey_hosts}}) and (",
        "starts_with(lower(http.request.uri.path), \"/admin\") or",
        "starts_with(lower(http.request.uri.path), \"/index.php/admin\") or",
        "starts_with(lower(http.request.uri.path), \"/index.php/rest\") or",
        "starts_with(lower(http.request.uri.path), \"/index.php/installer\") or",
        "lower(http.request.uri.query) contains \"r=admin\" or",
        "lower(http.request.uri.query) contains \"r=/admin\" or",
        "lower(http.request.uri.query) contains \"r=rest\")",
      ])
      action = "block"
    },
    {
      ref         = "allowed_methods"
      description = "Only the methods each host needs: statistics are read-only"
      expression = join(" ", [
        "(http.host in {${local.hosts.stats}} and not http.request.method in {\"GET\" \"HEAD\" \"OPTIONS\"}) or",
        "(http.host in {${local.hosts.wp} ${local.hosts.survey}} and not http.request.method in {\"GET\" \"HEAD\" \"POST\"})",
      ])
      action = "block"
    },
  ]
}

# Survey answers and bot-check verifications per visitor IP (per Cloudflare data
# centre). Generous on purpose: Indian mobile carriers put many people behind one
# IP (CGNAT). A respondent submits one page every few seconds at most.
resource "cloudflare_ruleset" "rate_limit" {
  zone_id     = local.zone_id
  name        = "itv rate limiting"
  description = "Managed by infra/terraform/cloudflare"
  kind        = "zone"
  phase       = "http_ratelimit"
  rules = [{
    ref         = "survey_posts"
    description = "Survey answer submissions and gate verifications per IP"
    expression  = "(http.host in {${local.public_survey_hosts}} and http.request.method eq \"POST\")"
    action      = "block"
    ratelimit = {
      characteristics     = ["cf.colo.id", "ip.src"]
      period              = 10
      requests_per_period = var.survey_posts_per_10s
      mitigation_timeout  = 10
    }
  }]
}
