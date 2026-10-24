# Staging environment. Everything except the values below is shared through
# ../modules/droplet; docs/environments.md compares dev, staging and production.

module "env" {
  source        = "../modules/droplet"
  environment   = "staging"
  droplet_name  = "itv-staging-1"
  droplet_size  = "s-1vcpu-2gb-amd" # Premium AMD 1 vCPU / 2 GB, US$14/month
  ssh_key_names = ["itv-staging-admin", "santosh-new", "mac-key", "newfold-laptop-santosh", "TSE1"]
}

# Resources created before the shared module existed keep their identity.
moved {
  from = digitalocean_droplet.staging
  to   = module.env.digitalocean_droplet.this
}
moved {
  from = digitalocean_firewall.staging
  to   = module.env.digitalocean_firewall.this
}
moved {
  from = digitalocean_project_resources.staging
  to   = module.env.digitalocean_project_resources.this
}

# The admin key was registered in DigitalOcean by this configuration; it is now
# referenced by name ("itv-staging-admin") from the module. Stop managing it here
# without deleting it from the account.
removed {
  from = digitalocean_ssh_key.admin
  lifecycle {
    destroy = false
  }
}
