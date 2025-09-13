# Unified File Storage System - Product Requirements Document

## Executive Summary

This PRP outlines the implementation of a unified file storage system to consolidate avatar management and chat attachment storage with support for both local development and cloud deployment (AWS S3). The current system has inconsistent storage mechanisms for user avatars, agent avatars, and file attachments, creating maintenance complexity and deployment challenges.

## Background & Current State

### User Avatars
- **Storage**: Local file system under `uploads/avatars/` with thumbnails in `small/`, `medium/`, `large/` subdirectories
- **Service**: `AvatarService` handles validation, saving, and thumbnail generation
- **URL Pattern**: `/api/v1/users/{user_id}/avatar` stored in `User.avatar_url`
- **Features**: Multiple thumbnail sizes, EXIF handling, comprehensive validation, security checks

### Agent Avatars  
- **Storage**: No file storage - `Agent.avatar_url` is a plain string field for external URLs
- **Service**: No dedicated service - managed directly in agent endpoints
- **URL Pattern**: External URLs provided by client
- **Features**: Basic string storage only

### Chat Attachments
- **Storage**: Local file system via `FileService` under `uploads/` directory
- **Service**: `FileService` with processing, analysis, and metadata extraction
- **URL Pattern**: File-based serving with database metadata
- **Features**: File processing, AI analysis, metadata extraction, comprehensive validation

### Problems with Current Architecture
1. **Inconsistent Storage**: Three different storage mechanisms for file-related data
2. **Development vs Production**: Local storage not suitable for cloud deployment
3. **Avatar Disparity**: User avatars have rich features while agent avatars are basic strings
4. **Deployment Complexity**: Manual file migration needed between environments
5. **Scalability Issues**: Local storage doesn't scale across multiple application instances

## Requirements

### Functional Requirements

#### FR-1: Unified Storage Interface
- Create a generic storage interface supporting both local filesystem and AWS S3
- Environment-based storage backend selection (local for dev, S3 for cloud)
- Transparent API regardless of underlying storage mechanism

#### FR-2: Avatar Standardization
- Unify user and agent avatar storage using the same backend system
- Support thumbnail generation for all avatar types
- Maintain existing avatar API endpoints and functionality
- Agent avatars should support file uploads like user avatars

#### FR-3: Chat Attachment Cloud Support
- Extend file attachment storage to support S3 backend
- Maintain existing file processing and analysis capabilities
- Support large file handling in cloud environment

#### FR-4: Environment Configuration
- Local storage for development environment (`ENVIRONMENT=development`)
- S3 storage for staging/production environments (`ENVIRONMENT=staging|production`)
- Configuration via environment variables
- Graceful fallback mechanisms

#### FR-5: Migration Support
- Data migration utilities for moving from local to S3 storage
- Backward compatibility during transition period
- URL rewriting for existing stored URLs

### Non-Functional Requirements

#### NFR-1: Performance
- Upload/download performance equivalent to current system
- Efficient thumbnail generation and caching
- Streaming support for large files

#### NFR-2: Security
- Maintain existing security validations for all file types
- Secure S3 access with appropriate IAM policies
- Signed URLs for private file access
- CORS configuration for browser uploads

#### NFR-3: Reliability
- Error handling and retry mechanisms for cloud operations
- Graceful degradation when storage backend unavailable
- Transaction safety for database and storage operations

#### NFR-4: Scalability
- Support for multiple application instances
- CDN integration for public file serving
- Efficient storage organization and cleanup

## Technical Design

### Storage Interface Architecture

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, IO
from pathlib import Path

class StorageBackend(ABC):
    """Abstract storage backend interface"""
    
    @abstractmethod
    async def upload_file(self, content: bytes, key: str, metadata: Dict[str, Any] = None) -> str:
        """Upload file and return access URL"""
        pass
    
    @abstractmethod
    async def download_file(self, key: str) -> Optional[bytes]:
        """Download file by key"""
        pass
    
    @abstractmethod
    async def delete_file(self, key: str) -> bool:
        """Delete file by key"""
        pass
    
    @abstractmethod
    async def file_exists(self, key: str) -> bool:
        """Check if file exists"""
        pass
    
    @abstractmethod
    async def get_file_url(self, key: str, expires_in: Optional[int] = None) -> str:
        """Get public or signed URL for file"""
        pass

class LocalStorageBackend(StorageBackend):
    """Local filesystem storage implementation"""
    pass

class S3StorageBackend(StorageBackend):
    """AWS S3 storage implementation"""
    pass
```

### Storage Service Architecture

```python
class StorageService:
    """Generic storage service for file operations"""
    
    def __init__(self, backend: StorageBackend):
        self.backend = backend
    
    async def upload_file(self, file: UploadFile, storage_key: str, metadata: Dict[str, Any] = None) -> str:
        """Upload generic file"""
        pass
    
    async def upload_content(self, content: bytes, storage_key: str, content_type: str, metadata: Dict[str, Any] = None) -> str:
        """Upload raw content"""
        pass
    
    async def download_file(self, storage_key: str) -> Optional[bytes]:
        """Download file content"""
        pass
    
    async def delete_file(self, storage_key: str) -> bool:
        """Delete file"""
        pass

