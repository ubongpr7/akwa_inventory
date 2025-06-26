# `common_inventory` Django App Documentation

## Overview

The `common_inventory` Django app is a reusable inventory management system for a multitenant, microservices-based SaaS booking platform targeting Nigeria and Africa. It is stored on GitHub and installable via `pip` using a Git URL (e.g., `pip install git+https://github.com/yourusername/common_inventory.git`). The app enables microservices (e.g., hotel booking, transportation) to manage inventory (e.g., hotel rooms, taxi vehicles) with tenant-specific permissions and blockchain integration.

## Features

- **Core Models**: Abstract (`ProfileMixin`, `BaseInventoryItem`) and concrete (`InventoryReservation`, `InventoryPricing`, etc.) models for inventory management.
- **Permissions**: Integrates with a blockchain-based permission system (`PermissionManager.sol`) for tenant-specific access.
- **APIs**: Django REST Framework (DRF) views and serializers for CRUD operations.
- **Blockchain Sync**: Logs inventory actions and syncs with blockchain events using web3.py.
- **Extensibility**: Allows microservices to inherit and customize models (e.g., `HotelRoom`).
- **Scalability**: Optimized for high transaction volumes with PostgreSQL/MongoDB.

## App Structure

```
common_inventory/
├── __init__.py
├── apps.py
├── models/
│   ├── __init__.py
│   ├── base.py
│   ├── reservation.py
│   ├── pricing.py
│   ├── maintenance.py
│   ├── analytics.py
│   ├── alert.py
│   ├── bulk_operation.py
├── views/
│   ├── __init__.py
│   ├── inventory.py
│   ├── reservation.py
│   ├── pricing.py
│   ├── maintenance.py
│   ├── analytics.py
│   ├── alert.py
│   ├── bulk_operation.py
├── serializers/
│   ├── __init__.py
│   ├── inventory.py
│   ├── reservation.py
│   ├── pricing.py
│   ├── maintenance.py
│   ├── analytics.py
│   ├── alert.py
│   ├── bulk_operation.py
├── permissions/
│   ├── __init__.py
│   ├── blockchain.py
├── utils/
│   ├── __init__.py
│   ├── blockchain.py
│   ├── notifications.py
├── signals/
│   ├── __init__.py
│   ├── handlers.py
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_views.py
│   ├── test_serializers.py
├── migrations/
│   ├── __init__.py
│   ├── 0001_initial.py
├── admin.py
├── urls.py
├── setup.py
├── README.md
├── MANIFEST.in
├── .gitignore
```

## Installation

1. **Set Up GitHub Repository**:

   - Create a GitHub repository (e.g., `https://github.com/yourusername/common_inventory`).
   - Initialize with the app structure and commit your code.

2. **Install via pip**:

   - In each microservice, install the app from the Git URL:

     ```bash
     pip install git+https://github.com/yourusername/common_inventory.git
     ```
   - For a specific branch or tag (e.g., `v1.0.0`):

     ```bash
     pip install git+https://github.com/yourusername/common_inventory.git@v1.0.0
     ```
   - Add to `INSTALLED_APPS` in the microservice’s `settings.py`:

     ```python
     INSTALLED_APPS = [
         ...,
         'common_inventory',
     ]
     ```

3. **Database Setup**:

   - Run migrations:

     ```bash
     python manage.py makemigrations
     python manage.py migrate
     ```
   - Configure PostgreSQL in `settings.py`:

     ```python
     DATABASES = {
         'default': {
             'ENGINE': 'django.db.backends.postgresql',
             'NAME': 'inventory_db',
             'USER': 'postgres',
             'PASSWORD': 'password',
             'HOST': 'localhost',
             'PORT': '5432',
         }
     }
     ```

4. **Blockchain Integration**:

   - Install web3.py:

     ```bash
     pip install web3
     ```
   - Configure Polygon connection in `settings.py`:

     ```python
     BLOCKCHAIN = {
         'PROVIDER_URL': 'https://polygon-rpc.com',
         'CONTRACT_ADDRESS': '0x...',
         'CONTRACT_ABI': [...],
         'ADMIN_ADDRESS': '0x...',
         'PRIVATE_KEY': 'your_private_key',
     }
     ```
   - Deploy `PermissionManager.sol` to Polygon.

