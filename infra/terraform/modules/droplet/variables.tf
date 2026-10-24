variable "environment" {
  description = "staging or production (tags the droplet and names the firewall)"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production."
  }
}

variable "droplet_name" {
  type = string
}

variable "droplet_size" {
  description = "DigitalOcean size slug, e.g. s-1vcpu-2gb-amd (Premium AMD 2 GB)"
  type        = string
}

variable "region" {
  description = "Bangalore is closest to respondents"
  type        = string
  default     = "blr1"
}

variable "image" {
  type    = string
  default = "ubuntu-24-04-x64"
}

variable "project_name" {
  description = "Existing DigitalOcean project to attach the droplet to"
  type        = string
  default     = "indiantaxpayervoice.org"
}

variable "ssh_key_names" {
  description = "DigitalOcean account SSH keys that may log in (as deploy)"
  type        = list(string)
}

variable "admin_cidrs" {
  description = "Addresses allowed to SSH in. Default: anywhere, relying on key-only auth (owner has a dynamic IP)"
  type        = list(string)
  default     = ["0.0.0.0/0", "::/0"]
}

variable "cloudflare_cidrs" {
  description = "Cloudflare edge ranges (cloudflare.com/ips-v4, /ips-v6, fetched 2026-10-24); keep in sync with infra/staging/Caddyfile*"
  type        = list(string)
  default = [
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22",
    "141.101.64.0/18", "108.162.192.0/18", "190.93.240.0/20", "188.114.96.0/20",
    "197.234.240.0/22", "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
    "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
    "2400:cb00::/32", "2606:4700::/32", "2803:f800::/32", "2405:b500::/32",
    "2405:8100::/32", "2a06:98c0::/29", "2c0f:f248::/32",
  ]
}
