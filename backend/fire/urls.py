from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    IndexLayerViewSet, SatelliteImageViewSet,
    IranProvinceViewSet, IranCountyViewSet, IranForestViewSet
)

router = DefaultRouter()
router.register(r"index", IndexLayerViewSet, basename="fire-index")
router.register(r"satellite-images", SatelliteImageViewSet, basename="fire-satellite-images")
router.register(r"provinces", IranProvinceViewSet, basename="fire-provinces")
router.register(r"counties", IranCountyViewSet, basename="fire-counties")
router.register(r"forests", IranForestViewSet, basename="fire-forests")

urlpatterns = [
    path("", include(router.urls)),
]
