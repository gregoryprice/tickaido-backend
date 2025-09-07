name: "User Avatar Backend Enhancement"
description: |

## Purpose  
Comprehensive PRP for implementing robust backend support for user profile pictures ("avatars"). This feature enables users to upload, update, and display their profile pictures across the platform, including chat, profile management, and user components. The backend must fully support common image formats (.jpg, .jpeg, .png, .heic, .gif, etc.), enforce validation and security, and provide a scalable, maintainable API for avatar management.

## Core Principles
1. **Context is King**: All relevant model fields, API endpoints, and storage options must be documented. Include sample payloads, validation caveats, and error handling descriptions.
2. **Validation Loops**: Provide executable tests for upload, update, retrieval, file type validation, storage, and deletion. Include lints and edge case checks (e.g., oversized files, malformed images).
3. **Progressive Success**: Start with minimal upload/retrieval endpoints and basic format validation. Progress to storage, CDN integration (if any), and additional image formats. Each step must include running and passing tests.
4. **Global Rules**: Adhere to all rules specified in CLAUDE.md, including security, privacy, and audit logging for user data changes.
5. **You Must Test**: Every backend feature must have corresponding tests in the test suite. Run tests before proceeding to the next implementation step.

---

## Goal
Implement a complete user avatar/profile picture backend system that allows users to upload, update, retrieve, and delete their profile pictures with comprehensive validation, security, and error handling.

## Why
- **Business Value**: Enhanced user experience with personalized profile pictures across chat, tickets, and user interfaces
- **Integration**: Seamless avatar display in existing chat system, user profiles, and ticket assignments
- **User Impact**: Professional appearance for support agents and improved user identification in conversations

## What
A secure, validated avatar upload system with the following user-visible behavior:
- Users can upload profile pictures via API endpoints
- Avatars display automatically in chat, user profiles, and ticket interfaces
- Fallback to default avatars when no custom avatar is set
- Secure validation prevents malicious file uploads
- Images are resized/optimized for web display

### Success Criteria
- [ ] Users can upload avatars in common formats (JPG, PNG, GIF, HEIC)
- [ ] System validates file security using multiple validation layers
- [ ] Avatars display in chat interfaces and user profiles
- [ ] API provides proper error handling for edge cases
- [ ] All endpoints are documented in OpenAPI specification
- [ ] Test suite covers upload, validation, retrieval, and deletion flows

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- file: app/models/user.py:185-189
  why: User model already has avatar_url field, understand current structure
  critical: Line 185 shows existing avatar_url column definition
  
- file: app/models/file.py:26-38
  why: FileType enum shows IMAGE type already exists, reuse this pattern
  critical: Existing file validation and processing patterns to follow

- file: app/services/file_service.py:49-108  
  why: Existing file upload implementation with validation patterns
  critical: Follow _detect_file_type() pattern and validation approach

- file: app/schemas/file.py:41-70
  why: File upload request schema with size/type validation patterns
  critical: FileUploadRequest shows validation patterns to mirror

- file: tests/test_services.py:73-99
  why: File service testing patterns with mocks and validation
  critical: Follow existing test structure for new avatar tests

- url: https://fastapi.tiangolo.com/tutorial/request-files/
  why: Official FastAPI file upload documentation
  section: Using UploadFile for avatar uploads

- url: https://pillow.readthedocs.io/en/stable/reference/Image.html
  why: PIL/Pillow for image validation and format checking
  section: Image.verify() for validation and format detection

- url: https://docs.python.org/3/library/imghdr.html  
  why: Python magic number validation for images
  critical: Provides secure format detection beyond MIME type spoofing
```

### Current Codebase Structure
```bash
app/
├── api/v1/              # FastAPI route handlers
├── models/
│   ├── user.py          # User model with avatar_url field (line 185)
│   └── file.py          # File model with image processing
├── schemas/
│   ├── user.py          # User response schemas  
│   └── file.py          # File upload validation schemas
├── services/
│   ├── user_service.py  # User business logic
│   └── file_service.py  # File upload/processing logic
└── tests/
    ├── test_api_endpoints.py  # API endpoint tests
    └── test_services.py       # Service layer tests
```

### Desired Codebase Structure with New Files
```bash
app/
├── api/v1/
│   └── users.py         # NEW: User avatar endpoints (/users/{id}/avatar)
├── models/
│   └── user.py          # EXTEND: Add avatar metadata fields if needed
├── schemas/
│   └── user.py          # EXTEND: Add avatar upload/response schemas
├── services/
│   └── avatar_service.py # NEW: Dedicated avatar processing service
└── tests/
    └── test_avatar_api.py # NEW: Avatar-specific tests
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: FastAPI requires python-multipart for file uploads
# Install with: poetry add python-multipart

# CRITICAL: Use UploadFile not File for larger files (>1MB)
# File() loads entire content into memory, UploadFile streams from disk

# CRITICAL: PIL/Pillow validation patterns
# Always use Image.verify() AND magic number checking
# MIME type headers can be spoofed, magic numbers are more reliable

# CRITICAL: Existing user model avatar_url field (line 185)
# Don't create new fields, use existing avatar_url pattern

# CRITICAL: Follow existing file upload patterns from file_service.py
# Don't reinvent validation, storage, or error handling

# CRITICAL: Existing FileType.IMAGE enum in file.py:29
# Reuse existing file type classification system

# CRITICAL: Current upload directory from settings
# Use self.settings.upload_directory pattern from FileService

# CRITICAL: Authentication required for user-specific endpoints
# Use get_current_active_user dependency pattern
```

## Implementation Blueprint

### Data Models and Structure
```python
# EXTEND app/models/user.py - avatar_url field already exists (line 185)
# CONSIDER: Add avatar metadata fields if needed:
# - avatar_uploaded_at: DateTime (when avatar was last updated)
# - avatar_file_size: Integer (for cleanup/optimization)
# - avatar_mime_type: String (for serving with correct headers)

# EXTEND app/schemas/user.py - Add avatar-specific schemas:
class AvatarUploadRequest(BaseSchema):
    # Follow FileUploadRequest pattern from schemas/file.py:41-70
    pass

class AvatarResponse(BaseSchema):  
    # Standard response with avatar URL and metadata
    pass
