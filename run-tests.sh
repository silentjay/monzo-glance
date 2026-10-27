#!/usr/bin/env bash
# The whole suite, on invented data: no network, no keyring, no Monzo account, no browser.
#
#   ./run-tests.sh [PYTHON]
#
# PYTHON must have engine/requirements.txt installed (T9 imports the engine's package, which
# imports Monzo-API only lazily; the adapter tests use stand-ins and need no server).
# Default: ./.venv/bin/python, else the installed engine's venv.
#   T9    the model against an independent oracle, hand-pinned cases, and its mutants
#   T10   the bar tick end to end (face states, fetch gates, files, log, config), and its mutants
#   demo  the invented household renders, in pounds, for every scene (tools/demo.py --check)
#   open  the two ways "Open Monzo" can go, and install-webapp.sh, with recorders on PATH
# The gesture test is separate (tools/gesture_test.py): it needs a running Omarchy shell.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${1:-}"
if [[ -z $PY ]]; then
  for candidate in "$ROOT/.venv/bin/python" "$HOME/.local/share/monzo-glance/venv/bin/python"; do
    [[ -x $candidate ]] && { PY=$candidate; break; }
  done
fi
[[ -n $PY && -x $PY ]] || { echo "run-tests.sh: no python with the requirements; see README, Tests" >&2; exit 2; }
PY="$(realpath -s "$PY")"       # a venv python reached through ".." makes Python warn about its prefix

rc=0
"$PY" -B -W error::SyntaxWarning "$ROOT/engine/tests/t9_monzoglance_model.py" "$ROOT/engine" || rc=1
"$PY" -B -W error::SyntaxWarning "$ROOT/engine/tests/t10_monzoglance_face.py" "$ROOT/engine" "$ROOT/engine/monzo-glance" || rc=1
"$PY" -B "$ROOT/tools/demo.py" --check || rc=1
"$ROOT/tools/open_test.sh" || rc=1
echo
[[ $rc -eq 0 ]] && echo "ALL SUITES PASS" || echo "SOME SUITE FAILED"
exit $rc
