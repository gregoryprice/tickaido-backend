# Support Attachments Feature - Phase 2 Implementation

## Executive Summary

This document defines Phase 2 enhancements to the file attachment system, building on the Phase 1 foundation. Phase 2 adds advanced security features, public file sharing, analytics, and scalability improvements.

## Phase 2 Scope

### ✅ New Features in Phase 2
- **Advanced Security**: Multi-layer malware scanning, quarantine system, threat detection
- **Public File Sharing**: Public access controls and sharing mechanisms
- **Analytics & Monitoring**: Download tracking, access logging, usage metrics
- **File Quality Assessment**: Automated quality scoring and recommendations
- **Tag Management**: User-defined tagging system with search capabilities
- **Scalable Uploads**: Chunked uploads and presigned URLs for large files
- **External References**: Integration tracking and external system links
- **Advanced Access Controls**: Granular permissions and sharing controls

### 🔄 Enhanced from Phase 1
- **File Model**: Extended with security, analytics, and sharing fields
- **Validation Pipeline**: Multi-layer security scanning
- **API Endpoints**: Additional endpoints for sharing, analytics, and management
- **Agent Integration**: Enhanced context with security and quality metadata

## Enhanced File Model & Database Schema

Phase 2 extends the Phase 1 schema with additional fields for security and analytics:

```sql
CREATE TABLE files (
    -- Phase 1 Base Fields (unchanged)
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL UNIQUE,
    mime_type VARCHAR(100) NOT NULL,
    file_size BIGINT NOT NULL,
    file_hash VARCHAR(64) NOT NULL UNIQUE,
    file_type file_type_enum NOT NULL DEFAULT 'other',
    status file_status_enum NOT NULL DEFAULT 'uploaded',
    processing_started_at TIMESTAMPTZ,
    processing_completed_at TIMESTAMPTZ,
    processing_error TEXT,
    processing_attempts INTEGER DEFAULT 0,
    processing_time_seconds INTEGER,
    uploaded_by_id UUID REFERENCES users(id) NOT NULL,
    organization_id UUID REFERENCES organizations(id) NOT NULL,
    ai_analysis_version VARCHAR(20),
    ai_confidence_score VARCHAR(10),
    extracted_context JSON,
    extraction_method VARCHAR(50),
    content_summary TEXT,
    language_detection VARCHAR(10),
    retention_policy VARCHAR(50),
    expires_at TIMESTAMPTZ,
    archived_at TIMESTAMPTZ,

    -- Phase 2: Security & Malware Scanning
    virus_scan_result VARCHAR(20),  -- 'clean', 'infected', 'suspicious', 'unknown'
    virus_scan_at TIMESTAMPTZ,
    virus_details TEXT,
    quarantine_reason TEXT,
    security_scan_version VARCHAR(20),
    threat_level VARCHAR(20), -- 'none', 'low', 'medium', 'high', 'critical'
    
    -- Phase 2: Public Sharing & Access Control
    is_public BOOLEAN DEFAULT FALSE,
    public_access_token VARCHAR(64), -- For secure public sharing
    public_expires_at TIMESTAMPTZ,
    access_permissions JSON, -- Granular user/role permissions
    share_settings JSON, -- Sharing configuration and restrictions
    
    -- Phase 2: Analytics & Usage Tracking
    download_count INTEGER DEFAULT 0,
    public_download_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    access_history JSON, -- Recent access log (limited entries)
    referrer_sources JSON, -- Where downloads/views came from
    
    -- Phase 2: Quality & Classification
    file_quality_score VARCHAR(10), -- 0.0-1.0 quality assessment
    quality_issues JSON, -- List of detected quality problems
    content_classification JSON, -- Automated content categories
    
    -- Phase 2: Tagging & Organization
    tags JSON, -- User and system-generated tags
    user_tags JSON, -- User-defined tags (separate from system tags)
    tag_suggestions JSON, -- AI-suggested tags not yet applied
    
    -- Phase 2: Integration Sync Status (external refs handled at app level)
    sync_status VARCHAR(20), -- 'synced', 'pending', 'failed', 'not_applicable'
    last_sync_at TIMESTAMPTZ,
    
    -- Phase 2: Advanced Metadata
    processing_metadata JSON, -- Detailed processing results and metrics
    scan_history JSON, -- History of security scans
    version_history JSON, -- If file versioning is implemented
    
    -- Additional Indexes for Phase 2
    INDEX idx_files_virus_scan_result (virus_scan_result),
    INDEX idx_files_is_public (is_public),
    INDEX idx_files_public_access_token (public_access_token),
    INDEX idx_files_threat_level (threat_level),
    INDEX idx_files_tags (tags) -- GIN index for tag search
);
```

