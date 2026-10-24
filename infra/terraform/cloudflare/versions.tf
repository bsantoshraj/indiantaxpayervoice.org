terraform {
  required_version = ">= 1.9.0"
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "= 5.28.1"
    }
  }
}

# Token comes from the CLOUDFLARE_API_TOKEN environment variable (never a file in git).
provider "cloudflare" {}
