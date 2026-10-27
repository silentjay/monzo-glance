"""`moth-now login`: connect Moth to your Monzo account.

Moth reads Monzo through Monzo's own OAuth — there is no bank aggregator and no server to run.
Signing in means authorising a Monzo OAuth client you created yourself (developers.monzo.com),
whose redirect URL is a localhost address, so no domain is needed:

    Client ID / Client Secret   from your Monzo OAuth client
    redirect_uri                http://localhost:8080/callback (must match the client exactly)

What happens:
    1. Moth starts a throwaway web server on the redirect's port and opens your browser to Monzo.
    2. You log in and approve the app's access in the Monzo app (Strong Customer Authentication).
    3. Monzo redirects back to Moth's little server with a code; Moth exchanges it for an access
       and a refresh token. The tokens go straight into the keyring (never a file, a log or the
       clipboard); the refresh token keeps you signed in.
    4. Immediately — Monzo only offers full history for five minutes after this — Moth pulls your
       whole history into a local ledger, so the usual month has real depth from day one.

Set MOTH_MONZO_CLIENT_ID / MOTH_MONZO_CLIENT_SECRET / MOTH_MONZO_REDIRECT_URI to skip the prompts.
"""
import os
import subprocess
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from . import adapter, secret, store

DEFAULT_REDIRECT = "http://localhost:8080/callback"
WAIT_SECONDS = 600
APPROVE_SECONDS = 285        # how long to wait for the in-app approval before seeding history


