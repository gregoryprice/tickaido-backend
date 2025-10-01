#!/usr/bin/env python3
"""
Application settings and configuration management
"""

from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings using Pydantic BaseSettings.
    Automatically loads from environment variables and .env files.
    """
    
    # Application Settings
    app_name: str = Field(default="TickAido", description="Application name")
    environment: str = Field(default="development", description="Environment (production, sandbox, development)")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Database Settings
    database_url: str = Field(..., description="PostgreSQL database URL")
    database_echo: bool = Field(default=False, description="Echo SQL queries to logs")
    
    # HTTP Debug Logging Settings
    http_debug_logging_enabled: bool = Field(default=False, description="Enable HTTP debug logging")
    http_debug_log_level: str = Field(default="DEBUG", description="Log level for HTTP debug messages")
    
    # Redis Settings
    redis_url: str = Field(..., description="Redis URL for caching and pub/sub")
    
    # MCP Server Settings
    mcp_server_url: str = Field(default="http://localhost:8001", description="MCP server URL")
    
    # AI Configuration
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    gemini_api_key: Optional[str] = Field(default=None, description="Google Gemini API key")
    
    # AI Usage Limits (for Pydantic AI agents)
    ai_request_limit: int = Field(default=5, description="Default AI request limit per conversation")
    ai_total_tokens_limit: int = Field(default=5000, description="Default AI total tokens limit per conversation")
    ai_max_iterations: int = Field(default=5, description="Default maximum AI agent iterations")
    
    # JWT Authentication
    secret_key: str = Field(default="your-secret-key-change-in-production", description="JWT secret key")
    jwt_secret_key: str = Field(default="your-jwt-secret-key-change-in-production", description="JWT secret key")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    algorithms: List[str] = Field(default=["HS256", "RS256"], description="Allowed JWT algorithms")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration time")
    
    # File Upload Settings
    max_file_size: int = Field(default=25 * 1024 * 1024, description="Maximum file size in bytes (25MB)", env="MAX_FILE_SIZE_BYTES")
    upload_directory: str = Field(default="uploads", description="Directory for file uploads")
    hard_delete_files: bool = Field(default=True, description="Whether to hard delete files (True) or soft delete (False)")
    allowed_file_types: List[str] = Field(
        default=[
            "image/jpeg", "image/png", "image/gif",
            "audio/mpeg", "audio/wav", "audio/mp3",
            "video/mp4", "video/avi", "video/mov",
            "application/pdf", "text/plain",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ],
        description="Allowed MIME types for file uploads"
    )
    
    # Storage Backend Settings
    storage_backend: str = Field(default="local", description="Storage backend (local, s3)")
    
    # AWS S3 Settings
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS access key ID")
    aws_secret_access_key: Optional[str] = Field(default=None, description="AWS secret access key")
    aws_region: str = Field(default="us-east-1", description="AWS region")
    s3_bucket_name: Optional[str] = Field(default=None, description="S3 bucket name for file storage")
    s3_bucket_path: str = Field(default="", description="S3 bucket path prefix")
    cloudfront_domain: Optional[str] = Field(default=None, description="CloudFront domain for CDN URLs")
    
    # WebSocket Settings
    websocket_heartbeat_interval: int = Field(default=30, description="WebSocket heartbeat interval in seconds")
    websocket_timeout: int = Field(default=60, description="WebSocket connection timeout in seconds")
    
    # Celery Settings
    celery_broker_url: Optional[str] = Field(default=None, description="Celery broker URL (defaults to redis_url)")
    celery_result_backend: Optional[str] = Field(default=None, description="Celery result backend (defaults to redis_url)")
    celery_worker_concurrency: int = Field(default=4, description="Number of concurrent worker processes")
    celery_worker_prefetch_multiplier: int = Field(default=1, description="Worker prefetch multiplier")
    
    # Third-party Integration Settings
    salesforce_client_id: Optional[str] = Field(default=None, description="Salesforce client ID")
    salesforce_client_secret: Optional[str] = Field(default=None, description="Salesforce client secret")
    jira_url: Optional[str] = Field(default=None, description="Jira instance URL")
    jira_email: Optional[str] = Field(default=None, description="Jira user email")
    jira_api_token: Optional[str] = Field(default=None, description="Jira API token")
    zendesk_subdomain: Optional[str] = Field(default=None, description="Zendesk subdomain")
    zendesk_email: Optional[str] = Field(default=None, description="Zendesk user email")
    zendesk_api_token: Optional[str] = Field(default=None, description="Zendesk API token")
    github_token: Optional[str] = Field(default=None, description="GitHub personal access token")
    slack_bot_token: Optional[str] = Field(default=None, description="Slack bot token")
    teams_webhook_url: Optional[str] = Field(default=None, description="Microsoft Teams webhook URL")
    
    # CORS Settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080", "chrome-extension://*"],
        description="Allowed CORS origins"
    )
    
    # Rate Limiting Settings
    rate_limit_requests: int = Field(default=100, description="Rate limit requests per minute")
    rate_limit_window: int = Field(default=60, description="Rate limit window in seconds")
    
    # Logging Settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment setting"""
        valid_environments = ["development", "staging", "production", "testing"]
        if v not in valid_environments:
            raise ValueError(f"Environment must be one of: {valid_environments}")
        return v
    
    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v):
        """Validate database URL format"""
        if not v.startswith(("postgresql://", "postgres://", "postgresql+asyncpg://")):
            raise ValueError("Database URL must start with postgresql://, postgres://, or postgresql+asyncpg://")
        return v
    
    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, v):
        """Validate Redis URL format"""
        if not v.startswith("redis://"):
            raise ValueError("Redis URL must start with redis://")
        return v
    
    @field_validator("storage_backend")
    @classmethod
    def validate_storage_backend(cls, v):
        """Validate storage backend setting"""
        valid_backends = ["local", "s3"]
        if v not in valid_backends:
            raise ValueError(f"Storage backend must be one of: {valid_backends}")
        return v
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.environment == "production"
    
    @property
    def effective_celery_broker_url(self) -> str:
        """Get effective Celery broker URL (defaults to Redis URL)"""
        return self.celery_broker_url or self.redis_url
    
    @property
    def effective_celery_result_backend(self) -> str:
        """Get effective Celery result backend (defaults to Redis URL)"""
        return self.celery_result_backend or self.redis_url
    
    @property
    def JWT_SECRET_KEY(self) -> str:
        """Get JWT secret key for compatibility"""
        return self.jwt_secret_key
    
    @property 
    def REDIS_URL(self) -> str:
        """Get Redis URL for compatibility"""
        return self.redis_url
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "env_ignore_empty": True,
        "extra": "ignore"
    }


# Global settings instance
_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """
    Get application settings instance.
    Implements singleton pattern for settings.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

def reload_settings() -> Settings:
    """
    Reload settings from environment/files.
    Useful for testing or configuration changes.
    """
    global _settings
    _settings = Settings()
    return _settings