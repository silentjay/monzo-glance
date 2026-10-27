#!/usr/bin/env bash
# Install (or update) Monzo Glance's engine, monzo-glance, from this checkout. Idempotent. No root.
#   venv      ~/.local/share/monzo-glance/venv         built from engine/requirements.txt with
#                                                     --require-hashes (every wheel checked)
#   package   ~/.local/share/monzo-glance/monzoglance      a copy of engine/monzoglance
#   launcher  ~/.local/bin/monzo-glance
# It does not touch shell.json, the keyring, the cache or your config. Run it again after
# `omarchy plugin update io.github.silentjay.monzoglance`.
set -euo pipefail
export LC_ALL=C       # one file order everywhere, so the fingerprint printed below is comparable
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/engine"
DST="$HOME/.local/share/monzo-glance"
BIN="$HOME/.local/bin"
PY="$(command -v "${PYTHON:-python3}" || true)"

[ -n "$PY" ] || { echo "install.sh: python3 not found" >&2; exit 1; }
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' ||
  { echo "install.sh: Python 3.11 or newer is needed ($("$PY" --version 2>&1) found)" >&2; exit 1; }

mkdir -p "$DST" "$BIN"
if command -v uv >/dev/null 2>&1; then
  [ -x "$DST/venv/bin/python" ] || uv venv --python "${MONZO_GLANCE_PYTHON:-3.13}" "$DST/venv" -q
  uv pip install --python "$DST/venv/bin/python" --require-hashes -r "$SRC/requirements.txt" -q
else
  [ -x "$DST/venv/bin/python" ] || "$PY" -m venv "$DST/venv"
  "$DST/venv/bin/python" -m pip install -q --disable-pip-version-check --require-hashes -r "$SRC/requirements.txt"
fi
cp "$SRC/requirements.txt" "$DST/requirements.txt"

rm -rf "$DST/monzoglance.new"
mkdir "$DST/monzoglance.new"
cp "$SRC"/monzoglance/*.py "$DST/monzoglance.new/"
rm -rf "$DST/monzoglance.old"
[ -d "$DST/monzoglance" ] && mv "$DST/monzoglance" "$DST/monzoglance.old"
mv "$DST/monzoglance.new" "$DST/monzoglance"
rm -rf "$DST/monzoglance.old"

install -m 0755 "$SRC/monzo-glance" "$BIN/monzo-glance"

echo "engine:   $DST/monzoglance ($(cd "$DST/monzoglance" && sha256sum ./*.py | sha256sum | cut -c1-16), a hash of the package's file hashes)"
echo "launcher: $BIN/monzo-glance"
"$DST/venv/bin/python" -c 'import monzo, importlib.metadata as m; print("client:   Monzo-API", m.version("Monzo-API"))'
command -v secret-tool >/dev/null 2>&1 || echo "note:     secret-tool (libsecret) is not installed; \`monzo-glance login\` needs it"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "note:     $BIN is not on your PATH; run the engine as $BIN/monzo-glance" ;; esac
echo "next:     monzo-glance login"
