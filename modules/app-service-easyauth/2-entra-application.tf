data "azuread_client_config" "current" {}

# ---------------------------------------------------------------------------
# App registration - the identity App Service signs users in with.
#
# App Service Authentication is configured entirely from this registration
# (see auth_settings_v2 in 3-app-service.tf): there are no WEBSITE_AUTH_*
# app settings to set by hand.
# ---------------------------------------------------------------------------
resource "azuread_application" "main" {
  display_name = "${var.name_prefix} EasyAuth"
  owners       = [data.azuread_client_config.current.object_id]

  web {
    implicit_grant {
      # App Service reads the user's identity from the ID token.
      id_token_issuance_enabled = true
    }
  }

  lifecycle {
    # Managed by azuread_application_identifier_uri and
    # azuread_application_redirect_uris below.
    ignore_changes = [identifier_uris, web[0].redirect_uris]
  }
}

# The application ID URI, api://<client id>, which callers use to request an
# access token for this app - see /api/whoami in the README.
resource "azuread_application_identifier_uri" "main" {
  application_id = azuread_application.main.id
  identifier_uri = "api://${azuread_application.main.client_id}"
}

# The redirect URI App Service's sign-in callback lives at. It's added once the
# Web App exists, as it's built from the Web App's hostname.
resource "azuread_application_redirect_uris" "main" {
  application_id = azuread_application.main.id
  type           = "Web"
  redirect_uris  = ["https://${azurerm_linux_web_app.main.default_hostname}/.auth/login/aad/callback"]
}

resource "azuread_service_principal" "main" {
  client_id = azuread_application.main.client_id
  owners    = [data.azuread_client_config.current.object_id]
}

# The client secret App Service redeems the sign-in code with. With it, the
# token store also holds an access token and a refresh token, not just the ID
# token.
resource "azuread_application_password" "main" {
  application_id = azuread_application.main.id
  display_name   = "App Service Authentication"
}
