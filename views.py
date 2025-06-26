"""
Common Inventory Management Views
Base views and common functionality for all inventory microservices
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta
import logging

from .models import (
    BaseInventoryItem, InventoryReservation, InventoryPricing,
    InventoryMaintenance, InventoryAnalytics, InventoryAlert,
    InventoryBulkOperation
)
from .serializers import (
    BaseInventoryItemSerializer, InventoryReservationSerializer,
    InventoryPricingSerializer, InventoryMaintenanceSerializer,
    InventoryAnalyticsSerializer, InventoryAlertSerializer,
    InventoryBulkOperationSerializer, InventorySummarySerializer
)

from .permissions import PermissionRequiredMixin
# from .blockchain.integration import get_inventory_logger

logger = logging.getLogger(__name__)


class BaseInventoryViewSet(PermissionRequiredMixin,viewsets.ModelViewSet):
    """Base viewset for inventory management"""
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'base_price', 'available_quantity']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter by profile_id for multi-tenancy"""
        profile_id = self.request.user.profile.get('profile_id')
        if not profile_id:
            return self.queryset.none()
        return self.queryset.filter(profile_id=profile_id)
    
    def perform_create(self, serializer):
        """Set profile_id and log to blockchain"""
        profile_id = self.request.user.profile.get('profile_id')
        created_by_id = str(self.request.user.id)
        
        instance = serializer.save(
            profile_id=profile_id,
            created_by_id=created_by_id
        )
        
        # Log to blockchain
        # try:
        #     blockchain_logger = get_inventory_logger()
        #     tx_hash = blockchain_logger.log_inventory_creation(instance)
        #     if tx_hash:
        #         instance.blockchain_hash = tx_hash
        #         instance.last_blockchain_sync = timezone.now()
        #         instance.save(update_fields=['blockchain_hash', 'last_blockchain_sync'])
        # except Exception as e:
        #     logger.error(f"Failed to log inventory creation to blockchain: {e}")
    
    def perform_update(self, serializer):
        """Log updates to blockchain"""
        instance = serializer.save(
            modified_by_id=str(self.request.user.id)
        )
        
        # Log to blockchain
        # try:
        #     blockchain_logger = get_inventory_logger()
        #     changes = {field: getattr(instance, field) for field in serializer.validated_data.keys()}
        #     tx_hash = blockchain_logger.log_inventory_update(instance, changes)
        #     if tx_hash:
        #         instance.last_blockchain_sync = timezone.now()
        #         instance.save(update_fields=['last_blockchain_sync'])
        # except Exception as e:
        #     logger.error(f"Failed to log inventory update to blockchain: {e}")
    
    @action(detail=True, methods=['post'])
    def reserve(self, request, pk=None):
        """Reserve inventory items"""
        inventory_item = self.get_object()
        quantity = request.data.get('quantity', 1)
        customer_user_id = request.data.get('customer_user_id')
        expiry_hours = request.data.get('expiry_hours', 24)
        
        if not customer_user_id:
            return Response(
                {'error': 'customer_user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if inventory_item.available_quantity < quantity:
            return Response(
                {'error': 'Insufficient inventory available'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create reservation
        expiry_date = timezone.now() + timedelta(hours=expiry_hours)
        reservation = InventoryReservation.objects.create(
            profile_id=inventory_item.profile_id,
            inventory_item_id=inventory_item.id,
            inventory_type=inventory_item.inventory_type,
            customer_user_id=customer_user_id,
            quantity_reserved=quantity,
            expiry_date=expiry_date,
            created_by_id=str(request.user.id)
        )
        
        # Update inventory quantities
        inventory_item.reserve(quantity)
        
        # Log to blockchain
        # try:
        #     blockchain_logger = get_inventory_logger()
        #     blockchain_logger.log_reservation(reservation)
        # except Exception as e:
        #     logger.error(f"Failed to log reservation to blockchain: {e}")
        
        serializer = InventoryReservationSerializer(reservation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def release_reservation(self, request, pk=None):
        """Release reserved inventory"""
        inventory_item = self.get_object()
        reservation_id = request.data.get('reservation_id')
        
        try:
            reservation = InventoryReservation.objects.get(
                id=reservation_id,
                inventory_item_id=inventory_item.id,
                status='active'
            )
            
            # Release inventory
            inventory_item.release_reservation(reservation.quantity_reserved)
            reservation.status = 'cancelled'
            reservation.save()
            
            return Response({'message': 'Reservation released successfully'})
            
        except InventoryReservation.DoesNotExist:
            return Response(
                {'error': 'Reservation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get analytics for specific inventory item"""
        inventory_item = self.get_object()
        period = request.query_params.get('period', 'monthly')
        
        analytics = InventoryAnalytics.objects.filter(
            inventory_item_id=inventory_item.id,
            period_type=period
        ).order_by('-date')[:12]  # Last 12 periods
        
        serializer = InventoryAnalyticsSerializer(analytics, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get inventory summary for dashboard"""
        profile_id = request.user.profile.get('profile_id')
        queryset = self.get_queryset()
        
        # Calculate summary metrics
        total_items = queryset.count()
        available_items = queryset.filter(available_quantity__gt=0).count()
        reserved_items = queryset.filter(reserved_quantity__gt=0).count()
        maintenance_items = queryset.filter(status='maintenance').count()
        
        # Calculate total value
        total_value = queryset.aggregate(
            total=Sum('base_price') * Sum('total_quantity')
        )['total'] or 0
        
        # Calculate occupancy rate
        total_capacity = queryset.aggregate(Sum('total_quantity'))['total_quantity__sum'] or 0
        total_available = queryset.aggregate(Sum('available_quantity'))['available_quantity__sum'] or 0
        occupancy_rate = 0
        if total_capacity > 0:
            occupancy_rate = ((total_capacity - total_available) / total_capacity) * 100
        
        # Get revenue data (placeholder - would integrate with booking system)
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # Get alerts count
        alerts_count = InventoryAlert.objects.filter(
            profile_id=profile_id,
            is_resolved=False
        ).count()
        
        # Get pending maintenance
        pending_maintenance = InventoryMaintenance.objects.filter(
            profile_id=profile_id,
            status__in=['scheduled', 'in_progress']
        ).count()
        
        summary_data = {
            'total_items': total_items,
            'available_items': available_items,
            'reserved_items': reserved_items,
            'maintenance_items': maintenance_items,
            'total_value': total_value,
            'occupancy_rate': round(occupancy_rate, 2),
            'revenue_today': 0,  # Placeholder
            'revenue_this_week': 0,  # Placeholder
            'revenue_this_month': 0,  # Placeholder
            'alerts_count': alerts_count,
            'pending_maintenance': pending_maintenance,
        }
        
        serializer = InventorySummarySerializer(summary_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """Bulk update inventory items"""
        updates = request.data.get('updates', [])
        
        if not updates:
            return Response(
                {'error': 'No updates provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create bulk operation record
        bulk_operation = InventoryBulkOperation.objects.create(
            profile_id=request.user.profile.get('profile_id'),
            operation_type='bulk_update',
            inventory_type=request.data.get('inventory_type', 'mixed'),
            total_items=len(updates),
            created_by_id=str(request.user.id)
        )
        
        # Process updates (this would typically be done asynchronously)
        successful_updates = 0
        failed_updates = 0
        errors = []
        
        for update_data in updates:
            try:
                item_id = update_data.get('id')
                if not item_id:
                    continue
                
                item = self.get_queryset().get(id=item_id)
                for field, value in update_data.items():
                    if field != 'id' and hasattr(item, field):
                        setattr(item, field, value)
                item.save()
                successful_updates += 1
                
            except Exception as e:
                failed_updates += 1
                errors.append(f"Item {item_id}: {str(e)}")
        
        # Update bulk operation
        bulk_operation.processed_items = successful_updates
        bulk_operation.failed_items = failed_updates
        bulk_operation.status = 'completed'
        bulk_operation.completed_at = timezone.now()
        if errors:
            bulk_operation.error_log = '\n'.join(errors)
        bulk_operation.save()
        
        return Response({
            'operation_id': bulk_operation.id,
            'successful_updates': successful_updates,
            'failed_updates': failed_updates,
            'errors': errors
        })


class InventoryReservationViewSet(PermissionRequiredMixin,viewsets.ModelViewSet):
    """Viewset for inventory reservations"""
    
    queryset = InventoryReservation.objects.all()
    serializer_class = InventoryReservationSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'inventory_type']
    ordering = ['-created_at']
    
    def get_queryset(self):
        profile_id = self.request.user.profile.get('profile_id')
        if not profile_id:
            return self.queryset.none()
        return self.queryset.filter(profile_id=profile_id)
    
    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """Get reservations expiring in the next hour"""
        one_hour_from_now = timezone.now() + timedelta(hours=1)
        expiring = self.get_queryset().filter(
            status='active',
            expiry_date__lte=one_hour_from_now
        )
        
        serializer = self.get_serializer(expiring, many=True)
        return Response(serializer.data)


class InventoryMaintenanceViewSet(PermissionRequiredMixin,viewsets.ModelViewSet):
    """Viewset for inventory maintenance"""
    
    queryset = InventoryMaintenance.objects.all()
    serializer_class = InventoryMaintenanceSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'maintenance_type', 'inventory_type']
    ordering = ['scheduled_date']
    
    def get_queryset(self):
        profile_id = self.request.user.profile.get('profile_id')
        if not profile_id:
            return self.queryset.none()
        return self.queryset.filter(profile_id=profile_id)
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue maintenance items"""
        overdue = self.get_queryset().filter(
            status__in=['scheduled', 'in_progress'],
            scheduled_date__lt=timezone.now()
        )
        
        serializer = self.get_serializer(overdue, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark maintenance as completed"""
        maintenance = self.get_object()
        
        maintenance.status = 'completed'
        maintenance.completed_date = timezone.now()
        maintenance.actual_cost = request.data.get('actual_cost', maintenance.estimated_cost)
        maintenance.notes = request.data.get('notes', maintenance.notes)
        maintenance.save()
        
        # Log to blockchain
        # try:
        #     blockchain_logger = get_inventory_logger()
        #     blockchain_logger.log_maintenance(maintenance)
        # except Exception as e:
        #     logger.error(f"Failed to log maintenance completion to blockchain: {e}")
        
        serializer = self.get_serializer(maintenance)
        return Response(serializer.data)


class InventoryAlertViewSet(PermissionRequiredMixin,viewsets.ModelViewSet):
    """Viewset for inventory alerts"""
    
    queryset = InventoryAlert.objects.all()
    serializer_class = InventoryAlertSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['alert_type', 'severity', 'is_read', 'is_resolved']
    ordering = ['-created_at']
    
    def get_queryset(self):
        profile_id = self.request.user.profile.get('profile_id')
        if not profile_id:
            return self.queryset.none()
        return self.queryset.filter(profile_id=profile_id)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark alert as read"""
        alert = self.get_object()
        alert.is_read = True
        alert.save()
        
        serializer = self.get_serializer(alert)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve alert"""
        alert = self.get_object()
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.resolved_by_id = str(request.user.id)
        alert.action_taken = request.data.get('action_taken', '')
        alert.save()
        
        serializer = self.get_serializer(alert)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def critical(self, request):
        """Get critical unresolved alerts"""
        critical_alerts = self.get_queryset().filter(
            severity='critical',
            is_resolved=False
        )
        
        serializer = self.get_serializer(critical_alerts, many=True)
        return Response(serializer.data)


class InventoryBulkOperationViewSet(PermissionRequiredMixin,viewsets.ReadOnlyModelViewSet):
    """Viewset for bulk operations (read-only)"""
    
    queryset = InventoryBulkOperation.objects.all()
    serializer_class = InventoryBulkOperationSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['operation_type', 'status', 'inventory_type']
    ordering = ['-created_at']
    
    def get_queryset(self):
        profile_id = self.request.user.profile.get('profile_id')
        if not profile_id:
            return self.queryset.none()
        return self.queryset.filter(profile_id=profile_id)
