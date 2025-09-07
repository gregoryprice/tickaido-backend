#!/usr/bin/env python3
"""
Encryption service for handling sensitive data like API keys and credentials
"""

import base64
import os
import json
from typing import Any, Dict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data.
    Uses Fernet symmetric encryption with a key derived from environment variables.
    """
    
    def __init__(self):
        self._fernet = None
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize encryption with key from environment"""
        encryption_key = os.getenv("ENCRYPTION_KEY")
        
        if not encryption_key:
            # Generate a key from JWT secret + salt for backwards compatibility
            jwt_secret = os.getenv("JWT_SECRET_KEY")
            if not jwt_secret:
                raise ValueError("Either ENCRYPTION_KEY or JWT_SECRET_KEY must be set for data encryption")
            
            # Use a fixed salt for consistent key generation
            salt = b"ai_tickets_encryption_salt_2024"
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(jwt_secret.encode()))
            self._fernet = Fernet(key)
        else:
            # Use provided encryption key
            try:
                self._fernet = Fernet(encryption_key.encode())
            except Exception as e:
                logger.error(f"Invalid encryption key: {e}")
                raise ValueError("Invalid ENCRYPTION_KEY format")
    
    def encrypt_data(self, data: Any) -> str:
        """
        Encrypt any serializable data.
        
        Args:
            data: Data to encrypt (will be JSON serialized)
            
        Returns:
            str: Base64 encoded encrypted data
        """
        try:
            if data is None:
                return ""
            
            # Serialize data to JSON string
            json_data = json.dumps(data, sort_keys=True)
            
            # Encrypt the JSON string
            encrypted_bytes = self._fernet.encrypt(json_data.encode('utf-8'))
            
            # Return base64 encoded string for database storage
            return base64.b64encode(encrypted_bytes).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError(f"Failed to encrypt data: {str(e)}")
    
    def decrypt_data(self, encrypted_data: str) -> Any:
        """
        Decrypt data back to original format.
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            
        Returns:
            Any: Original decrypted data
        """
        try:
            if not encrypted_data:
                return None
            
            # Decode base64
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Decrypt to JSON string
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            json_data = decrypted_bytes.decode('utf-8')
            
            # Parse JSON back to original data structure
            return json.loads(json_data)
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError(f"Failed to decrypt data: {str(e)}")
    
    def encrypt_credentials(self, credentials: Dict[str, Any]) -> str:
        """
        Encrypt credentials dictionary for storage.
        
        Args:
            credentials: Dictionary containing sensitive credentials
            
        Returns:
            str: Encrypted credentials string
        """
        if not credentials:
            return ""
        
        # Filter out None values and empty strings
        filtered_credentials = {
            k: v for k, v in credentials.items() 
            if v is not None and v != ""
        }
        
        return self.encrypt_data(filtered_credentials)
    
    def decrypt_credentials(self, encrypted_credentials: str) -> Dict[str, Any]:
        """
        Decrypt credentials back to dictionary.
        
        Args:
            encrypted_credentials: Encrypted credentials string
            
        Returns:
            Dict[str, Any]: Decrypted credentials dictionary
        """
        if not encrypted_credentials:
            return {}
        
        decrypted_data = self.decrypt_data(encrypted_credentials)
        return decrypted_data if isinstance(decrypted_data, dict) else {}
    
    def hash_api_key(self, api_key: str) -> str:
        """
        Create a hash of API key for verification purposes.
        Uses Fernet's encryption but only returns first 16 chars for identification.
        
        Args:
            api_key: API key to hash
            
        Returns:
            str: Hash identifier (not reversible)
        """
        if not api_key:
            return ""
        
        try:
            encrypted = self._fernet.encrypt(api_key.encode('utf-8'))
            # Return first 16 chars of base64 encoded encrypted data as identifier
            return base64.b64encode(encrypted).decode('utf-8')[:16]
        except Exception as e:
            logger.error(f"API key hashing failed: {e}")
            return ""
    
    def mask_sensitive_value(self, value: str, show_chars: int = 4) -> str:
        """
        Mask sensitive value for display purposes.
        
        Args:
            value: Sensitive value to mask
            show_chars: Number of characters to show at the end
            
        Returns:
            str: Masked value (e.g., "****1234")
        """
        if not value or len(value) <= show_chars:
            return "****"
        
        return "*" * (len(value) - show_chars) + value[-show_chars:]


# Global instance
_encryption_service = None

def get_encryption_service() -> EncryptionService:
    """Get or create global encryption service instance"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def encrypt_credentials(credentials: Dict[str, Any]) -> str:
    """Convenience function to encrypt credentials"""
    return get_encryption_service().encrypt_credentials(credentials)


def decrypt_credentials(encrypted_credentials: str) -> Dict[str, Any]:
    """Convenience function to decrypt credentials"""
    return get_encryption_service().decrypt_credentials(encrypted_credentials)


def mask_credentials(credentials: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mask sensitive values in credentials for safe display.
    
    Args:
        credentials: Credentials dictionary
        
    Returns:
        Dict[str, Any]: Credentials with masked values
    """
    if not credentials:
        return {}
    
    encryption_service = get_encryption_service()
    masked = {}
    
    sensitive_keys = {
        'password', 'api_key', 'api_token', 'secret', 'client_secret', 
        'private_key', 'token', 'access_token', 'refresh_token'
    }
    
    for key, value in credentials.items():
        if isinstance(value, str) and any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
            masked[key] = encryption_service.mask_sensitive_value(value)
        else:
            masked[key] = value
    
    return masked