class _Callback(BaseHTTPRequestHandler):
    def do_GET(self):                                   # noqa: N802 - http.server's name
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "code" in query or "error" in query:         # ignore the browser's /favicon.ico etc.
            self.server.code = query.get("code", [None])[0]
            self.server.state = query.get("state", [None])[0]
            self.server.error = query.get("error", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<html><body style='font-family:sans-serif'>Moth: signed in. You can close this tab.</body></html>")

    def log_message(self, *a):                          # keep the terminal quiet
        pass


def _why(exc):
    """Walk the exception chain and name the real cause — monzo-api wraps every HTTP error as a
    bare MonzoAuthenticationError, hiding Monzo's own message. Shows the status and body."""
    parts, seen, e = [], set(), exc
    while e is not None and id(e) not in seen:
        seen.add(id(e))
        code = getattr(e, "code", None)
        body = ""
        if hasattr(e, "read"):
            try:
                body = e.read().decode("utf-8", "replace")[:300]
            except Exception:                           # noqa: BLE001
                body = ""
        parts.append("%s%s%s" % (type(e).__name__, " [%s]" % code if code else "", (": " + body) if body else ""))
        e = e.__cause__ or e.__context__
    return " <- ".join(parts)


def _ask(out, label, default):
    out.write("%s%s: " % (label, " [%s]" % default if default else ""))
    out.flush()
    return sys.stdin.readline().strip() or default


def _open_browser(url, out):
    for opener in (["xdg-open"], ["gio", "open"]):
        try:
            subprocess.Popen(opener + [url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except OSError:
            continue
    out.write("Could not open a browser; open this URL yourself:\n  %s\n" % url)


def _serve(redirect):
    parts = urllib.parse.urlparse(redirect)
    host = parts.hostname or "localhost"
    port = parts.port or 80
    if parts.path not in ("", "/callback"):
        raise ValueError("the redirect path should be /callback, not %r" % parts.path)
    server = HTTPServer((host, port), _Callback)
    server.code = server.state = server.error = None
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def configure(out=sys.stdout):
    client_id = os.environ.get("MOTH_MONZO_CLIENT_ID") or _ask(out, "Monzo client ID", "")
    if client_id.startswith("user_"):
        out.write("That is your Monzo user ID, not an OAuth client ID.\n"
                  "Create (or open) an OAuth client at https://developers.monzo.com/ and use its\n"
                  "Client ID, which starts with 'oauth2client_'. Nothing was stored.\n")
        return 1
    client_secret = os.environ.get("MOTH_MONZO_CLIENT_SECRET")
    if client_secret is None:
        import getpass
        client_secret = getpass.getpass("Monzo client secret (hidden): ")
    redirect = os.environ.get("MOTH_MONZO_REDIRECT_URI") or _ask(out, "Redirect URI", DEFAULT_REDIRECT)
    if not (client_id and client_secret and redirect):
        out.write("A client ID, client secret and redirect URI are all needed. Nothing was stored.\n")
        return 1

    from monzo.authentication import Authentication
    auth = Authentication(client_id=client_id, client_secret=client_secret, redirect_url=redirect)
    auth.register_callback_handler(secret.MonzoStorage())

    try:
        server = _serve(redirect)
    except (OSError, ValueError) as e:
        out.write("Could not listen on the redirect address (%s). Nothing was stored.\n" % e)
        return 1

    out.write("Opening your browser to authorise Moth with Monzo.\n"
              "  - log in, then approve access in the Monzo app (you'll get a push notification).\n"
              "  If a browser does not open, visit:\n  %s\n" % auth.authentication_url)
    out.flush()
    _open_browser(auth.authentication_url, out)

    deadline = time.monotonic() + WAIT_SECONDS
    while time.monotonic() < deadline and not (server.code or server.error):
        time.sleep(0.5)
    code, error, state = server.code, server.error, server.state
    server.shutdown()

    if error or not code:
        out.write("Authorisation was not completed (%s). Nothing was stored.\n" % (error or "timed out"))
        store.log("login", result="cancelled")
        return 1

    try:
        auth.authenticate(code, state)
    except Exception as e:      # noqa: BLE001
        out.write("Monzo refused the sign-in (%s). Nothing was stored.\n" % _why(e))
        store.log("login", result="refused")
        return 1

    connection = secret.load() or {}
    connection.update({"client_id": client_id, "client_secret": client_secret, "redirect_uri": redirect})
    secret.store(connection)

    out.write("Signed in. Now approve Moth in the Monzo app (you will get a notification); "
              "Moth is waiting.\n")
    out.flush()
    verified = False
    deadline = time.monotonic() + APPROVE_SECONDS
    while time.monotonic() < deadline:
        try:
            adapter.verify(connection)
            verified = True
            break
        except adapter.FetchError as e:
            if e.kind != "auth":
                out.write("Monzo refused a read (%s): %s\n" % (e.kind, _why(e)))
                store.log("login", result="verify-failed", kind=e.kind)
                return 1
            time.sleep(3.0)
    if not verified:
        out.write("Moth was not approved in the Monzo app within %d minutes. Approve it there, "
                  "then run `moth-now login` again.\n" % (APPROVE_SECONDS // 60))
        store.log("login", result="verify-timeout")
        return 1
    out.write("Approved.\n")

    out.write("Pulling your full history (Monzo only offers it for five minutes)...\n")
    out.flush()
    try:
        n = adapter.seed(connection)
        out.write("Stored %d transactions.\n" % n)
    except adapter.FetchError as e:
        out.write("Signed in, but the history pull failed (%s); the hourly fetch will still work.\n" % e.kind)

    state_doc = store.read_state()
    state_doc.pop("last_error", None)
    state_doc.pop("last_error_detail", None)
    state_doc.pop("last_attempt", None)       # so the next bar tick fetches at once
    state_doc["signed_in_at"] = time.time()
    store.write_state(state_doc)
    store.log("login", result="ok")
    out.write("The connection is in the keyring (\"%s\").\n" % secret.LABEL)
    poke_bar()
    return 0


def poke_bar():
    """Ask the bar widget to run the engine now instead of at its next tick. Best effort."""
    try:
        subprocess.run(["omarchy-shell", "io.github.silentjay.moth", "refresh"], capture_output=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        pass
