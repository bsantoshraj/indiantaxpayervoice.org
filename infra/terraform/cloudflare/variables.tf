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
  default     = ["survey-staging.indiantaxpayervoice.org"]
}

variable "wordpress_edge_ttl" {
  description = "Seconds an anonymous WordPress page stays at the edge (deploys purge it)"
  type        = number
  default     = 600
}
