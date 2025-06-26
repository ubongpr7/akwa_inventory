"""
Common Inventory Management Serializers
Base serializers for all inventory-related models
"""

from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone
from .models import (
    BaseInventoryItem, InventoryReservation, InventoryPricing,
    InventoryMaintenance, InventoryAnalytics, InventoryAlert,
    InventoryBulkOperation
)


class BaseInventoryItemSerializer(serializers.ModelSerializer):
    """Base serializer for inventory items"""
    
    occupancy_rate = serializers.SerializerMethodField()
    revenue_today = serializers.SerializerMethodField()
    
    class Meta:
        model = BaseInventoryItem
        fields = [
            'id', 'name', 'description', 'inventory_type',
            'total_quantity', 'available_quantity', 'reserved_quantity',
            'base_price', 'currency', 'status', 'is_active', 'is_featured',
            'metadata', 'blockchain_hash', 'last_blockchain_sync',
            'occupancy_rate', 'revenue_today',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'blockchain_hash', 'last_blockchain_sync', 'created_at', 'updated_at']
    
    def get_occupancy_rate(self, obj) -> float:
        """Calculate current occupancy rate"""
        if obj.total_quantity == 0:
            return 0.0
        occupied = obj.total_quantity - obj.available_quantity
        return round((occupied / obj.total_quantity) * 100, 2)
    
    def get_revenue_today(self, obj) -> Decimal:
        """Get today's revenue for this inventory item"""
        # This would typically query related booking/sales models
        # For now, return a placeholder
        return Decimal('0.00')


class InventoryReservationSerializer(serializers.ModelSerializer):
    """Serializer for inventory reservations"""
    
    time_until_expiry = serializers.SerializerMethodField()
    
    class Meta:
        model = InventoryReservation
        fields = [
            'id', 'inventory_item_id', 'inventory_type',
            'customer_user_id', 'quantity_reserved',
            'reservation_date', 'expiry_date', 'status',
            'blockchain_hash', 'time_until_expiry',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'blockchain_hash', 'created_at', 'updated_at']
    
    def get_time_until_expiry(self, obj) -> int:
        """Get minutes until reservation expires"""
        if obj.expiry_date:
            delta = obj.expiry_date - timezone.now()
            return max(0, int(delta.total_seconds() / 60))
        return 0


