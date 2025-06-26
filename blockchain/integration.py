"""
Blockchain Integration for Inventory Management
Polygon blockchain integration for transparency and KYC verification
"""

import json
import logging
from decimal import Decimal
from typing import Dict, Any, Optional, List
from datetime import datetime

from web3 import Web3
from web3.middleware import geth_poa_middleware
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class BlockchainIntegration:
    """Main blockchain integration class for inventory management"""
    
    def __init__(self):
        # Polygon Mumbai Testnet (for development)
        self.rpc_url = getattr(settings, 'POLYGON_RPC_URL', 'https://rpc-mumbai.maticvigil.com/')
        self.chain_id = getattr(settings, 'POLYGON_CHAIN_ID', 80001)
        self.private_key = getattr(settings, 'BLOCKCHAIN_PRIVATE_KEY', '')
        
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        # Contract addresses (deploy these contracts first)
        self.permission_manager_address = getattr(settings, 'PERMISSION_MANAGER_CONTRACT', '')
        self.inventory_logger_address = getattr(settings, 'INVENTORY_LOGGER_CONTRACT', '')
        
        # Load contract ABIs
        self.permission_manager_abi = self._load_contract_abi('PermissionManager')
        self.inventory_logger_abi = self._load_contract_abi('InventoryLogger')
        
        # Initialize contracts
        if self.permission_manager_address:
            self.permission_contract = self.w3.eth.contract(
                address=self.permission_manager_address,
                abi=self.permission_manager_abi
            )
        
        if self.inventory_logger_address:
            self.inventory_contract = self.w3.eth.contract(
                address=self.inventory_logger_address,
                abi=self.inventory_logger_abi
            )
    
    def _load_contract_abi(self, contract_name: str) -> List[Dict]:
        """Load contract ABI from file or return default"""
        try:
            # In production, load from file
            # with open(f'contracts/{contract_name}.json', 'r') as f:
            #     contract_data = json.load(f)
            #     return contract_data['abi']
            
            # For now, return minimal ABI structures
            if contract_name == 'PermissionManager':
                return [
                    {
                        "inputs": [{"name": "user", "type": "address"}, {"name": "profileId", "type": "string"}],
                        "name": "checkKYC",
                        "outputs": [{"name": "", "type": "bool"}],
                        "type": "function"
                    },
                    {
                        "inputs": [{"name": "user", "type": "address"}, {"name": "profileId", "type": "string"}],
                        "name": "verifyKYC",
                        "outputs": [],
                        "type": "function"
                    }
                ]
            elif contract_name == 'InventoryLogger':
                return [
                    {
                        "inputs": [
                            {"name": "profileId", "type": "string"},
                            {"name": "inventoryId", "type": "string"},
                            {"name": "action", "type": "string"},
                            {"name": "data", "type": "string"}
                        ],
                        "name": "logInventoryAction",
                        "outputs": [],
                        "type": "function"
                    }
                ]
        except Exception as e:
            logger.error(f"Error loading contract ABI for {contract_name}: {e}")
            return []
    
    def check_kyc_status(self, user_address: str, profile_id: str) -> bool:
        """Check KYC status from blockchain"""
        try:
            # First check cache
            cache_key = f"kyc_status_{user_address}_{profile_id}"
            cached_status = cache.get(cache_key)
            if cached_status is not None:
                return cached_status
            
            # Check blockchain
            if hasattr(self, 'permission_contract'):
                is_verified = self.permission_contract.functions.checkKYC(
                    user_address, profile_id
                ).call()
                
                # Cache for 1 hour
                cache.set(cache_key, is_verified, 3600)
                return is_verified
            
            # Fallback: assume verified for development
            logger.warning("Permission contract not available, assuming KYC verified")
            return True
            
        except Exception as e:
            logger.error(f"Error checking KYC status: {e}")
            return False
    
    def verify_kyc(self, user_address: str, profile_id: str) -> Optional[str]:
        """Verify KYC on blockchain"""
        try:
            if not hasattr(self, 'permission_contract'):
                logger.error("Permission contract not available")
                return None
            
            # Build transaction
            account = self.w3.eth.account.from_key(self.private_key)
            nonce = self.w3.eth.get_transaction_count(account.address)
            
            transaction = self.permission_contract.functions.verifyKYC(
                user_address, profile_id
            ).build_transaction({
                'chainId': self.chain_id,
                'gas': 100000,
                'gasPrice': self.w3.to_wei('20', 'gwei'),
                'nonce': nonce,
            })
            
            # Sign and send transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            # Clear cache
            cache_key = f"kyc_status_{user_address}_{profile_id}"
            cache.delete(cache_key)
            
            return receipt.transactionHash.hex()
            
        except Exception as e:
            logger.error(f"Error verifying KYC: {e}")
            return None
    
    def log_inventory_action(
        self,
        profile_id: str,
        inventory_id: str,
        action: str,
        data: Dict[str, Any]
    ) -> Optional[str]:
        """Log inventory action to blockchain"""
        try:
            if not hasattr(self, 'inventory_contract'):
                logger.warning("Inventory contract not available, skipping blockchain logging")
                return None
            
            # Prepare data
            data_json = json.dumps(data, default=str)
            
            # Build transaction
            account = self.w3.eth.account.from_key(self.private_key)
            nonce = self.w3.eth.get_transaction_count(account.address)
            
            transaction = self.inventory_contract.functions.logInventoryAction(
                profile_id, inventory_id, action, data_json
            ).build_transaction({
                'chainId': self.chain_id,
                'gas': 150000,
                'gasPrice': self.w3.to_wei('20', 'gwei'),
                'nonce': nonce,
            })
            
            # Sign and send transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Don't wait for confirmation to avoid blocking
            logger.info(f"Inventory action logged to blockchain: {tx_hash.hex()}")
            return tx_hash.hex()
            
        except Exception as e:
            logger.error(f"Error logging inventory action to blockchain: {e}")
            return None
    
    def get_transaction_status(self, tx_hash: str) -> Dict[str, Any]:
        """Get transaction status and details"""
        try:
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            return {
                'status': 'success' if receipt.status == 1 else 'failed',
                'block_number': receipt.blockNumber,
                'gas_used': receipt.gasUsed,
                'transaction_hash': receipt.transactionHash.hex()
            }
        except Exception as e:
            logger.error(f"Error getting transaction status: {e}")
            return {'status': 'unknown', 'error': str(e)}


