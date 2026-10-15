#!/usr/bin/env bash
set -euo pipefail
SKHUB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SKHUB_ROOT/scripts/manage.py" "$@"
