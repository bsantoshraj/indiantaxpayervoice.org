variable "project_name" {
  description = "Existing DigitalOcean project to attach resources to"
  type        = string
  default     = "indiantaxpayervoice.org"
}

variable "region" {
  description = "Bangalore is closest to respondents"
  type        = string
  default     = "blr1"
}

variable "droplet_size" {
  description = "Premium (NVMe) 2 GB droplet"
  type        = string
  default     = "s-1vcpu-2gb-amd"
}

variable "image" {
  type    = string
  default = "ubuntu-24-04-x64"
}

variable "ssh_public_key_path" {
  type    = string
  default = "~/.ssh/id_rsa.pub"
}

variable "admin_cidrs" {
  description = "Addresses allowed to SSH in. Default: anywhere, relying on key-only auth (owner has a dynamic IP)"
  type        = list(string)
  default     = ["0.0.0.0/0", "::/0"]
}

variable "extra_ssh_key_names" {
  description = "Existing DigitalOcean account SSH keys that may also log in (as deploy)"
  type        = list(string)
  default     = ["santosh-new", "mac-key", "newfold-laptop-santosh", "TSE1"]
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
