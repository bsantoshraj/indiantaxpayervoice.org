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
