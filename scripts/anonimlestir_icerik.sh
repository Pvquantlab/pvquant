#!/usr/bin/env bash
set -e
grep -rl -i "merkas" \
  --include="*.py" --include="*.md" --include="*.toml" \
  --include="*.txt" --include="*.json" --include="*.yml" . \
  | grep -v ".git/" | while read f; do
    sed -i.bak -e 's/MERKAS/REFPLANT/g' \
               -e 's/Merkas/Refplant/g' \
               -e 's/merkas/refplant/g' "$f" && rm "$f.bak"
done
echo "kalan (0 olmali):"
grep -ri "merkas" --include="*.py" --include="*.md" . | grep -v ".git/" | wc -l
