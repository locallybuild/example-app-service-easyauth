```
ooooo                                      oooo  oooo              
`888'                                      `888  `888              
 888          .ooooo.   .ooooo.   .oooo.    888   888  oooo    ooo 
 888         d88' `88b d88' `"Y8 `P  )88b   888   888   `88.  .8'
 888         888   888 888        .oP"888   888   888    `88..8'
 888       o 888   888 888   .o8 d8(  888   888   888     `888'
o888ooooood8 `Y8bod8P' `Y8bod8P' `Y888""8o o888o o888o     .8'
                                                       .o..P'
                                                       `Y8P'
```


# Example: Sign in to an App Service app with App Service Authentication within Locally

This example shows how to put [App Service Authentication](https://learn.microsoft.com/azure/app-service/overview-authentication-authorization) (also known as EasyAuth) in front of an App Service app, on [Locally Build](https://locally.build).

The application is a small Python app, run on App Service's Python 3.14 stack, whose only job is to show what App Service Authentication hands it. App Service signs the user in before a request reaches the app, then passes who they are in the `X-MS-CLIENT-PRINCIPAL*` headers and, with the token store enabled, the tokens it obtained in the `X-MS-TOKEN-AAD-*` headers. The app does no authentication of its own. The source lives in [`app/`](./app) in this repository.

Sign-in uses a Microsoft Entra app registration, created by this example against Locally's [Directory Emulator](https://locally.build/docs/data-plane-emulators/directory-emulator). App Service Authentication is configured entirely from that registration through `auth_settings_v2`, the same as on Azure: there are no `WEBSITE_AUTH_*` app settings to set by hand.

Once deployed, the app has:

| Path | What it does |
|---|---|
| `/` | Requires sign-in. Shows who you're signed in as, your claims, and the ID token, access token and refresh token App Service obtained. |
| `/api/whoami` | Requires sign-in. Returns the caller's identity as JSON, for calling with a bearer token rather than from a browser. |
| `/signed-out` | Where signing out takes you. Doesn't require sign-in. |
| `/.auth/login/aad`, `/.auth/logout`, `/.auth/me` | Provided by App Service Authentication. |

## Requirements

* [Locally Build](https://locally.build).
* Either [HashiCorp Terraform](https://terraform.io) or [OpenTofu](https://opentofu.org).
* Either [Docker](https://www.docker.com) or [Podman](https://podman.io) (recommended).
* The Locally Plugin for `Microsoft.Web` installed (`locally plugin install --name Microsoft.Web`).

## Running the example

First up, we need to ensure our container runtime (Docker or Podman) is running, then launch Locally:

```bash
locally build
```

With Locally running, in another terminal we can initialise Terraform, which both downloads the providers we need and configures the module for use:

```bash
cd environments/locally
terraform init
```

> [!NOTE]
> It's possible to use OpenTofu here by substituting `terraform` for `tofu`.

With Terraform initialised, we can then provision the example by running:

```bash
locally run terraform apply
```

Once you approve the plan and the resources have been deployed, the application is running at the URL in the outputs:

```
https://locally-example-easyauth-app.furnace.locally:5663
```

### Signing in with a browser

[Open that URL in a browser](https://locally-example-easyauth-app.furnace.locally:5663) and App Service Authentication sends you to Locally's Directory sign-in, where you can pick which identity to sign in as. Since this is within Locally we're not concerned with you knowing the username or password for the user (although you can use it if you want) - just pick the identity you want and you're in.

You're then returned to the app, which shows who you're signed in as, your claims, and the tokens App Service passed it. **Sign out** takes you to `/signed-out`, and opening the app again asks you to sign in.

### Calling the app with a bearer token

Code calls an App Service Authentication-protected API by sending an access token for the app's registration. Request one for the app's application ID URI (in the outputs), then send it as a bearer token:

```bash
TOKEN=$(locally run az account get-access-token --resource "$(terraform output -raw application_id_uri)" --query accessToken -o tsv)
curl -H "Authorization: Bearer $TOKEN" https://locally-example-easyauth-app.furnace.locally:5663/api/whoami
```

App Service validates the token and passes the caller's identity to the app, which returns it:

```json
{
  "name": "<the caller's name>",
  "id": "<the caller's object ID>",
  "identityProvider": "aad",
  "claims": {
    "aud": "api://<client id>",
    "idtyp": "app",
    ...
  }
}
```

A request without a token, or with a token for a different audience, is refused with a `401`.

## Running this on Azure

The same module deploys to Azure. Point `authority_host` at `https://login.microsoftonline.com` and use one of Azure's regions for `location`.

## Tearing it down

```bash
cd environments/locally
locally run terraform destroy
```
