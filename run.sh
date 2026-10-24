#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if command -v python3 >/dev/null 2>&1; then
    python3 "$DIR/patch_antigravity_window.py" "$@"
else
    python "$DIR/patch_antigravity_window.py" "$@"
fi
