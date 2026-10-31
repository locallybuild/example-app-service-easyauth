provider "azuread" {}

provider "azurerm" {
  features {}
}

module "app-service-easyauth" {
  source = "../../modules/app-service-easyauth"

  name_prefix = "locally-example-easyauth"
  location    = "berlin"
  tags = {
    ProvisionedVia = "Terraform"
  }

  authority_host = var.authority_host
}

variable "authority_host" {
  description = "The Microsoft Entra authority App Service signs users in against: Locally's, using its *.locally name. On Azure, this is https://login.microsoftonline.com."
  type        = string
  default     = "https://auth.locally:5677"
}
