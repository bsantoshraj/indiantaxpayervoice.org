terraform {
  required_version = ">= 1.9.0"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "= 2.104.0"
    }
  }
}

# Token comes from the DIGITALOCEAN_TOKEN environment variable (never a file in git).
provider "digitalocean" {}
