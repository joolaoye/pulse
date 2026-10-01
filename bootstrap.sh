#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(
    cd "$(dirname "${BASH_SOURCE[0]}")" && pwd
)"

if command -v python3 >/dev/null 2>&1; then
    exec python3 "$SCRIPT_DIR/bootstrap.py"
fi

if command -v python >/dev/null 2>&1; then
    exec python "$SCRIPT_DIR/bootstrap.py"
fi

echo "Python is required to bootstrap Pulse." >&2
exit 1
