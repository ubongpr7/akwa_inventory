# `akwa_inventory` Django App Documentation

## Overview

The `akwa_inventory` Django app is a reusable inventory management system designed for a multitenant, microservices-based SaaS booking platform targeting Nigeria and Africa. Hosted on GitHub at `https://github.com/ubongpr7/akwa_inventory`, it is installable via `pip` using a Git URL (e.g., `pip install git+https://github.com/ubongpr7/akwa_inventory.git@v0.1.0`). The app supports microservices (e.g., hotel bookings, transportation) to manage inventory (e.g., rooms, vehicles) with tenant-specific permissions and blockchain integration.

## Features

- **Core Models**: Abstract (`ProfileMixin`, `BaseInventoryItem`) and concrete models for inventory management.
- **Permissions**: Blockchain-based access control via `PermissionManager.sol`.
- **APIs**: Django REST Framework (DRF) views and serializers for CRUD operations.
- **Blockchain Sync**: Logs actions and syncs with blockchain events using web3.py.
- **Extensibility**: Allows microservice-specific model inheritance (e.g., `HotelRoom`).
- **Scalability**: Optimized for high transaction volumes with PostgreSQL.

## App Structure

```
akwa_inventory/
├── __init__.py
├── apps.py
├── models/
│   ├── __init__.py
│   ├── base.py         # Defines ProfileMixin, BaseInventoryItem
│   ├── reservation.py  # Defines InventoryReservation
│   ├── pricing.py      # Defines InventoryPricing
├── views/
│   ├── __init__.py
│   ├── inventory.py    # Defines InventoryItemViewSet
│   ├── reservation.py  # Defines ReservationViewSet
├── serializers/
│   ├── __init__.py
│   ├── inventory.py    # Defines InventoryItemSerializer
│   ├── reservation.py  # Defines ReservationSerializer
├── permissions/
│   ├── __init__.py
│   ├── blockchain.py   # Defines BlockchainPermission
├── utils/
│   ├── __init__.py
│   ├── blockchain.py   # Handles blockchain sync
├── migrations/
│   ├── __init__.py
│   ├── 0001_initial.py
├── admin.py
├── urls.py
├── tests/
│   ├── __init__.py
│   ├── test_models.py
├── setup.py
├── README.md
├── requirements.txt
├── .gitignore
```

## Installation

1. **Set Up GitHub Repository**:
   - Ensure the repository is initialized at `https://github.com/ubongpr7/akwa_inventory`.
   - Commit the app structure using Git.

2. **Install via pip**:
   - In a microservice’s virtual environment:
     ```bash
     pip install git+https://github.com/ubongpr7/akwa_inventory.git@v0.1.0
     ```
   - Add to `INSTALLED_APPS` in `settings.py`:
     ```python
     INSTALLED_APPS = [
         ...,
         'akwa_inventory',
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
             'NAME': 'akwa_inventory_db',
             'USER': 'postgres',
             'PASSWORD': 'your_password',
             'HOST': 'localhost',
             'PORT': '5432',
         }
     }
     ```

4. **Blockchain Integration**:
   - Install dependencies:
     ```bash
     pip install web3
     ```
   - Configure Polygon in `settings.py`:
     ```python
     BLOCKCHAIN = {
         'PROVIDER_URL': 'https://polygon-rpc.com',
         'CONTRACT_ADDRESS': '0xYourContractAddress',
         'CONTRACT_ABI': [...],
         'ADMIN_ADDRESS': '0xYourAdminAddress',
         'PRIVATE_KEY': 'your_private_key',
     }
     ```
   - Deploy `PermissionManager.sol` to Polygon.

5. **Dependencies**:
   - Install from `requirements.txt`:
     ```
     Django>=4.0
     djangorestframework>=3.13
     web3>=6.0
     psycopg2-binary
     ```
     ```bash
     pip install -r requirements.txt
     ```

## Models

### `ProfileMixin` (Abstract)
- **Fields**: `profile_id`, `created_by_id`, `modified_by_id`, `created_at`, `updated_at`.
- **Manager**: `InventoryManager` with `for_profile`, `active`, `available`.

### `BaseInventoryItem` (Abstract)
- **Fields**: `id`, `name`, `description`, `inventory_type`, `total_quantity`, `available_quantity`, `reserved_quantity`, `base_price`, `currency`, `status`.
- **Methods**: `reserve`, `release_reservation`.

### Concrete Models
- `InventoryReservation`: Tracks `inventory_item_id`, `customer_user_id`, `quantity_reserved`.
- `InventoryPricing`: Manages `price`, `start_date`.

## Views
### Example: `InventoryItemViewSet`
```python
from rest_framework import viewsets
from akwa_inventory.models import BaseInventoryItem
from akwa_inventory.serializers import InventoryItemSerializer
from akwa_inventory.permissions import BlockchainPermission

class InventoryItemViewSet(viewsets.ModelViewSet):
    serializer_class = InventoryItemSerializer
    permission_classes = [BlockchainPermission]
    def get_queryset(self):
        return BaseInventoryItem.objects.for_profile(self.request.user.profile_id)
```

## Serializers
### Example: `InventoryItemSerializer`
```python
from rest_framework import serializers
from akwa_inventory.models import BaseInventoryItem

class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaseInventoryItem
        fields = ['id', 'name', 'description', 'total_quantity', 'available_quantity']
```

## Permissions
### `BlockchainPermission`
```python
from rest_framework.permissions import BasePermission
from akwa_inventory.utils import has_blockchain_permission

class BlockchainPermission(BasePermission):
    def has_permission(self, request, view):
        user_address = request.user.user_address
        return has_blockchain_permission(user_address, view.action + '_inventory')
```

## URLs
### `urls.py`
```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from akwa_inventory.views import InventoryItemViewSet, InventoryReservationViewSet

router = DefaultRouter()
router.register(r'inventory-items', InventoryItemViewSet)
router.register(r'reservations', InventoryReservationViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
```

## Setup Guide

1. **Clone Repository**:
   - Clone from `https://github.com/ubongpr7/akwa_inventory.git`.

2. **Install Dependencies**:
   - Run `pip install -r requirements.txt`.

3. **Configure Settings**:
   - Update `settings.py` with database and blockchain details.

4. **Apply Migrations**:
   - Run `python manage.py migrate`.

5. **Extend for Microservices**:
   - Example `HotelRoom` model:
     ```python
     from akwa_inventory.models import BaseInventoryItem

     class HotelRoom(BaseInventoryItem):
         room_type = models.CharField(max_length=50)
     ```

6. **Test**:
   - Run `python manage.py test akwa_inventory`.

## Versioning
- Automated with `release-it` based on conventional commits.
- Bump versions (e.g., `0.1.0` to `0.2.0`) with:
  ```bash
  release-it --increment minor
  ```
- Install specific versions: `pip install git+https://github.com/ubongpr7/akwa_inventory.git@v0.2.0`.

## Notes
- **Multitenancy**: Use `profile_id` for isolation.
- **Blockchain**: Sync permissions via events.
- **Nigeria Context**: Optimize for low-bandwidth environments.