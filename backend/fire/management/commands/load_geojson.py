# fire/management/commands/load_geojson.py
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, MultiPoint
from django.db import transaction

from fire.models import IranProvince, IranCounty, IranForest, FireRiskArea


def _read_geojson(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise CommandError(f"File not found: {path}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise CommandError(f"Invalid JSON: {e}")


def _as_geos(geom_obj: dict, srid: int = 4326) -> GEOSGeometry:
    # geom_obj is like {"type": "...", "coordinates": ...}
    g = GEOSGeometry(json.dumps(geom_obj))
    g.srid = srid
    return g


def _coerce_to_multipolygon(g: GEOSGeometry):
    """
    Accept Polygon/MultiPolygon. Convert Polygon -> MultiPolygon.
    Return (geom or None, skip_reason or None)
    """
    if g is None:
        return None, "empty geometry"

    if g.geom_type == "MultiPolygon":
        return g, None
    if g.geom_type == "Polygon":
        return MultiPolygon(g), None

    # Sometimes geometry collections exist
    if g.geom_type == "GeometryCollection":
        polys = []
        for part in g:
            if part.geom_type == "Polygon":
                polys.append(part)
            elif part.geom_type == "MultiPolygon":
                for p in part:
                    polys.append(p)
        if polys:
            return MultiPolygon(*polys), None
        return None, "GeometryCollection without polygons"

    return None, f"unsupported geom_type for multipolygon: {g.geom_type}"


def _coerce_to_polygon(g: GEOSGeometry):
    """
    Accept Polygon/MultiPolygon. If MultiPolygon, take the first polygon (fallback).
    Return (geom or None, skip_reason or None)
    """
    if g is None:
        return None, "empty geometry"

    if g.geom_type == "Polygon":
        return g, None
    if g.geom_type == "MultiPolygon":
        # fallback: take first polygon (keeps loader running)
        try:
            return g[0], None
        except Exception:
            return None, "MultiPolygon empty"

    if g.geom_type == "GeometryCollection":
        for part in g:
            if part.geom_type == "Polygon":
                return part, None
            if part.geom_type == "MultiPolygon":
                try:
                    return part[0], None
                except Exception:
                    pass
        return None, "GeometryCollection without polygons"

    return None, f"unsupported geom_type for polygon: {g.geom_type}"


def _coerce_to_points(g: GEOSGeometry):
    """
    Accept Point/MultiPoint. If MultiPoint, return list of Points.
    Return (points_list, skip_reason or None)
    """
    if g is None:
        return [], "empty geometry"

    if g.geom_type == "Point":
        return [g], None

    if g.geom_type == "MultiPoint":
        pts = []
        for p in g:
            if p.geom_type == "Point":
                pts.append(p)
        if pts:
            return pts, None
        return [], "MultiPoint empty"

    # If somebody gives Polygon for risk layer, we could take centroid, but
    # for now we skip explicitly to avoid silent wrong data.
    return [], f"unsupported geom_type for point: {g.geom_type}"


class Command(BaseCommand):
    help = "Load Fire subsystem GeoJSON into PostGIS tables."

    def add_arguments(self, parser):
        parser.add_argument("--kind", required=True, choices=["provinces", "counties", "forests", "fire-risk"])
        parser.add_argument("--path", required=True, help="Path to GeoJSON FeatureCollection")
        parser.add_argument("--truncate", action="store_true", help="Truncate table before insert")
        parser.add_argument("--batch", type=int, default=1000, help="bulk_create batch size")

    @transaction.atomic
    def handle(self, *args, **opts):
        kind = opts["kind"]
        path = opts["path"]
        truncate = opts["truncate"]
        batch = opts["batch"]

        data = _read_geojson(path)

        if data.get("type") != "FeatureCollection":
            raise CommandError("GeoJSON must be a FeatureCollection")

        features = data.get("features") or []
        if not isinstance(features, list):
            raise CommandError("Invalid FeatureCollection: features must be a list")

        # Map kind -> model + geometry coercer + table name
        if kind == "provinces":
            model = IranProvince
            geom_mode = "polygon"  # your model is PolygonField currently
        elif kind == "counties":
            model = IranCounty
            geom_mode = "polygon"  # your model is PolygonField currently
        elif kind == "forests":
            model = IranForest
            geom_mode = "multipolygon"  # your model is MultiPolygonField
        elif kind == "fire-risk":
            model = FireRiskArea
            geom_mode = "point"  # after your migration: PointField
        else:
            raise CommandError(f"Unknown kind: {kind}")

        if truncate:
            self.stdout.write(self.style.WARNING(f"Truncated: {model._meta.db_table}"))
            model.objects.all().delete()

        inserted = 0
        skipped = 0
        objs = []

        for feat in features:
            if not isinstance(feat, dict) or feat.get("type") != "Feature":
                skipped += 1
                continue

            geom_obj = feat.get("geometry")
            if not geom_obj:
                skipped += 1
                continue

            props = feat.get("properties") or {}
            name = (props.get("name") or props.get("Name") or props.get("NAME") or "").strip()
            if not name:
                # fallback name
                name = f"{kind}_{inserted + skipped + 1}"

            try:
                g = _as_geos(geom_obj, srid=4326)
            except Exception:
                skipped += 1
                continue

            # --- geometry coercion per kind ---
            if geom_mode == "multipolygon":
                geom, reason = _coerce_to_multipolygon(g)
                if geom is None:
                    skipped += 1
                    continue
                objs.append(model(name=name, geometry=geom))

            elif geom_mode == "polygon":
                geom, reason = _coerce_to_polygon(g)
                if geom is None:
                    skipped += 1
                    continue
                objs.append(model(name=name, geometry=geom))

            elif geom_mode == "point":
                points, reason = _coerce_to_points(g)
                if not points:
                    skipped += 1
                    continue

                # level is optional; default 1
                lvl = props.get("level") or props.get("Level") or props.get("LEVEL") or 1
                try:
                    lvl = int(lvl)
                except Exception:
                    lvl = 1

                # explode multipoint -> many rows
                for p in points:
                    objs.append(model(name=name, level=lvl, geometry=p))

            # flush batches
            if len(objs) >= batch:
                model.objects.bulk_create(objs, batch_size=batch)
                inserted += len(objs)
                objs = []

        if objs:
            model.objects.bulk_create(objs, batch_size=batch)
            inserted += len(objs)

        self.stdout.write(self.style.SUCCESS(
            f"Inserted={inserted} | Skipped={skipped} | Table={model._meta.db_table}"
        ))
