# fire/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    FireCatalogAPIView,
    AOIViewSet,
    IndexLayerViewSet, SatelliteImageViewSet,
    IranProvinceViewSet, IranCountyViewSet, IranForestViewSet,
    FireRiskAreaViewSet,
)

router = DefaultRouter()
router.register(r"aoi", AOIViewSet, basename="aoi")
router.register(r"indexes", IndexLayerViewSet, basename="indexes")
router.register(r"satellite-images", SatelliteImageViewSet, basename="satellite-images")

router.register(r"vectors/provinces", IranProvinceViewSet, basename="provinces")
router.register(r"vectors/counties", IranCountyViewSet, basename="counties")
router.register(r"vectors/forests", IranForestViewSet, basename="forests")
router.register(r"vectors/fire-risk", FireRiskAreaViewSet, basename="fire-risk")

urlpatterns = [
    path("catalog/", FireCatalogAPIView.as_view(), name="fire-catalog"),
    path("", include(router.urls)),
]
