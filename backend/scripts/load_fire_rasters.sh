#!/usr/bin/env bash
set -euo pipefail

WEB="docker compose exec -T web"
IDX_DIR="/app/data/fire/indexes"
SAT_DIR="/app/data/fire/satellite_images"

month_to_num () {
  case "$1" in
    Jan) echo "01" ;; Feb) echo "02" ;; Mar) echo "03" ;; Apr) echo "04" ;;
    May) echo "05" ;; Jun) echo "06" ;; Jul) echo "07" ;; Aug) echo "08" ;;
    Sep) echo "09" ;; Oct) echo "10" ;; Nov) echo "11" ;; Dec) echo "12" ;;
    *) echo "" ;;
  esac
}

parse_index_meta () {
  local fname="$1"
  local prefix monthyear mon year mm

  prefix="${fname%%_*}"
  monthyear="$(echo "$fname" | grep -oE '_(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[0-9]{4}_' || true)"

  if [[ -z "$monthyear" ]]; then
    echo "${prefix,,}|2000-01-01"
    return
  fi

  mon="$(echo "$monthyear" | grep -oE '(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)')"
  year="$(echo "$monthyear" | grep -oE '[0-9]{4}')"
  mm="$(month_to_num "$mon")"

  if [[ -z "$mm" ]]; then
    echo "${prefix,,}|${year}-01-01"
  else
    echo "${prefix,,}|${year}-${mm}-01"
  fi
}

echo "== Loading Index rasters from $IDX_DIR =="
mapfile -t INDEX_TIFS < <($WEB bash -lc "ls -1 $IDX_DIR/*.tif 2>/dev/null || true")
for tif in "${INDEX_TIFS[@]}"; do
  base="$(basename "$tif")"
  meta="$(parse_index_meta "$base")"
  index_name="${meta%%|*}"
  date="${meta##*|}"

  echo "-> $base  index=$index_name  date=$date"
  $WEB python manage.py load_raster_metadata \
    --kind index \
    --path "$tif" \
    --satellite sentinel2 \
    --index-name "$index_name" \
    --date "$date" \
    --title "$base" \
    --minio-link "about:blank"
done

echo "== Loading SatelliteImage rasters from $SAT_DIR =="
mapfile -t SAT_TIFS < <($WEB bash -lc "ls -1 $SAT_DIR/*.tif 2>/dev/null || true")
for tif in "${SAT_TIFS[@]}"; do
  base="$(basename "$tif")"
  dt="2025-01-01T00:00:00Z"

  echo "-> $base  datetime=$dt"
  $WEB python manage.py load_raster_metadata \
    --kind satellite-image \
    --path "$tif" \
    --satellite sentinel2 \
    --datetime "$dt" \
    --title "$base" \
    --minio-link "about:blank"
done

echo "DONE."
