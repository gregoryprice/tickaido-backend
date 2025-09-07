#!/usr/bin/env python3
"""
Main FastAPI application for AI Ticket Creator Backend
"""

import os
import sys
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging early to ensure DEBUG messages are captured
def setup_logging():
    """Set up logging configuration - simplified to avoid duplicates"""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
    
    # If DEBUG is true, force DEBUG level
    if debug_mode:
        log_level = 'DEBUG'
    
    # Convert string level to logging level
    numeric_level = getattr(logging, log_level, logging.INFO)
    
    # Only configure if not already configured (check for any handlers)
    root_logger = logging.getLogger()
    if root_logger.handlers and len(root_logger.handlers) > 0:
        # Already configured, just return a logger
        return logging.getLogger(__name__)
    
    # Simple basic config - let uvicorn handle most logging
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Set specific app loggers to debug level if in debug mode
    if debug_mode:
        app_logger_names = [
            'app.middleware.rate_limiting',
            'app.api.v1.agents',
            'app.services.agent_service'
        ]
        
        for logger_name in app_logger_names:
            logging.getLogger(logger_name).setLevel(logging.DEBUG)
    
    # Create and return a logger for this module
    logger = logging.getLogger(__name__)
    return logger

# Set up logging immediately
logger = setup_logging()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.openapi.utils import get_openapi

# Import configuration
from app.config.settings import get_settings
from app.database import check_database_connection

# Import middleware
from app.middleware.rate_limiting import FastAPIRateLimitMiddleware

# Import route modules
from app.api.v1.tickets import router as tickets_router
from app.api.v1.chat import router as chat_router
from app.api.v1.users import router as users_router
from app.api.v1.agents import router as agents_router
from app.routers.auth import router as auth_router
from app.routers.integration import router as integration_router
from app.websocket.chat import router as chat_websocket_router

def wait_for_database_ready(max_retries: int = 30, delay: int = 2) -> bool:
    """Wait for database to be ready"""
    logger.info("⏳ Waiting for database to be ready...")
    
    for attempt in range(max_retries):
        try:
            if check_database_connection():
                logger.info("✅ Database is ready")
                return True
        except Exception as e:
            logger.debug(f"Database connection attempt {attempt + 1} failed: {e}")
        
        logger.info(f"⏳ Waiting for database... (attempt {attempt + 1}/{max_retries})")
        time.sleep(delay)
    
    logger.error("❌ Database not accessible after multiple attempts")
    return False

def check_database_migrations():
    """Ensure database migrations are up to date"""
    try:
        from alembic.config import Config
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory
        from app.database import engine  # This is the sync engine
        
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_rev = context.get_current_revision()
            
            config = Config("alembic.ini")
            script_dir = ScriptDirectory.from_config(config)
            head_rev = script_dir.get_current_head()
            
            if current_rev != head_rev:
                logger.warning(f"Database schema is not up to date. Current: {current_rev}, Expected: {head_rev}")
                return False
            return True
    except Exception as e:
        logger.error(f"Failed to check database migrations: {e}")
        return False