class AvatarStorageService:
    """Avatar-specific storage service with thumbnail generation"""
    
    def __init__(self, backend: StorageBackend):
        self.backend = backend
    
    async def upload_user_avatar(self, user_id: UUID, file: UploadFile) -> Dict[str, str]:
        """Upload user avatar with thumbnail generation"""
        pass
    
    async def upload_agent_avatar(self, agent_id: UUID, file: UploadFile) -> Dict[str, str]:
        """Upload agent avatar with thumbnail generation"""
        pass
    
    async def get_avatar_url(self, entity_id: UUID, entity_type: str, size: str, expires_in: int = None) -> Optional[str]:
        """Get avatar URL for specific size"""
        pass
```

### Configuration Settings

```python
class StorageSettings:
    # Storage backend selection
    storage_backend: str = Field(default="local", description="Storage backend (local, s3)")
    
    # Local storage settings
    upload_directory: str = Field(default="uploads", description="Local upload directory")
    
    # S3 storage settings  
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS access key")
    aws_secret_access_key: Optional[str] = Field(default=None, description="AWS secret key")
    aws_region: str = Field(default="us-east-1", description="AWS region")
    s3_bucket_name: Optional[str] = Field(default=None, description="S3 bucket name")
    s3_bucket_path: str = Field(default="", description="S3 bucket path prefix")
    cloudfront_domain: Optional[str] = Field(default=None, description="CloudFront domain for CDN")
```

### File Organization Structure

```
Storage Root/
├── avatars/
│   ├── users/
│   │   ├── {user_id}/
│   │   │   ├── original.{ext}
│   │   │   ├── small.{ext}
│   │   │   ├── medium.{ext}
│   │   │   └── large.{ext}
│   └── agents/
│       ├── {agent_id}/
│       │   ├── original.{ext}
│       │   ├── small.{ext}
│       │   ├── medium.{ext}
│       │   └── large.{ext}
├── attachments/
│   ├── {year}/{month}/
│   │   ├── {file_id}.{ext}
│   └── processed/
│       ├── {file_id}_metadata.json
└── temp/
    ├── uploads/
    └── processing/
```

## API Changes

### New Agent Avatar Endpoints

```
POST /api/v1/agents/{agent_id}/avatar
GET /api/v1/agents/{agent_id}/avatar?size=small|medium|large
DELETE /api/v1/agents/{agent_id}/avatar
GET /api/v1/agents/{agent_id}/avatar/info
```

### Updated Agent Schema

```python
class AgentResponse(BaseModel):
    # ... existing fields
    avatar_url: Optional[str] = Field(default=None, description="Avatar URL (now supports file uploads)")
    has_custom_avatar: bool = Field(description="Whether agent has uploaded avatar")
```

### Environment-Based URL Generation

- **Development**: `http://localhost:8000/api/v1/storage/avatars/users/{user_id}/medium.jpg`
- **Production**: `https://cdn.example.com/avatars/users/{user_id}/medium.jpg`

## Database Schema Changes

### New Storage Metadata Table

```sql
CREATE TABLE file_storage_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    storage_key VARCHAR(500) NOT NULL UNIQUE,
    original_filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL, -- MIME type of the file
    storage_backend VARCHAR(20) NOT NULL, -- 'local', 's3'
    file_size BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB, -- Additional file metadata
    INDEX(storage_key),
    INDEX(content_type),
    INDEX(storage_backend),
    INDEX(created_at)
);
```

### Avatar Size Variant Metadata

```sql
CREATE TABLE avatar_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    base_file_id UUID NOT NULL, -- References file_storage_metadata
    entity_type VARCHAR(20) NOT NULL, -- 'user', 'agent'
    entity_id UUID NOT NULL, -- user_id or agent_id
    size_variant VARCHAR(20) NOT NULL, -- 'original', 'small', 'medium', 'large'
    storage_key VARCHAR(500) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    INDEX(entity_type, entity_id),
    INDEX(entity_id, size_variant),
    FOREIGN KEY (base_file_id) REFERENCES file_storage_metadata(id) ON DELETE CASCADE
);
```

### Agent Table Updates

```sql
-- Add avatar metadata to agents table
ALTER TABLE agents ADD COLUMN has_custom_avatar BOOLEAN DEFAULT FALSE;
```

## Metadata Design Principles

### Generic File Storage Metadata
- `file_storage_metadata` table stores generic information about any file in the system
- `content_type` field stores the actual MIME type (e.g., 'image/jpeg', 'text/plain')
- No entity-specific information stored - keeps the schema generic and reusable
- Storage key is unique across all backends and file types

