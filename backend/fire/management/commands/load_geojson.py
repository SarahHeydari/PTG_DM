# fire/management/commands/load_geojson.py
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.db import transaction

from fire.models import IranForest, IranCounty, IranProvince, FireRiskArea


KIND_MAP = {
    "forests": IranForest,
    "counties": IranCounty,
    "provinces": IranProvince,
    "fire-risk": FireRiskArea,
}


def _pick_name(props: dict, fallback: str = "Unnamed") -> str:
    # رایج‌ترین کلیدهای نام در دیتاهای ایران
    for k in ("name", "Name", "NAME", "نام", "title", "Title"):
        v = props.get(k)
        if v:
            return str(v).strip()
    return fallback


def _pick_level(props: dict, default: int = 1) -> int:
    # برای fire-risk
    for k in ("level", "Level", "LEVEL", "risk", "RISK", "class", "Class"):
        v = props.get(k)
        if v is None:
            continue
        try:
            return int(v)
        except Exception:
            continue
    return default


def _normalize_geom(geom: GEOSGeometry):
    """
    Accept only Polygon/MultiPolygon.
    Convert Polygon -> MultiPolygon when needed.
    """
    if geom is None:
        return None

    # بعضی geojson ها geometry=null دارن
    try:
        gtype = geom.geom_type
    except Exception:
        return None

    if gtype not in ("Polygon", "MultiPolygon"):
        return None

    if gtype == "Polygon":
        return MultiPolygon(geom)

    return geom  # MultiPolygon


class Command(BaseCommand):
    help = "Load a GeoJSON FeatureCollection into fire vector tables."

    def add_arguments(self, parser):
        parser.add_argument(
            "--kind",
            required=True,
            choices=KIND_MAP.keys(),
            help="Target kind: forests | counties | provinces | fire-risk",
        )
        parser.add_argument(
            "--path",
            required=True,
            help="Path to .geojson file (inside container, e.g. /app/data/fire/geojson/jungle.geojson)",
        )
        parser.add_argument(
            "--truncate",
            action="store_true",
            help="Truncate table before insert",
        )
        parser.add_argument(
            "--batch",
            type=int,
            default=1000,
            help="bulk_create batch size (default 1000)",
        )

    def handle(self, *args, **options):
        kind = options["kind"]
        path = options["path"]
        truncate = options["truncate"]
        batch = options["batch"]

        model = KIND_MAP[kind]

        p = Path(path)
        if not p.exists():
            raise CommandError(f"File not found: {path}")

        # load json
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            raise CommandError(f"Invalid JSON: {e}")

        if data.get("type") != "FeatureCollection":
            raise CommandError("GeoJSON must be a FeatureCollection")

        features = data.get("features") or []
        if not isinstance(features, list):
            raise CommandError("GeoJSON 'features' must be a list")

        table_name = model._meta.db_table

        if truncate:
            model.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Truncated: {table_name}"))

        inserted = 0
        skipped = 0
        objs = []

        # SRID: چون خروجی ogr2ogr -t_srs EPSG:4326 بوده
        # پس هندسه‌ها باید 4326 باشند.
        for f in features:
            if not isinstance(f, dict):
                skipped += 1
                continue

            geom_json = f.get("geometry")
            props = f.get("properties") or {}

            if not geom_json:
                skipped += 1
                continue

            try:
                geom = GEOSGeometry(json.dumps(geom_json), srid=4326)
            except Exception:
                skipped += 1
                continue

            geom = _normalize_geom(geom)
            if geom is None:
                skipped += 1
                continue

            name = _pick_name(props, fallback="Unnamed")

            if kind == "fire-risk":
                level = _pick_level(props, default=1)
                objs.append(model(name=name, level=level, geometry=geom))
            else:
                objs.append(model(name=name, geometry=geom))

            # flush batch
            if len(objs) >= batch:
                with transaction.atomic():
                    model.objects.bulk_create(objs, batch_size=batch)
                inserted += len(objs)
                objs = []

        # final flush
        if objs:
            with transaction.atomic():
                model.objects.bulk_create(objs, batch_size=batch)
            inserted += len(objs)

        self.stdout.write(
            self.style.SUCCESS(
                f"Inserted={inserted} | Skipped={skipped} | Table={table_name}"
            )
        )
