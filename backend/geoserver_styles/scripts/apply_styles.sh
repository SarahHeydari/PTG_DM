#!/bin/sh
set -eu

GS="${GS:-http://geoserver:8080/geoserver}"
GS_USER="${GS_USER:-admin}"
GS_PASS="${GS_PASS:-geoserver}"
WS="${GS_WORKSPACE:-fire}"

ROOT="/work"
STYLES_DIR="${ROOT}/styles"

echo "GS=$GS"
echo "WS=$WS"
echo "STYLES_DIR=$STYLES_DIR"

echo "==> List /work"
ls -lah "$ROOT" || true
echo "==> List styles"
ls -lah "$STYLES_DIR" || true

# Fail early if SLDs missing
for f in ndvi.sld nbr.sld lst.sld; do
  if [ ! -s "$STYLES_DIR/$f" ]; then
    echo "ERROR: missing style file: $STYLES_DIR/$f"
    exit 1
  fi
done

# Wait until GeoServer REST is reachable (with auth)
echo "==> Checking GeoServer REST..."
curl -sS -u "$GS_USER:$GS_PASS" -f "$GS/rest/about/version.xml" >/dev/null

apply_one() {
  name="$1"
  sld="$2"

  echo "==> Apply style: $name ($sld)"

  # If exists -> PUT, else -> POST create
  if curl -sS -u "$GS_USER:$GS_PASS" -f "$GS/rest/workspaces/$WS/styles/$name.json" >/dev/null 2>&1; then
    echo "    updating (PUT)..."
    curl -sS -u "$GS_USER:$GS_PASS" \
      -H "Content-Type: application/vnd.ogc.sld+xml" \
      -X PUT \
      --data-binary "@$sld" \
      "$GS/rest/workspaces/$WS/styles/$name" >/dev/null
  else
    echo "    creating (POST)..."
    curl -sS -u "$GS_USER:$GS_PASS" \
      -H "Content-Type: application/vnd.ogc.sld+xml" \
      -X POST \
      --data-binary "@$sld" \
      "$GS/rest/workspaces/$WS/styles?name=$name" >/dev/null
  fi
}

apply_one "ndvi" "$STYLES_DIR/ndvi.sld"
apply_one "nbr"  "$STYLES_DIR/nbr.sld"
apply_one "lst"  "$STYLES_DIR/lst.sld"

echo "DONE: styles applied."