```

### List of Tasks (In Order) - WITH MANDATORY TESTING & VALIDATION

⚠️ **CRITICAL RULE: Each task MUST pass ALL validation steps before proceeding to the next task.**

```yaml
Task 1: Create Avatar Service
CREATE app/services/avatar_service.py:
  Implementation:
    - MIRROR pattern from: app/services/file_service.py:37-108
    - MODIFY for avatar-specific validation (image formats only)
    - KEEP error handling and async patterns identical
    - ADD image format validation using PIL and magic numbers
    - ADD thumbnail generation for optimized display

  MANDATORY VALIDATION - Task 1:
    Step 1.1: Syntax Validation
      - RUN: poetry run ruff check app/services/avatar_service.py --fix
      - RUN: poetry run mypy app/services/avatar_service.py
      - REQUIREMENT: Zero errors, zero warnings
      - BLOCKER: Fix all errors before proceeding

    Step 1.2: Import Validation
      - RUN: python -c "from app.services.avatar_service import AvatarService; print('Import successful')"
      - REQUIREMENT: No import errors
      - BLOCKER: Fix import issues before proceeding

    Step 1.3: Unit Tests for Service Layer
      - CREATE: tests/test_avatar_service.py with minimum tests:
        * test_avatar_service_initialization()
        * test_validate_avatar_file_valid_formats()
        * test_validate_avatar_file_invalid_formats()
        * test_validate_image_security_magic_numbers()
        * test_upload_avatar_success_path()
      - RUN: poetry run pytest tests/test_avatar_service.py -v
      - REQUIREMENT: All tests PASS (100% success rate)
      - BLOCKER: Cannot proceed until ALL tests pass

    Step 1.4: Service Integration Test
      - RUN: docker compose up -d postgres redis
      - RUN: poetry run alembic upgrade head
      - RUN: python -c "
        import asyncio
        from app.services.avatar_service import AvatarService
        async def test():
            service = AvatarService()
            print('Service instantiated successfully')
        asyncio.run(test())"
      - REQUIREMENT: No runtime errors
      - BLOCKER: Fix service instantiation before proceeding

  EXIT CRITERIA FOR TASK 1:
    ✅ All syntax validation passes
    ✅ All unit tests pass
    ✅ Service instantiates without errors
    ✅ Code follows existing patterns from file_service.py

Task 2: Extend User Schemas  
MODIFY app/schemas/user.py:
  Implementation:
    - FIND pattern: existing user response schemas
    - ADD AvatarUploadRequest class following FileUploadRequest pattern
    - ADD AvatarResponse class with avatar URL and metadata
    - PRESERVE existing user schema structure

  MANDATORY VALIDATION - Task 2:
    Step 2.1: Schema Syntax Validation
      - RUN: poetry run ruff check app/schemas/user.py --fix
      - RUN: poetry run mypy app/schemas/user.py
      - REQUIREMENT: Zero errors, zero warnings
      - BLOCKER: Fix all errors before proceeding

    Step 2.2: Schema Import Validation
      - RUN: python -c "
        from app.schemas.user import AvatarUploadRequest, AvatarResponse
        print('Schema imports successful')"
      - REQUIREMENT: No import errors
      - BLOCKER: Fix import issues before proceeding

    Step 2.3: Schema Validation Tests
      - CREATE: tests/test_avatar_schemas.py with tests:
        * test_avatar_upload_request_validation()
        * test_avatar_upload_request_invalid_data()
        * test_avatar_response_serialization()
        * test_avatar_response_fields_present()
      - RUN: poetry run pytest tests/test_avatar_schemas.py -v
      - REQUIREMENT: All tests PASS (100% success rate)
      - BLOCKER: Cannot proceed until ALL tests pass

    Step 2.4: Pydantic Model Validation
      - RUN: python -c "
        from app.schemas.user import AvatarUploadRequest, AvatarResponse
        # Test valid data
        req = AvatarUploadRequest()
        resp = AvatarResponse(avatar_url='http://test.com/avatar.jpg')
        print('Schema validation successful')"
      - REQUIREMENT: No validation errors
      - BLOCKER: Fix schema definitions before proceeding

  EXIT CRITERIA FOR TASK 2:
    ✅ All schema validation passes
    ✅ All Pydantic model tests pass
    ✅ Schemas follow existing patterns
    ✅ Import/export works correctly

Task 3: Create Avatar API Endpoints
CREATE app/api/v1/users.py:
  Implementation:
    - MIRROR pattern from: app/api/v1/tickets.py (router setup)
    - CREATE endpoints: POST/GET/DELETE /users/{id}/avatar
    - USE get_current_active_user dependency for auth
    - FOLLOW existing error handling patterns

  MANDATORY VALIDATION - Task 3:
    Step 3.1: API Syntax Validation
      - RUN: poetry run ruff check app/api/v1/users.py --fix
      - RUN: poetry run mypy app/api/v1/users.py
      - REQUIREMENT: Zero errors, zero warnings
      - BLOCKER: Fix all errors before proceeding

    Step 3.2: FastAPI Route Validation
      - RUN: python -c "
        from app.api.v1.users import router
        print(f'Router loaded with {len(router.routes)} routes')
        for route in router.routes:
            print(f'Route: {route.methods} {route.path}')"
      - REQUIREMENT: All expected routes present
      - BLOCKER: Fix route definitions before proceeding

    Step 3.3: API Unit Tests
      - CREATE: tests/test_avatar_api_endpoints.py with tests:
        * test_upload_avatar_success()
        * test_upload_avatar_unauthorized()
        * test_upload_avatar_forbidden()
        * test_upload_avatar_invalid_format()
        * test_upload_avatar_oversized()
        * test_get_avatar_success()
        * test_get_avatar_not_found()
        * test_delete_avatar_success()
        * test_delete_avatar_unauthorized()
      - RUN: poetry run pytest tests/test_avatar_api_endpoints.py -v
      - REQUIREMENT: All tests PASS (100% success rate)
      - BLOCKER: Cannot proceed until ALL tests pass

    Step 3.4: OpenAPI Schema Validation
      - RUN: python -c "
        from app.main import app
        openapi = app.openapi()
        paths = openapi.get('paths', {})
        avatar_paths = [p for p in paths.keys() if 'avatar' in p]
        print(f'Avatar endpoints in OpenAPI: {avatar_paths}')
        assert len(avatar_paths) > 0, 'No avatar endpoints found'"
      - REQUIREMENT: Avatar endpoints appear in OpenAPI schema
      - BLOCKER: Fix OpenAPI integration before proceeding

  EXIT CRITERIA FOR TASK 3:
    ✅ All API endpoint tests pass
    ✅ All authentication/authorization tests pass
    ✅ OpenAPI schema includes avatar endpoints
    ✅ Error handling follows existing patterns