### Avatar-Specific Metadata
- `avatar_variants` table specifically handles avatar size variants
- Links to the base file via `base_file_id` foreign key
- Stores entity information (user/agent) and size variants separately
- Allows for flexible avatar management without polluting the generic file metadata

### Benefits of Separated Design
1. **Generic File Storage**: `file_storage_metadata` can be used for any file type
2. **Type-Specific Extensions**: Avatar variants handled in dedicated table
3. **Clean Separation**: File storage concerns separated from business logic
4. **Scalability**: Easy to add new file type metadata tables as needed

## Implementation Plan

### Phase 1: Core Storage Interface
- [ ] Implement abstract `StorageBackend` interface
- [ ] Create `LocalStorageBackend` with existing functionality
- [ ] Create `S3StorageBackend` with AWS integration
- [ ] Add storage configuration to settings
- [ ] Create `StorageService` 

### Phase 2: Avatar Standardization  
- [ ] Update `AvatarService` to use unified storage
- [ ] Implement agent avatar upload endpoints
- [ ] Add thumbnail generation for agent avatars
- [ ] Update agent schemas and API responses
- [ ] Migrate existing user avatars to new system

### Phase 3: Attachment Cloud Support
- [ ] Update `FileService` to use unified storage
- [ ] Implement S3 backend for file attachments
- [ ] Add signed URL generation for private files
- [ ] Update file serving endpoints

### Phase 4: Testing & Migration
- [ ] Comprehensive test suite for all storage operations
- [ ] Integration tests for local and S3 backends
- [ ] Migration scripts for existing data
- [ ] Performance testing and optimization
- [ ] Documentation updates

### Phase 5: Production Deployment
- [ ] S3 bucket setup and IAM policies
- [ ] CloudFront CDN configuration
- [ ] Environment-specific configuration
- [ ] Data migration to production S3
- [ ] Monitoring and alerting setup

## Testing Strategy

### Unit Tests
- Storage backend implementations (local and S3)
- Unified storage service methods
- Avatar and file upload/download operations
- Thumbnail generation and validation
- Error handling and edge cases

### Integration Tests
- End-to-end avatar upload/download workflows
- File attachment processing with cloud storage
- Cross-environment compatibility testing
- Migration script validation
- Performance benchmarking

### Test Environments
- **Development**: Local storage backend testing
- **Staging**: S3 backend testing with test bucket
- **CI/CD**: Mock S3 backend for automated testing

## Security Considerations

### File Upload Security
- Maintain existing file validation and security checks
- S3 bucket policies restricting public access
- Signed URL generation with appropriate expiration
- Virus scanning integration for uploaded files

### Access Control
- Role-based access to file storage operations
- User avatar privacy controls
- Organization-scoped agent avatar access
- Secure file deletion and cleanup

### Data Protection
- Encryption at rest (S3 server-side encryption)
- Encryption in transit (HTTPS/TLS)
- Regular security audits of storage configurations
- Compliance with data retention policies

## Monitoring & Observability

### Metrics
- File upload/download success rates
- Storage backend response times
- Error rates by operation type
- Storage utilization and costs
- CDN hit rates and performance

### Logging
- All storage operations with request IDs
- Error logs with context and retry information
- Migration progress and status tracking
- Security events and access patterns

### Alerting
- Storage backend unavailability
- High error rates or unusual patterns
- Storage quota warnings
- Failed migration operations

## Success Criteria

### Functional Success
- [ ] All avatar operations work identically across user and agent types
- [ ] File attachments support both local and S3 storage seamlessly
- [ ] Existing API compatibility maintained during transition
- [ ] Environment-based storage backend selection working correctly

### Performance Success  
- [ ] Upload/download times within 10% of current performance
- [ ] Thumbnail generation time unchanged
- [ ] No impact on API response times for non-storage operations
- [ ] CDN integration reduces file serving latency by >50%

### Operational Success
- [ ] Zero-downtime migration from local to S3 storage
- [ ] Automated backup and disaster recovery procedures
- [ ] Clear monitoring and alerting for storage operations
- [ ] Documentation and runbooks for operational procedures

## Risk Assessment

### Technical Risks
- **S3 API complexity**: Mitigated by comprehensive testing and phased rollout
- **File migration integrity**: Addressed with validation scripts and rollback procedures  
- **Performance regression**: Monitored with benchmarking and performance testing
- **Storage cost escalation**: Controlled with lifecycle policies and monitoring

### Operational Risks
- **Data loss during migration**: Prevented with backup procedures and validation
- **Service disruption**: Minimized with blue-green deployment and rollback plans
- **Configuration errors**: Reduced with infrastructure as code and peer review
- **Vendor lock-in**: Addressed with abstract storage interface design

## Conclusion

The unified file storage system will provide a robust, scalable foundation for all file-related operations in the AI Ticket Creator backend. By standardizing avatar management across user and agent types, and enabling cloud storage for all file types, this implementation supports both current needs and future growth while maintaining backward compatibility and operational simplicity.