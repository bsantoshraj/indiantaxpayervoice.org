output "ip" {
  value = digitalocean_droplet.this.ipv4_address
}

# Public keys only (not secret), used by scripts/sync-staging-keys.sh.
output "authorized_keys" {
  value = join("\n", [for k in data.digitalocean_ssh_key.allowed : trimspace(k.public_key)])
}
