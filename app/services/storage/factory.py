#!/usr/bin/env python3
"""
Storage backend factory and service creation
"""

from typing import Optional

from app.config.settings import get_settings

from .avatar_storage_service import AvatarStorageService
from .backend import StorageBackend
from .local_backend import LocalStorageBackend
from .s3_backend import S3StorageBackend
from .storage_service import StorageService


def create_storage_backend(
    backend_type: Optional[str] = None,
    **kwargs
) -> StorageBackend:
    """
    Create storage backend based on configuration
    
    Args:
        backend_type: Override backend type (defaults to settings.storage_backend)
        **kwargs: Additional arguments passed to backend constructor
        
    Returns:
        Configured storage backend instance
        
    Raises:
        ValueError: If backend type is unsupported
    """
    settings = get_settings()
    backend_type = backend_type or settings.storage_backend
    
    if backend_type == "local":
        return LocalStorageBackend(
            base_path=kwargs.get('base_path', settings.upload_directory),
            base_url=kwargs.get('base_url', "/api/v1/storage")
        )
    elif backend_type == "s3":
        return S3StorageBackend(
            bucket_name=kwargs.get('bucket_name', settings.s3_bucket_name),
            region=kwargs.get('region', settings.aws_region),
            access_key=kwargs.get('access_key', settings.aws_access_key_id),
            secret_key=kwargs.get('secret_key', settings.aws_secret_access_key),
            bucket_path=kwargs.get('bucket_path', settings.s3_bucket_path),
            cloudfront_domain=kwargs.get('cloudfront_domain', settings.cloudfront_domain)
        )
    else:
        raise ValueError(f"Unsupported storage backend: {backend_type}")


def create_storage_service(
    backend: Optional[StorageBackend] = None,
    backend_type: Optional[str] = None,
    **kwargs
) -> StorageService:
    """
    Create storage service with configured backend
    
    Args:
        backend: Pre-configured storage backend (if not provided, creates one)
        backend_type: Backend type to create (if backend not provided)
        **kwargs: Additional arguments for backend creation
        
    Returns:
        Configured storage service
    """
    if backend is None:
        backend = create_storage_backend(backend_type, **kwargs)
    
    return StorageService(backend)


# Global service instance (singleton pattern)
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """
    Get global storage service instance (singleton)
    
    Returns:
        Configured storage service instance
    """
    global _storage_service
    if _storage_service is None:
        _storage_service = create_storage_service()
    return _storage_service


def create_avatar_storage_service(
    backend: Optional[StorageBackend] = None,
    backend_type: Optional[str] = None,
    **kwargs
) -> AvatarStorageService:
    """
    Create avatar storage service with configured backend
    
    Args:
        backend: Pre-configured storage backend (if not provided, creates one)
        backend_type: Backend type to create (if backend not provided)
        **kwargs: Additional arguments for backend creation
        
    Returns:
        Configured avatar storage service
    """
    if backend is None:
        backend = create_storage_backend(backend_type, **kwargs)
    
    return AvatarStorageService(backend)


# Global avatar service instance (singleton pattern)
_avatar_storage_service: Optional[AvatarStorageService] = None


def get_avatar_storage_service() -> AvatarStorageService:
    """
    Get global avatar storage service instance (singleton)
    
    Returns:
        Configured avatar storage service instance
    """
    global _avatar_storage_service
    if _avatar_storage_service is None:
        _avatar_storage_service = create_avatar_storage_service()
    return _avatar_storage_service


def reset_storage_service() -> None:
    """
    Reset global storage service (useful for testing)
    """
    global _storage_service, _avatar_storage_service
    _storage_service = None
    _avatar_storage_service = None