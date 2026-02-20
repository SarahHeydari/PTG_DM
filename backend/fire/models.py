# fire/models.py
from django.db import models
from django.contrib.gis.db import models as gis_models


# fire/models.py
from django.db import models
from django.contrib.gis.db import models as gis_models


class IndexLayer(models.Model):
    title = models.CharField(max_length=200)
    minio_link = models.URLField(max_length=500)  # legacy/optional (we will keep)
    index_name = models.CharField(max_length=50)  # NDVI, NBR, ...
    date = models.DateField()
    satellite_name = models.CharField(max_length=50)  # SENTINEL2, LANDSAT8, ...
    geometry = gis_models.PolygonField(geography=True, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    # -------------------------
    # Upload pipeline fields
    # -------------------------
    minio_bucket = models.CharField(max_length=100, default="fire")
    minio_object = models.CharField(max_length=600, null=True, blank=True)  # object key/path in MinIO

    geoserver_workspace = models.CharField(max_length=100, default="fire")
    geoserver_store = models.CharField(max_length=200, null=True, blank=True)
    geoserver_layer = models.CharField(max_length=300, null=True, blank=True)

    wms_url = models.URLField(max_length=500, null=True, blank=True)
    wmts_url = models.URLField(max_length=500, null=True, blank=True)

    is_published = models.BooleanField(default=False)

    STATUS_CHOICES = [
        ("pending", "pending"),
        ("minio_ok", "minio_ok"),
        ("geoserver_ok", "geoserver_ok"),
        ("failed", "failed"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "index"  # keep stable (do NOT rename now)
        indexes = [
            models.Index(fields=["index_name", "date"]),
            models.Index(fields=["satellite_name", "date"]),
            models.Index(fields=["status"]),
            models.Index(fields=["is_published"]),
        ]

    def __str__(self):
        return f"{self.index_name} | {self.title}"


class SatelliteImage(models.Model):
    satellite_name = models.CharField(max_length=50)
    date_time = models.DateTimeField()
    image_name = models.CharField(max_length=200)
    minio_link = models.URLField(max_length=500)  # legacy/optional (we will keep)
    geometry = gis_models.PolygonField(geography=True, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    # -------------------------
    # Upload pipeline fields
    # -------------------------
    minio_bucket = models.CharField(max_length=100, default="fire")
    minio_object = models.CharField(max_length=600, null=True, blank=True)  # object key/path in MinIO

    geoserver_workspace = models.CharField(max_length=100, default="fire")
    geoserver_store = models.CharField(max_length=200, null=True, blank=True)
    geoserver_layer = models.CharField(max_length=300, null=True, blank=True)

    wms_url = models.URLField(max_length=500, null=True, blank=True)
    wmts_url = models.URLField(max_length=500, null=True, blank=True)

    is_published = models.BooleanField(default=False)

    STATUS_CHOICES = [
        ("pending", "pending"),
        ("minio_ok", "minio_ok"),
        ("geoserver_ok", "geoserver_ok"),
        ("failed", "failed"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "satellite_images"
        indexes = [
            models.Index(fields=["satellite_name", "date_time"]),
            models.Index(fields=["status"]),
            models.Index(fields=["is_published"]),
        ]

    def __str__(self):
        return f"{self.satellite_name} | {self.image_name}"

class IranCounty(gis_models.Model):
    name = models.CharField(max_length=100)
    geometry = gis_models.MultiPolygonField(geography=True)  # ✅ was PolygonField

    class Meta:
        db_table = "iran_counties"
        indexes = [models.Index(fields=["name"])]

    def __str__(self):
        return self.name


class IranProvince(gis_models.Model):
    name = models.CharField(max_length=100)
    geometry = gis_models.MultiPolygonField(geography=True)  # ✅ was PolygonField

    class Meta:
        db_table = "iran_provinces"
        indexes = [models.Index(fields=["name"])]

    def __str__(self):
        return self.name


class IranForest(gis_models.Model):
    name = models.CharField(max_length=100)
    geometry = gis_models.MultiPolygonField(geography=True)

    class Meta:
        db_table = "iran_forests"
        indexes = [models.Index(fields=["name"])]

    def __str__(self):
        return self.name


class AOI(gis_models.Model):
    """
    User-defined Area Of Interest (AOI)
    - source: kml | draw
    """
    name = models.CharField(max_length=120, default="AOI")
    source = models.CharField(max_length=20, default="draw")  # draw | kml
    geometry = gis_models.PolygonField(geography=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fire_aoi"
        ordering = ["-id"]

    def __str__(self):
        return f"{self.name} ({self.source})"

class FireRiskArea(gis_models.Model):
    name = models.CharField(max_length=120)
    level = models.IntegerField(default=1)
    geometry = gis_models.PointField(geography=True)  # ✅ چون shapefile Point است

    class Meta:
        db_table = "fire_risk_areas"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["level"]),
        ]

    def __str__(self):
        return self.name
