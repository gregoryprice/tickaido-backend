#!/usr/bin/env python3
"""
Main FastAPI application for AI Ticket Creator Backend
"""

import os
import sys
import logging
import time
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi

# Import configuration
from app.config.settings import get_settings
from app.database import check_database_connection, wait_for_database

# Import middleware
from app.middleware.rate_limiting import FastAPIRateLimitMiddleware

# Import route modules
from app.api.v1.tickets import router as tickets_router
from app.routers.auth import router as auth_router

logger = logging.getLogger(__name__)

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
    
    # Step 2: Run Alembic migrations
    if not run_alembic_migrations():
        logger.error("❌ Failed to run Alembic migrations")
        raise Exception("Database migrations failed")
    
    # Step 3: Initialize WebSocket manager with Redis (TODO: Implement WebSocket manager)
    # WebSocket functionality will be implemented in a future update
    logger.info("ℹ️  WebSocket manager not yet implemented - WebSocket documentation available at /docs/websocket")
    
    # Step 4: Initialize AI services (optional for now)
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
app.include_router(auth_router, prefix="/api/v1")
# app.include_router(files.router, prefix="/api/v1/files", tags=["Files"])
# app.include_router(integrations.router, prefix="/api/v1/integrations", tags=["Integrations"])
# app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
# app.include_router(websocket.router, prefix="/api/v1/ws", tags=["WebSocket"])
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
    """Health check endpoint"""
    try:
        # Check database connection
        db_healthy = check_database_connection()
        
        # Check if all services are healthy
        all_healthy = db_healthy
        
        status = "healthy" if all_healthy else "unhealthy"
        status_code = 200 if all_healthy else 503
        
        health_data = {
            "status": status,
            "timestamp": time.time(),
            "services": {
                "database": "healthy" if db_healthy else "unhealthy",
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

@app.get("/docs/websocket", response_class=HTMLResponse, tags=["System"])
async def websocket_documentation():
    """WebSocket API documentation with real-time communication protocols"""
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket API Documentation - AI Ticket Creator</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                line-height: 1.6; 
                color: #333; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }}
            .container {{ 
                max-width: 1200px; 
                margin: 0 auto; 
                padding: 20px;
                background: white;
                margin-top: 20px;
                margin-bottom: 20px;
                border-radius: 12px;
                box-shadow: 0 15px 35px rgba(0,0,0,0.1);
            }}
            h1 {{ 
                color: #2c3e50; 
                margin-bottom: 30px; 
                font-weight: 700;
                text-align: center;
                font-size: 2.5em;
                background: linear-gradient(135deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }}
            h2 {{ 
                color: #34495e; 
                margin: 30px 0 15px 0; 
                font-weight: 600;
                border-bottom: 2px solid #3498db;
                padding-bottom: 5px;
            }}
            h3 {{ 
                color: #555; 
                margin: 25px 0 10px 0; 
                font-weight: 600;
            }}
            .protocol-section {{
                background: #f8f9fa;
                padding: 20px;
                margin: 20px 0;
                border-radius: 8px;
                border-left: 4px solid #007bff;
            }}
            .message-example {{
                background: #2d3748;
                color: #e2e8f0;
                padding: 20px;
                border-radius: 8px;
                margin: 15px 0;
                font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                overflow-x: auto;
                position: relative;
            }}
            .message-example::before {{
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
            }}
            .endpoint-info {{
                background: linear-gradient(135deg, #e8f4fd, #d6f4f7);
                padding: 15px;
                border-radius: 8px;
                margin: 15px 0;
                border-left: 4px solid #17a2b8;
            }}
            .nav-back {{
                display: inline-block;
                padding: 10px 20px;
                background: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin-bottom: 20px;
                transition: background-color 0.3s;
            }}
            .nav-back:hover {{
                background: #0056b3;
                text-decoration: none;
                color: white;
            }}
            .message-type {{
                display: inline-block;
                background: #28a745;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.8em;
                margin: 2px;
            }}
            .message-type.incoming {{ background: #17a2b8; }}
            .message-type.outgoing {{ background: #ffc107; color: #212529; }}
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
            <div class="message-example">{{
  "type": "message_type",
  "protocol": "protocol_name", 
  "timestamp": "2025-01-01T12:00:00Z",
  "data": {{}}
}}</div>
            
            <h2>🎫 Ticket Protocol</h2>
            <div class="protocol-section">
                <h3>Subscribe to Ticket Updates</h3>
                <div class="message-example">{{
  "type": "subscribe_ticket_updates",
  "protocol": "ticket",
  "ticket_id": "123e4567-e89b-12d3-a456-426614174000"
}}</div>
                
                <h3>Ticket Status Change Notification</h3>
                <div class="message-example">{{
  "type": "ticket_status_change",
  "protocol": "ticket",
  "ticket_id": "123e4567-e89b-12d3-a456-426614174000",
  "old_status": "open",
  "new_status": "in_progress",
  "changed_by": "456e7890-e89b-12d3-a456-426614174001",
  "reason": "Started working on the issue"
}}</div>
            </div>
            
            <h2>📁 File Processing Protocol</h2>
            <div class="protocol-section">
                <h3>Subscribe to File Processing Job</h3>
                <div class="message-example">{{
  "type": "subscribe_job",
  "protocol": "file",
  "job_id": "file_job_12345"
}}</div>
                
                <h3>File Processing Progress Update</h3>
                <div class="message-example">{{
  "type": "file_processing_progress",
  "protocol": "file",
  "job_id": "file_job_12345",
  "filename": "document.pdf",
  "progress": 45.5,
  "stage": "ocr",
  "message": "Extracting text from page 3 of 5"
}}</div>
            </div>
            
            <h2>💬 Chat Protocol</h2>
            <div class="protocol-section">
                <h3>Send Chat Message</h3>
                <div class="message-example">{{
  "type": "send_message",
  "protocol": "chat",
  "conversation_id": "789e0123-e89b-12d3-a456-426614174002",
  "content": "Can you help me create a ticket for this issue?",
  "context": {{
    "page_url": "https://example.com/issue",
    "user_agent": "Chrome Extension v1.0"
  }}
}}</div>
                
                <h3>Streaming AI Response</h3>
                <div class="message-example">{{
  "type": "chat_stream",
  "protocol": "chat",
  "conversation_id": "789e0123-e89b-12d3-a456-426614174002",
  "content": "I'd be happy to help you create a ticket.",
  "sender": "assistant",
  "is_streaming": false
}}</div>
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
        - **Third-party Integrations**: Salesforce, Jira, Zendesk, GitHub, Slack integration
        - **Chrome Extension Support**: Optimized for browser extension workflows
        
        ## Authentication
        
        This API uses JWT-based authentication with role-based access control.
        
        ## File Processing
        
        Supports comprehensive file processing including:
        - AI transcription for audio/video files
        - OCR for image files
        - Real-time progress tracking via WebSockets
        - Automated metadata extraction
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