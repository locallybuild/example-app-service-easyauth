"""A small app that shows what App Service Authentication (EasyAuth) hands it.

App Service signs the user in before a request reaches the app, then passes
who they are in the X-MS-CLIENT-PRINCIPAL* headers and, with the token store
enabled, the tokens it obtained in X-MS-TOKEN-AAD-*. The app does no
authentication of its own: it only reads those headers.

It's a WSGI app named `app` in app.py, which App Service's Python stack
serves with gunicorn without a startup command. It uses only the standard
library, so there's nothing to install. Run `python app.py` to try it locally.
"""

import base64
import html
import json
import os
from wsgiref.simple_server import make_server


def principal(headers):
    """Decodes X-MS-CLIENT-PRINCIPAL, the base64 JSON App Service sends with
    the signed-in identity's provider and claims. None when not signed in."""
    encoded = headers.get("X-MS-CLIENT-PRINCIPAL")
    if not encoded:
        return None
    return json.loads(base64.b64decode(encoded))


def claims(p):
    """The principal's claims as (type, value) pairs."""
    return [(c.get("typ", ""), c.get("val", "")) for c in (p or {}).get("claims", [])]


def jwt_payload(token):
    """Decodes a JWT's payload for display. App Service has already validated
    the token, so the signature isn't checked here."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except (IndexError, ValueError):
        return None


def tokens(headers):
    """The tokens App Service's token store passes to the app."""
    found = {}
    for name in ("ID-TOKEN", "ACCESS-TOKEN", "REFRESH-TOKEN", "EXPIRES-ON"):
        value = headers.get(f"X-MS-TOKEN-AAD-{name}")
        if value:
            found[name.lower()] = value
    return found


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>App Service Authentication</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 60rem; margin: 2rem auto; padding: 0 1rem; color: #1f2328; }}
  h1 {{ font-size: 1.5rem; }}
  h2 {{ font-size: 1.1rem; margin-top: 2rem; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; }}
  td {{ border-top: 1px solid #d0d7de; padding: 0.35rem 0.5rem; vertical-align: top; word-break: break-all; }}
  td:first-child {{ width: 14rem; color: #59636e; }}
  pre {{ background: #f6f8fa; padding: 0.75rem; overflow-x: auto; font-size: 0.8rem; }}
  .button {{ display: inline-block; padding: 0.4rem 0.9rem; border-radius: 6px; background: #0969da; color: #fff; text-decoration: none; }}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def signed_in_page(headers):
    p = principal(headers)
    name = headers.get("X-MS-CLIENT-PRINCIPAL-NAME", "")
    rows = "".join(
        f"<tr><td>{html.escape(t)}</td><td>{html.escape(v)}</td></tr>" for t, v in claims(p)
    )
    parts = [
        "<h1>Signed in with App Service Authentication</h1>",
        f"<p>Signed in as <strong>{html.escape(name)}</strong> "
        f"(identity provider <code>{html.escape(headers.get('X-MS-CLIENT-PRINCIPAL-IDP', ''))}</code>, "
        f"object ID <code>{html.escape(headers.get('X-MS-CLIENT-PRINCIPAL-ID', ''))}</code>).</p>",
        '<p><a class="button" href="/.auth/logout?post_logout_redirect_uri=/signed-out">Sign out</a> '
        '&nbsp; <a href="/.auth/me">View <code>/.auth/me</code></a></p>',
        "<h2>Claims (<code>X-MS-CLIENT-PRINCIPAL</code>)</h2>",
        f"<table>{rows}</table>",
    ]
    found = tokens(headers)
    if not found:
        parts.append("<h2>Tokens</h2><p>The token store passed no tokens.</p>")
    for kind, value in found.items():
        header = f"X-MS-TOKEN-AAD-{kind.upper()}"
        parts.append(f"<h2>{html.escape(kind)} (<code>{header}</code>)</h2>")
        payload = jwt_payload(value)
        if payload is not None:
            parts.append(f"<pre>{html.escape(json.dumps(payload, indent=2))}</pre>")
        else:
            parts.append(f"<pre>{html.escape(value)}</pre>")
    return PAGE.format(body="\n".join(parts))


SIGNED_OUT_PAGE = PAGE.format(
    body='<h1>Signed out</h1><p><a class="button" href="/">Sign in again</a></p>'
)


class Headers:
    """Reads request headers from a WSGI environ by their HTTP names."""

    def __init__(self, environ):
        self.environ = environ

    def get(self, name, default=None):
        return self.environ.get("HTTP_" + name.upper().replace("-", "_"), default)


def app(environ, start_response):
    headers = Headers(environ)
    path = environ.get("PATH_INFO", "/")
    if path == "/signed-out":
        status, content_type, body = "200 OK", "text/html; charset=utf-8", SIGNED_OUT_PAGE
    elif path == "/api/whoami":
        # For callers that send a bearer token rather than signing in with a
        # browser: App Service validates the token and passes the same
        # principal headers.
        p = principal(headers)
        status, content_type = "200 OK", "application/json"
        body = json.dumps(
            {
                "name": headers.get("X-MS-CLIENT-PRINCIPAL-NAME"),
                "id": headers.get("X-MS-CLIENT-PRINCIPAL-ID"),
                "identityProvider": headers.get("X-MS-CLIENT-PRINCIPAL-IDP"),
                "claims": dict(claims(p)),
            },
            indent=2,
        )
    elif path == "/":
        status, content_type, body = "200 OK", "text/html; charset=utf-8", signed_in_page(headers)
    else:
        status, content_type, body = "404 Not Found", "text/plain; charset=utf-8", "Not Found"

    data = body.encode("utf-8")
    start_response(status, [("Content-Type", content_type), ("Content-Length", str(len(data)))])
    return [data]


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    make_server("0.0.0.0", port, app).serve_forever()
