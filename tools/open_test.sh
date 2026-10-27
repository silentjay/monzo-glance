#!/usr/bin/env bash
# The click path, with nothing real launched: xdg-open is replaced by a recorder, HOME is a temp
# directory, and PATH holds nothing else of Omarchy's. No network and no browser.
#
#   tools/open_test.sh        exit 0 when every check passes
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPEN="$ROOT/bin/monzo-glance-open"
URL="https://web.monzo.com"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fails=0
check() { if [[ $2 == "$3" ]]; then echo "PASS  $1"; else echo "FAIL  $1"; echo "      expected: $3"; echo "      got:      $2"; fails=$((fails + 1)); fi; }

mkdir -p "$TMP/bin" "$TMP/sys" "$TMP/home"
cat >"$TMP/bin/xdg-open" <<STUB
#!/usr/bin/env bash
printf "xdg-open" >>"$TMP/calls"; printf " %s" "\$@" >>"$TMP/calls"; echo >>"$TMP/calls"
STUB
chmod +x "$TMP/bin/xdg-open"
for tool in bash env; do ln -s "$(command -v "$tool")" "$TMP/sys/$tool"; done
run() { : >"$TMP/calls"; env -i HOME="$TMP/home" PATH="$TMP/bin:$TMP/sys" "$@" >"$TMP/out" 2>&1; echo $? >"$TMP/rc"; }
calls() { cat "$TMP/calls"; }

run "$OPEN" --print
check "--print says browser" "$(cat "$TMP/out")" "browser $URL"
check "--print opens nothing" "$(calls)" ""

run "$OPEN"
check "xdg-open gets the URL" "$(calls)" "xdg-open $URL"
check "exit 0" "$(cat "$TMP/rc")" "0"

check "no image is bundled in the repository" "$(cd "$ROOT" && git ls-files 2>/dev/null | grep -v '^docs/monzo-glance-' | grep -i -E 'monzo[^/]*\.(png|svg|ico|jpg)$|monarch|logo' || true)" ""

echo
if (( fails )); then echo "open test: $fails FAILED"; exit 1; fi
echo "open test: ALL PASS"