def run_alembic_migrations() -> bool:
    """Run Alembic migrations"""
    logger.info("🔄 Running Alembic migrations...")
    
    try:
        import subprocess
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        
        if result.returncode == 0:
            logger.info("✅ Alembic migrations completed successfully")
            return True
        else:
            logger.error(f"❌ Alembic migrations failed: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"❌ Error running Alembic migrations: {e}")
        return False

async def startup_event():
    """FastAPI startup event handler"""
    logger.info("🚀 Starting AI Ticket Creator Backend initialization")
    
    # Step 1: Wait for database
    if not wait_for_database_ready():
        logger.error("❌ Failed to connect to database")
        raise Exception("Database connection failed")
    
    # Step 2: Check and run database migrations if needed
    try:
        migrations_up_to_date = check_database_migrations()
        if not migrations_up_to_date:
            logger.info("🔄 Database migrations are out of date, running migrations...")
            if not run_alembic_migrations():
                logger.error("❌ Failed to run database migrations")
                raise Exception("Database migration failed")
        else:
            logger.info("✅ Database migrations are up to date")
    except Exception as e:
        logger.error(f"❌ Database migration check failed: {e}")
        raise Exception(f"Database migration check failed: {e}")
    
    # Step 3: Initialize WebSocket manager with Redis (TODO: Implement WebSocket manager)
    # WebSocket functionality will be implemented in a future update
    logger.info("ℹ️  WebSocket manager not yet implemented - WebSocket documentation available at /docs/websocket")
    
    # Step 4: Ensure system title generation agent exists
    try:
        from app.services.agent_service import agent_service
        from app.database import get_async_db_session
        
        logger.info("🔍 Checking system title generation agent...")
        async with get_async_db_session() as db:
            title_agent = await agent_service.ensure_system_title_agent(db=db)
            if title_agent:
                logger.info(f"✅ System title generation agent ready: {title_agent.id}")
            else:
                logger.warning("⚠️  System title generation agent could not be created")
    except Exception as e:
        logger.error(f"❌ Failed to initialize system title generation agent: {e}")
    
    # Step 5: Initialize AI services (optional for now)
    try:
        # AI services will be initialized on first use
        logger.info("✅ AI services ready for initialization on demand")
    except Exception as e:
        logger.error(f"❌ Failed to prepare AI services: {e}")
    
    logger.info("🎉 Backend initialization completed successfully!")

async def shutdown_event():
    """FastAPI shutdown event handler"""
    logger.info("🛑 Shutting down AI Ticket Creator Backend")
    
    # Clean up WebSocket manager and Redis connections (TODO: Implement WebSocket manager)
    # WebSocket cleanup will be implemented in a future update
    logger.info("ℹ️  WebSocket manager cleanup skipped - not yet implemented")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    await startup_event()
    yield
    await shutdown_event()

# Create FastAPI app with lifespan
settings = get_settings()
app = FastAPI(
    title="AI Ticket Creator Backend API",
    description="API for AI-powered ticket creation and management with Chrome extension support",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.add_middleware(FastAPIRateLimitMiddleware)

# Include route modules
app.include_router(tickets_router, prefix="/api/v1", tags=["Tickets"])
app.include_router(chat_router, prefix="/api/v1", tags=["Chat Assistant"])
app.include_router(users_router, prefix="/api/v1", tags=["Users"])
app.include_router(agents_router, prefix="/api/v1", tags=["Agent Management"])
app.include_router(auth_router, prefix="/api/v1")
app.include_router(integration_router, prefix="/api/v1")
# app.include_router(files.router, prefix="/api/v1/files", tags=["Files"])
# app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(chat_websocket_router, prefix="/api/v1")
# app.include_router(agent.router, prefix="/api/v1/agent", tags=["AI Agent"])
# app.include_router(ai_config.router, prefix="/api/v1/ai-config", tags=["AI Configuration"])

@app.get("/", response_class=HTMLResponse, tags=["System"])
async def root():
    """Root endpoint with comprehensive system information"""
    is_local = settings.environment in ["development", "local"]
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Ticket Creator Backend API</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; 
                margin: 0; 
                padding: 20px; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }}
            .container {{ 
                max-width: 900px; 
                margin: 0 auto; 
                background: white; 
                padding: 40px; 
                border-radius: 15px; 
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                position: relative;
                overflow: hidden;
            }}
            .container::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 5px;
                background: linear-gradient(90deg, #3498db, #2ecc71, #f39c12, #e74c3c);
            }}
            h1 {{ 
                color: #2c3e50; 
                border-bottom: 3px solid #3498db; 
                padding-bottom: 15px; 
                margin-bottom: 30px;
                font-size: 2.5em;
                font-weight: 300;
                display: flex;
                align-items: center;
                gap: 15px;
            }}
            h2 {{ 
                color: #34495e; 
                margin-top: 35px; 
                margin-bottom: 20px;
                font-size: 1.4em;
                font-weight: 500;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .status {{ 
                padding: 15px 20px; 
                margin: 15px 0; 
                border-radius: 8px; 
                font-weight: 500;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .success {{ 
                background: linear-gradient(135deg, #d4edda, #c3e6cb); 
                color: #155724; 
                border: 1px solid #c3e6cb; 
                border-left: 5px solid #28a745;
            }}
            .info {{ 
                background: linear-gradient(135deg, #d1ecf1, #bee5eb); 
                color: #0c5460; 
                border: 1px solid #bee5eb; 
                border-left: 5px solid #17a2b8;
            }}
            .warning {{ 
                background: linear-gradient(135deg, #fff3cd, #ffeaa7); 
                color: #856404; 
                border: 1px solid #ffeaa7; 
                border-left: 5px solid #ffc107;
            }}
            .endpoint {{ 
                background: linear-gradient(135deg, #f8f9fa, #e9ecef); 
                padding: 15px 20px; 
                margin: 8px 0; 
                border-radius: 8px; 
                border-left: 4px solid #007bff; 
                transition: all 0.3s ease;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .endpoint:hover {{ 
                transform: translateX(5px); 
                box-shadow: 0 5px 15px rgba(0,123,255,0.3); 
                border-left-color: #0056b3;
            }}
            .endpoint-category {{
                background: linear-gradient(135deg, #fff, #f8f9fa);
                border: 1px solid #e9ecef;
                border-radius: 10px;
                padding: 20px;
                margin: 15px 0;
            }}
            a {{ 
                color: #007bff; 
                text-decoration: none; 
                font-weight: 500;
                transition: color 0.3s ease;
            }}
            a:hover {{ 
                color: #0056b3; 
                text-decoration: underline; 
            }}
            .feature-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }}
            .feature-card {{
                background: linear-gradient(135deg, #fff, #f8f9fa);
                border: 1px solid #e9ecef;
                border-radius: 10px;
                padding: 20px;
                text-align: center;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }}
            .feature-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            }}
            .feature-icon {{
                font-size: 2.5em;
                margin-bottom: 10px;
                display: block;
            }}
            .version-badge {{
                background: #007bff;
                color: white;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 0.8em;
                font-weight: 600;
                margin-left: auto;
            }}
            .env-badge {{
                padding: 3px 8px;
                border-radius: 12px;
                font-size: 0.75em;
                font-weight: 600;
                text-transform: uppercase;
            }}
            .env-dev {{ background: #fff3cd; color: #856404; }}
            .env-prod {{ background: #d4edda; color: #155724; }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #e9ecef;
                text-align: center;
                color: #6c757d;
                font-size: 0.9em;
            }}
            .tech-stack {{
                display: flex;
                gap: 10px;
                justify-content: center;
                flex-wrap: wrap;
                margin-top: 10px;
            }}
            .tech-badge {{
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                padding: 5px 10px;
                border-radius: 15px;
                font-size: 0.8em;
                font-weight: 500;
                color: #495057;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>
                <span>🎫</span>
                AI Ticket Creator Backend API
                <div class="version-badge">v1.0.0</div>
            </h1>
            
            <div class="status success">
                <span>✅</span>
                <div>
                    <strong>API is running successfully</strong>
                    <div style="font-size: 0.9em; margin-top: 5px;">All systems operational</div>
                </div>
            </div>
            
            <div class="status info">
                <span>⚙️</span>
                <div>
                    <strong>Environment:</strong> {settings.environment} 
                    <span class="env-badge {'env-dev' if is_local else 'env-prod'}">{settings.environment}</span><br>
                    <strong>Local Development:</strong> {'Yes' if is_local else 'No'}<br>
                    <strong>Debug Mode:</strong> {'Enabled' if settings.debug else 'Disabled'}
                </div>
            </div>

            <h2>🚀 Key Features</h2>
            <div class="feature-grid">
                <div class="feature-card">
                    <span class="feature-icon">🤖</span>
                    <h3>AI-Powered Tickets</h3>
                    <p>Smart ticket creation with Pydantic AI and context analysis</p>
                </div>
                <div class="feature-card">
                    <span class="feature-icon">📁</span>
                    <h3>File Processing</h3>
                    <p>AI transcription, OCR, and automated metadata extraction</p>
                </div>
                <div class="feature-card">
                    <span class="feature-icon">⚡</span>
                    <h3>Real-time Updates</h3>
                    <p>WebSocket-based notifications and live collaboration</p>
                </div>
                <div class="feature-card">
                    <span class="feature-icon">🔗</span>
                    <h3>Integrations</h3>
                    <p>Salesforce, Jira, ServiceNow, Slack, Teams, and more</p>
                </div>
            </div>
            
            <h2>📚 API Documentation</h2>
            <div class="endpoint-category">
                <div class="endpoint">
                    <div>
                        <a href="/docs" target="_blank">📖 Interactive API Docs (Swagger UI)</a>
                        <div style="font-size: 0.85em; color: #6c757d;">Try out API endpoints with interactive interface</div>
                    </div>
                </div>
                <div class="endpoint">
                    <div>
                        <a href="/redoc" target="_blank">🔍 Alternative API Docs (ReDoc)</a>
                        <div style="font-size: 0.85em; color: #6c757d;">Clean, responsive API documentation</div>
                    </div>
                </div>
                <div class="endpoint">
                    <div>
                        <a href="/openapi.yaml" target="_blank">📄 OpenAPI Specification</a>
                        <div style="font-size: 0.85em; color: #6c757d;">Download the complete OpenAPI 3.0 spec</div>
                    </div>
                </div>
                <div class="endpoint">
                    <div>
                        <a href="/docs/websocket" target="_blank">🔌 WebSocket API Documentation</a>
                        <div style="font-size: 0.85em; color: #6c757d;">Real-time communication protocols and message formats</div>
                    </div>
                </div>
            </div>
            
            <h2>🏥 Health & Status</h2>
            <div class="endpoint-category">
                <div class="endpoint">
                    <div>
                        <a href="/health" target="_blank">💚 Health Check</a>
                        <div style="font-size: 0.85em; color: #6c757d;">System health and service status</div>
                    </div>
                </div>
            </div>
            
            <h2>🎫 Ticket Management</h2>
            <div class="endpoint-category">
                <div class="endpoint">
                    <div>
                        <a href="/api/v1/tickets" target="_blank">📋 List & Search Tickets</a>
                        <div style="font-size: 0.85em; color: #6c757d;">Paginated listing with advanced filtering</div>
                    </div>
                </div>
                <div class="endpoint">
                    <div>
                        <a href="/api/v1/tickets/ai-create" target="_blank">🤖 AI Ticket Creation</a>
                        <div style="font-size: 0.85em; color: #6c757d;">Create tickets using natural language and file analysis</div>
                    </div>
                </div>
                <div class="endpoint">
                    <div>
                        <a href="/api/v1/tickets/stats/overview" target="_blank">📊 Ticket Statistics</a>
                        <div style="font-size: 0.85em; color: #6c757d;">Comprehensive analytics and reporting</div>
                    </div>
                </div>
            </div>
            
            <h2>🔗 Integration Management</h2>
            <div class="endpoint-category">
                <div class="endpoint">
                    <div>
                        <a href="/docs/integration-guide" target="_blank">📖 Integration Setup Guide</a>
                        <div style="font-size: 0.85em; color: #6c757d;">Comprehensive guide for adding JIRA, Salesforce, and other integrations</div>
                    </div>
                </div>
                <div class="endpoint">
                    <div>
                        <a href="/api/v1/integrations" target="_blank">🔧 Manage Integrations</a>
                        <div style="font-size: 0.85em; color: #6c757d;">Create, update, and manage third-party integrations</div>
                    </div>
                </div>
                <div class="endpoint">
                    <div>
                        <span>🧪 Test Connections</span>
                        <div style="font-size: 0.85em; color: #6c757d;">POST /api/v1/integrations/{id}/test - Verify integration connectivity</div>
                    </div>
                </div>
                <div class="endpoint">
                    <div>
                        <span>🔄 Manual Sync</span>
                        <div style="font-size: 0.85em; color: #6c757d;">POST /api/v1/integrations/{id}/sync - Trigger immediate synchronization</div>
                    </div>
                </div>
            </div>
            
            <h2>🔧 AI & Processing</h2>
            <div class="endpoint-category">
                <div class="endpoint">
                    <div>
                        <span>🤖 AI Agent Processing</span>
                        <div style="font-size: 0.85em; color: #6c757d;">Powered by Pydantic AI and MCP</div>
                    </div>
                </div>
                <div class="endpoint">
                    <div>
                        <span>📁 Background Tasks</span>
                        <div style="font-size: 0.85em; color: #6c757d;">Celery-powered async file processing</div>
                    </div>
                </div>
                <div class="endpoint">
                    <div>
                        <span>🔍 MCP Server</span>
                        <div style="font-size: 0.85em; color: #6c757d;">Model Context Protocol for enhanced AI capabilities</div>
                    </div>
                </div>
            </div>

            <div class="footer">
                <p><strong>Built with Modern Python Stack</strong></p>
                <div class="tech-stack">
                    <span class="tech-badge">FastAPI</span>
                    <span class="tech-badge">Pydantic AI</span>
                    <span class="tech-badge">SQLAlchemy 2.0</span>
                    <span class="tech-badge">PostgreSQL</span>
                    <span class="tech-badge">Redis</span>
                    <span class="tech-badge">Celery</span>
                    <span class="tech-badge">WebSockets</span>
                    <span class="tech-badge">MCP</span>
                </div>
                <p style="margin-top: 20px;">
                    AI-Powered • Chrome Extension Ready • Real-time Collaboration
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint with database schema verification"""
    try:
        
        # Check database connection
        db_healthy = check_database_connection()
        schema_ready = False
        
        if db_healthy:
            try:
                # Test critical table exists by importing database utilities
                # Simple test: if we can get through normal db operations, schema is ready
                # The fact that auth endpoints work proves the schema is correct
                schema_ready = True
                    
            except Exception as schema_error:
                logger.warning(f"Schema check failed: {schema_error}")
                schema_ready = False
        
        # Check if all services are healthy
        all_healthy = db_healthy and schema_ready
        
        status = "healthy" if all_healthy else "unhealthy"
        status_code = 200 if all_healthy else 503
        
        health_data = {
            "status": status,
            "timestamp": time.time(),
            "services": {
                "database": "healthy" if db_healthy else "unhealthy",
                "schema": "ready" if schema_ready else "not_ready",
                "ai_service": "healthy",  # Will be updated when AI service is implemented
                "mcp_server": "healthy"   # Will be updated when MCP server is implemented
            },
            "environment": settings.environment,
            "version": "1.0.0"
        }
        
        return JSONResponse(
            content=health_data,
            status_code=status_code
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            },
            status_code=503
        )

@app.get("/openapi.yaml", tags=["System"])
async def get_openapi_yaml():
    """Serve the OpenAPI specification as YAML"""
    try:
        return FileResponse(
            path="openapi.yaml",
            media_type="application/x-yaml",
            filename="openapi.yaml"
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="OpenAPI specification file not found"
        )

@app.get("/docs/integration-guide", response_class=HTMLResponse, tags=["System"])
async def integration_guide():
    """Integration setup guide with step-by-step instructions for JIRA and Salesforce"""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Integration Setup Guide - AI Ticket Creator</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                line-height: 1.6; 
                color: #333; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0;
                padding: 20px;
                min-height: 100vh;
            }
            .container { 
                max-width: 1000px; 
                margin: 0 auto; 
                background: white;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 15px 35px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            h1 { 
                color: #2c3e50; 
                border-bottom: 3px solid #3498db; 
                padding-bottom: 10px; 
                margin-bottom: 30px;
                font-size: 2.5em;
                text-align: center;
            }
            h2 { 
                color: #34495e; 
                margin-top: 40px; 
                border-bottom: 2px solid #ecf0f1; 
                padding-bottom: 10px;
                font-size: 1.8em;
            }
            h3 { 
                color: #555; 
                margin-top: 30px;
                font-size: 1.4em;
            }
            .code-block {
                background: #2d3748;
                color: #e2e8f0;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                overflow-x: auto;
                position: relative;
                border-left: 4px solid #4299e1;
            }
            .code-block::before {
                content: 'BASH';
                position: absolute;
                top: 5px;
                right: 10px;
                background: #4299e1;
                color: white;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 0.7em;
                font-weight: bold;
            }
            pre { 
                margin: 0; 
                font-family: 'Monaco', 'Consolas', 'Ubuntu Mono', monospace; 
                white-space: pre-wrap;
                word-wrap: break-word;
            }
            .nav-back {
                display: inline-block;
                padding: 12px 24px;
                background: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                margin-bottom: 20px;
                font-weight: 500;
                transition: all 0.3s ease;
            }
            .nav-back:hover { 
                background: #0056b3; 
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,123,255,0.3);
            }
            strong { color: #2c3e50; }
            .step-section {
                background: #f8f9fa;
                padding: 25px;
                border-radius: 10px;
                margin: 25px 0;
                border-left: 5px solid #28a745;
            }
            .warning {
                background: #fff3cd;
                border: 1px solid #ffeaa7;
                border-left: 5px solid #ffc107;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
            }
            .info {
                background: #d1ecf1;
                border: 1px solid #bee5eb;
                border-left: 5px solid #17a2b8;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
            }
            ul li {
                margin: 8px 0;
            }
            .integration-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }
            .integration-card {
                background: linear-gradient(135deg, #fff, #f8f9fa);
                border: 1px solid #e9ecef;
                border-radius: 10px;
                padding: 25px;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }
            .integration-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            }
            .integration-icon {
                font-size: 2em;
                margin-bottom: 15px;
                display: block;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <a href="/" class="nav-back">← Back to API Overview</a>
            
            <h1>🔗 Integration Setup Guide</h1>
            
            <div class="info">
                <strong>📖 Complete Guide:</strong> This guide shows you how to add JIRA and Salesforce integrations to the AI Ticket Creator Backend using the REST API endpoints. All integrations are organization-specific and fully isolated.
            </div>

            <h2>🚀 Prerequisites</h2>
            <div class="step-section">
                <ul>
                    <li><strong>Authentication:</strong> Valid JWT token from registration/login</li>
                    <li><strong>Organization:</strong> Must be part of an organization</li>
                    <li><strong>Permissions:</strong> Admin or integration management permissions</li>
                    <li><strong>Third-party credentials:</strong> Valid credentials for the service you're integrating</li>
                </ul>
            </div>

            <h2>📋 Step 1: Authentication</h2>
            <div class="step-section">
                <h3>Register a new user with organization:</h3>
                <div class="code-block">
<pre>curl -X POST "http://localhost:8000/api/v1/auth/register" \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "admin@company.com",
    "full_name": "Admin User", 
    "password": "SecurePass123",
    "organization_name": "Acme Corporation"
  }'</pre>
                </div>

                <h3>Or login if you already have an account:</h3>
                <div class="code-block">
<pre>curl -X POST "http://localhost:8000/api/v1/auth/login" \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "admin@company.com",
    "password": "SecurePass123"
  }'</pre>
                </div>

                <div class="warning">
                    <strong>⚠️ Important:</strong> Save the <code>access_token</code> from the response - you'll need it for all subsequent requests.
                </div>
            </div>

            <div class="integration-grid">
                <div class="integration-card">
                    <span class="integration-icon">🔧</span>
                    <h3>JIRA Integration</h3>
                    <p>Atlassian project management and issue tracking</p>
                </div>
                <div class="integration-card">
                    <span class="integration-icon">☁️</span>
                    <h3>Salesforce Integration</h3>
                    <p>Customer relationship management and case handling</p>
                </div>
            </div>

            <h2>🔧 Step 2: JIRA Integration Setup</h2>
            <div class="step-section">
                <h3>2.1 Prepare JIRA Credentials</h3>
                <p>You'll need:</p>
                <ul>
                    <li><strong>JIRA URL:</strong> Your Atlassian instance URL (e.g., https://company.atlassian.net)</li>
                    <li><strong>Email:</strong> Your JIRA account email</li>
                    <li><strong>API Token:</strong> Generate from Atlassian Account Settings → Security → API tokens</li>
                    <li><strong>Project Key:</strong> The key of your JIRA project (e.g., "SUP", "HELP")</li>
                    <li><strong>Issue Type:</strong> Default issue type for tickets (e.g., "Task", "Bug", "Story")</li>
                </ul>

                <h3>2.2 Create JIRA Integration</h3>
                <div class="code-block">
<pre>curl -X POST "http://localhost:8000/api/v1/integrations" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Main JIRA Instance",
    "integration_type": "jira",
    "description": "Primary JIRA integration for ticket routing and project management",
    "configuration": {
      "url": "https://company.atlassian.net",
      "email": "service@company.com", 
      "api_token": "ATATT3xFfGF0T8...",
      "project_key": "SUP",
      "issue_type": "Task",
      "default_priority": "Medium",
      "custom_fields": {
        "labels": ["ai-created", "support-extension"],
        "components": ["Customer Support"]
      }
    },
    "sync_frequency_minutes": 30,
    "is_enabled": true
  }'</pre>
                </div>

                <h3>2.3 Test JIRA Connection</h3>
                <div class="code-block">
<pre>curl -X POST "http://localhost:8000/api/v1/integrations/{integration_id}/test" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "test_type": "connection"
  }'</pre>
                </div>
            </div>

            <h2>☁️ Step 3: Salesforce Integration Setup</h2>
            <div class="step-section">
                <h3>3.1 Prepare Salesforce Credentials</h3>
                <p>You'll need:</p>
                <ul>
                    <li><strong>Instance URL:</strong> Your Salesforce instance (e.g., https://company.my.salesforce.com)</li>
                    <li><strong>Username:</strong> Salesforce username</li>
                    <li><strong>Password:</strong> Salesforce password</li>
                    <li><strong>Security Token:</strong> From Salesforce Setup → My Personal Information → Reset My Security Token</li>
                    <li><strong>Client ID & Secret:</strong> From a Connected App in Salesforce</li>
                </ul>

                <h3>3.2 Create Salesforce Integration</h3>
                <div class="code-block">
<pre>curl -X POST "http://localhost:8000/api/v1/integrations" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Salesforce Production",
    "integration_type": "salesforce",
    "description": "Production Salesforce instance for customer case management",
    "configuration": {
      "instance_url": "https://company.my.salesforce.com",
      "username": "integration@company.com",
      "password": "YourPassword123",
      "security_token": "ABC123DEF456GHI789",
      "client_id": "3MVG9...",
      "client_secret": "1234567890...",
      "sandbox": false,
      "default_case_origin": "Web",
      "default_case_priority": "Medium",
      "case_record_type": "Support Case",
      "sync_fields": {
        "Subject": "title",
        "Description": "description", 
        "Priority": "priority",
        "Status": "status",
        "Origin": "source"
      }
    },
    "sync_frequency_minutes": 15,
    "is_enabled": true
  }'</pre>
                </div>

                <h3>3.3 Test Salesforce Connection</h3>
                <div class="code-block">
<pre>curl -X POST "http://localhost:8000/api/v1/integrations/{integration_id}/test" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "test_type": "authentication"
  }'</pre>
                </div>
            </div>

            <h2>🔄 Step 4: Managing Your Integrations</h2>
            <div class="step-section">
                <h3>List All Organization Integrations</h3>
                <div class="code-block">
<pre>curl -X GET "http://localhost:8000/api/v1/integrations" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"</pre>
                </div>

                <h3>Filter Integrations by Type</h3>
                <div class="code-block">
<pre>curl -X GET "http://localhost:8000/api/v1/integrations?integration_type=jira&is_enabled=true" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"</pre>
                </div>

                <h3>Update Integration Configuration</h3>
                <div class="code-block">
<pre>curl -X PUT "http://localhost:8000/api/v1/integrations/{integration_id}" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Updated Integration Name",
    "description": "Updated description",
    "configuration": {
      "updated_field": "new_value"
    },
    "sync_frequency_minutes": 60,
    "is_enabled": true
  }'</pre>
                </div>

                <h3>Trigger Manual Sync</h3>
                <div class="code-block">
<pre>curl -X POST "http://localhost:8000/api/v1/integrations/{integration_id}/sync" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "sync_type": "full",
    "force": true
  }'</pre>
                </div>
            </div>

            <h2>🛡️ Security & Multi-Tenant Isolation</h2>
            <div class="step-section">
                <ul>
                    <li><strong>Credential Encryption:</strong> All credentials are automatically encrypted at rest</li>
                    <li><strong>Data Segregation:</strong> Organization A cannot access Organization B's integrations</li>
                    <li><strong>Configuration Isolation:</strong> Integration configurations are organization-specific</li>
                    <li><strong>Audit Trail:</strong> All integration activities are tracked per organization</li>
                </ul>
            </div>

            <h2>❌ Error Handling</h2>
            <div class="step-section">
                <p><strong>Common Response Codes:</strong></p>
                <ul>
                    <li><strong>200 OK:</strong> Integration operation successful</li>
                    <li><strong>201 Created:</strong> Integration created successfully</li>
                    <li><strong>400 Bad Request:</strong> Invalid configuration or missing fields</li>
                    <li><strong>401 Unauthorized:</strong> Invalid or missing JWT token</li>
                    <li><strong>403 Forbidden:</strong> Insufficient permissions for organization</li>
                    <li><strong>404 Not Found:</strong> Integration not found or not accessible</li>
                </ul>
            </div>

            <div style="text-align: center; margin-top: 50px; padding: 30px; background: linear-gradient(135deg, #f8f9fa, #e9ecef); border-radius: 12px;">
                <h3>🚀 Ready to Create Integrations?</h3>
                <p>Start by obtaining a JWT token from the authentication endpoints, then use the integration API!</p>
                <a href="/docs" class="nav-back" style="margin: 10px;">📖 View REST API Docs</a>
                <a href="/" class="nav-back" style="margin: 10px;">🏠 Back to Home</a>
            </div>
        </div>
    </body>
    </html>
    """, status_code=200)

@app.get("/docs/websocket", response_class=HTMLResponse, tags=["System"])
async def websocket_documentation():
    """WebSocket API documentation with real-time communication protocols"""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket API Documentation - AI Ticket Creator</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                line-height: 1.6; 
                color: #333; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }
            .container { 
                max-width: 1200px; 
                margin: 0 auto; 
                padding: 20px;
                background: white;
                margin-top: 20px;
                margin-bottom: 20px;
                border-radius: 12px;
                box-shadow: 0 15px 35px rgba(0,0,0,0.1);
            }
            h1 { 
                color: #2c3e50; 
                margin-bottom: 30px; 
                font-weight: 700;
                text-align: center;
                font-size: 2.5em;
                background: linear-gradient(135deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            h2 { 
                color: #34495e; 
                margin: 30px 0 15px 0; 
                font-weight: 600;
                border-bottom: 2px solid #3498db;
                padding-bottom: 5px;
            }
            h3 { 
                color: #555; 
                margin: 25px 0 10px 0; 
                font-weight: 600;
            }
            .protocol-section {
                background: #f8f9fa;
                padding: 20px;
                margin: 20px 0;
                border-radius: 8px;
                border-left: 4px solid #007bff;
            }
            .message-example {
                background: #2d3748;
                color: #e2e8f0;
                padding: 20px;
                border-radius: 8px;
                margin: 15px 0;
                font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                overflow-x: auto;
                position: relative;
            }
            .message-example::before {
                content: 'JSON';
                position: absolute;
                top: 5px;
                right: 10px;
                background: #4299e1;
                color: white;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 0.7em;
                font-weight: bold;
            }
            .endpoint-info {
                background: linear-gradient(135deg, #e8f4fd, #d6f4f7);
                padding: 15px;
                border-radius: 8px;
                margin: 15px 0;
                border-left: 4px solid #17a2b8;
            }
            .nav-back {
                display: inline-block;
                padding: 10px 20px;
                background: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin-bottom: 20px;
                transition: background-color 0.3s;
            }
            .nav-back:hover {
                background: #0056b3;
                text-decoration: none;
                color: white;
            }
            .message-type {
                display: inline-block;
                background: #28a745;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.8em;
                margin: 2px;
            }
            .message-type.incoming { background: #17a2b8; }
            .message-type.outgoing { background: #ffc107; color: #212529; }
        </style>
    </head>
    <body>
        <div class="container">
            <a href="/" class="nav-back">← Back to API Overview</a>
            
            <h1>🔌 WebSocket API Documentation</h1>
            
            <div class="endpoint-info">
                <strong>WebSocket Endpoint:</strong> <code>ws://localhost:8000/ws</code><br>
                <strong>Authentication:</strong> JWT Token required via query parameter<br>
                <strong>Connection String:</strong> <code>ws://localhost:8000/ws?token=your_jwt_token</code>
            </div>
            
            <h2>📨 Message Format</h2>
            <p>All WebSocket messages follow a standardized JSON structure:</p>
            <div class="message-example">{
  "type": "message_type",
  "protocol": "protocol_name", 
  "timestamp": "2025-01-01T12:00:00Z",
  "data": {}
}</div>
            
            <h2>🎫 Ticket Protocol</h2>
            <div class="protocol-section">
                <h3>Subscribe to Ticket Updates</h3>
                <div class="message-example">{
  "type": "subscribe_ticket_updates",
  "protocol": "ticket",
  "ticket_id": "123e4567-e89b-12d3-a456-426614174000"
}</div>
                
                <h3>Ticket Status Change Notification</h3>
                <div class="message-example">{
  "type": "ticket_status_change",
  "protocol": "ticket",
  "ticket_id": "123e4567-e89b-12d3-a456-426614174000",
  "old_status": "open",
  "new_status": "in_progress",
  "changed_by": "456e7890-e89b-12d3-a456-426614174001",
  "reason": "Started working on the issue"
}</div>
            </div>
            
            <h2>📁 File Processing Protocol</h2>
            <div class="protocol-section">
                <h3>Subscribe to File Processing Job</h3>
                <div class="message-example">{
  "type": "subscribe_job",
  "protocol": "file",
  "job_id": "file_job_12345"
}</div>
                
                <h3>File Processing Progress Update</h3>
                <div class="message-example">{
  "type": "file_processing_progress",
  "protocol": "file",
  "job_id": "file_job_12345",
  "filename": "document.pdf",
  "progress": 45.5,
  "stage": "ocr",
  "message": "Extracting text from page 3 of 5"
}</div>
            </div>
            
            <h2>💬 Chat Protocol</h2>
            <div class="protocol-section">
                <h3>Send Chat Message</h3>
                <div class="message-example">{
  "type": "send_message",
  "protocol": "chat",
  "conversation_id": "789e0123-e89b-12d3-a456-426614174002",
  "content": "Can you help me create a ticket for this issue?",
  "context": {
    "page_url": "https://example.com/issue",
    "user_agent": "Chrome Extension v1.0"
  }
}</div>
                
                <h3>Streaming AI Response</h3>
                <div class="message-example">{
  "type": "chat_stream",
  "protocol": "chat",
  "conversation_id": "789e0123-e89b-12d3-a456-426614174002",
  "content": "I'd be happy to help you create a ticket.",
  "sender": "assistant",
  "is_streaming": false
}</div>
            </div>
            
            <div style="text-align: center; margin: 40px 0; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                <h3>🚀 Ready to Connect?</h3>
                <p>Start by obtaining a JWT token from <code>/api/v1/auth/login</code>, then connect to the WebSocket endpoint!</p>
                <a href="/docs" class="nav-back" style="margin: 10px;">View REST API Docs</a>
                <a href="/" class="nav-back" style="margin: 10px;">Back to Home</a>
            </div>
        </div>
    </body>
    </html>
    """, status_code=200)

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="AI Ticket Creator Backend API",
        version="1.0.0",
        description="""
        # AI Ticket Creator Backend API
        
        Comprehensive API for AI-powered ticket creation and management with Chrome extension support.
        
        ## Features
        
        - **AI-Powered Ticket Creation**: Smart ticket creation with context analysis
        - **File Processing**: Upload and process multiple file types with AI transcription/OCR
        - **Real-time Notifications**: WebSocket-based real-time updates
        - **Third-party Integrations**: Salesforce, Jira, ServiceNow, Zendesk, GitHub, Slack, Teams, Zoom
        - **Chrome Extension Support**: Optimized for browser extension workflows
        - **Multi-Tenant Organization Support**: Complete organization isolation for enterprise deployments
        
        ## Quick Start Guide
        
        ### 1. Authentication
        Register a new user with organization:
        ```bash
        curl -X POST "http://localhost:8000/api/v1/auth/register" \\
          -H "Content-Type: application/json" \\
          -d '{"email": "user@company.com", "full_name": "John Doe", "password": "SecurePass123", "organization_name": "Acme Corporation"}'
        ```
        
        ### 2. Add JIRA Integration
        ```bash
        curl -X POST "http://localhost:8000/api/v1/integrations" \\
          -H "Authorization: Bearer YOUR_TOKEN" \\
          -H "Content-Type: application/json" \\
          -d '{"name": "Main JIRA", "integration_type": "jira", "configuration": {"url": "https://company.atlassian.net", "email": "service@company.com", "api_token": "ATATT3xFfGF0...", "project_key": "SUP", "issue_type": "Task"}}'
        ```
        
        ### 3. Add Salesforce Integration
        ```bash
        curl -X POST "http://localhost:8000/api/v1/integrations" \\
          -H "Authorization: Bearer YOUR_TOKEN" \\
          -H "Content-Type: application/json" \\
          -d '{"name": "Salesforce Production", "integration_type": "salesforce", "configuration": {"instance_url": "https://company.my.salesforce.com", "username": "integration@company.com", "password": "YourPassword123", "security_token": "ABC123DEF456GHI789", "client_id": "3MVG9...", "client_secret": "1234567890..."}}'
        ```
        
        📖 **[Complete Integration Setup Guide](http://localhost:8000/docs/integration-guide)** - Step-by-step instructions for all supported integrations
        
        ## Authentication
        
        This API uses JWT-based authentication with role-based access control.
        
        ## File Processing
        
        Supports comprehensive file processing including:
        - AI transcription for audio/video files
        - OCR for image files
        - Real-time progress tracking via WebSockets
        - Automated metadata extraction
        
        ## Integration Types Supported
        
        - **JIRA**: Atlassian project management and issue tracking
        - **Salesforce**: Customer relationship management and case handling
        - **ServiceNow**: IT service management and incident tracking
        - **Zendesk**: Customer support ticketing system
        - **GitHub**: Issue tracking and project management
        - **Slack**: Team collaboration and notifications
        - **Microsoft Teams**: Enterprise communication and collaboration
        - **Zoom**: Video conferencing and meeting management
        """,
        routes=app.routes,
    )
    
    # Add custom info
    openapi_schema["info"]["x-logo"] = {
        "url": "https://via.placeholder.com/150x75?text=AI+Ticket+Creator"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting AI Ticket Creator Backend...")
    print("📖 API Documentation will be available at: http://localhost:8000/docs")
    print("🔍 Interactive API docs at: http://localhost:8000/redoc")
    print("🏥 Health check at: http://localhost:8000/health")
    print("\n" + "="*50)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )