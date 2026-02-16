# fire/management/commands/load_raster_metadata.py
from __future__ import annotations

from datetime import datetime, date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_date, parse_datetime
from django.contrib.gis.geos import Polygon

from fire.models import IndexLayer, SatelliteImage


class Command(BaseCommand):
    help = "Load raster (GeoTIFF) metadata into IndexLayer or SatelliteImage with footprint geometry."

    def add_arguments(self, parser):
        parser.add_argument("--kind", required=True, choices=["index", "satellite-image"])
        parser.add_argument("--path", required=True, help="Absolute path inside container, e.g. /app/data/fire/indexes/NDVI_...tif")

        # common metadata
        parser.add_argument("--satellite", required=True, help="e.g. sentinel2, landsat8")
        parser.add_argument("--minio-link", default="", help="Optional URL (can be empty for now)")
        parser.add_argument("--title", default="", help="Optional title")

        # index-specific
        parser.add_argument("--index-name", default="", help="Required when kind=index (e.g. ndvi, nbr, lst, dnbr)")
        parser.add_argument("--date", default="", help="Required when kind=index. Format: YYYY-MM-DD")

        # satellite-image-specific
        parser.add_argument("--datetime", default="", help="Required when kind=satellite-image. ISO format e.g. 2025-11-01T10:30:00Z")

        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--no-geom", action="store_true", help="Skip geometry extraction (not recommended)")

    def handle(self, *args, **opts):
        kind = opts["kind"]
        p = Path(opts["path"])
        if not p.exists():
            raise CommandError(f"File not found: {p}")

        satellite = (opts["satellite"] or "").strip()
        if not satellite:
            raise CommandError("--satellite is required")

        minio_link = (opts["minio_link"] or "").strip()
        title = (opts["title"] or "").strip() or p.stem

        geom = None
        if not opts["no_geom"]:
            geom = self._extract_footprint_4326(str(p))

        if kind == "index":
            index_name = (opts["index_name"] or "").strip()
            if not index_name:
                raise CommandError("--index-name is required for kind=index")
            d = parse_date(opts["date"] or "")
            if not d:
                raise CommandError("--date is required for kind=index (YYYY-MM-DD)")

            obj = IndexLayer(
                title=title,
                minio_link=minio_link or "about:blank",
                index_name=index_name,
                date=d,
                satellite_name=satellite,
                geometry=geom,
            )

        else:
            dt = parse_datetime(opts["datetime"] or "")
            if not dt:
                raise CommandError("--datetime is required for kind=satellite-image (ISO datetime)")
            obj = SatelliteImage(
                satellite_name=satellite,
                date_time=dt,
                image_name=title,
                minio_link=minio_link or "about:blank",
                geometry=geom,
            )

        if opts["dry_run"]:
            self.stdout.write(self.style.WARNING("DRY RUN: not saving to DB"))
            self.stdout.write(f"kind={kind} file={p.name} geom={'yes' if geom else 'no'}")
            return

        obj.save()
        self.stdout.write(self.style.SUCCESS(f"OK: inserted id={obj.id} kind={kind} file={p.name}"))

    def _extract_footprint_4326(self, tif_path: str):
        # Import here so command still loads even if rasterio missing
        import rasterio
        from rasterio.warp import transform_bounds

        with rasterio.open(tif_path) as ds:
            b = ds.bounds  # left, bottom, right, top
            src_crs = ds.crs

            if src_crs is None:
                # Assume already lon/lat if CRS missing (last resort)
                left, bottom, right, top = b.left, b.bottom, b.right, b.top
            else:
                left, bottom, right, top = transform_bounds(src_crs, "EPSG:4326", b.left, b.bottom, b.right, b.top, densify_pts=21)

            poly = Polygon.from_bbox((left, bottom, right, top))
            poly.srid = 4326
            return poly
