#!/bin/bash
KOK=$(git rev-parse --show-toplevel); R="$KOK/perf/.replika/$1/caddy"
for f in "$R"/*.pid; do [ -f "$f" ] && kill "$(cat "$f")" 2>/dev/null; rm -f "$f"; done; echo "durdu: $1"
