#!/bin/bash
# Write this session into the learning ledger, then fill in the sessions the
# hook never fired for.
#
# SessionEnd fires on clear, resume, logout and prompt_input_exit -- not when
# the terminal is killed or the process crashes. So the second step matters as
# much as the first: it re-reads every transcript on disk and captures whatever
# is missing. Both steps are idempotent by content hash, so running this on
# every session end costs one ignored write per already-known session.
#
# This hook must never take the session down with it. Every failure is written
# to ~/.vibe-trading/hook.log by the CLI and reported by the exit code, which
# SessionEnd treats as a non-blocking notice.

set -u

PROJECT="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$PROJECT" ]; then
  PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fi

PY="$PROJECT/.venv/Scripts/python.exe"
[ -x "$PY" ] || PY="$PROJECT/.venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "learning hook: no interpreter under $PROJECT/.venv" >&2
  exit 1
fi

cd "$PROJECT/agent" || {
  echo "learning hook: no agent directory under $PROJECT" >&2
  exit 1
}

payload="$(cat)"
status=0
printf '%s' "$payload" | "$PY" -m src.learning.cli capture >/dev/null || status=1
"$PY" -m src.learning.cli scan >/dev/null || status=1
exit "$status"
