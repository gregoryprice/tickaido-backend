#!/usr/bin/env python3
"""
AWS S3 storage backend implementation
"""

from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import quote

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from app.config.settings import get_settings

from .backend import StorageBackend


class S3StorageBackend(StorageBackend):
    """AWS S3 storage implementation"""
    
    def __init__(
        self, 
        bucket_name: Optional[str] = None,
        region: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket_path: Optional[str] = None,
        cloudfront_domain: Optional[str] = None
    ):
        """
        Initialize S3 storage backend
        
        Args:
            bucket_name: S3 bucket name (defaults to settings)
            region: AWS region (defaults to settings)
            access_key: AWS access key (defaults to settings/env)
            secret_key: AWS secret key (defaults to settings/env)
            bucket_path: Path prefix within bucket (defaults to settings)
            cloudfront_domain: CloudFront domain for CDN URLs
        """
        self.settings = get_settings()
        
        self.bucket_name = bucket_name or self.settings.s3_bucket_name
        self.region = region or self.settings.aws_region
        self.bucket_path = bucket_path or self.settings.s3_bucket_path
        self.cloudfront_domain = cloudfront_domain or self.settings.cloudfront_domain
        
        if not self.bucket_name:
            raise ValueError("S3 bucket name is required")
        
        # Initialize S3 client
        session = boto3.Session(
            aws_access_key_id=access_key or self.settings.aws_access_key_id,
            aws_secret_access_key=secret_key or self.settings.aws_secret_access_key,
            region_name=self.region
        )
        
        self.s3_client = session.client('s3')
        
        # Validate credentials and bucket access
        self._validate_setup()
    
    def _validate_setup(self):
        """Validate S3 credentials and bucket access"""
        try:
            # Try to head the bucket to validate access
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except NoCredentialsError:
            raise ValueError("AWS credentials not found or invalid")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                raise ValueError(f"S3 bucket '{self.bucket_name}' not found")
            elif error_code == '403':
                raise ValueError(f"Access denied to S3 bucket '{self.bucket_name}'")
            elif error_code == 'NoCredentialsError':
                raise ValueError("AWS credentials not found or invalid")
            else:
                raise ValueError(f"S3 setup validation failed: {e}")
    
    def _get_full_key(self, key: str) -> str:
        """Get full S3 key with bucket path prefix"""
        if self.bucket_path:
            return f"{self.bucket_path.rstrip('/')}/{key.lstrip('/')}"
        return key
    
    def _get_public_url(self, key: str) -> str:
        """Get public URL for S3 object"""
        full_key = self._get_full_key(key)
        
        if self.cloudfront_domain:
            # Use CloudFront CDN URL
            return f"https://{self.cloudfront_domain.rstrip('/')}/{quote(full_key)}"
        else:
            # Use direct S3 URL
            return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{quote(full_key)}"
    
    async def upload_file(
        self, 
        content: bytes, 
        key: str, 
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Upload file to S3"""
        full_key = self._get_full_key(key)
        
        # Prepare upload parameters
        upload_args = {
            'Bucket': self.bucket_name,
            'Key': full_key,
            'Body': content,
        }
        
        if content_type:
            upload_args['ContentType'] = content_type
        
        if metadata:
            # Convert metadata to string values (S3 requirement)
            s3_metadata = {k: str(v) for k, v in metadata.items()}
            upload_args['Metadata'] = s3_metadata
        
        # Add timestamp metadata
        upload_args.setdefault('Metadata', {})['uploaded_at'] = datetime.now().isoformat()
        
        try:
            # Upload to S3
            self.s3_client.put_object(**upload_args)
            
            # Return public URL
            return self._get_public_url(key)
            
        except ClientError as e:
            raise Exception(f"Failed to upload file to S3: {e}")
    
    async def download_file(self, key: str) -> Optional[bytes]:
        """Download file from S3"""
        full_key = self._get_full_key(key)
        
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=full_key
            )
            return response['Body'].read()
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                return None
            else:
                raise Exception(f"Failed to download file from S3: {e}")
    
    async def delete_file(self, key: str) -> bool:
        """Delete file from S3"""
        full_key = self._get_full_key(key)
        
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=full_key
            )
            return True
            
        except ClientError:
            # S3 delete returns success even if object doesn't exist
            return False
    
    async def file_exists(self, key: str) -> bool:
        """Check if file exists in S3"""
        full_key = self._get_full_key(key)
        
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=full_key
            )
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                return False
            else:
                raise Exception(f"Failed to check file existence in S3: {e}")
    
    async def get_file_url(
        self, 
        key: str, 
        expires_in: Optional[int] = None,
        public: bool = False
    ) -> str:
        """Get public or signed URL for S3 file"""
        if public or expires_in is None:
            return self._get_public_url(key)
        
        # Generate signed URL
        full_key = self._get_full_key(key)
        
        try:
            signed_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': full_key
                },
                ExpiresIn=expires_in
            )
            return signed_url
            
        except ClientError as e:
            raise Exception(f"Failed to generate signed URL: {e}")
    
    async def get_file_info(self, key: str) -> Optional[Dict[str, Any]]:
        """Get file info from S3"""
        full_key = self._get_full_key(key)
        
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=full_key
            )
            
            info = {
                'size': response.get('ContentLength', 0),
                'content_type': response.get('ContentType'),
                'modified_time': response.get('LastModified').isoformat() if response.get('LastModified') and hasattr(response.get('LastModified'), 'isoformat') else str(response.get('LastModified', '')),
                'etag': response.get('ETag', '').strip('"'),
            }
            
            # Add custom metadata
            if 'Metadata' in response:
                info.update(response['Metadata'])
            
            return info
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                return None
            else:
                raise Exception(f"Failed to get file info from S3: {e}")
    
    async def list_files(
        self, 
        prefix: str = "", 
        limit: Optional[int] = None
    ) -> list[str]:
        """List files in S3 with prefix filter"""
        full_prefix = self._get_full_key(prefix)
        
        try:
            list_args = {
                'Bucket': self.bucket_name,
                'Prefix': full_prefix,
            }
            
            if limit:
                list_args['MaxKeys'] = limit
            
            response = self.s3_client.list_objects_v2(**list_args)
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    # Remove bucket path prefix to get relative key
                    key = obj['Key']
                    if self.bucket_path and key.startswith(self.bucket_path):
                        key = key[len(self.bucket_path):].lstrip('/')
                    files.append(key)
            
            return files
            
        except ClientError as e:
            raise Exception(f"Failed to list files in S3: {e}")
    
    @property
    def backend_type(self) -> str:
        """Get backend type identifier"""
        return "s3"
    
    @property
    def supports_public_urls(self) -> bool:
        """S3 backend supports public URLs"""
        return True
    
    @property
    def supports_signed_urls(self) -> bool:
        """S3 backend supports signed URLs with expiration"""
        return True