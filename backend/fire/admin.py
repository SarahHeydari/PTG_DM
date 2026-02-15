# fire/admin.py
from django.contrib import admin
from .models import IndexLayer, SatelliteImage, IranCounty, IranProvince, IranForest


@admin.register(IndexLayer)
class IndexLayerAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "index_name", "date", "satellite_name")
    list_filter = ("index_name", "satellite_name", "date")
    search_fields = ("title", "minio_link")


@admin.register(SatelliteImage)
class SatelliteImageAdmin(admin.ModelAdmin):
    list_display = ("id", "satellite_name", "image_name", "date_time")
    list_filter = ("satellite_name",)
    search_fields = ("image_name", "minio_link")


@admin.register(IranCounty)
class IranCountyAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(IranProvince)
class IranProvinceAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(IranForest)
class IranForestAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
