#!/usr/bin/env python3
"""
Tests for S3StorageBackend (mocked)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from botocore.exceptions import ClientError

from app.services.storage.s3_backend import S3StorageBackend


@pytest.fixture
def mock_s3_client():
    """Create mock S3 client"""
    client = MagicMock()
    
    # Mock successful head_bucket for validation
    client.head_bucket.return_value = {}
    
    # Mock successful put_object
    client.put_object.return_value = {}
    
    # Mock successful get_object
    mock_response = {
        'Body': MagicMock(),
        'ContentLength': 100,
        'ContentType': 'text/plain',
        'LastModified': '2024-01-01T00:00:00Z',
        'ETag': '"abc123"'
    }
    mock_response['Body'].read.return_value = b"test content"
    client.get_object.return_value = mock_response
    
    # Mock successful head_object
    from datetime import datetime
    client.head_object.return_value = {
        'ContentLength': 100,
        'ContentType': 'text/plain',
        'LastModified': datetime(2024, 1, 1),
        'ETag': '"abc123"',
        'Metadata': {'custom': 'value'}
    }
    
    # Mock successful delete_object
    client.delete_object.return_value = {}
    
    # Mock successful list_objects_v2
    client.list_objects_v2.return_value = {
        'Contents': [
            {'Key': 'test/file1.txt'},
            {'Key': 'test/file2.txt'}
        ]
    }
    
    # Mock generate_presigned_url
    client.generate_presigned_url.return_value = "https://signed-url.example.com"
    
    return client


@pytest.fixture
def s3_backend(mock_s3_client):
    """Create S3StorageBackend instance with mocked S3 client"""
    with patch('boto3.Session') as mock_session:
        mock_session.return_value.client.return_value = mock_s3_client
        
        backend = S3StorageBackend(
            bucket_name="test-bucket",
            region="us-east-1",
            access_key="test-key",
            secret_key="test-secret",
            bucket_path="test-prefix",
            cloudfront_domain="cdn.example.com"
        )
        
        # Replace the client created during __init__ with our mock
        backend.s3_client = mock_s3_client
        
        return backend


class TestS3StorageBackend:
    """Tests for S3StorageBackend"""
    
    @pytest.mark.asyncio
    async def test_upload_file(self, s3_backend, mock_s3_client):
        """Test file upload to S3"""
        content = b"test file content"
        key = "test/file.txt"
        content_type = "text/plain"
        metadata = {"test": "value"}
        
        # Upload file
        url = await s3_backend.upload_file(content, key, content_type, metadata)
        
        # Check URL format (with CloudFront)
        assert url == "https://cdn.example.com/test-prefix/test/file.txt"
        
        # Verify S3 client was called correctly
        mock_s3_client.put_object.assert_called_once()
        call_args = mock_s3_client.put_object.call_args
        
        assert call_args[1]['Bucket'] == "test-bucket"
        assert call_args[1]['Key'] == "test-prefix/test/file.txt"
        assert call_args[1]['Body'] == content
        assert call_args[1]['ContentType'] == content_type
        assert call_args[1]['Metadata']['test'] == "value"
        assert 'uploaded_at' in call_args[1]['Metadata']
    
    @pytest.mark.asyncio
    async def test_download_file(self, s3_backend, mock_s3_client):
        """Test file download from S3"""
        key = "test/file.txt"
        
        # Download file
        content = await s3_backend.download_file(key)
        
        # Check result
        assert content == b"test content"
        
        # Verify S3 client was called correctly
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="test-prefix/test/file.txt"
        )
    
    @pytest.mark.asyncio
    async def test_download_file_not_found(self, s3_backend, mock_s3_client):
        """Test file download when file doesn't exist"""
        # Mock NoSuchKey error
        mock_s3_client.get_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey'}}, 'GetObject'
        )
        
        key = "nonexistent/file.txt"
        
        # Download file
        content = await s3_backend.download_file(key)
        
        # Should return None
        assert content is None
    
    @pytest.mark.asyncio
    async def test_delete_file(self, s3_backend, mock_s3_client):
        """Test file deletion from S3"""
        key = "test/file.txt"
        
        # Delete file
        success = await s3_backend.delete_file(key)
        
        # Check result
        assert success == True
        
        # Verify S3 client was called correctly
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="test-prefix/test/file.txt"
        )
    
    @pytest.mark.asyncio
    async def test_file_exists_true(self, s3_backend, mock_s3_client):
        """Test file exists check when file exists"""
        key = "test/file.txt"
        
        # Check if file exists
        exists = await s3_backend.file_exists(key)
        
        # Should return True
        assert exists == True
        
        # Verify S3 client was called correctly
        mock_s3_client.head_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="test-prefix/test/file.txt"
        )
    
    @pytest.mark.asyncio
    async def test_file_exists_false(self, s3_backend, mock_s3_client):
        """Test file exists check when file doesn't exist"""
        # Mock 404 error
        mock_s3_client.head_object.side_effect = ClientError(
            {'Error': {'Code': '404'}}, 'HeadObject'
        )
        
        key = "nonexistent/file.txt"
        
        # Check if file exists
        exists = await s3_backend.file_exists(key)
        
        # Should return False
        assert exists == False
    
    @pytest.mark.asyncio
    async def test_get_file_url_public(self, s3_backend):
        """Test getting public file URL"""
        key = "test/file.txt"
        
        # Get public URL
        url = await s3_backend.get_file_url(key, public=True)
        
        # Check CloudFront URL format
        assert url == "https://cdn.example.com/test-prefix/test/file.txt"
    
    @pytest.mark.asyncio
    async def test_get_file_url_signed(self, s3_backend, mock_s3_client):
        """Test getting signed file URL"""
        key = "test/file.txt"
        expires_in = 3600
        
        # Get signed URL
        url = await s3_backend.get_file_url(key, expires_in=expires_in)
        
        # Check result
        assert url == "https://signed-url.example.com"
        
        # Verify S3 client was called correctly
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            'get_object',
            Params={
                'Bucket': 'test-bucket',
                'Key': 'test-prefix/test/file.txt'
            },
            ExpiresIn=expires_in
        )
    
    @pytest.mark.asyncio
    async def test_get_file_info(self, s3_backend, mock_s3_client):
        """Test getting file info from S3"""
        key = "test/file.txt"
        
        # Get file info
        info = await s3_backend.get_file_info(key)
        
        # Check result
        assert info is not None
        assert info['size'] == 100
        assert info['content_type'] == 'text/plain'
        assert info['etag'] == 'abc123'
        assert info['custom'] == 'value'
        assert 'modified_time' in info
    
    @pytest.mark.asyncio
    async def test_get_file_info_not_found(self, s3_backend, mock_s3_client):
        """Test getting file info when file doesn't exist"""
        # Mock 404 error
        mock_s3_client.head_object.side_effect = ClientError(
            {'Error': {'Code': '404'}}, 'HeadObject'
        )
        
        key = "nonexistent/file.txt"
        
        # Get file info
        info = await s3_backend.get_file_info(key)
        
        # Should return None
        assert info is None
    
    @pytest.mark.asyncio
    async def test_list_files(self, s3_backend, mock_s3_client):
        """Test listing files in S3"""
        prefix = "test/"
        limit = 10
        
        # List files
        files = await s3_backend.list_files(prefix, limit)
        
        # Check result
        assert len(files) == 2
        assert "test/file1.txt" in files
        assert "test/file2.txt" in files
        
        # Verify S3 client was called correctly
        mock_s3_client.list_objects_v2.assert_called_once_with(
            Bucket="test-bucket",
            Prefix="test-prefix/test/",
            MaxKeys=limit
        )
    
    def test_backend_properties(self, s3_backend):
        """Test backend properties"""
        assert s3_backend.backend_type == "s3"
        assert s3_backend.supports_public_urls == True
        assert s3_backend.supports_signed_urls == True
    
    def test_get_full_key(self, s3_backend):
        """Test _get_full_key method"""
        key = "test/file.txt"
        full_key = s3_backend._get_full_key(key)
        assert full_key == "test-prefix/test/file.txt"
    
    def test_get_public_url_cloudfront(self, s3_backend):
        """Test _get_public_url method with CloudFront"""
        key = "test/file.txt"
        url = s3_backend._get_public_url(key)
        assert url == "https://cdn.example.com/test-prefix/test/file.txt"
    
    def test_get_public_url_direct_s3(self):
        """Test _get_public_url method with direct S3 URL"""
        with patch('boto3.Session') as mock_session:
            mock_client = MagicMock()
            mock_client.head_bucket.return_value = {}
            mock_session.return_value.client.return_value = mock_client
            
            # Create backend without CloudFront
            backend = S3StorageBackend(
                bucket_name="test-bucket",
                region="us-west-2",
                access_key="test-key",
                secret_key="test-secret",
                bucket_path="prefix",
                cloudfront_domain=None
            )
            backend.s3_client = mock_client
            
            key = "test/file.txt"
            url = backend._get_public_url(key)
            assert url == "https://test-bucket.s3.us-west-2.amazonaws.com/prefix/test/file.txt"