Task 4: Database Migration (if needed)
MODIFY alembic migration:
  Implementation:
    - CHECK if additional avatar metadata fields needed
    - CREATE migration if extending user model
    - TEST migration runs successfully

  MANDATORY VALIDATION - Task 4:
    Step 4.1: Migration Generation Test
      - RUN: poetry run alembic revision --autogenerate -m "Add avatar metadata fields" --dry-run
      - REQUIREMENT: Check if migration is needed
      - ACTION: Only create migration if new fields required

    Step 4.2: Migration Syntax Validation (if created)
      - RUN: poetry run alembic check
      - RUN: poetry run ruff check alembic/versions/*.py
      - REQUIREMENT: No syntax errors in migration
      - BLOCKER: Fix migration syntax before proceeding

    Step 4.3: Migration Forward Test
      - RUN: docker compose up -d postgres
      - RUN: poetry run alembic upgrade head
      - REQUIREMENT: Migration applies successfully
      - BLOCKER: Fix migration issues before proceeding

    Step 4.4: Migration Rollback Test
      - RUN: poetry run alembic downgrade -1
      - RUN: poetry run alembic upgrade head
      - REQUIREMENT: Migration can rollback and reapply
      - BLOCKER: Fix migration reversibility before proceeding

    Step 4.5: Database State Validation
      - RUN: python -c "
        import asyncio
        from app.database import get_db_session
        from app.models.user import User
        async def test():
            async with get_db_session() as session:
                # Check if user model has expected fields
                user_fields = [field.name for field in User.__table__.columns]
                print(f'User model fields: {user_fields}')
                assert 'avatar_url' in user_fields, 'avatar_url field missing'
        asyncio.run(test())"
      - REQUIREMENT: User model has correct fields
      - BLOCKER: Fix model structure before proceeding

  EXIT CRITERIA FOR TASK 4:
    ✅ Database migration (if needed) applies successfully
    ✅ Migration can rollback cleanly
    ✅ User model has all required fields
    ✅ Database constraints are correct

Task 5: Integrate with Main Router
MODIFY app/main.py:
  Implementation:
    - FIND pattern: existing router inclusions
    - ADD users router to main app
    - PRESERVE existing middleware and dependency patterns

  MANDATORY VALIDATION - Task 5:
    Step 5.1: Main App Syntax Validation
      - RUN: poetry run ruff check app/main.py --fix
      - RUN: poetry run mypy app/main.py
      - REQUIREMENT: Zero errors, zero warnings
      - BLOCKER: Fix all errors before proceeding

    Step 5.2: Application Startup Test
      - RUN: python -c "
        from app.main import app
        print('App imported successfully')
        print(f'App routes: {len(app.routes)}')
        route_paths = [getattr(route, 'path', 'N/A') for route in app.routes]
        avatar_routes = [path for path in route_paths if 'avatar' in str(path)]
        print(f'Avatar routes found: {avatar_routes}')"
      - REQUIREMENT: App starts and includes avatar routes
      - BLOCKER: Fix application integration before proceeding

    Step 5.3: Router Integration Tests
      - RUN: poetry run pytest tests/test_main_app.py -v -k "avatar"
      - CREATE test if it doesn't exist:
        * test_avatar_routes_included()
        * test_avatar_endpoints_accessible()
      - REQUIREMENT: All integration tests PASS
      - BLOCKER: Cannot proceed until ALL tests pass

    Step 5.4: Full Application Test
      - RUN: docker compose up -d
      - RUN: curl -f http://localhost:8000/docs
      - REQUIREMENT: FastAPI docs load successfully
      - REQUIREMENT: Avatar endpoints visible in Swagger UI
      - BLOCKER: Fix application startup before proceeding

  EXIT CRITERIA FOR TASK 5:
    ✅ Main application starts successfully
    ✅ Avatar routes are registered
    ✅ Integration tests pass
    ✅ Swagger UI shows avatar endpoints

Task 6: Create Comprehensive Tests
CREATE tests/test_avatar_api.py:
  Implementation:
    - MIRROR pattern from: tests/test_services.py:73-99
    - TEST upload valid/invalid formats, oversized files
    - TEST retrieval with correct MIME types
    - TEST deletion and security edge cases
    - FOLLOW existing mock and AsyncMock patterns

  MANDATORY VALIDATION - Task 6:
    Step 6.1: Test File Syntax Validation
      - RUN: poetry run ruff check tests/test_avatar_api.py --fix
      - RUN: poetry run mypy tests/test_avatar_api.py
      - REQUIREMENT: Zero errors, zero warnings
      - BLOCKER: Fix all errors before proceeding

    Step 6.2: Individual Test Execution
      - RUN: poetry run pytest tests/test_avatar_api.py::test_upload_avatar_valid_formats -v
      - RUN: poetry run pytest tests/test_avatar_api.py::test_upload_avatar_invalid_format -v
      - RUN: poetry run pytest tests/test_avatar_api.py::test_upload_avatar_oversized -v
      - RUN: poetry run pytest tests/test_avatar_api.py::test_upload_avatar_malicious_file -v
      - RUN: poetry run pytest tests/test_avatar_api.py::test_avatar_retrieval -v
      - RUN: poetry run pytest tests/test_avatar_api.py::test_avatar_deletion -v
      - RUN: poetry run pytest tests/test_avatar_api.py::test_avatar_permission_checks -v
      - REQUIREMENT: Each test PASSES individually
      - BLOCKER: Fix failing tests before proceeding

    Step 6.3: Complete Test Suite Execution
      - RUN: poetry run pytest tests/test_avatar_api.py -v
      - REQUIREMENT: 100% test success rate
      - REQUIREMENT: Minimum 80% code coverage for avatar module
      - RUN: poetry run pytest tests/test_avatar_api.py --cov=app.services.avatar_service --cov=app.api.v1.users --cov-report=term-missing
      - BLOCKER: Cannot proceed with <80% coverage or any failing tests

    Step 6.4: Integration Test with Real Files
      - CREATE: tests/fixtures/test_images/ with:
        * valid_avatar.jpg (small JPEG)
        * valid_avatar.png (small PNG)
        * invalid_file.pdf (non-image)
        * oversized_image.jpg (>5MB file)
        * malicious_file.jpg.pdf (spoofed extension)
      - RUN: poetry run pytest tests/test_avatar_api.py::test_real_file_upload -v
      - REQUIREMENT: Real file handling works correctly
      - BLOCKER: Fix file processing before proceeding

    Step 6.5: End-to-End API Test
      - RUN: docker compose up -d
      - RUN: ./tests/scripts/test_avatar_e2e.sh (create this script)
      - Script should:
        * Create test user
        * Upload avatar
        * Retrieve avatar
        * Delete avatar
        * Verify each step
      - REQUIREMENT: E2E test completes successfully
      - BLOCKER: Fix E2E issues before proceeding

  EXIT CRITERIA FOR TASK 6:
    ✅ All unit tests pass (100% success rate)
    ✅ Code coverage ≥80% for avatar modules
    ✅ Integration tests with real files pass
    ✅ End-to-end API test completes successfully
    ✅ Security validation tests pass

Task 7: Update OpenAPI Documentation
MODIFY openapi.yaml:
  Implementation:
    - ADD avatar endpoint specifications
    - INCLUDE example requests/responses
    - DOCUMENT error codes and validation rules

  MANDATORY VALIDATION - Task 7:
    Step 7.1: OpenAPI Syntax Validation
      - RUN: poetry run python -c "
        import yaml
        with open('openapi.yaml', 'r') as f:
            spec = yaml.safe_load(f)
        print('OpenAPI YAML syntax valid')"
      - REQUIREMENT: Valid YAML syntax
      - BLOCKER: Fix YAML syntax errors before proceeding

    Step 7.2: OpenAPI Schema Validation
      - RUN: pip install openapi-spec-validator
      - RUN: python -c "
        from openapi_spec_validator import validate_spec
        import yaml
        with open('openapi.yaml', 'r') as f:
            spec = yaml.safe_load(f)
        validate_spec(spec)
        print('OpenAPI schema valid')"
      - REQUIREMENT: Valid OpenAPI 3.0 specification
      - BLOCKER: Fix schema validation errors before proceeding

    Step 7.3: Avatar Endpoints Documentation Test
      - RUN: python -c "
        import yaml
        with open('openapi.yaml', 'r') as f:
            spec = yaml.safe_load(f)
        paths = spec.get('paths', {})
        avatar_paths = [p for p in paths.keys() if 'avatar' in p]
        print(f'Avatar endpoints documented: {avatar_paths}')
        required_paths = ['/users/{user_id}/avatar']
        for req_path in required_paths:
            found = any(req_path in path for path in avatar_paths)
            assert found, f'Missing required path: {req_path}'
        print('All required avatar endpoints documented')"
      - REQUIREMENT: All avatar endpoints documented
      - BLOCKER: Add missing endpoint documentation before proceeding

    Step 7.4: Documentation Completeness Test
      - RUN: python -c "
        import yaml
        with open('openapi.yaml', 'r') as f:
            spec = yaml.safe_load(f)
        avatar_path = None
        for path, methods in spec['paths'].items():
            if 'avatar' in path:
                avatar_path = path
                break
        assert avatar_path, 'No avatar path found'
        
        # Check POST method
        post_method = spec['paths'][avatar_path].get('post', {})
        assert 'requestBody' in post_method, 'POST missing requestBody'
        assert 'responses' in post_method, 'POST missing responses'
        assert '200' in post_method['responses'], 'POST missing 200 response'
        assert '400' in post_method['responses'], 'POST missing 400 response'
        
        print('Avatar endpoint documentation complete')"
      - REQUIREMENT: Complete request/response documentation
      - BLOCKER: Add missing documentation before proceeding

    Step 7.5: Documentation Example Test
      - RUN: python -c "
        import yaml
        with open('openapi.yaml', 'r') as f:
            spec = yaml.safe_load(f)
        
        # Find avatar POST endpoint
        avatar_post = None
        for path, methods in spec['paths'].items():
            if 'avatar' in path and 'post' in methods:
                avatar_post = methods['post']
                break
        
        assert avatar_post, 'Avatar POST endpoint not found'
        
        # Check for examples
        responses = avatar_post.get('responses', {})
        success_response = responses.get('200', {})
        assert 'content' in success_response, 'Missing response content'
        
        content = success_response['content']
        json_content = content.get('application/json', {})
        assert 'example' in json_content or 'examples' in json_content, 'Missing response examples'
        
        print('Avatar endpoint examples documented')"
      - REQUIREMENT: Request/response examples present
      - BLOCKER: Add missing examples before proceeding

  EXIT CRITERIA FOR TASK 7:
    ✅ OpenAPI YAML syntax is valid
    ✅ OpenAPI schema passes specification validation
    ✅ All avatar endpoints are documented
    ✅ Request/response schemas are complete
    ✅ Examples are provided for all endpoints

Task 8: Regenerate OpenAPI Specification and Update Postman Collection
REGENERATE openapi.yaml and UPDATE Postman collection:
  Implementation:
    - REGENERATE OpenAPI specification from FastAPI application
    - VALIDATE generated specification includes avatar endpoints
    - UPDATE Postman collection with new avatar endpoints
    - TEST Postman collection requests work correctly

  MANDATORY VALIDATION - Task 8:
    Step 8.1: OpenAPI Specification Regeneration
      - RUN: python -c "
        from app.main import app
        import json
        openapi_spec = app.openapi()
        with open('docs/openapi.yaml', 'w') as f:
            import yaml
            yaml.dump(openapi_spec, f, default_flow_style=False)
        print('OpenAPI specification regenerated')"
      - REQUIREMENT: Specification file updated successfully
      - BLOCKER: Fix generation issues before proceeding

    Step 8.2: Avatar Endpoints Verification in Generated Spec
      - RUN: python -c "
        import yaml
        with open('docs/openapi.yaml', 'r') as f:
            spec = yaml.safe_load(f)
        paths = spec.get('paths', {})
        avatar_endpoints = [p for p in paths.keys() if 'avatar' in p.lower()]
        print(f'Avatar endpoints found: {avatar_endpoints}')
        
        required_endpoints = ['/api/v1/users/{user_id}/avatar']
        missing_endpoints = []
        for req_endpoint in required_endpoints:
            found = any(req_endpoint in path for path in avatar_endpoints)
            if not found:
                missing_endpoints.append(req_endpoint)
        
        if missing_endpoints:
            raise Exception(f'Missing avatar endpoints: {missing_endpoints}')
        
        # Verify HTTP methods for avatar endpoint
        avatar_path = None
        for path in paths.keys():
            if 'avatar' in path.lower():
                avatar_path = path
                break
        
        if avatar_path:
            methods = list(paths[avatar_path].keys())
            print(f'Avatar endpoint methods: {methods}')
            required_methods = ['post', 'get', 'delete']
            missing_methods = [m for m in required_methods if m not in methods]
            if missing_methods:
                raise Exception(f'Missing HTTP methods: {missing_methods}')
        
        print('✅ Avatar endpoints properly included in OpenAPI spec')"
      - REQUIREMENT: All avatar endpoints and methods present
      - BLOCKER: Fix missing endpoints before proceeding

    Step 8.3: Postman Collection Update
      - CHECK: If docs/postman/ directory exists with collection files
      - CREATE OR UPDATE: Postman collection with avatar endpoints
      - INCLUDE: Example requests for:
        * POST /users/{user_id}/avatar (with file upload)
        * GET /users/{user_id}/avatar
        * DELETE /users/{user_id}/avatar
      - ADD: Environment variables for user_id and auth tokens
      - CREATE: docs/postman/avatar_endpoints.postman_collection.json

    Step 8.4: Postman Collection Validation
      - RUN: python -c "
        import json
        import os
        postman_file = 'docs/postman/avatar_endpoints.postman_collection.json'
        if os.path.exists(postman_file):
            with open(postman_file, 'r') as f:
                collection = json.load(f)
            
            # Verify collection structure
            assert 'info' in collection, 'Missing collection info'
            assert 'item' in collection, 'Missing collection items'
            
            # Count avatar-related requests
            items = collection.get('item', [])
            avatar_requests = []
            for item in items:
                if 'avatar' in item.get('name', '').lower():
                    avatar_requests.append(item.get('name'))
            
            print(f'Avatar requests in collection: {avatar_requests}')
            
            required_requests = ['Upload Avatar', 'Get Avatar', 'Delete Avatar']
            for req in required_requests:
                found = any(req.lower() in ar.lower() for ar in avatar_requests)
                if not found:
                    print(f'⚠️  Consider adding request: {req}')
            
            print('✅ Postman collection structure validated')
        else:
            print('ℹ️  No Postman collection found - creating basic structure recommended')"
      - REQUIREMENT: Postman collection has valid structure
      - ACTION: Create collection if it doesn't exist

    Step 8.5: Documentation Sync Verification
      - RUN: python -c "
        import yaml
        import json
        
        # Compare OpenAPI spec with current FastAPI app
        from app.main import app
        live_spec = app.openapi()
        
        with open('docs/openapi.yaml', 'r') as f:
            file_spec = yaml.safe_load(f)
        
        # Check if avatar paths match
        live_paths = set(live_spec.get('paths', {}).keys())
        file_paths = set(file_spec.get('paths', {}).keys())
        
        avatar_paths_live = {p for p in live_paths if 'avatar' in p.lower()}
        avatar_paths_file = {p for p in file_paths if 'avatar' in p.lower()}
        
        if avatar_paths_live != avatar_paths_file:
            print(f'⚠️  Path mismatch:')
            print(f'   Live: {avatar_paths_live}')
            print(f'   File: {avatar_paths_file}')
            raise Exception('OpenAPI spec out of sync with application')
        
        print('✅ OpenAPI specification is in sync with application')
        
        # Verify info section is updated
        info = file_spec.get('info', {})
        print(f'API Title: {info.get(\"title\", \"N/A\")}')
        print(f'API Version: {info.get(\"version\", \"N/A\")}')
        print('✅ Documentation sync verified')"
      - REQUIREMENT: Generated spec matches live application
      - BLOCKER: Fix sync issues before proceeding

  EXIT CRITERIA FOR TASK 8:
    ✅ OpenAPI specification regenerated from live FastAPI application
    ✅ Avatar endpoints present in generated specification
    ✅ All HTTP methods (POST/GET/DELETE) documented for avatar endpoints
    ✅ Postman collection updated with avatar endpoint examples
    ✅ Generated specification matches live application routes
    ✅ Documentation and code are synchronized
```

### Task 1 Pseudocode - Avatar Service
```python
# app/services/avatar_service.py
class AvatarService:
    def __init__(self):
        # PATTERN: Follow FileService initialization (file_service.py:40-47)
        self.settings = get_settings()
        self.avatar_directory = Path(self.settings.upload_directory) / "avatars"
        self.max_avatar_size = 5 * 1024 * 1024  # 5MB limit
        self.allowed_formats = ['image/jpeg', 'image/png', 'image/gif', 'image/heic']
        
    async def upload_avatar(self, user_id: UUID, file: UploadFile) -> str:
        # PATTERN: Validation first (file_service.py:68-74)
        await self._validate_avatar_file(file)
        
        # CRITICAL: Use magic number validation + PIL verification
        content = await file.read()
        self._validate_image_security(content)
        
        # PATTERN: Generate unique filename (file_service.py:77-80)
        file_path = await self._save_avatar_file(user_id, content, file.filename)
        
        # PATTERN: Update database (follow existing user update pattern)
        avatar_url = self._generate_avatar_url(file_path)
        await self._update_user_avatar_url(user_id, avatar_url)
        
        return avatar_url
        
    def _validate_image_security(self, content: bytes):
        # CRITICAL: Multiple validation layers
        # 1. Magic number check using imghdr or python-magic
        # 2. PIL format validation with Image.verify()
        # 3. Check for image bombs (PIL MAX_IMAGE_PIXELS)
        pass
```

### Task 3 Pseudocode - API Endpoints  
```python
# app/api/v1/users.py
router = APIRouter(prefix="/users")

@router.post("/{user_id}/avatar")
async def upload_avatar(
    user_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    # PATTERN: Auth check (tickets.py permission patterns)
    if user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # PATTERN: Service call with error handling
    try:
        avatar_url = await avatar_service.upload_avatar(user_id, file)
        return {"avatar_url": avatar_url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{user_id}/avatar")
async def get_avatar(user_id: UUID, db: AsyncSession = Depends(get_db_session)):
    # PATTERN: File serving with correct headers
    # Return image file with proper Content-Type
    pass

@router.delete("/{user_id}/avatar") 
async def delete_avatar(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    # PATTERN: Auth check + soft delete following file patterns
    pass
```

### Integration Points
```yaml
DATABASE:
  - existing: "avatar_url field in users table (line 185-189)"
  - consider: "avatar_uploaded_at, avatar_file_size metadata fields"
  
CONFIG:
  - add to: app/config/settings.py
  - pattern: "AVATAR_MAX_SIZE = int(os.getenv('AVATAR_MAX_SIZE', '5242880'))"  # 5MB
  - pattern: "AVATAR_ALLOWED_FORMATS = ['image/jpeg', 'image/png', 'image/gif']"
  
ROUTES:
  - add to: app/main.py
  - pattern: "app.include_router(users_router, prefix='/api/v1', tags=['users'])"
  
STORAGE:
  - extend: "upload_directory/avatars/ subdirectory"
  - pattern: "use existing settings.upload_directory base path"
```

## COMPREHENSIVE VALIDATION FRAMEWORK

⚠️ **MANDATORY TESTING RULES:**
1. **No Implementation Without Tests**: Every function must have corresponding unit tests
2. **No Progression Without Passing Tests**: All tests must pass before moving to next task  
3. **100% Test Success Rate Required**: No failing tests allowed in any step
4. **Real Integration Testing**: Manual API calls must succeed before completion
5. **Security Validation Mandatory**: Malicious file handling must be tested

---

### VALIDATION LEVEL 1: Pre-Implementation Setup

#### Step 0.1: Test Environment Validation
```bash
# Ensure testing dependencies are installed
poetry install --with dev
poetry add pytest-cov python-multipart pillow python-magic

# Verify test environment
poetry run pytest --version
poetry run pytest tests/test_simple.py -v

# BLOCKER: Must pass before any implementation begins
```

#### Step 0.2: Create Test Fixtures Directory
```bash
# Create test fixtures structure
mkdir -p tests/fixtures/images
mkdir -p tests/scripts

# Download test images or create them programmatically:
# - valid_avatar.jpg (100KB JPEG)
# - valid_avatar.png (50KB PNG)  
# - valid_avatar.gif (80KB GIF)
# - invalid_file.pdf (small PDF file)
# - oversized_image.jpg (6MB JPEG - over limit)
# - malicious_file.jpg.exe (executable with .jpg extension)

# BLOCKER: Test fixtures must exist before testing
```

---

### VALIDATION LEVEL 2: Per-Task Testing Requirements

#### For EVERY Task (1-7): Mandatory Test Sequence
```bash
# 2A: Syntax and Type Checking (MUST be clean)
poetry run ruff check [file_path] --fix
poetry run mypy [file_path] --strict
# REQUIREMENT: Zero errors, zero warnings

# 2B: Import Testing (MUST succeed)  
python -c "import [module_path]; print('✅ Import successful')"
# REQUIREMENT: No ImportError, ModuleNotFoundError

# 2C: Unit Test Execution (MUST pass 100%)
poetry run pytest tests/test_[module]_*.py -v --tb=short
# REQUIREMENT: All tests PASSED, no FAILED, no SKIPPED allowed

# 2D: Code Coverage Analysis (MUST meet threshold)
poetry run pytest tests/test_[module]_*.py --cov=[module_path] --cov-report=term-missing --cov-fail-under=80
# REQUIREMENT: Minimum 80% code coverage for new modules

# 2E: Integration Testing (MUST validate real behavior)
# Task-specific integration commands (see individual task sections)
```

---

### VALIDATION LEVEL 3: Security-First Testing

#### Step 3.1: File Upload Security Tests
```python
# MANDATORY tests in tests/test_avatar_security.py

def test_malicious_file_rejection():
    """CRITICAL: Test rejection of files with spoofed extensions"""
    # Test: file.jpg that's actually a PDF (magic number mismatch)
    # Test: file.png that's actually an executable
    # Test: file.gif with embedded malicious scripts
    # REQUIREMENT: All malicious files REJECTED with 400 status
    
def test_oversized_file_protection():  
    """CRITICAL: Test rejection of files exceeding size limits"""
    # Test: 10MB JPEG file (over 5MB limit)
    # Test: 50MB PNG file (extreme oversize)
    # REQUIREMENT: Files rejected with 413 status code

def test_image_bomb_protection():
    """CRITICAL: Test protection against decompression bombs"""
    # Test: Small file that expands to huge dimensions (10000x10000px)
    # Test: GIF with excessive frame count 
    # REQUIREMENT: Files rejected or safely processed

def test_path_traversal_protection():
    """CRITICAL: Test filename sanitization"""
    # Test: filename="../../../etc/passwd"  
    # Test: filename="..\\..\\windows\\system32\\config"
    # REQUIREMENT: Filenames sanitized, no directory traversal

def test_mime_type_spoofing_detection():
    """CRITICAL: Test magic number validation"""
    # Test: Content-Type: image/jpeg with PDF magic number
    # Test: Content-Type: image/png with executable magic number
    # REQUIREMENT: Magic number validation catches spoofing
```

#### Step 3.2: Authentication & Authorization Security Tests  
```python
# MANDATORY tests in tests/test_avatar_auth.py

def test_unauthorized_upload_rejected():
    """CRITICAL: Test upload without JWT token"""
    # Test: POST /users/{id}/avatar without Authorization header
    # REQUIREMENT: 401 Unauthorized response

def test_forbidden_cross_user_access():
    """CRITICAL: Test user A cannot modify user B's avatar"""  
    # Test: User A tries to upload avatar for User B
    # Test: Non-admin user tries to modify admin avatar
    # REQUIREMENT: 403 Forbidden response

def test_jwt_token_validation():
    """CRITICAL: Test JWT token integrity"""
    # Test: Expired JWT token
    # Test: Malformed JWT token  
    # Test: JWT token with wrong signature
    # REQUIREMENT: All invalid tokens rejected with 401

def test_admin_privilege_escalation():
    """CRITICAL: Test admin-only operations are protected"""
    # Test: Regular user cannot delete other users' avatars
    # Test: Admin can perform cross-user operations
    # REQUIREMENT: Privilege boundaries enforced
```

---

### VALIDATION LEVEL 4: End-to-End Integration Testing

#### Step 4.1: Complete API Flow Test Script
```bash
#!/bin/bash
# tests/scripts/test_avatar_e2e.sh

set -e  # Exit on any error

echo "🚀 Starting Avatar API E2E Test"

# Start services
docker compose up -d postgres redis app
sleep 10  # Wait for services

# Health check
curl -f http://localhost:8000/health || (echo "❌ Service not healthy" && exit 1)

# Test user registration/login
USER_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123","full_name":"Test User"}')

USER_ID=$(echo $USER_RESPONSE | jq -r '.user.id')
ACCESS_TOKEN=$(echo $USER_RESPONSE | jq -r '.access_token')

echo "✅ User created: $USER_ID"

# Test avatar upload
UPLOAD_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/users/$USER_ID/avatar" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@tests/fixtures/images/valid_avatar.jpg")

AVATAR_URL=$(echo $UPLOAD_RESPONSE | jq -r '.avatar_url')
echo "✅ Avatar uploaded: $AVATAR_URL"

# Test avatar retrieval
curl -f -X GET "http://localhost:8000/api/v1/users/$USER_ID/avatar" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -o /tmp/downloaded_avatar.jpg

echo "✅ Avatar downloaded successfully"

# Test avatar deletion
curl -f -X DELETE "http://localhost:8000/api/v1/users/$USER_ID/avatar" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

echo "✅ Avatar deleted successfully"

# Test avatar not found after deletion
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  "http://localhost:8000/api/v1/users/$USER_ID/avatar")

if [ "$HTTP_STATUS" = "404" ]; then
    echo "✅ Avatar properly removed (404 response)"
else
    echo "❌ Avatar should return 404 after deletion, got $HTTP_STATUS"
    exit 1
fi

echo "🎉 All E2E tests passed!"

# Cleanup
docker compose down
```

#### Step 4.2: Performance & Load Testing
```bash
# MANDATORY performance validation before completion

# Test concurrent uploads (simulate multiple users)
echo "🔄 Testing concurrent avatar uploads..."
for i in {1..10}; do
  curl -X POST "http://localhost:8000/api/v1/users/$USER_ID/avatar" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -F "file=@tests/fixtures/images/valid_avatar.jpg" &
done
wait

# Test file size limits
echo "🔍 Testing file size validation..."
curl -X POST "http://localhost:8000/api/v1/users/$USER_ID/avatar" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@tests/fixtures/images/oversized_image.jpg" \
  --max-time 30

# REQUIREMENT: Should reject with 413 status within 30 seconds
```

---

### VALIDATION LEVEL 5: Final Deployment Readiness

#### Step 5.1: Full Test Suite Execution
```bash
# MUST pass before considering feature complete
poetry run pytest tests/ -v --cov=app --cov-report=html --cov-fail-under=85

# REQUIREMENTS:
# - All tests PASS (100% success rate)
# - Code coverage ≥85% overall
# - No security vulnerabilities detected
# - Performance benchmarks met
```

#### Step 5.2: Manual Production-Like Testing
```bash
# Test in production-like environment
export ENVIRONMENT=production
docker compose -f docker-compose.prod.yml up -d

# Run complete test suite against production build
./tests/scripts/test_avatar_e2e.sh

# Test with real image files from different sources:
# - Photos from iPhone/Android devices  
# - Images downloaded from web
# - Screenshots from different OS
# - Images with EXIF data
# - Animated GIFs

# REQUIREMENT: All real-world files handled correctly
```

---

### FAILURE HANDLING & DEBUGGING

#### When Tests Fail:
```bash
# 1. Get detailed error information
poetry run pytest tests/test_failing.py -v --tb=long --capture=no

# 2. Run specific failing test in isolation
poetry run pytest tests/test_failing.py::test_specific_function -s

# 3. Enable debug logging
export LOG_LEVEL=DEBUG
poetry run pytest tests/test_failing.py -s --log-cli-level=DEBUG

# 4. Check database state
docker exec -it postgres_container psql -U user -d ai_tickets -c "SELECT * FROM users;"

# 5. Inspect uploaded files
ls -la uploads/avatars/
file uploads/avatars/*

# RULE: Fix root cause, don't mask symptoms
# RULE: Re-run all tests after fixes
# RULE: Document recurring issues and their solutions
```

#### Exit Criteria for COMPLETE FEATURE:
```
✅ All 7 tasks completed with 100% test success
✅ Security tests pass (malicious file handling)
✅ Performance tests meet requirements
✅ End-to-end integration works correctly
✅ Code coverage ≥85% for avatar modules
✅ OpenAPI documentation complete and valid
✅ Production deployment test successful
✅ Manual testing with real files successful
✅ Zero known security vulnerabilities
✅ Error handling covers all edge cases
```

**⚠️ ABSOLUTE REQUIREMENT: Any failing test is a BLOCKER. Feature is not complete until ALL tests pass.**

## FINAL VALIDATION CHECKLIST - MUST BE 100% COMPLETE

### ✅ TASK COMPLETION VERIFICATION
- [ ] **Task 1 COMPLETE**: Avatar service created and ALL unit tests pass
- [ ] **Task 2 COMPLETE**: User schemas extended and ALL schema tests pass  
- [ ] **Task 3 COMPLETE**: API endpoints created and ALL endpoint tests pass
- [ ] **Task 4 COMPLETE**: Database migration (if needed) and ALL migration tests pass
- [ ] **Task 5 COMPLETE**: Main router integration and ALL integration tests pass
- [ ] **Task 6 COMPLETE**: Comprehensive tests created and ALL tests pass
- [ ] **Task 7 COMPLETE**: OpenAPI documentation updated and ALL validation tests pass
- [ ] **Task 8 COMPLETE**: OpenAPI specification regenerated and Postman collection updated

### ✅ CODE QUALITY VERIFICATION
- [ ] **Zero Syntax Errors**: `poetry run ruff check app/ --fix` (no remaining errors)
- [ ] **Zero Type Errors**: `poetry run mypy app/ --strict` (no type issues)
- [ ] **Code Coverage ≥85%**: `poetry run pytest tests/ --cov=app --cov-fail-under=85`
- [ ] **All Tests Pass 100%**: `poetry run pytest tests/ -v` (no FAILED, no SKIPPED)

### ✅ SECURITY VALIDATION VERIFICATION  
- [ ] **Malicious File Rejection**: Tests confirm spoofed files are rejected
- [ ] **File Size Limits**: Tests confirm oversized files (>5MB) are rejected
- [ ] **Path Traversal Protection**: Tests confirm filename sanitization works
- [ ] **MIME Type Validation**: Tests confirm magic number checking works
- [ ] **Authentication Required**: Tests confirm JWT token requirement
- [ ] **Authorization Enforced**: Tests confirm cross-user access is blocked

### ✅ API FUNCTIONALITY VERIFICATION
- [ ] **Avatar Upload Success**: Manual test with valid JPEG/PNG succeeds
- [ ] **Avatar Retrieval Success**: Manual test downloads correct image with proper headers
- [ ] **Avatar Deletion Success**: Manual test removes avatar and updates database
- [ ] **Error Handling Complete**: All error codes (400, 401, 403, 404, 413, 422) tested
- [ ] **OpenAPI Integration**: Avatar endpoints visible in Swagger UI at /docs

### ✅ INTEGRATION VERIFICATION
- [ ] **Database Integration**: User model avatar_url field properly updated
- [ ] **File Storage**: Avatar files saved to correct directory with proper naming
- [ ] **Service Integration**: Avatar service integrates cleanly with existing patterns
- [ ] **Router Integration**: Users router properly included in main application
- [ ] **Middleware Compatibility**: Avatar endpoints work with existing auth middleware

### ✅ END-TO-END VERIFICATION
- [ ] **E2E Script Success**: `./tests/scripts/test_avatar_e2e.sh` completes without errors
- [ ] **Docker Environment**: Avatar functionality works in containerized environment
- [ ] **Real File Testing**: Manual tests with actual photos/images from devices
- [ ] **Performance Testing**: Concurrent upload test handles multiple users
- [ ] **Production-Like Testing**: Feature works in production configuration

### ✅ DOCUMENTATION VERIFICATION
- [ ] **OpenAPI Complete**: All avatar endpoints documented with examples
- [ ] **Schema Validation**: OpenAPI spec passes validation tools
- [ ] **Request/Response Examples**: All endpoints have proper example payloads
- [ ] **Error Code Documentation**: All error scenarios documented
- [ ] **OpenAPI Regenerated**: Specification regenerated from live FastAPI application
- [ ] **Documentation Sync**: Generated spec matches live application routes
- [ ] **Postman Collection Updated**: Collection includes avatar endpoint examples
- [ ] **Postman Collection Validated**: Collection structure and requests verified

### ⚠️ CRITICAL BLOCKERS - MUST BE RESOLVED
- [ ] **No Failing Tests**: Any test failure blocks completion
- [ ] **No Security Vulnerabilities**: Any security test failure blocks completion  
- [ ] **No Performance Issues**: Upload must complete within 30 seconds for 5MB files
- [ ] **No Breaking Changes**: Existing API functionality must remain intact

---

### 🚫 FEATURE IS NOT COMPLETE UNTIL ALL CHECKBOXES ARE ✅

**FINAL COMMAND SEQUENCE TO VERIFY COMPLETION:**
```bash
# 1. Complete test suite
poetry run pytest tests/ -v --tb=short --maxfail=1

# 2. Security-focused test run  
poetry run pytest tests/test_avatar_security.py tests/test_avatar_auth.py -v

# 3. Integration test
./tests/scripts/test_avatar_e2e.sh

# 4. Code quality validation
poetry run ruff check app/ --fix && poetry run mypy app/ --strict

# 5. Coverage report
poetry run pytest tests/ --cov=app --cov-report=html --cov-fail-under=85

# 6. Regenerate OpenAPI specification
python -c "
from app.main import app
import yaml
openapi_spec = app.openapi()
with open('docs/openapi.yaml', 'w') as f:
    yaml.dump(openapi_spec, f, default_flow_style=False)
print('✅ OpenAPI specification regenerated')
"

# 7. Verify avatar endpoints in generated spec
python -c "
import yaml
with open('docs/openapi.yaml', 'r') as f:
    spec = yaml.safe_load(f)
avatar_paths = [p for p in spec.get('paths', {}).keys() if 'avatar' in p]
assert len(avatar_paths) > 0, 'Avatar endpoints not documented in generated spec'
print(f'✅ Avatar endpoints found: {avatar_paths}')
"

# 8. Validate Postman collection (if exists)
python -c "
import json
import os
postman_file = 'docs/postman/avatar_endpoints.postman_collection.json'
if os.path.exists(postman_file):
    with open(postman_file, 'r') as f:
        collection = json.load(f)
    items = collection.get('item', [])
    avatar_requests = [item.get('name') for item in items if 'avatar' in item.get('name', '').lower()]
    print(f'✅ Postman collection has avatar requests: {avatar_requests}')
else:
    print('ℹ️  No Postman collection found - consider creating one')
"

# 9. Final documentation sync check
python -c "
from app.main import app
import yaml
live_spec = app.openapi()
with open('docs/openapi.yaml', 'r') as f:
    file_spec = yaml.safe_load(f)
live_paths = set(live_spec.get('paths', {}).keys())
file_paths = set(file_spec.get('paths', {}).keys())
avatar_paths_live = {p for p in live_paths if 'avatar' in p.lower()}
avatar_paths_file = {p for p in file_paths if 'avatar' in p.lower()}
assert avatar_paths_live == avatar_paths_file, 'OpenAPI spec out of sync with application'
print('✅ Documentation is in sync with application')
"

# IF ALL COMMANDS PASS: Feature is complete
# IF ANY COMMAND FAILS: Continue development until all pass
```

**🎯 SUCCESS CRITERIA: All commands above must execute successfully with zero errors.**

---

## Implementation Notes

### Security Validation Stack
1. **File Size**: 5MB maximum (configurable via environment)
2. **MIME Type**: Basic validation against allowed formats
3. **Magic Number**: Use `imghdr` or `python-magic` for file header validation
4. **PIL Verification**: Use `PIL.Image.verify()` to validate image integrity
5. **Format Restriction**: Only allow specific image formats (no SVG for XSS protection)

### Image Processing Requirements
- Generate thumbnails for optimized display (150x150 for profiles, 32x32 for chat)
- Preserve original for high-quality displays
- Store both original and thumbnail URLs in user model

### Storage Strategy
- Follow existing `app/services/file_service.py` storage patterns
- Use `settings.upload_directory/avatars/` subdirectory
- Generate unique filenames: `{user_id}_avatar_{timestamp}.{ext}`
- Store relative paths in database, construct full URLs in API responses

### URL Generation Pattern
```python
# Follow existing file serving patterns
avatar_url = f"/api/v1/users/{user_id}/avatar"  # API endpoint that serves file
# OR if serving static files:
avatar_url = f"/uploads/avatars/{user_id}_avatar.jpg"  # Direct file access
```

### Error Handling Matrix
- **400 Bad Request**: Invalid file format, oversized file, corrupted image
- **401 Unauthorized**: Missing or invalid JWT token  
- **403 Forbidden**: User trying to modify another user's avatar
- **404 Not Found**: User has no avatar set
- **413 Payload Too Large**: File exceeds size limits
- **422 Unprocessable Entity**: Image fails PIL validation

### Fallback Logic
- Default avatar generation using user initials or generic placeholder
- Graceful handling when avatar file is missing from storage
- Consistent avatar URLs even when no custom avatar is set

## Anti-Patterns to Avoid
- ❌ Don't store binary image data in PostgreSQL database
- ❌ Don't trust MIME type headers alone (security risk)
- ❌ Don't skip PIL image verification (malicious file risk)
- ❌ Don't allow SVG uploads (XSS vulnerability)
- ❌ Don't create new file storage patterns (reuse existing)
- ❌ Don't skip thumbnail generation (performance impact)
- ❌ Don't allow unlimited file sizes (DoS attack vector)

---

**PRP Quality Score: 9/10**

This PRP provides comprehensive context including existing code patterns, security considerations, validation requirements, and progressive implementation steps. The validation loops are executable and follow existing codebase patterns. The only minor gap is potential CDN integration which may require additional research during implementation.