## Advanced Security Implementation

### Multi-Layer Malware Scanning System

Phase 2 implements comprehensive malware detection using multiple scanning engines:

```python
class MalwareScannerService:
    """Multi-layer malware scanning service for Phase 2"""
    
    def __init__(self):
        self.clamav_client = ClamAVClient()
        self.virustotal_api = VirusTotalClient()
        self.yara_engine = YaraEngine()
        self.hash_reputation_db = HashReputationDatabase()
        
    async def scan_file(self, file_content: bytes, filename: str) -> ScanResult:
        """Perform comprehensive multi-layer malware scan"""
        
        # Stage 1: Quick hash-based reputation check
        file_hash = hashlib.sha256(file_content).hexdigest()
        reputation = await self.hash_reputation_db.check_hash(file_hash)
        
        if reputation.is_known_malicious:
            return ScanResult(
                is_clean=False,
                threat="Known malicious hash",
                threat_level="critical",
                scanner="hash_reputation",
                confidence=0.99
            )
        elif reputation.is_known_clean:
            return ScanResult(
                is_clean=True,
                scanner="hash_reputation",
                confidence=0.95
            )
        
        # Stage 2: Local ClamAV signature-based scan
        clamav_result = await self.clamav_client.scan_bytes(file_content)
        if not clamav_result.is_clean:
            threat_level = self._assess_threat_level(clamav_result.threat_name)
            return ScanResult(
                is_clean=False,
                threat=clamav_result.threat_name,
                threat_level=threat_level,
                scanner="clamav",
                confidence=0.9
            )
        
        # Stage 3: YARA rules for behavioral analysis
        yara_result = await self.yara_engine.scan_content(file_content, filename)
        if yara_result.matches:
            return ScanResult(
                is_clean=False,
                threat=f"Suspicious patterns: {', '.join(yara_result.matches)}",
                threat_level="medium",
                scanner="yara",
                confidence=0.7
            )
        
        # Stage 4: Cloud-based multi-engine scan (high-risk files only)
        if self._is_high_risk_file(filename, file_content):
            vt_result = await self.virustotal_api.scan_file(file_content)
            if vt_result.detection_count > 2:  # More than 2 engines detected threats
                threat_level = self._assess_vt_threat_level(vt_result.detection_count)
                return ScanResult(
                    is_clean=False,
                    threat=f"Multiple engines detected threats ({vt_result.detection_count}/70)",
                    threat_level=threat_level,
                    scanner="virustotal",
                    confidence=0.95
                )
        
        return ScanResult(is_clean=True, scanner="multi-layer", confidence=0.85)
    
    def _assess_threat_level(self, threat_name: str) -> str:
        """Assess threat level based on threat signature"""
        threat_name_lower = threat_name.lower()
        
        if any(keyword in threat_name_lower for keyword in ['trojan', 'backdoor', 'rootkit']):
            return "critical"
        elif any(keyword in threat_name_lower for keyword in ['virus', 'worm', 'malware']):
            return "high"
        elif any(keyword in threat_name_lower for keyword in ['adware', 'pup', 'suspicious']):
            return "medium"
        else:
            return "low"
    
    def _is_high_risk_file(self, filename: str, content: bytes) -> bool:
        """Determine if file requires cloud scanning"""
        high_risk_extensions = ['.exe', '.scr', '.bat', '.cmd', '.com', '.pif', '.jar']
        suspicious_mime_types = ['application/x-executable', 'application/x-msdownload']
        
        return (
            any(filename.lower().endswith(ext) for ext in high_risk_extensions) or
            len(content) > 50 * 1024 * 1024 or  # Files larger than 50MB
            self._has_suspicious_patterns(content[:1024])  # Check first 1KB
        )
    
    async def quarantine_file(self, file_obj: File, scan_result: ScanResult):
        """Move infected file to secure quarantine"""
        
        # Move to quarantine storage
        quarantine_path = f"quarantine/{file_obj.file_hash[:2]}/{file_obj.file_hash}"
        await self.storage_service.move_to_quarantine(file_obj.file_path, quarantine_path)
        
        # Update database record
        file_obj.status = FileStatus.QUARANTINED
        file_obj.virus_scan_result = "infected"
        file_obj.virus_details = scan_result.threat
        file_obj.quarantine_reason = f"Malware detected: {scan_result.threat}"
        file_obj.threat_level = scan_result.threat_level
        file_obj.virus_scan_at = datetime.now(timezone.utc)
        
        # Log security event
        await self.security_logger.log_quarantine_event(file_obj, scan_result)
```

