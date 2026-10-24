output "ip" {
  value = module.env.ip
}

output "ssh" {
  value = "ssh deploy@${module.env.ip}"
}

# Public keys only (not secret), used by scripts/sync-staging-keys.sh.
output "authorized_keys" {
  value = module.env.authorized_keys
}
