variable "zone_name" {
  type    = string
  default = "indiantaxpayervoice.org"
}

# Every environment served from this zone and its hostnames. DNS, Access, cache
# rules, WAF and rate limiting are generated from this map; docs/environments.md
# compares the environments (local dev is Docker Compose and not managed here).
variable "environments" {
  type = map(object({
    website      = string
    survey       = string
    survey_admin = string
    stats        = string
    www_redirect = bool # also serve www.<website> as a redirect to the website
  }))
  default = {
    staging = {
      website      = "staging.indiantaxpayervoice.org"
      survey       = "survey-staging.indiantaxpayervoice.org"
      survey_admin = "survey-admin-staging.indiantaxpayervoice.org"
      stats        = "stats-staging.indiantaxpayervoice.org"
      www_redirect = false
    }
    production = {
      website      = "indiantaxpayervoice.org"
      survey       = "survey.indiantaxpayervoice.org"
      survey_admin = "survey-admin.indiantaxpayervoice.org"
      stats        = "stats.indiantaxpayervoice.org"
      www_redirect = true
    }
  }
}

variable "wordpress_edge_ttl" {
  description = "Seconds an anonymous WordPress page stays at the edge (deploys purge it)"
  type        = number
  default     = 600
}

variable "survey_admin_emails" {
  description = "Email addresses allowed into the LimeSurvey and WordPress admins (one-time code login), in every environment"
  type        = list(string)
  default     = ["hello@indiantaxpayervoice.org"]
}

variable "survey_posts_per_10s" {
  description = "Edge limit on survey POSTs per IP per 10 s (CGNAT: many users can share one IP)"
  type        = number
  default     = 50
}