class TestS3BackendInitialization:
    """Tests for S3StorageBackend initialization"""
    
    def test_init_missing_bucket_name(self):
        """Test initialization without bucket name"""
        with pytest.raises(ValueError, match="S3 bucket name is required"):
            with patch('boto3.Session'):
                S3StorageBackend(
                    bucket_name=None,
                    access_key="test-key",
                    secret_key="test-secret"
                )
    
    def test_init_invalid_credentials(self):
        """Test initialization with invalid credentials"""
        with patch('boto3.Session') as mock_session:
            mock_client = MagicMock()
            mock_client.head_bucket.side_effect = ClientError(
                {'Error': {'Code': 'NoCredentialsError'}}, 'HeadBucket'
            )
            mock_session.return_value.client.return_value = mock_client
            
            with pytest.raises(ValueError, match="AWS credentials not found"):
                S3StorageBackend(
                    bucket_name="test-bucket",
                    access_key="invalid",
                    secret_key="invalid"
                )
    
    def test_init_bucket_not_found(self):
        """Test initialization with non-existent bucket"""
        with patch('boto3.Session') as mock_session:
            mock_client = MagicMock()
            mock_client.head_bucket.side_effect = ClientError(
                {'Error': {'Code': '404'}}, 'HeadBucket'
            )
            mock_session.return_value.client.return_value = mock_client
            
            with pytest.raises(ValueError, match="S3 bucket 'test-bucket' not found"):
                S3StorageBackend(
                    bucket_name="test-bucket",
                    access_key="test-key",
                    secret_key="test-secret"
                )
    
    def test_init_access_denied(self):
        """Test initialization with access denied to bucket"""
        with patch('boto3.Session') as mock_session:
            mock_client = MagicMock()
            mock_client.head_bucket.side_effect = ClientError(
                {'Error': {'Code': '403'}}, 'HeadBucket'
            )
            mock_session.return_value.client.return_value = mock_client
            
            with pytest.raises(ValueError, match="Access denied to S3 bucket"):
                S3StorageBackend(
                    bucket_name="test-bucket",
                    access_key="test-key",
                    secret_key="test-secret"
                )