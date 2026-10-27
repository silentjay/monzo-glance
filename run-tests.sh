#!/usr/bin/env bash
# The whole suite, on invented data: no network, no keyring, no Monzo account, no browser.
#
#   ./run-tests.sh [PYTHON]
#
# PYTHON must be 3.11+; the engine and its vendored Monzo client are pure standard library.
# Default: python3.
#   T9    the model against an independent oracle, hand-pinned cases, and its mutants
#   T10   the bar tick end to end (face states, fetch gates, files, log, config), and its mutants
#   demo  the invented household renders, in pounds, for every scene (tools/demo.py --check)
#   open  the click path, with xdg-open replaced by a recorder on PATH
# The gesture test is separate (tools/gesture_test.py): it needs a running Omarchy shell.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${1:-python3}"
command -v "$PY" >/dev/null 2>&1 || { echo "run-tests.sh: $PY not found" >&2; exit 2; }
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' ||
  { echo "run-tests.sh: Python 3.11 or newer is needed ($("$PY" --version 2>&1) found)" >&2; exit 2; }

rc=0
"$PY" -B -W error::SyntaxWarning "$ROOT/engine/tests/t9_monzoglance_model.py" "$ROOT/engine" || rc=1
"$PY" -B -W error::SyntaxWarning "$ROOT/engine/tests/t10_monzoglance_face.py" "$ROOT/engine" "$ROOT/engine/monzo-glance" || rc=1
"$PY" -B "$ROOT/tools/demo.py" --check || rc=1
"$ROOT/tools/open_test.sh" || rc=1
echo
[[ $rc -eq 0 ]] && echo "ALL SUITES PASS" || echo "SOME SUITE FAILED"
exit $rc
