# Problem Resolution Plan: Database Migration Fix

## Problem Summary

**Issue**: Authentication endpoints failing with "relation 'users' does not exist" error when attempting login/registration.

**Error Details**:
```
2025-09-05 14:38:48 - app.routers.auth - ERROR - ❌ User registration failed: 
(sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "users" does not exist
```

**Root Cause**: Database migrations have not been applied to create the required database schema. The application is running but the database tables don't exist.

## Current State Analysis

### Database Migration Status
- Migration file exists: `alembic/versions/cbe1d08d4020_initial_database_schema.py`
- Migration includes full schema with all required tables:
  - `users` table (lines 209-244)
  - `organizations` table (lines 44-76) 
  - `tickets` table (lines 356-411)
  - `files` table (lines 430-486)
  - `integrations` table (lines 141-201)
  - Additional supporting tables

### Environment Configuration
- Database URL configured in environment variables
- Alembic configuration properly set up in `alembic/env.py`
- Async PostgreSQL connection configured correctly

## Resolution Steps

### Step 1: Verify Database Connection
```bash
# Check if database is accessible
docker compose up -d postgres
docker compose logs postgres
```

### Step 2: Apply Database Migrations
```bash
# Run the migration to create all tables
poetry run alembic upgrade head
```

Alternative with explicit database URL:
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/ai_tickets poetry run alembic upgrade head
```

### Step 3: Verify Schema Creation
```bash
# Verify tables were created successfully
poetry run python -c "
from sqlalchemy import create_engine, text
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

async def check_tables():
    engine = create_async_engine('postgresql+asyncpg://user:pass@localhost:5432/ai_tickets')
    async with engine.connect() as conn:
        result = await conn.execute(text(\"SELECT tablename FROM pg_tables WHERE schemaname = 'public';\"))
        tables = [row[0] for row in result.fetchall()]
        print('Created tables:', tables)
        await engine.dispose()

asyncio.run(check_tables())
"
```

### Step 4: Test Authentication Endpoints
```bash
# Test user registration
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123","full_name":"Test User"}'

# Test user login  
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}'
```

## Prevention Measures

### 1. Add Migration Check to Startup
Add database migration check to application startup in `app/main.py`:

```python
async def check_database_migrations():
    """Ensure database migrations are up to date"""
    try:
        from alembic.config import Config
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory
        from app.database import engine
        
        async with engine.connect() as connection:
            def check_migrations(conn):
                context = MigrationContext.configure(conn)
                current_rev = context.get_current_revision()
                
                config = Config("alembic.ini")
                script_dir = ScriptDirectory.from_config(config)
                head_rev = script_dir.get_current_head()
                
                if current_rev != head_rev:
                    logger.warning(f"Database schema is not up to date. Current: {current_rev}, Expected: {head_rev}")
                    return False
                return True
            
            return await connection.run_sync(check_migrations)
    except Exception as e:
        logger.error(f"Failed to check database migrations: {e}")
        return False
```

### 2. Update Docker Compose with Migration
Add migration step to docker-compose startup:

```yaml
services:
  app:
    # ... existing configuration
    depends_on:
      postgres:
        condition: service_healthy
    command: >
      sh -c "
        poetry run alembic upgrade head &&
        poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000
      "
```

### 3. Add Health Check for Database Schema
Enhance `/health` endpoint to verify database schema:

```python
@app.get("/health")
async def health_check():
    try:
        # Test database connection
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            
        # Test critical table exists
        async with AsyncSession(engine) as session:
            await session.execute(select(User).limit(1))
            
        return {"status": "healthy", "database": "connected", "schema": "ready"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

## Immediate Action Required

**Priority**: High - Authentication is completely broken

**Command to Execute**:
```bash
poetry run alembic upgrade head
```

**Expected Outcome**: 
- All database tables created successfully
- Authentication endpoints functional
- Application ready for normal operation

**Verification**:
- Login/registration requests return proper responses instead of 500 errors
- Health check shows database connectivity
- User table queries work correctly

## Timeline

- **Immediate**: Run migration command (< 1 minute)
- **Short-term**: Test authentication flows (5 minutes)  
- **Medium-term**: Implement prevention measures (30 minutes)
- **Long-term**: Add automated checks to CI/CD pipeline

## Risk Assessment

**Low Risk**: This is a standard database migration operation that creates the initial schema. No data loss risk since tables don't exist yet.

**Dependencies**: PostgreSQL database must be running and accessible.

## Success Criteria

✅ Database migration completes without errors  
✅ All required tables exist in database  
✅ Authentication endpoints return proper HTTP status codes  
✅ User registration/login functionality works  
✅ Health check passes  

## Notes

- This appears to be an initial deployment where migrations were never run
- The migration file contains the complete schema and should create all necessary tables
- No manual SQL operations required - Alembic will handle everything
- Consider adding migration checks to deployment scripts to prevent this issue in production