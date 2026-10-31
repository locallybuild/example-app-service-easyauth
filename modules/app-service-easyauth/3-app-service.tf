# ---------------------------------------------------------------------------
# The application, zipped for deployment.
# ---------------------------------------------------------------------------
locals {
  app_dir = "${path.module}/../../app"

  # A hash of the app's files. It names the zip, as App Service only deploys
  # zip_deploy_file again when its path changes.
  app_hash = sha1(join("", [for f in sort(fileset(local.app_dir, "*.py")) : filesha1("${local.app_dir}/${f}")]))
}

data "archive_file" "app" {
  type        = "zip"
  source_dir  = local.app_dir
  output_path = "${path.module}/../../.build/app-${local.app_hash}.zip"
  excludes    = ["__pycache__"]
}

# ---------------------------------------------------------------------------
# App Service Plan - houses the Web App.
# ---------------------------------------------------------------------------
resource "azurerm_service_plan" "main" {
  name                = "${var.name_prefix}-plan"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = var.app_service_sku
}

# ---------------------------------------------------------------------------
# Linux Web App - runs the Python app, with App Service Authentication in front.
# ---------------------------------------------------------------------------
resource "azurerm_linux_web_app" "main" {
  name                = "${var.name_prefix}-app"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_service_plan.main.location
  service_plan_id     = azurerm_service_plan.main.id
  https_only          = true
  tags                = var.tags

  zip_deploy_file = data.archive_file.app.output_path

  site_config {
    # No startup command: App Service serves the WSGI app in app.py with
    # gunicorn.
    application_stack {
      python_version = "3.12"
    }
  }

  app_settings = {
    # The app has no dependencies, so there's nothing to build on deploy.
    SCM_DO_BUILD_DURING_DEPLOYMENT = "false"

    # The app registration's client secret, which auth_settings_v2 refers to
    # by this setting's name.
    MICROSOFT_PROVIDER_AUTHENTICATION_SECRET = azuread_application_password.main.value
  }

  auth_settings_v2 {
    auth_enabled           = true
    require_authentication = true
    unauthenticated_action = "RedirectToLoginPage"
    default_provider       = "azureactivedirectory"

    # The page the app sends you to after signing out, which has to be
    # reachable without signing in.
    excluded_paths = ["/signed-out"]

    active_directory_v2 {
      client_id                  = azuread_application.main.client_id
      client_secret_setting_name = "MICROSOFT_PROVIDER_AUTHENTICATION_SECRET"
      tenant_auth_endpoint       = "${var.authority_host}/${data.azuread_client_config.current.tenant_id}/v2.0"

      # Accept access tokens requested for the app ID URI, as well as for the
      # client ID, from callers that send a bearer token.
      allowed_audiences = ["api://${azuread_application.main.client_id}"]
    }

    login {
      # Keep the tokens App Service obtains at sign-in, and pass them to the app
      # in the X-MS-TOKEN-AAD-* headers.
      token_store_enabled = true
    }
  }
}