class InventoryPricingSerializer(serializers.ModelSerializer):
    """Serializer for dynamic pricing"""
    
    is_currently_active = serializers.SerializerMethodField()
    
    class Meta:
        model = InventoryPricing
        fields = [
            'id', 'inventory_item_id', 'inventory_type', 'name', 'price',
            'start_date', 'end_date', 'start_time', 'end_time',
            'days_of_week', 'is_seasonal', 'is_peak_pricing',
            'minimum_stay', 'priority', 'is_active',
            'is_currently_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_is_currently_active(self, obj) -> bool:
        """Check if pricing rule is currently active"""
        now = timezone.now()
        today = now.date()
        current_time = now.time()
        current_weekday = now.weekday()
        
        if obj.start_date and today < obj.start_date:
            return False
        if obj.end_date and today > obj.end_date:
            return False
        
        # Check time range
        if obj.start_time and current_time < obj.start_time:
            return False
        if obj.end_time and current_time > obj.end_time:
            return False
        
        # Check days of week
        if obj.days_of_week and current_weekday not in obj.days_of_week:
            return False
        
        return obj.is_active


class InventoryMaintenanceSerializer(serializers.ModelSerializer):
    """Serializer for maintenance schedules"""
    
    is_overdue = serializers.SerializerMethodField()
    days_until_scheduled = serializers.SerializerMethodField()
    
    class Meta:
        model = InventoryMaintenance
        fields = [
            'id', 'inventory_item_id', 'inventory_type',
            'maintenance_type', 'description', 'scheduled_date',
            'completed_date', 'status', 'estimated_cost',
            'actual_cost', 'vendor_name', 'notes',
            'blockchain_hash', 'is_overdue', 'days_until_scheduled',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'blockchain_hash', 'created_at', 'updated_at']
    
    def get_is_overdue(self, obj) -> bool:
        """Check if maintenance is overdue"""
        if obj.status in ['completed', 'cancelled']:
            return False
        return obj.scheduled_date < timezone.now()
    
    def get_days_until_scheduled(self, obj) -> int:
        """Get days until scheduled maintenance"""
        if obj.status in ['completed', 'cancelled']:
            return 0
        delta = obj.scheduled_date - timezone.now()
        return max(0, delta.days)


class InventoryAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for inventory analytics"""
    
    performance_score = serializers.SerializerMethodField()
    
    class Meta:
        model = InventoryAnalytics
        fields = [
            'id', 'inventory_item_id', 'inventory_type',
            'date', 'period_type', 'total_bookings', 'total_revenue',
            'occupancy_rate', 'utilization_rate', 'average_booking_value',
            'cancellation_rate', 'no_show_rate', 'custom_metrics',
            'performance_score', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_performance_score(self, obj) -> float:
        """Calculate overall performance score"""
        # Weighted score based on key metrics
        occupancy_weight = 0.4
        revenue_weight = 0.3
        reliability_weight = 0.3
        
        occupancy_score = min(float(obj.occupancy_rate), 100.0)
        revenue_score = min(float(obj.average_booking_value) / 100, 100.0)  # Normalize
        reliability_score = 100.0 - float(obj.cancellation_rate + obj.no_show_rate)
        
        total_score = (
            occupancy_score * occupancy_weight +
            revenue_score * revenue_weight +
            reliability_score * reliability_weight
        )
        
        return round(total_score, 2)


class InventoryAlertSerializer(serializers.ModelSerializer):
    """Serializer for inventory alerts"""
    
    age_hours = serializers.SerializerMethodField()
    
    class Meta:
        model = InventoryAlert
        fields = [
            'id', 'inventory_item_id', 'inventory_type',
            'alert_type', 'title', 'message', 'severity',
            'is_read', 'is_resolved', 'resolved_at',
            'action_required', 'action_taken',
            'age_hours', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_age_hours(self, obj) -> int:
        """Get alert age in hours"""
        delta = timezone.now() - obj.created_at
        return int(delta.total_seconds() / 3600)


class InventoryBulkOperationSerializer(serializers.ModelSerializer):
    """Serializer for bulk operations"""
    
    progress_percentage = serializers.SerializerMethodField()
    estimated_completion = serializers.SerializerMethodField()
    
    class Meta:
        model = InventoryBulkOperation
        fields = [
            'id', 'operation_type', 'inventory_type', 'status',
            'total_items', 'processed_items', 'failed_items',
            'input_file', 'output_file', 'error_log',
            'progress_percentage', 'estimated_completion',
            'started_at', 'completed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'processed_items', 'failed_items', 'output_file',
            'error_log', 'started_at', 'completed_at', 'created_at', 'updated_at'
        ]
    
    def get_progress_percentage(self, obj) -> float:
        """Calculate progress percentage"""
        if obj.total_items == 0:
            return 0.0
        return round((obj.processed_items / obj.total_items) * 100, 2)
    
    def get_estimated_completion(self, obj) -> str:
        """Estimate completion time"""
        if obj.status == 'completed':
            return "Completed"
        if obj.status == 'failed':
            return "Failed"
        if obj.total_items == 0 or obj.processed_items == 0:
            return "Unknown"
        
        # Simple estimation based on current progress
        remaining = obj.total_items - obj.processed_items
        if obj.started_at:
            elapsed = timezone.now() - obj.started_at
            rate = obj.processed_items / elapsed.total_seconds()
            if rate > 0:
                remaining_seconds = remaining / rate
                return f"{int(remaining_seconds / 60)} minutes"
        
        return "Calculating..."


class InventorySummarySerializer(serializers.Serializer):
    """Summary serializer for dashboard"""
    
    total_items = serializers.IntegerField()
    available_items = serializers.IntegerField()
    reserved_items = serializers.IntegerField()
    maintenance_items = serializers.IntegerField()
    total_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    occupancy_rate = serializers.FloatField()
    revenue_today = serializers.DecimalField(max_digits=12, decimal_places=2)
    revenue_this_week = serializers.DecimalField(max_digits=12, decimal_places=2)
    revenue_this_month = serializers.DecimalField(max_digits=12, decimal_places=2)
    alerts_count = serializers.IntegerField()
    pending_maintenance = serializers.IntegerField()