5. **Dependencies**:

   - Include a `requirements.txt`:

     ```
     Django>=4.0
     djangorestframework>=3.13
     web3>=6.0
     celery>=5.2
     psycopg2-binary
     ```
   - Install:

     ```bash
     pip install -r requirements.txt
     ```

## Models

### `ProfileMixin` (Abstract)

- **Fields**: `profile_id`, `created_by_id`, `modified_by_id`, `created_at`, `updated_at`.
- **Manager**: `InventoryManager` with `for_profile`, `active`, `available`.

### `BaseInventoryItem` (Abstract)

- **Fields**: `id`, `name`, `description`, `inventory_type`, `total_quantity`, `available_quantity`, `reserved_quantity`, `base_price`, `currency`, `status`, `is_active`, `is_featured`, `metadata`, `blockchain_hash`, `last_blockchain_sync`.
- **Methods**: `reserve`, `release_reservation`, `occupy`, `make_available`.

### Concrete Models

- `InventoryReservation`: Tracks reservations with `inventory_item_id`, `customer_user_id`, `quantity_reserved`, etc.
- `InventoryPricing`: Manages dynamic pricing with `price`, `start_date`, `priority`, etc.
- `InventoryMaintenance`: Schedules maintenance with `maintenance_type`, `scheduled_date`, etc.
- `InventoryAnalytics`: Stores metrics like `total_bookings`, `occupancy_rate`.
- `InventoryAlert`: Handles notifications for `low_stock`, etc.
- `InventoryBulkOperation`: Tracks bulk operations like `import`, `bulk_update`.

## Views

DRF ViewSets with blockchain permissions:

### Example: `InventoryItemViewSet`

```python
from rest_framework import viewsets
from common_inventory.models import BaseInventoryItem
from common_inventory.serializers import InventoryItemSerializer
from common_inventory.permissions.blockchain import BlockchainPermission

class InventoryItemViewSet(viewsets.ModelViewSet):
    serializer_class = InventoryItemSerializer
    permission_classes = [BlockchainPermission]
    
    def get_queryset(self):
        return BaseInventoryItem.objects.for_profile(self.request.user.profile_id)
    
    def perform_create(self, serializer):
        instance = serializer.save(profile_id=self.request.user.profile_id)
        blockchain_utils.log_inventory_action(
            profile_id=self.request.user.profile_id,
            inventory_id=instance.id,
            action='create'
        )
```

## Serializers

### Example: `InventoryItemSerializer`

```python
from rest_framework import serializers
from common_inventory.models import BaseInventoryItem

class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaseInventoryItem
        fields = [
            'id', 'name', 'description', 'inventory_type', 'total_quantity',
            'available_quantity', 'reserved_quantity', 'base_price', 'currency',
            'status', 'is_active', 'is_featured', 'metadata', 'blockchain_hash'
        ]
    
    def validate(self, data):
        if data['available_quantity'] > data['total_quantity']:
            raise serializers.ValidationError("Available quantity cannot exceed total quantity.")
        return data
```

## Permissions

### `BlockchainPermission`

```python
from rest_framework.permissions import BasePermission
from common_inventory.utils.blockchain import has_blockchain_permission

class BlockchainPermission(BasePermission):
    def has_permission(self, request, view):
        user_address = request.user.user_address
        action = view.action
        permission_codename = f"{action}_inventory"
        return has_blockchain_permission(user_address, permission_codename)
```

## Blockchain Utilities

### `blockchain.py`

```python
from web3 import Web3
from django.conf import settings

web3 = Web3(Web3.HTTPProvider(settings.BLOCKCHAIN['PROVIDER_URL']))
contract = web3.eth.contract(
    address=settings.BLOCKCHAIN['CONTRACT_ADDRESS'],
    abi=settings.BLOCKCHAIN['CONTRACT_ABI']
)

def has_blockchain_permission(user_address, codename):
    permission_id = contract.functions.getPermissionId(codename).call()
    return contract.functions.hasPermission(user_address, permission_id).call()

def log_inventory_action(profile_id, inventory_id, action):
    tx = contract.functions.updateInventory(
        profile_id, 'inventory', inventory_id, 0
    ).buildTransaction({
        'from': settings.BLOCKCHAIN['ADMIN_ADDRESS'],
        'nonce': web3.eth.getTransactionCount(settings.BLOCKCHAIN['ADMIN_ADDRESS'])
    })
    signed_tx = web3.eth.account.signTransaction(tx, settings.BLOCKCHAIN['PRIVATE_KEY'])
    tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
    return tx_hash.hex()
```

