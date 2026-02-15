# fire/models.py
from django.db import models
from django.contrib.gis.db import models as gis_models


class IndexLayer(models.Model):
    """
    Table name: index
    Fields:
      id
      title
      minio_link
      index_name (e.g., ndvi)
      date
      geometry (polygon)
      satellite_name
    """
    title = models.CharField(max_length=200)
    minio_link = models.URLField(max_length=500)
    index_name = models.CharField(max_length=50)  # e.g., NDVI, NBR
    date = models.DateField()
    satellite_name = models.CharField(max_length=50)  # e.g., LANDSAT
    geometry = gis_models.PolygonField(geography=True, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "index"
        indexes = [
            models.Index(fields=["index_name", "date"]),
            models.Index(fields=["satellite_name", "date"]),
        ]

    def __str__(self):
        return f"{self.index_name} | {self.title}"


class SatelliteImage(models.Model):
    """
    Table name: satellite_images
    Fields:
      id
      satellite_name
      date_time
      image_name
      minio_link
      geometry (polygon)
    """
    satellite_name = models.CharField(max_length=50)
    date_time = models.DateTimeField()
    image_name = models.CharField(max_length=200)
    minio_link = models.URLField(max_length=500)
    geometry = gis_models.PolygonField(geography=True, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "satellite_images"
        indexes = [
            models.Index(fields=["satellite_name", "date_time"]),
        ]

    def __str__(self):
        return f"{self.satellite_name} | {self.image_name}"


class IranCounty(gis_models.Model):
    """
    Table name: iran_counties
    """
    name = models.CharField(max_length=100)
    geometry = gis_models.PolygonField(geography=True)

    class Meta:
        db_table = "iran_counties"

    def __str__(self):
        return self.name


class IranProvince(gis_models.Model):
    """
    Table name: iran_provinces
    """
    name = models.CharField(max_length=100)
    geometry = gis_models.PolygonField(geography=True)

    class Meta:
        db_table = "iran_provinces"

    def __str__(self):
        return self.name


class IranForest(gis_models.Model):
    """
    Table name: iran_forests
    """
    name = models.CharField(max_length=100)
    geometry = gis_models.PolygonField(geography=True)

    class Meta:
        db_table = "iran_forests"

    def __str__(self):
        return self.name
