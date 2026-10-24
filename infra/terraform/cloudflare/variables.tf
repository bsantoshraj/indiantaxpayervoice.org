variable "zone_name" {
  type    = string
  default = "indiantaxpayervoice.org"
}

# One list per role, so production hostnames are added here when it exists.
variable "wordpress_hosts" {
  description = "Hostnames served by WordPress (HTML cached at the edge for anonymous visitors)"
  type        = list(string)
  default     = ["staging.indiantaxpayervoice.org"]
}

variable "stats_hosts" {
  description = "Hostnames serving public statistics (cached per the origin's Cache-Control)"
  type        = list(string)
  default     = ["stats-staging.indiantaxpayervoice.org"]
}

variable "survey_hosts" {
  description = "Hostnames serving the survey and its admin: never cached"
  type        = list(string)
  default     = ["survey-staging.indiantaxpayervoice.org", "survey-admin-staging.indiantaxpayervoice.org"]
}

variable "wordpress_edge_ttl" {
  description = "Seconds an anonymous WordPress page stays at the edge (deploys purge it)"
  type        = number
  default     = 600
}

variable "staging_survey_admin_host" {
  description = "LimeSurvey admin hostname for staging (Cloudflare Access protected)"
  type        = string
  default     = "survey-admin-staging.indiantaxpayervoice.org"
}

variable "survey_admin_emails" {
  description = "Email addresses allowed into the LimeSurvey and WordPress admins (one-time code login)"
  type        = list(string)
  default     = ["hello@indiantaxpayervoice.org"]
}

variable "public_survey_hosts" {
  description = "Hostnames where the public takes the survey (admin routes blocked at the edge)"
  type        = list(string)
  default     = ["survey-staging.indiantaxpayervoice.org"]
}

variable "survey_posts_per_10s" {
  description = "Edge limit on survey POSTs per IP per 10 s (CGNAT: many users can share one IP)"
  type        = number
  default     = 50
}

variable "staging_wordpress_host" {
  description = "WordPress host whose /wp-admin and /wp-login.php sit behind Cloudflare Access"
  type        = string
  default     = "staging.indiantaxpayervoice.org"
}
