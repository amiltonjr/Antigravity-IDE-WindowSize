#!/bin/bash
# Helper runner para o patch do Antigravity
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$DIR/patch_antigravity_window.py" "$@"
