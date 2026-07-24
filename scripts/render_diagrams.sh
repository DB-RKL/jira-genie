#!/usr/bin/env bash
# Render Mermaid source files (.mmd) to PNG for GitHub embedding.
#
# Preferred: mmdc (npm install -g @mermaid-js/mermaid-cli)
# Fallback:  Kroki.io API (no local install required)
#
# Usage: ./scripts/render_diagrams.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIAGRAMS="$ROOT/docs/diagrams"

render_mmdc() {
  local src="$1" dst="$2"
  mmdc -i "$src" -o "$dst" -b white -q
}

render_kroki() {
  local src="$1" dst="$2"
  python3 - <<'PY' "$src" "$dst"
import sys, urllib.request, base64, zlib

def encode(graph: str) -> str:
    compressed = zlib.compress(graph.encode("utf-8"), 9)
    return base64.urlsafe_b64encode(compressed).decode("ascii")

src, dst = sys.argv[1], sys.argv[2]
graph = open(src, encoding="utf-8").read()
url = f"https://kroki.io/mermaid/png/{encode(graph)}"
urllib.request.urlretrieve(url, dst)
print(f"Wrote {dst} (via Kroki)")
PY
}

for mmd in "$DIAGRAMS"/*.mmd; do
  png="${mmd%.mmd}.png"
  echo "Rendering $(basename "$mmd") ..."
  if command -v mmdc >/dev/null 2>&1; then
    render_mmdc "$mmd" "$png"
  else
    render_kroki "$mmd" "$png"
  fi
done

echo "Done."
