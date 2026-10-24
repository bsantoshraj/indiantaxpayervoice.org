# One environment's server: a droplet built from the shared cloud-init, a
# firewall that accepts HTTPS only from Cloudflare (SSH key-only), and the
# DigitalOcean project assignment. Environment-specific values are inputs;
# see docs/environments.md for the comparison.

terraform {
  required_providers {
    digitalocean = { source = "digitalocean/digitalocean" }
  }
}

data "digitalocean_project" "itv" {
  name = var.project_name
}

# Keys already registered in the DigitalOcean account (it refuses duplicates).
data "digitalocean_ssh_key" "allowed" {
  for_each = toset(var.ssh_key_names)
  name     = each.value
}

resource "digitalocean_droplet" "this" {
  name       = var.droplet_name
  region     = var.region
  size       = var.droplet_size
  image      = var.image
  ssh_keys   = [for k in data.digitalocean_ssh_key.allowed : k.fingerprint]
  monitoring = true
  ipv6       = true
  backups    = false # encrypted database backups: infra/staging/backup-db.sh
  tags       = ["itv", var.environment]
  user_data  = file("${path.module}/../../staging/cloud-init.yaml")

  # Key and cloud-init edits must not rebuild a running droplet (keys on a live
  # host are synced by scripts/sync-staging-keys.sh). Destroying a droplet
  # deletes its survey data: remove prevent_destroy deliberately if ever needed.
  lifecycle {
    ignore_changes  = [ssh_keys, user_data]
    prevent_destroy = true
  }
}

resource "digitalocean_firewall" "this" {
  name        = "itv-${var.environment}"
  droplet_ids = [digitalocean_droplet.this.id]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = var.admin_cidrs
  }
  # HTTPS only from Cloudflare's edge; port 80 closed (Cloudflare redirects).
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

resource "digitalocean_project_resources" "this" {
  project   = data.digitalocean_project.itv.id
  resources = [digitalocean_droplet.this.urn]
}
