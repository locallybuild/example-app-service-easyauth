output "application_url" {
  description = "Where to reach the application in a browser."
  value       = module.app-service-easyauth.application_url
}

output "application_id_uri" {
  description = "The app registration's application ID URI, to request an access token for the app with."
  value       = module.app-service-easyauth.application_id_uri
}