### Enhanced File Validation Pipeline

```python
class AdvancedFileValidator:
    """Phase 2 comprehensive file validation with security scanning"""
    
    def __init__(self):
        self.basic_validator = BasicFileValidator()  # From Phase 1
        self.malware_scanner = MalwareScannerService()
        self.content_classifier = ContentClassificationService()
    
    async def validate_upload(self, file: UploadFile, user: User) -> FileValidationResult:
        """Comprehensive Phase 2 file validation"""
        
        # Phase 1 basic validation
        basic_result = await self.basic_validator.validate_upload(file, user)
        file_content = basic_result.file_content
        
        # Phase 2 security scanning
        scan_result = await self.malware_scanner.scan_file(file_content, file.filename)
        
        if not scan_result.is_clean:
            # Create quarantined file record
            quarantine_record = await self._create_quarantine_record(
                file, scan_result, user
            )
            raise SecurityError(
                f"File failed security scan: {scan_result.threat}",
                quarantine_id=quarantine_record.id
            )
        
        # Content classification and quality assessment
        classification = await self.content_classifier.classify_content(
            file_content, file.filename, file.content_type
        )
        
        return FileValidationResult(
            valid=True,
            file_content=file_content,
            scan_result=scan_result,
            classification=classification
        )
```

## Public File Sharing System

Phase 2 adds secure public file sharing capabilities:

```python
class PublicFileSharingService:
    """Secure public file sharing with access controls"""
    
    async def make_file_public(
        self,
        db: AsyncSession,
        file_id: UUID,
        user: User,
        sharing_config: PublicSharingConfig
    ) -> PublicShareResult:
        """Create public share link for file"""
        
        file_obj = await self.file_service.get_file(db, file_id)
        if not file_obj or file_obj.uploaded_by_id != user.id:
            raise ValueError("File not found or not accessible")
        
        # Verify file is safe for public sharing
        if file_obj.threat_level in ["medium", "high", "critical"]:
            raise ValueError("File cannot be shared publicly due to security concerns")
        
        # Generate secure access token
        access_token = secrets.token_urlsafe(32)
        
        # Configure public sharing
        file_obj.is_public = True
        file_obj.public_access_token = access_token
        file_obj.public_expires_at = sharing_config.expires_at
        file_obj.share_settings = {
            "allow_download": sharing_config.allow_download,
            "require_auth": sharing_config.require_auth,
            "allowed_domains": sharing_config.allowed_domains,
            "download_limit": sharing_config.download_limit,
            "password_protected": bool(sharing_config.password)
        }
        
        await db.commit()
        
        # Generate public URL
        public_url = f"{self.base_url}/public/files/{access_token}"
        
        return PublicShareResult(
            share_url=public_url,
            access_token=access_token,
            expires_at=file_obj.public_expires_at
        )
    
    async def access_public_file(
        self,
        access_token: str,
        request: Request
    ) -> PublicFileResponse:
        """Handle public file access with security checks"""
        
        # Find file by access token
        file_obj = await self.get_file_by_public_token(access_token)
        if not file_obj or not file_obj.is_public:
            raise HTTPException(404, "File not found")
        
        # Check expiration
        if file_obj.public_expires_at and datetime.now(timezone.utc) > file_obj.public_expires_at:
            raise HTTPException(410, "Share link has expired")
        
        # Apply sharing restrictions
        share_settings = file_obj.share_settings or {}
        
        # Domain restriction
        if share_settings.get("allowed_domains"):
            referrer_domain = self._extract_domain(request.headers.get("referer"))
            if referrer_domain not in share_settings["allowed_domains"]:
                raise HTTPException(403, "Access not allowed from this domain")
        
        # Download limit check
        if share_settings.get("download_limit"):
            if file_obj.public_download_count >= share_settings["download_limit"]:
                raise HTTPException(429, "Download limit exceeded")
        
        # Log access
        await self._log_public_access(file_obj, request)
        
        # Update counters
        file_obj.public_download_count += 1
        file_obj.last_accessed_at = datetime.now(timezone.utc)
        
        return PublicFileResponse(
            filename=file_obj.filename,
            file_size=file_obj.file_size,
            mime_type=file_obj.mime_type,
            download_url=await self.generate_download_url(file_obj)
        )
```