## URLs

### `urls.py`

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from common_inventory.views import (
    InventoryItemViewSet, InventoryReservationViewSet,
    InventoryPricingViewSet, InventoryMaintenanceViewSet,
    InventoryAnalyticsViewSet, InventoryAlertViewSet,
    InventoryBulkOperationViewSet
)

router = DefaultRouter()
router.register('inventory-items', InventoryItemViewSet)
router.register('reservations', InventoryReservationViewSet)
router.register('pricing', InventoryPricingViewSet)
router.register('maintenance', InventoryMaintenanceViewSet)
router.register('analytics', InventoryAnalyticsViewSet)
router.register('alerts', InventoryAlertViewSet)
router.register('bulk-operations', InventoryBulkOperationViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
```

## Setup.py

```python
from setuptools import setup, find_packages

setup(
    name='common_inventory',
    version='1.0.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Django>=4.0',
        'djangorestframework>=3.13',
        'web3>=6.0',
        'celery>=5.2',
        'psycopg2-binary',
    ],
    author='Your Name',
    description='Reusable inventory management for microservices',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
)
```

## MANIFEST.in

```
include README.md
include requirements.txt
recursive-include common_inventory/migrations *.py
recursive-include common_inventory/static *
recursive-include common_inventory/templates *
```

## .gitignore

```
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
*.sqlite3
.migrations
*.log
local_settings.py
```

## Example: Extending for Hotel Microservice

### Model Extension

```python
from common_inventory.models import BaseInventoryItem, ProfileMixin
from django.db import models

class HotelRoom(BaseInventoryItem):
    room_type = models.CharField(max_length=50)
    amenities = models.JSONField(default=list)
    floor_number = models.PositiveIntegerField(null=True)
    
    class Meta:
        db_table = 'hotel_rooms'
    
    def save(self, *args, **kwargs):
        self.inventory_type = 'room'
        super().save(*args, **kwargs)
```

### View Extension

```python
from common_inventory.views.inventory import InventoryItemViewSet
from .serializers import HotelRoomSerializer

class HotelRoomViewSet(InventoryItemViewSet):
    serializer_class = HotelRoomSerializer
    queryset = HotelRoom.objects.all()
```

## Setup Guide

1. **Initialize GitHub Repository**:

   - Create `https://github.com/yourusername/common_inventory`.
   - Copy the app structure and commit:

     ```bash
     git init
     git add .
     git commit -m "Initial commit"
     git remote add origin https://github.com/yourusername/common_inventory.git
     git push -u origin main
     ```

2. **Install in Microservice**:

   - In the microservice’s virtual environment:

     ```bash
     pip install git+https://github.com/yourusername/common_inventory.git
     ```
   - Add to `INSTALLED_APPS`:

     ```python
     INSTALLED_APPS = [
         ...,
         'common_inventory',
     ]
     ```

3. **Run Migrations**:

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

4. **Configure Blockchain**:

   - Deploy `PermissionManager.sol` to Polygon.
   - Update `settings.py` with blockchain details.

5. **Extend for Microservices**:

   - Create service-specific models (e.g., `HotelRoom`).
   - Include `common_inventory.urls` in the microservice’s `urls.py`.

6. **Test**:

   - Run tests: `python manage.py test common_inventory`.
   - Test APIs with sample data.

## Notes

- **Multitenancy**: Use `profile_id` for tenant isolation.
- **Blockchain**: Cache permissions locally, sync via events.
- **Nigeria Context**: Optimize for low-bandwidth with cached responses.
- **Versioning**: Update `setup.py` version (e.g., `1.0.1`) and push changes to GitHub for updates.