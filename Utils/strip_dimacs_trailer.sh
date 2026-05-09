#!/bin/bash
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <directory>"
    echo "Removes trailing '% 0' from all .cnf files recursively."
    exit 1
fi

DIR="$1"

if [ ! -d "$DIR" ]; then
    echo "Error: directory not found: $DIR" >&2
    exit 1
fi

echo "Scanning: $DIR"

total=0
fixed=0
skipped=0

while IFS= read -r -d '' f; do
    total=$((total + 1))
    if perl -0777 -ne 'exit(/\s*%\s*0\s*$/ ? 0 : 1)' "$f"; then
        perl -0777 -pi -e 's/\s*%\s*0\s*$//' "$f"
        fixed=$((fixed + 1))
        echo "[FIX] $f"
    else
        skipped=$((skipped + 1))
    fi
done < <(find "$DIR" -name "*.cnf" -type f -print0)

echo ""
echo "=== Summary ==="
echo "Total : $total"
echo "Fixed : $fixed"
echo "Skipped (no trailing % 0): $skipped"
