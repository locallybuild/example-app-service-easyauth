output "application_url" {
  description = "Where to reach the application in a browser."
  value       = "https://${azurerm_linux_web_app.main.default_hostname}"
}

output "application_id_uri" {
  description = "The app registration's application ID URI, to request an access token for the app with."
  value       = azuread_application_identifier_uri.main.identifier_uri
}

output "resource_group" {
  description = "The resource group containing the deployed resources."
  value       = azurerm_resource_group.main.name
}
