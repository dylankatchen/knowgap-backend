from quart import redirect, request
from werkzeug.urls import iri_to_uri

from config import Config

# Sent on every API response. The API only returns JSON, so nothing it
# serves should ever load other content, run in a frame, or leak a referrer.
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Content-Security-Policy': "default-src 'none'; frame-ancestors 'none'",
    'Referrer-Policy': 'no-referrer',
}
HSTS_HEADER = 'max-age=31536000'  # one year


def _last_forwarded_value(name):
    """The last entry of an X-Forwarded-* header, which is the one Heroku's
    router added. Earlier entries are whatever the client sent."""
    values = ','.join(request.headers.getlist(name)).split(',')
    values = [value.strip() for value in values if value.strip()]
    return values[-1] if values else None


def client_ip():
    """The visitor's IP address. Behind Heroku's router, remote_addr is the
    router itself, so the address comes from X-Forwarded-For instead."""
    if Config.BEHIND_PROXY:
        return _last_forwarded_value('X-Forwarded-For') or request.remote_addr
    return request.remote_addr


def _forwarded_scheme():
    if Config.BEHIND_PROXY:
        scheme = _last_forwarded_value('X-Forwarded-Proto')
        return scheme.lower() if scheme else None
    return None


async def _redirect_plain_http():
    # 308 keeps the method and body, so a POST is retried as a POST. Only
    # Heroku says which scheme the visitor used; locally nothing redirects.
    if _forwarded_scheme() == 'http':
        return redirect(f'https://{request.host}{_raw_target()}', 308)
    return None


def _raw_target():
    """The path and query exactly as the client sent them. request.url is
    rebuilt from the decoded path, which would turn %2F into a real slash."""
    path = request.scope.get('raw_path') or b''
    if not path.startswith(b'/'):
        # Absolute-form request line ("GET http://host/x") or no raw path.
        path = iri_to_uri(request.path).encode('ascii')
    target = path.decode('latin-1')
    if request.query_string:
        target += '?' + request.query_string.decode('latin-1')
    return target


async def _add_security_headers(response):
    for name, value in SECURITY_HEADERS.items():
        response.headers[name] = value
    if _forwarded_scheme() == 'https':
        response.headers['Strict-Transport-Security'] = HSTS_HEADER
    return response


def init_security(app):
    """Redirect plain HTTP to HTTPS and add security headers to every
    response. Register before other before_request hooks, so a plain-HTTP
    request is redirected before anything else runs or counts it."""
    app.before_request(_redirect_plain_http)
    app.after_request(_add_security_headers)
