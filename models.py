"""
Core Inventory Management System Models
Base models and common functionality for all microservices
"""

import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import json

class Address(models.Model):

    
    country = models.CharField(
        max_length=255,
        verbose_name=_('Country'),
        help_text=_('Country of the address'),
        null=True,
        blank=True
    )
    region = models.CharField(
        max_length=255,
        verbose_name=_('Region/State'),
        help_text=_('Region or state within the country'),
        null=True,
        blank=True
    )
    subregion = models.CharField(
        max_length=255,
        verbose_name=_('Subregion/Province'),
        help_text=_('Subregion or province within the region'),
        null=True,
        blank=True
    )
    city = models.CharField(
        max_length=255,
        verbose_name=_('City'),
        help_text=_('City of the address'),
        null=True,
        blank=True
    )
    apt_number = models.PositiveIntegerField(
        verbose_name=_('Apartment number'),
        null=True,
        blank=True
    )
    street_number = models.PositiveIntegerField(
        verbose_name=_('Street number'),
        null=True,
        blank=True
    )
    street = models.CharField(max_length=255,blank=False,null=True)

    postal_code = models.CharField(
        max_length=10,
        verbose_name=_('Postal code'),
        help_text=_('Postal code'),
        blank=True,
        null=True,
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        verbose_name=_('Latitude'),
        help_text=_('Geographical latitude of the address'),
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        verbose_name=_('Longitude'),
        help_text=_('Geographical longitude of the address'),
        null=True,
        blank=True
    )

    def __str__(self):
        return f'{self.street}, {self.city}, {self.region}, {self.country}'


class InventoryManager(models.Manager):
    """Custom manager for inventory-related models"""
    
    def for_profile(self, profile_id):
        return self.get_queryset().filter(profile_id=profile_id)
    
    def active(self):
        return self.get_queryset().filter(is_active=True)
    
    def available(self):
        return self.get_queryset().filter(is_active=True, available_quantity__gt=0)
    
    def available_for_dates(self, check_in, check_out):
        return self.get_queryset().filter(
            is_active=True,
            availability__date__range=[check_in, check_out],
            availability__is_available=True
        ).distinct()


class ProfileMixin(models.Model):
    """Abstract model providing multi-tenant functionality"""
    
    profile_id = models.CharField(
        max_length=50,
        help_text="Reference to CompanyProfile ID from users service"
    )
    created_by_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Reference to User ID from users service"
    )
    modified_by_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Reference to User ID from users service"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = InventoryManager()
    
    class Meta:
        abstract = True


class InventoryType(models.TextChoices):
    """Types of inventory across all microservices"""
    ROOM = 'room', _('Hotel Room')
    VEHICLE = 'vehicle', _('Vehicle')
    TICKET = 'ticket', _('Event Ticket')
    APPOINTMENT = 'appointment', _('Appointment Slot')
    WORKSPACE = 'workspace', _('Workspace')
    SERVICE = 'service', _('Service')
    PRODUCT = 'product', _('Product')
    TABLE = 'table', _('Restaurant Table')


class InventoryStatus(models.TextChoices):
    """Common inventory statuses"""
    AVAILABLE = 'available', _('Available')
    RESERVED = 'reserved', _('Reserved')
    OCCUPIED = 'occupied', _('Occupied')
    MAINTENANCE = 'maintenance', _('Under Maintenance')
    OUT_OF_ORDER = 'out_of_order', _('Out of Order')
    RETIRED = 'retired', _('Retired')


class BaseInventoryItem(ProfileMixin):
    """Base model for all inventory items"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    inventory_type = models.CharField(max_length=20, choices=InventoryType.choices)
    
    # Quantity Management
    total_quantity = models.PositiveIntegerField(default=1)
    available_quantity = models.PositiveIntegerField(default=1)
    reserved_quantity = models.PositiveIntegerField(default=0)
    
    # Pricing
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='NGN')
    
    # Status and Flags
    status = models.CharField(
        max_length=20,
        choices=InventoryStatus.choices,
        default=InventoryStatus.AVAILABLE
    )
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # Blockchain Integration
    blockchain_hash = models.CharField(max_length=66, blank=True,null=True,editable=False)
    last_blockchain_sync = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['profile_id', 'inventory_type']),
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['available_quantity']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_inventory_type_display()})"
    
    def reserve(self, quantity=1):
        """Reserve inventory items"""
        if self.available_quantity >= quantity:
            self.available_quantity -= quantity
            self.reserved_quantity += quantity
            self.save()
            return True
        return False
    
    def release_reservation(self, quantity=1):
        """Release reserved inventory"""
        if self.reserved_quantity >= quantity:
            self.reserved_quantity -= quantity
            self.available_quantity += quantity
            self.save()
            return True
        return False
    
    def occupy(self, quantity=1):
        """Mark inventory as occupied"""
        if self.reserved_quantity >= quantity:
            self.reserved_quantity -= quantity
            # Don't add back to available - it's now occupied
            self.save()
            return True
        return False
    
    def make_available(self, quantity=1):
        """Make inventory available again"""
        self.available_quantity += quantity
        self.save()


class InventoryReservation(ProfileMixin):
    """Track inventory reservations"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventory_item_id = models.UUIDField()  # Generic foreign key
    inventory_type = models.CharField(max_length=20, choices=InventoryType.choices)
    
    # Reservation Details
    customer_user_id = models.CharField(max_length=50)
    quantity_reserved = models.PositiveIntegerField(default=1)
    reservation_date = models.DateTimeField(default=timezone.now)
    expiry_date = models.DateTimeField()
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', _('pending')),
            ('confirmed', _('Confirmed/Paid for')),
            ('active', _('Active')),
            ('expired', _('Expired')),
            ('cancelled', _('Cancelled')),
        ],
        default='pending'
    )
    
    # Blockchain
    blockchain_hash = models.CharField(max_length=66, blank=True,null=True,editable=False)
    
    class Meta:
        indexes = [
            models.Index(fields=['profile_id', 'status']),
            models.Index(fields=['inventory_item_id', 'inventory_type']),
            models.Index(fields=['expiry_date']),
        ]


