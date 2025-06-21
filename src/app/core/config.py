"""
Configuration Module for Machina Registry Service

This module provides centralized configuration management for the Machina Registry
Service, implementing DevQ.ai's standard configuration patterns with environment
variable support, validation, and type safety.

Features:
- Environment-based configuration with .env file support
- Pydantic validation for type safety and data validation
- Separate settings for different environments (development, production, testing)
- Database connection string generation
- Redis connection configuration
- Logfire observability integration settings
"""

import os
from typing import Optional, List
from pydantic import field_validator, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings with environment variable support.

    This class uses Pydantic BaseSettings to automatically load configuration
    from environment variables, with fallback defaults for development.
    """

    # Application Configuration
    PROJECT_NAME: str = Field(default="Machina Registry Service", description="Application name")
    VERSION: str = Field(default="1.0.0", description="Application version")
    API_V1_STR: str = Field(default="/api/v1", description="API version prefix")
    DEBUG: bool = Field(default=False, description="Debug mode flag")
    ENVIRONMENT: str = Field(default="development", description="Environment name")

    # Server Configuration
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    RELOAD: bool = Field(default=True, description="Auto-reload on code changes")

    # Database Configuration
    POSTGRES_SERVER: str = Field(default="localhost", description="PostgreSQL server host")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL server port")
    POSTGRES_USER: str = Field(default="postgres", description="PostgreSQL username")
    POSTGRES_PASSWORD: str = Field(default="postgres", description="PostgreSQL password")
    POSTGRES_DB: str = Field(default="machina_registry", description="PostgreSQL database name")
    DATABASE_URI: Optional[str] = Field(default=None, description="Complete database URI")

    # Redis Configuration
    REDIS_HOST: str = Field(default="localhost", description="Redis server host")
    REDIS_PORT: int = Field(default=6379, description="Redis server port")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis password")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    REDIS_URI: Optional[str] = Field(default=None, description="Complete Redis URI")

    # Cache Configuration
    CACHE_TTL: int = Field(default=3600, description="Default cache TTL in seconds")
    CACHE_PREFIX: str = Field(default="machina:registry:", description="Cache key prefix")

    # Security Configuration
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production", description="Secret key for signing")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="JWT token expiration time")

    # Logfire Configuration
    LOGFIRE_TOKEN: Optional[str] = Field(default=None, description="Logfire API token")
    LOGFIRE_PROJECT_NAME: Optional[str] = Field(default=None, description="Logfire project name")
    LOGFIRE_SERVICE_NAME: str = Field(default="machina-registry", description="Logfire service name")
    LOGFIRE_ENVIRONMENT: Optional[str] = Field(default=None, description="Logfire environment")

    # MCP Configuration
    MCP_SERVER_NAME: str = Field(default="machina-registry", description="MCP server name")
    MCP_SERVER_VERSION: str = Field(default="1.0.0", description="MCP server version")
    MCP_TOOLS_ENABLED: bool = Field(default=True, description="Enable MCP tools")

    # Registry Configuration
    REGISTRY_HEALTH_CHECK_INTERVAL: int = Field(default=30, description="Health check interval in seconds")
    REGISTRY_MAX_RETRIES: int = Field(default=3, description="Maximum retry attempts for failed operations")
    REGISTRY_TIMEOUT: int = Field(default=10, description="Request timeout in seconds")

    # CORS Configuration
    CORS_ORIGINS: List[str] = Field(default=["*"], description="Allowed CORS origins")
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, description="Allow CORS credentials")
    CORS_ALLOW_METHODS: List[str] = Field(default=["*"], description="Allowed CORS methods")
    CORS_ALLOW_HEADERS: List[str] = Field(default=["*"], description="Allowed CORS headers")

    # Performance Configuration
    MAX_CONNECTIONS: int = Field(default=100, description="Maximum database connections")
    POOL_SIZE: int = Field(default=10, description="Database connection pool size")
    POOL_OVERFLOW: int = Field(default=20, description="Database connection pool overflow")

    @field_validator("DATABASE_URI", mode="before")
    @classmethod
    def assemble_database_uri(cls, v: Optional[str], info) -> str:
        """Generate database URI from individual components if not provided."""
        if isinstance(v, str):
            return v

        # Get field values from info context
        field_values = info.data if hasattr(info, 'data') else {}

        # Use async PostgreSQL driver for SQLAlchemy
        return (
            f"postgresql+asyncpg://"
            f"{field_values.get('POSTGRES_USER', 'postgres')}:"
            f"{field_values.get('POSTGRES_PASSWORD', 'postgres')}@"
            f"{field_values.get('POSTGRES_SERVER', 'localhost')}:"
            f"{field_values.get('POSTGRES_PORT', 5432)}/"
            f"{field_values.get('POSTGRES_DB', 'machina_registry')}"
        )

    @field_validator("REDIS_URI", mode="before")
    @classmethod
    def assemble_redis_uri(cls, v: Optional[str], info) -> str:
        """Generate Redis URI from individual components if not provided."""
        if isinstance(v, str):
            return v

        # Get field values from info context
        field_values = info.data if hasattr(info, 'data') else {}

        # Build Redis URI with optional password
        password_part = ""
        if field_values.get("REDIS_PASSWORD"):
            password_part = f":{field_values.get('REDIS_PASSWORD')}@"

        return (
            f"redis://"
            f"{password_part}"
            f"{field_values.get('REDIS_HOST', 'localhost')}:"
            f"{field_values.get('REDIS_PORT', 6379)}/"
            f"{field_values.get('REDIS_DB', 0)}"
        )

    @field_validator("LOGFIRE_PROJECT_NAME", mode="before")
    @classmethod
    def set_logfire_project_name(cls, v: Optional[str], info) -> str:
        """Set Logfire project name from PROJECT_NAME if not provided."""
        if v:
            return v
        field_values = info.data if hasattr(info, 'data') else {}
        return field_values.get("PROJECT_NAME", "machina-registry").lower().replace(" ", "-")

    @field_validator("LOGFIRE_ENVIRONMENT", mode="before")
    @classmethod
    def set_logfire_environment(cls, v: Optional[str], info) -> str:
        """Set Logfire environment from ENVIRONMENT if not provided."""
        if v:
            return v
        field_values = info.data if hasattr(info, 'data') else {}
        return field_values.get("ENVIRONMENT", "development")

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Validate that secret key is changed in production."""
        field_values = info.data if hasattr(info, 'data') else {}
        if field_values.get("ENVIRONMENT") == "production" and v == "your-secret-key-change-in-production":
            raise ValueError("SECRET_KEY must be changed in production environment")
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def is_development(self) -> bool:
        """Check if application is running in development mode."""
        return self.ENVIRONMENT.lower() in ("development", "dev", "local")

    @property
    def is_production(self) -> bool:
        """Check if application is running in production mode."""
        return self.ENVIRONMENT.lower() in ("production", "prod")

    @property
    def is_testing(self) -> bool:
        """Check if application is running in testing mode."""
        return self.ENVIRONMENT.lower() in ("testing", "test")

    @property
    def logfire_config(self) -> dict:
        """Get Logfire configuration dictionary."""
        config = {
            "service_name": self.LOGFIRE_SERVICE_NAME,
            "environment": self.LOGFIRE_ENVIRONMENT,
        }

        if self.LOGFIRE_TOKEN:
            config["token"] = self.LOGFIRE_TOKEN

        if self.LOGFIRE_PROJECT_NAME:
            config["project_name"] = self.LOGFIRE_PROJECT_NAME

        return config

    @property
    def database_config(self) -> dict:
        """Get database configuration dictionary."""
        return {
            "url": self.DATABASE_URI,
            "echo": self.DEBUG,
            "pool_size": self.POOL_SIZE,
            "max_overflow": self.POOL_OVERFLOW,
            "pool_pre_ping": True,
            "pool_recycle": 300,
        }

    @property
    def redis_config(self) -> dict:
        """Get Redis configuration dictionary."""
        return {
            "url": self.REDIS_URI,
            "encoding": "utf-8",
            "decode_responses": True,
            "socket_connect_timeout": 5,
            "socket_timeout": 5,
            "retry_on_timeout": True,
            "health_check_interval": 30,
        }

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        validate_assignment = True


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Get application settings instance.

    This function provides a way to access settings throughout the application
    and can be used with FastAPI's dependency injection system.

    Returns:
        Settings: The global settings instance
    """
    return settings


def reload_settings() -> Settings:
    """
    Reload settings from environment variables.

    This function creates a new settings instance, useful for testing
    or when environment variables have changed.

    Returns:
        Settings: A new settings instance
    """
    global settings
    settings = Settings()
    return settings


# Environment-specific configuration validation
def validate_environment_config():
    """
    Validate configuration for the current environment.

    This function performs environment-specific validation to ensure
    that required configuration is present and valid for the current
    deployment environment.

    Raises:
        ValueError: If required configuration is missing or invalid
    """
    if settings.is_production:
        # Production-specific validation
        required_prod_settings = [
            "SECRET_KEY",
            "POSTGRES_PASSWORD",
            "LOGFIRE_TOKEN",
        ]

        for setting in required_prod_settings:
            value = getattr(settings, setting, None)
            if not value or (isinstance(value, str) and value.startswith("your-")):
                raise ValueError(f"Production environment requires {setting} to be set")

    elif settings.is_development:
        # Development-specific validation
        if not settings.DEBUG:
            print("Warning: DEBUG is False in development environment")

    elif settings.is_testing:
        # Testing-specific validation
        if not settings.DATABASE_URI.endswith("test"):
            print("Warning: Using non-test database in testing environment")


# Initialize and validate configuration on import
validate_environment_config()
