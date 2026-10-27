#!/usr/bin/env bash
# Optional: put `monzo-glance` on your PATH. The widget itself runs the engine bundled in this
# plugin folder, so this is only for typing `monzo-glance login`, `status` and `check`.
#
#   ./install.sh        link ~/.local/bin/monzo-glance to this checkout's engine
#
# No venv, no packages, no network. Remove the link with:
#   rm ~/.local/bin/monzo-glance
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/engine/monzo-glance"
BIN="$HOME/.local/bin"

command -v python3 >/dev/null 2>&1 || { echo "install.sh: python3 not found" >&2; exit 1; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' ||
  { echo "install.sh: Python 3.11 or newer is needed ($(python3 --version 2>&1) found)" >&2; exit 1; }

mkdir -p "$BIN"
ln -sfn "$SRC" "$BIN/monzo-glance"
echo "linked:   $BIN/monzo-glance -> $SRC"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "note:     $BIN is not on your PATH; run the engine as $BIN/monzo-glance" ;; esac
echo "next:     monzo-glance login"
