# Staging: one droplet running WordPress and the survey stack in Docker, with
# MariaDB installed on the host. No secrets pass through Terraform (state
# would store them); the deploy script generates them on the droplet.

data "digitalocean_project" "itv" {
  name = var.project_name
}

resource "digitalocean_ssh_key" "admin" {
  name       = "itv-staging-admin"
  public_key = file(pathexpand(var.ssh_public_key_path))
}

data "digitalocean_ssh_key" "extra" {
  for_each = toset(var.extra_ssh_key_names)
  name     = each.value
}

resource "digitalocean_droplet" "staging" {
  name       = "itv-staging-1"
  region     = var.region
  size       = var.droplet_size
  image      = var.image
  ssh_keys   = concat([digitalocean_ssh_key.admin.fingerprint], [for k in data.digitalocean_ssh_key.extra : k.fingerprint])
  monitoring = true
  ipv6       = true
  backups    = false # staging holds no real data
  tags       = ["itv", "staging"]
  user_data  = file("${path.module}/cloud-init.yaml")

  # Key and cloud-init edits must not rebuild a running droplet; keys on a live
  # host are synced by scripts/sync-staging-keys.sh instead.
  lifecycle {
    ignore_changes = [ssh_keys, user_data]
  }
}

# HTTPS accepts only Cloudflare's edge, so the origin cannot be reached (or the
# gate and rate limits bypassed) by IP. Port 80 is closed: Cloudflare's "Always
# Use HTTPS" redirects at the edge. (The Let's Encrypt fallback Caddyfile needs
# 80/443 open to the internet and does not work behind this firewall.)
resource "digitalocean_firewall" "staging" {
  name        = "itv-staging"
  droplet_ids = [digitalocean_droplet.staging.id]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = var.admin_cidrs
  }
  inbound_rule {
    protocol         = "tcp"
    port_range       = "443"
    source_addresses = var.cloudflare_cidrs
  }
  # MariaDB (3306) is deliberately not opened: only containers on the host reach it.

  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

resource "digitalocean_project_resources" "staging" {
  project   = data.digitalocean_project.itv.id
  resources = [digitalocean_droplet.staging.urn]
}
