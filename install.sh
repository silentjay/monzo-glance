#!/usr/bin/env bash
# Install (or update) Moth's engine, moth-now, from this checkout. Idempotent. No root.
#   venv      ~/.local/share/moth-now/venv         built from engine/requirements.txt with
#                                                     --require-hashes (every wheel checked)
#   package   ~/.local/share/moth-now/mothnow      a copy of engine/mothnow
#   launcher  ~/.local/bin/moth-now
# It does not touch shell.json, the keyring, the cache or your config. Run it again after
# `omarchy plugin update io.github.silentjay.moth`.
set -euo pipefail
export LC_ALL=C       # one file order everywhere, so the fingerprint printed below is comparable
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/engine"
DST="$HOME/.local/share/moth-now"
BIN="$HOME/.local/bin"
PY="$(command -v "${PYTHON:-python3}" || true)"

[ -n "$PY" ] || { echo "install.sh: python3 not found" >&2; exit 1; }
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' ||
  { echo "install.sh: Python 3.11 or newer is needed ($("$PY" --version 2>&1) found)" >&2; exit 1; }

mkdir -p "$DST" "$BIN"
if command -v uv >/dev/null 2>&1; then
  [ -x "$DST/venv/bin/python" ] || uv venv --python "${MOTH_PYTHON:-3.13}" "$DST/venv" -q
  uv pip install --python "$DST/venv/bin/python" --require-hashes -r "$SRC/requirements.txt" -q
else
  [ -x "$DST/venv/bin/python" ] || "$PY" -m venv "$DST/venv"
  "$DST/venv/bin/python" -m pip install -q --disable-pip-version-check --require-hashes -r "$SRC/requirements.txt"
fi
cp "$SRC/requirements.txt" "$DST/requirements.txt"

rm -rf "$DST/mothnow.new"
mkdir "$DST/mothnow.new"
cp "$SRC"/mothnow/*.py "$DST/mothnow.new/"
rm -rf "$DST/mothnow.old"
[ -d "$DST/mothnow" ] && mv "$DST/mothnow" "$DST/mothnow.old"
mv "$DST/mothnow.new" "$DST/mothnow"
rm -rf "$DST/mothnow.old"

install -m 0755 "$SRC/moth-now" "$BIN/moth-now"

echo "engine:   $DST/mothnow ($(cd "$DST/mothnow" && sha256sum ./*.py | sha256sum | cut -c1-16), a hash of the package's file hashes)"
echo "launcher: $BIN/moth-now"
"$DST/venv/bin/python" -c 'import monzo, importlib.metadata as m; print("client:   Monzo-API", m.version("Monzo-API"))'
command -v secret-tool >/dev/null 2>&1 || echo "note:     secret-tool (libsecret) is not installed; \`moth-now login\` needs it"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "note:     $BIN is not on your PATH; run the engine as $BIN/moth-now" ;; esac
echo "next:     moth-now login"
