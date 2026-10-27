#!/usr/bin/env bash
# Optional: create the Monzo web app that a click on the butterfly and the card's
# "Open Monzo" button open (or focus). Without it they open Monzo in your default browser.
#
# It is an ordinary Omarchy web app, made by Omarchy's own installer:
#     ~/.local/share/applications/Monzo.desktop   Exec=omarchy-launch-webapp "https://web.monzo.com"
# The site's own icon is fetched by Omarchy. Remove the web app again with
# `omarchy-webapp-remove Monzo`.
#
#   install-webapp.sh           create it (does nothing when it already exists)
#   install-webapp.sh --force   recreate it
set -euo pipefail
NAME="Monzo"
URL="https://web.monzo.com"
DESKTOP="$HOME/.local/share/applications/$NAME.desktop"

command -v omarchy-webapp-install >/dev/null 2>&1 ||
  { echo "install-webapp.sh: omarchy-webapp-install not found (this step needs Omarchy)" >&2; exit 1; }

if [[ -e $DESKTOP && ${1:-} != "--force" ]]; then
  echo "The $NAME web app is already installed: $DESKTOP"
  echo "(run with --force to recreate it)"
  exit 0
fi

# No bundled icon: let Omarchy pick the site's own icon.
omarchy-webapp-install "$NAME" "$URL"

[[ -f $DESKTOP ]] || { echo "install-webapp.sh: $DESKTOP was not created" >&2; exit 1; }
echo "Created the $NAME web app: $DESKTOP"
echo "The butterfly and \"Open Monzo\" now open or focus it."