## Enhanced Analytics & Monitoring

Phase 2 provides comprehensive analytics and usage tracking:

```python
class FileAnalyticsService:
    """File usage analytics and monitoring"""
    
    async def record_file_access(
        self,
        file_id: UUID,
        user_id: UUID,
        access_type: str,  # 'view', 'download', 'share'
        request: Request
    ):
        """Record detailed file access event"""
        
        access_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": str(user_id),
            "access_type": access_type,
            "ip_address": request.client.host,
            "user_agent": request.headers.get("user-agent"),
            "referrer": request.headers.get("referer")
        }
        
        # Update file access history (keep last 100 entries)
        file_obj = await self.file_service.get_file(db, file_id)
        access_history = file_obj.access_history or []
        access_history.append(access_event)
        
        # Keep only recent entries
        if len(access_history) > 100:
            access_history = access_history[-100:]
        
        file_obj.access_history = access_history
        file_obj.last_accessed_at = datetime.now(timezone.utc)
        
        if access_type == "download":
            file_obj.download_count += 1
        
        await db.commit()
    
    async def get_file_analytics(
        self,
        db: AsyncSession,
        file_id: UUID,
        user: User
    ) -> FileAnalytics:
        """Get comprehensive analytics for a file"""
        
        file_obj = await self.file_service.get_file(db, file_id)
        if not file_obj or file_obj.organization_id != user.organization_id:
            raise ValueError("File not found or not accessible")
        
        # Calculate analytics
        access_history = file_obj.access_history or []
        
        return FileAnalytics(
            total_downloads=file_obj.download_count,
            public_downloads=file_obj.public_download_count,
            unique_viewers=len(set(event["user_id"] for event in access_history)),
            access_by_type={
                "view": len([e for e in access_history if e["access_type"] == "view"]),
                "download": len([e for e in access_history if e["access_type"] == "download"]),
                "share": len([e for e in access_history if e["access_type"] == "share"])
            },
            top_referrers=self._calculate_top_referrers(access_history),
            access_timeline=self._build_access_timeline(access_history),
            geographic_distribution=self._analyze_geographic_access(access_history)
        )
```

## Advanced Tagging System

Phase 2 implements a comprehensive tagging system:

```python
class FileTaggingService:
    """Advanced file tagging with AI suggestions"""
    
    async def generate_tag_suggestions(
        self,
        file_obj: File
    ) -> List[TagSuggestion]:
        """Generate AI-powered tag suggestions"""
        
        suggestions = []
        
        # Content-based tags from extracted context
        if file_obj.extracted_context:
            content_tags = await self.ai_service.suggest_tags_from_content(
                file_obj.extracted_context
            )
            suggestions.extend(content_tags)
        
        # File type and format tags
        format_tags = self._generate_format_tags(file_obj)
        suggestions.extend(format_tags)
        
        # Organization-specific tags
        org_tags = await self._suggest_organization_tags(
            file_obj.organization_id, file_obj.extracted_context
        )
        suggestions.extend(org_tags)
        
        # Quality and metadata tags
        quality_tags = self._generate_quality_tags(file_obj)
        suggestions.extend(quality_tags)
        
        return suggestions
    
    async def apply_tags(
        self,
        db: AsyncSession,
        file_id: UUID,
        user_tags: List[str],
        user: User
    ) -> File:
        """Apply user-defined tags to file"""
        
        file_obj = await self.file_service.get_file(db, file_id)
        if not file_obj or file_obj.organization_id != user.organization_id:
            raise ValueError("File not accessible")
        
        # Validate and clean tags
        cleaned_tags = [tag.strip().lower() for tag in user_tags if tag.strip()]
        cleaned_tags = list(set(cleaned_tags))  # Remove duplicates
        
        # Store user tags separately from system tags
        file_obj.user_tags = cleaned_tags
        
        # Combine with system tags
        system_tags = file_obj.tags or []
        all_tags = list(set(system_tags + cleaned_tags))
        file_obj.tags = all_tags
        
        await db.commit()
        return file_obj
    
    async def search_by_tags(
        self,
        db: AsyncSession,
        organization_id: UUID,
        tag_query: List[str],
        user: User
    ) -> List[File]:
        """Search files by tags"""
        
        query = select(File).where(
            and_(
                File.organization_id == organization_id,
                File.is_deleted == False
            )
        )
        
        # Add tag filters
        for tag in tag_query:
            query = query.where(File.tags.contains([tag]))
        
        result = await db.execute(query)
        return result.scalars().all()
```