class InventoryBlockchainLogger:
    """Specific logger for inventory-related blockchain events"""
    
    def __init__(self):
        self.blockchain = BlockchainIntegration()
    
    def log_inventory_creation(self, inventory_item) -> Optional[str]:
        """Log inventory item creation"""
        data = {
            'action': 'create',
            'inventory_type': inventory_item.inventory_type,
            'name': inventory_item.name,
            'quantity': str(inventory_item.total_quantity),
            'price': str(inventory_item.base_price),
            'timestamp': timezone.now().isoformat()
        }
        
        return self.blockchain.log_inventory_action(
            inventory_item.profile_id,
            str(inventory_item.id),
            'create',
            data
        )
    
    def log_inventory_update(self, inventory_item, changes: Dict[str, Any]) -> Optional[str]:
        """Log inventory item updates"""
        data = {
            'action': 'update',
            'inventory_id': str(inventory_item.id),
            'changes': changes,
            'timestamp': timezone.now().isoformat()
        }
        
        return self.blockchain.log_inventory_action(
            inventory_item.profile_id,
            str(inventory_item.id),
            'update',
            data
        )
    
    def log_reservation(self, reservation) -> Optional[str]:
        """Log inventory reservation"""
        data = {
            'action': 'reserve',
            'reservation_id': str(reservation.id),
            'inventory_id': str(reservation.inventory_item_id),
            'quantity': str(reservation.quantity_reserved),
            'customer': reservation.customer_user_id,
            'timestamp': timezone.now().isoformat()
        }
        
        return self.blockchain.log_inventory_action(
            reservation.profile_id,
            str(reservation.inventory_item_id),
            'reserve',
            data
        )
    
    def log_maintenance(self, maintenance) -> Optional[str]:
        """Log maintenance activities"""
        data = {
            'action': 'maintenance',
            'maintenance_id': str(maintenance.id),
            'inventory_id': str(maintenance.inventory_item_id),
            'maintenance_type': maintenance.maintenance_type,
            'status': maintenance.status,
            'timestamp': timezone.now().isoformat()
        }
        
        return self.blockchain.log_inventory_action(
            maintenance.profile_id,
            str(maintenance.inventory_item_id),
            'maintenance',
            data
        )


# Utility functions for blockchain integration
def get_blockchain_integration() -> BlockchainIntegration:
    """Get blockchain integration instance"""
    return BlockchainIntegration()


def get_inventory_logger() -> InventoryBlockchainLogger:
    """Get inventory blockchain logger instance"""
    return InventoryBlockchainLogger()


def verify_vendor_kyc(user_address: str, profile_id: str) -> bool:
    """Verify vendor KYC status"""
    blockchain = get_blockchain_integration()
    return blockchain.check_kyc_status(user_address, profile_id)


def log_inventory_blockchain(inventory_item, action: str, data: Dict[str, Any]) -> Optional[str]:
    """Log inventory action to blockchain"""
    logger = get_inventory_logger()
    return logger.blockchain.log_inventory_action(
        inventory_item.profile_id,
        str(inventory_item.id),
        action,
        data
    )
