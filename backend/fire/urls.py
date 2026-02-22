# fire/urls.py
from django.urls import path
from .views import *

urlpatterns = [
    path("counties/", CountiesGeoJSONAPIView.as_view(), name="fire-counties"),
    path("forests/", ForestsGeoJSONAPIView.as_view(), name="fire-forests"),
    path("fire-risk/", FireRiskGeoJSONAPIView.as_view(), name="fire-risk"),

    path("aoi/", AOIAPIView.as_view(), name="fire-aoi"),
    path("aoi/<int:aoi_id>/", AOIDetailAPIView.as_view(), name="fire-aoi-detail"),

    path("satellite-images/", SatelliteImagesAPIView.as_view(), name="fire-satellite-images"),
    path("index-layers/", IndexLayersAPIView.as_view(), name="fire-index-layers"),

    path("upload/satellite/", UploadSatelliteImageAPIView.as_view(), name="upload-satellite"),
    path("upload/index/", UploadIndexLayerAPIView.as_view(), name="upload-index"),
    path("styles/<str:style_name>/legend/", StyleLegendAPIView.as_view(), name="fire-style-legend"),
]