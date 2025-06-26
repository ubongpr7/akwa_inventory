"""
Inventory Management Filters
Advanced filtering for inventory queries
"""

import django_filters
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from .models import (
    BaseInventoryItem, InventoryReservation, InventoryMaintenance,
    InventoryAnalytics, InventoryAlert
)


class BaseInventoryFilter(django_filters.FilterSet):
    """Base filter for inventory items"""
    
    # Status filters
    status = django_filters.ChoiceFilter(choices=BaseInventoryItem._meta.get_field('status').choices)
    is_active = django_filters.BooleanFilter()
    is_featured = django_filters.BooleanFilter()
    
    # Quantity filters
    min_available = django_filters.NumberFilter(field_name='available_quantity', lookup_expr='gte')
    max_available = django_filters.NumberFilter(field_name='available_quantity', lookup_expr='lte')
    has_availability = django_filters.BooleanFilter(method='filter_has_availability')
    
    # Price filters
    min_price = django_filters.NumberFilter(field_name='base_price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='base_price', lookup_expr='lte')
    
    # Date filters
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    updated_after = django_filters.DateTimeFilter(field_name='updated_at', lookup_expr='gte')
    
    # Search filters
    search = django_filters.CharFilter(method='filter_search')
    
    class Meta:
        model = BaseInventoryItem
        fields = [
            'inventory_type', 'status', 'is_active', 'is_featured',
            'currency'
        ]
    
    def filter_has_availability(self, queryset, name, value):
        """Filter items with availability"""
        if value:
            return queryset.filter(available_quantity__gt=0)
        return queryset.filter(available_quantity=0)
    
    def filter_search(self, queryset, name, value):
        """Search across multiple fields"""
        return queryset.filter(
            Q(name__icontains=value) |
            Q(description__icontains=value) |
            Q(metadata__icontains=value)
        )


class InventoryReservationFilter(django_filters.FilterSet):
    """Filter for inventory reservations"""
    
    status = django_filters.ChoiceFilter(choices=InventoryReservation._meta.get_field('status').choices)
    inventory_type = django_filters.ChoiceFilter()
    
    # Date filters
    reserved_after = django_filters.DateTimeFilter(field_name='reservation_date', lookup_expr='gte')
    reserved_before = django_filters.DateTimeFilter(field_name='reservation_date', lookup_expr='lte')
    expires_after = django_filters.DateTimeFilter(field_name='expiry_date', lookup_expr='gte')
    expires_before = django_filters.DateTimeFilter(field_name='expiry_date', lookup_expr='lte')
    
    # Special filters
    expiring_soon = django_filters.BooleanFilter(method='filter_expiring_soon')
    expired = django_filters.BooleanFilter(method='filter_expired')
    
    class Meta:
        model = InventoryReservation
        fields = ['status', 'inventory_type', 'customer_user_id']
    
    def filter_expiring_soon(self, queryset, name, value):
        """Filter reservations expiring in next hour"""
        if value:
            one_hour_from_now = timezone.now() + timedelta(hours=1)
            return queryset.filter(
                status='active',
                expiry_date__lte=one_hour_from_now
            )
        return queryset
    
    def filter_expired(self, queryset, name, value):
        """Filter expired reservations"""
        if value:
            return queryset.filter(
                status='active',
                expiry_date__lt=timezone.now()
            )
        return queryset


class InventoryMaintenanceFilter(django_filters.FilterSet):
    """Filter for maintenance records"""
    
    status = django_filters.ChoiceFilter(choices=InventoryMaintenance._meta.get_field('status').choices)
    maintenance_type = django_filters.ChoiceFilter(choices=InventoryMaintenance._meta.get_field('maintenance_type').choices)
    inventory_type = django_filters.ChoiceFilter()
    
    # Date filters
    scheduled_after = django_filters.DateTimeFilter(field_name='scheduled_date', lookup_expr='gte')
    scheduled_before = django_filters.DateTimeFilter(field_name='scheduled_date', lookup_expr='lte')
    completed_after = django_filters.DateTimeFilter(field_name='completed_date', lookup_expr='gte')
    completed_before = django_filters.DateTimeFilter(field_name='completed_date', lookup_expr='lte')
    
    # Cost filters
    min_cost = django_filters.NumberFilter(field_name='estimated_cost', lookup_expr='gte')
    max_cost = django_filters.NumberFilter(field_name='estimated_cost', lookup_expr='lte')
    
    # Special filters
    overdue = django_filters.BooleanFilter(method='filter_overdue')
    due_soon = django_filters.BooleanFilter(method='filter_due_soon')
    
    class Meta:
        model = InventoryMaintenance
        fields = ['status', 'maintenance_type', 'inventory_type', 'vendor_name']
    
    def filter_overdue(self, queryset, name, value):
        """Filter overdue maintenance"""
        if value:
            return queryset.filter(
                status__in=['scheduled', 'in_progress'],
                scheduled_date__lt=timezone.now()
            )
        return queryset
    
    def filter_due_soon(self, queryset, name, value):
        """Filter maintenance due in next 7 days"""
        if value:
            seven_days_from_now = timezone.now() + timedelta(days=7)
            return queryset.filter(
                status='scheduled',
                scheduled_date__lte=seven_days_from_now
            )
        return queryset


class InventoryAnalyticsFilter(django_filters.FilterSet):
    """Filter for analytics data"""
    
    period_type = django_filters.ChoiceFilter(choices=InventoryAnalytics._meta.get_field('period_type').choices)
    inventory_type = django_filters.ChoiceFilter()
    
    # Date range
    date_from = django_filters.DateFilter(field_name='date', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='date', lookup_expr='lte')
    
    # Performance filters
    min_occupancy = django_filters.NumberFilter(field_name='occupancy_rate', lookup_expr='gte')
    min_revenue = django_filters.NumberFilter(field_name='total_revenue', lookup_expr='gte')
    
    class Meta:
        model = InventoryAnalytics
        fields = ['period_type', 'inventory_type']


class InventoryAlertFilter(django_filters.FilterSet):
    """Filter for inventory alerts"""
    
    alert_type = django_filters.ChoiceFilter(choices=InventoryAlert._meta.get_field('alert_type').choices)
    severity = django_filters.ChoiceFilter(choices=InventoryAlert._meta.get_field('severity').choices)
    is_read = django_filters.BooleanFilter()
    is_resolved = django_filters.BooleanFilter()
    action_required = django_filters.BooleanFilter()
    
    # Date filters
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    # Special filters
    unread_critical = django_filters.BooleanFilter(method='filter_unread_critical')
    
    class Meta:
        model = InventoryAlert
        fields = ['alert_type', 'severity', 'is_read', 'is_resolved', 'action_required']
    
    def filter_unread_critical(self, queryset, name, value):
        """Filter unread critical alerts"""
        if value:
            return queryset.filter(
                severity='critical',
                is_read=False,
                is_resolved=False
            )
        return queryset
