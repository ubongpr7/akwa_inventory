"""
Common Inventory Management URLs
Base URL patterns for inventory functionality
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    BaseInventoryViewSet, InventoryReservationViewSet,
    InventoryMaintenanceViewSet, InventoryAlertViewSet,
    InventoryBulkOperationViewSet
)

# Create router for common inventory endpoints
router = DefaultRouter()
router.register(r'reservations', InventoryReservationViewSet, basename='inventory-reservations')
router.register(r'maintenance', InventoryMaintenanceViewSet, basename='inventory-maintenance')
router.register(r'alerts', InventoryAlertViewSet, basename='inventory-alerts')
router.register(r'bulk-operations', InventoryBulkOperationViewSet, basename='inventory-bulk-operations')

urlpatterns = [
    path('', include(router.urls)),
]
