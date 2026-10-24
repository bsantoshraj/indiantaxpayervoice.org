output "ip" {
  value = digitalocean_droplet.staging.ipv4_address
}

output "ssh" {
  value = "ssh deploy@${digitalocean_droplet.staging.ipv4_address}"
}

# Proxied by Cloudflare (Origin CA certificate on the droplet).
output "urls" {
  value = {
    website = "https://staging.indiantaxpayervoice.org"
    survey  = "https://survey-staging.indiantaxpayervoice.org"
    stats   = "https://stats-staging.indiantaxpayervoice.org"
  }
}

# Public keys only (not secret), used by scripts/sync-staging-keys.sh.
output "authorized_keys" {
  value = join("\n", concat([trimspace(digitalocean_ssh_key.admin.public_key)], [for k in data.digitalocean_ssh_key.extra : trimspace(k.public_key)]))
}