## Quality Assessment System

Phase 2 includes automated file quality assessment:

```python
class FileQualityAssessment:
    """Automated file quality assessment and scoring"""
    
    async def assess_file_quality(self, file_obj: File) -> QualityAssessment:
        """Comprehensive quality assessment"""
        
        quality_score = 1.0
        quality_issues = []
        
        # File integrity checks
        integrity_score, integrity_issues = await self._check_file_integrity(file_obj)
        quality_score *= integrity_score
        quality_issues.extend(integrity_issues)
        
        # Content quality assessment
        if file_obj.extracted_context:
            content_score, content_issues = await self._assess_content_quality(
                file_obj.extracted_context
            )
            quality_score *= content_score
            quality_issues.extend(content_issues)
        
        # Processing quality
        processing_score, processing_issues = self._assess_processing_quality(file_obj)
        quality_score *= processing_score
        quality_issues.extend(processing_issues)
        
        # Update file record
        file_obj.file_quality_score = str(round(quality_score, 2))
        file_obj.quality_issues = quality_issues
        
        return QualityAssessment(
            overall_score=quality_score,
            category_scores={
                "integrity": integrity_score,
                "content": content_score,
                "processing": processing_score
            },
            issues=quality_issues,
            recommendations=self._generate_quality_recommendations(quality_issues)
        )
    
    async def _check_file_integrity(self, file_obj: File) -> Tuple[float, List[str]]:
        """Check file integrity and corruption"""
        issues = []
        score = 1.0
        
        # File size consistency
        if file_obj.file_size <= 0:
            issues.append("Invalid file size")
            score *= 0.5
        
        # MIME type consistency
        if not self._is_mime_type_consistent(file_obj.filename, file_obj.mime_type):
            issues.append("MIME type doesn't match file extension")
            score *= 0.8
        
        # Processing errors
        if file_obj.processing_error:
            issues.append(f"Processing error: {file_obj.processing_error}")
            score *= 0.6
        
        return score, issues
```

## Enhanced API Endpoints

Phase 2 adds several new endpoints:

```python
# Additional endpoints for Phase 2
POST   /api/v1/files/{file_id}/share              # Create public share link
DELETE /api/v1/files/{file_id}/share              # Remove public sharing
GET    /api/v1/files/{file_id}/analytics          # Get file analytics
POST   /api/v1/files/{file_id}/tags               # Apply tags to file
GET    /api/v1/files/search/tags                  # Search files by tags
POST   /api/v1/files/{file_id}/rescan             # Trigger security rescan
GET    /api/v1/files/quarantine                   # List quarantined files
POST   /api/v1/files/quarantine/{file_id}/restore # Restore from quarantine
GET    /public/files/{access_token}               # Public file access
POST   /api/v1/files/upload-url                   # Generate presigned URL
POST   /api/v1/files/chunked-upload               # Chunked upload support
```

## Implementation Timeline

### Phase 2 Tasks (Weeks 5-8)

1. **Week 5: Security Infrastructure**
   - Implement multi-layer malware scanning
   - Build quarantine system
   - Add threat assessment and logging
   - Security event monitoring

2. **Week 6: Public Sharing & Analytics**
   - Create public sharing system
   - Implement access controls and restrictions
   - Build analytics and usage tracking
   - Add comprehensive logging

3. **Week 7: Quality & Tagging Systems**
   - Develop quality assessment engine
   - Implement AI-powered tagging
   - Build search and discovery features
   - Add file recommendations

4. **Week 8: Scale & Performance**
   - Add chunked upload support
   - Implement presigned URL system
   - Performance optimization
   - Load testing and monitoring

## Success Metrics for Phase 2

### Security Metrics
- **Malware Detection Rate**: >99.5% with <0.1% false positives
- **Quarantine Response Time**: <5 seconds for threat isolation
- **Security Event Detection**: 100% logging of security events

### Sharing & Analytics Metrics
- **Public Share Usage**: 25% of files shared publicly within 60 days
- **Analytics Accuracy**: Real-time metrics with <1 minute delay
- **User Engagement**: 40% increase in file interactions

### Quality & Discovery Metrics
- **Quality Assessment Accuracy**: >90% correlation with user ratings
- **Tag Suggestion Adoption**: 60% of AI-suggested tags accepted
- **Search Effectiveness**: 80% of tag searches return relevant results

Phase 2 transforms the basic file attachment system into a comprehensive, secure, and intelligent file management platform with advanced capabilities for modern enterprise needs.