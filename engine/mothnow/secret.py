"""The Monzo connection lives in the Secret Service keyring (gnome-keyring on Omarchy), through
libsecret's `secret-tool`. Never in a file, never in a log, never on argv: the secret crosses a
pipe on stdin (store) or stdout (lookup) and nowhere else.

The item: label "Monzo connection (moth-now)", attributes service=moth-now kind=session.
The value is a small JSON object: {client_id, client_secret, redirect_uri, access_token,
access_token_expiry (epoch), refresh_token}. `MonzoStorage` is the handler monzo-api calls to
persist a refreshed token, so refreshed tokens land in the keyring too.
"""
import json
import subprocess

ATTRS = ["service", "moth-now", "kind", "session"]
LABEL = "Monzo connection (moth-now)"
TOOL = "/usr/bin/secret-tool"
TIMEOUT = 15


class KeyringError(Exception):
    pass


def store(connection):
    payload = json.dumps(connection, separators=(",", ":"))
    try:
        p = subprocess.run([TOOL, "store", "--label=" + LABEL] + ATTRS, input=payload, text=True,
                           capture_output=True, timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise KeyringError("secret-tool store: %s" % type(e).__name__)
    if p.returncode != 0:
        raise KeyringError("secret-tool store exited %d" % p.returncode)


def load():
    """The connection dict, or None when nothing is stored. KeyringError when it cannot be asked."""
    try:
        p = subprocess.run([TOOL, "lookup"] + ATTRS, text=True, capture_output=True, timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise KeyringError("secret-tool lookup: %s" % type(e).__name__)
    if p.returncode != 0 or not p.stdout.strip():
        return None
    try:
        doc = json.loads(p.stdout)
    except ValueError:
        return None
    return doc if isinstance(doc, dict) and doc else None


def clear():
    try:
        subprocess.run([TOOL, "clear"] + ATTRS, capture_output=True, timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise KeyringError("secret-tool clear: %s" % type(e).__name__)


class MonzoStorage:
    """monzo-api's credential handler, backed by the keyring. The library calls `store` with a
    refreshed token; `fetch` returns what is stored (it is not consulted by the library, which is
    handed its tokens by us, but is here for completeness)."""

    def fetch(self):
        return load() or {}

    def store(self, access_token, client_id, client_secret, expiry, refresh_token=""):
        conn = load() or {}
        conn.update({"access_token": access_token, "client_id": client_id, "client_secret": client_secret,
                     "access_token_expiry": expiry, "refresh_token": refresh_token or conn.get("refresh_token", "")})
        store(conn)