class InventoryPricing(ProfileMixin):
    """Dynamic pricing for inventory items"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventory_item_id = models.UUIDField()
    inventory_type = models.CharField(max_length=20, choices=InventoryType.choices)
    
    # Pricing Rules
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Conditions
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    days_of_week = models.JSONField(default=list)  # [0,1,2,3,4,5,6]
    
    # Seasonal/Event Pricing
    is_seasonal = models.BooleanField(default=False)
    is_peak_pricing = models.BooleanField(default=False)
    minimum_stay = models.PositiveIntegerField(null=True, blank=True)
    
    # Priority (higher number = higher priority)
    priority = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['inventory_item_id', 'inventory_type']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['is_active', 'priority']),
        ]


class InventoryMaintenance(ProfileMixin):
    """Track maintenance schedules for inventory"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventory_item_id = models.UUIDField()
    inventory_type = models.CharField(max_length=20, choices=InventoryType.choices)
    
    # Maintenance Details
    maintenance_type = models.CharField(
        max_length=50,
        choices=[
            ('routine', _('Routine Maintenance')),
            ('repair', _('Repair')),
            ('inspection', _('Inspection')),
            ('cleaning', _('Deep Cleaning')),
            ('upgrade', _('Upgrade')),
        ]
    )
    
    description = models.TextField()
    scheduled_date = models.DateTimeField()
    completed_date = models.DateTimeField(null=True, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('scheduled', _('Scheduled')),
            ('in_progress', _('In Progress')),
            ('completed', _('Completed')),
            ('cancelled', _('Cancelled')),
        ],
        default='scheduled'
    )
    
    # Cost and Details
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    vendor_name = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    
    # Blockchain
    blockchain_hash = models.CharField(max_length=66, blank=True,null=True,editable=False)
    
    class Meta:
        ordering = ['scheduled_date']
        indexes = [
            models.Index(fields=['inventory_item_id', 'inventory_type']),
            models.Index(fields=['scheduled_date', 'status']),
        ]


class InventoryAnalytics(ProfileMixin):
    """Store analytics data for inventory performance"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventory_item_id = models.UUIDField()
    inventory_type = models.CharField(max_length=20, choices=InventoryType.choices)
    
    # Time Period
    date = models.DateField()
    period_type = models.CharField(
        max_length=20,
        choices=[
            ('daily', _('Daily')),
            ('weekly', _('Weekly')),
            ('monthly', _('Monthly')),
        ]
    )
    
    # Metrics
    total_bookings = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    occupancy_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Percentage
    utilization_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Performance Indicators
    average_booking_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cancellation_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    no_show_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Additional Metrics (JSON for flexibility)
    custom_metrics = models.JSONField(default=dict)
    
    class Meta:
        unique_together = ['inventory_item_id', 'inventory_type', 'date', 'period_type']
        indexes = [
            models.Index(fields=['inventory_item_id', 'inventory_type']),
            models.Index(fields=['date', 'period_type']),
        ]


class InventoryAlert(ProfileMixin):
    """Alerts and notifications for inventory management"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventory_item_id = models.UUIDField(null=True, blank=True)
    inventory_type = models.CharField(max_length=20, choices=InventoryType.choices, null=True, blank=True)
    
    # Alert Details
    alert_type = models.CharField(
        max_length=50,
        choices=[
            ('low_stock', _('Low Stock')),
            ('maintenance_due', _('Maintenance Due')),
            ('high_demand', _('High Demand')),
            ('price_optimization', _('Price Optimization')),
            ('overbooking', _('Overbooking Risk')),
            ('system_error', _('System Error')),
        ]
    )
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    severity = models.CharField(
        max_length=20,
        choices=[
            ('low', _('Low')),
            ('medium', _('Medium')),
            ('high', _('High')),
            ('critical', _('Critical')),
        ],
        default='medium'
    )
    
    # Status
    is_read = models.BooleanField(default=False)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by_id = models.CharField(max_length=50, blank=True)
    
    # Actions
    action_required = models.BooleanField(default=False)
    action_taken = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['profile_id', 'is_read']),
            models.Index(fields=['alert_type', 'severity']),
            models.Index(fields=['is_resolved', 'created_at']),
        ]


class InventoryBulkOperation(ProfileMixin):
    """Track bulk operations on inventory"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Operation Details
    operation_type = models.CharField(
        max_length=50,
        choices=[
            ('import', _('Import')),
            ('export', _('Export')),
            ('bulk_update', _('Bulk Update')),
            ('bulk_pricing', _('Bulk Pricing')),
            ('bulk_maintenance', _('Bulk Maintenance')),
        ]
    )
    
    inventory_type = models.CharField(max_length=20, choices=InventoryType.choices)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', _('Pending')),
            ('processing', _('Processing')),
            ('completed', _('Completed')),
            ('failed', _('Failed')),
        ],
        default='pending'
    )
    
    # Progress
    total_items = models.PositiveIntegerField(default=0)
    processed_items = models.PositiveIntegerField(default=0)
    failed_items = models.PositiveIntegerField(default=0)
    
    # Files
    input_file = models.FileField(upload_to='inventory/bulk_operations/', null=True, blank=True)
    output_file = models.FileField(upload_to='inventory/bulk_operations/', null=True, blank=True)
    error_log = models.TextField(blank=True)
    
    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['profile_id', 'status']),
            models.Index(fields=['operation_type', 'inventory_type']),
        ]
