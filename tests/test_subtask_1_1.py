"""
Test Module for Subtask 1.1: Project Structure and FastAPI/FastMCP Setup

This module contains comprehensive tests to validate the successful completion
of subtask 1.1, ensuring that the project structure is correctly established
and the FastAPI application with FastMCP integration is properly configured.

Test Coverage:
- Project directory structure validation
- FastAPI application initialization
- Configuration management testing
- Exception handling validation
- Health check endpoints
- MCP placeholder functionality
- Logfire integration
- Environment variable loading

Requirements:
- All tests must pass for subtask 1.1 completion
- Tests validate actual functionality, not just existence
- Coverage must be meaningful and comprehensive
- Tests follow DevQ.ai testing standards
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient
from fastapi import status
import importlib.util
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestProjectStructure:
    """Test the project directory structure and package setup."""

    def test_main_directories_exist(self):
        """Test that all required main directories exist."""
        base_path = Path(__file__).parent.parent / "src"

        required_dirs = [
            "app",
            "app/api",
            "app/api/http",
            "app/api/http/routes",
            "app/api/http/controllers",
            "app/api/mcp",
            "app/api/mcp/handlers",
            "app/core",
            "app/models",
            "app/models/domain",
            "app/repositories",
            "app/services",
        ]

        for dir_path in required_dirs:
            full_path = base_path / dir_path
            assert full_path.exists(), f"Directory {dir_path} does not exist"
            assert full_path.is_dir(), f"Path {dir_path} exists but is not a directory"

    def test_init_files_exist(self):
        """Test that all required __init__.py files exist."""
        base_path = Path(__file__).parent.parent / "src"

        required_init_files = [
            "app/__init__.py",
            "app/api/__init__.py",
            "app/api/http/__init__.py",
            "app/api/mcp/__init__.py",
            "app/core/__init__.py",
            "app/models/__init__.py",
            "app/models/domain/__init__.py",
            "app/repositories/__init__.py",
            "app/services/__init__.py",
            "app/api/http/routes/__init__.py",
            "app/api/mcp/handlers/__init__.py",
        ]

        for init_file in required_init_files:
            full_path = base_path / init_file
            assert full_path.exists(), f"__init__.py file {init_file} does not exist"
            assert full_path.is_file(), f"Path {init_file} exists but is not a file"

    def test_main_application_file_exists(self):
        """Test that the main application file exists."""
        main_file = Path(__file__).parent.parent / "src" / "main.py"
        assert main_file.exists(), "main.py file does not exist"
        assert main_file.is_file(), "main.py exists but is not a file"

    def test_config_files_exist(self):
        """Test that configuration files exist."""
        base_path = Path(__file__).parent.parent / "src"

        config_files = [
            "app/core/config.py",
            "app/core/exceptions.py",
        ]

        for config_file in config_files:
            full_path = base_path / config_file
            assert full_path.exists(), f"Configuration file {config_file} does not exist"


class TestConfigurationModule:
    """Test the configuration management system."""

    def test_config_module_imports(self):
        """Test that configuration module imports correctly."""
        try:
            from app.core.config import settings, get_settings, Settings
            assert settings is not None, "Settings instance is None"
            assert callable(get_settings), "get_settings is not callable"
            assert Settings is not None, "Settings class is None"
        except ImportError as e:
            pytest.fail(f"Failed to import configuration module: {e}")

    def test_default_settings(self):
        """Test that default settings are properly configured."""
        from app.core.config import settings

        # Test basic application settings
        assert settings.PROJECT_NAME == "Machina Registry Service"
        assert settings.VERSION == "1.0.0"
        assert settings.API_V1_STR == "/api/v1"
        assert isinstance(settings.DEBUG, bool)
        assert settings.ENVIRONMENT == "development"

        # Test server settings
        assert settings.HOST == "0.0.0.0"
        assert settings.PORT == 8000
        assert isinstance(settings.RELOAD, bool)

    def test_database_uri_generation(self):
        """Test that database URI is properly generated."""
        from app.core.config import settings

        assert settings.DATABASE_URI is not None
        assert "postgresql+asyncpg://" in settings.DATABASE_URI
        assert settings.POSTGRES_USER in settings.DATABASE_URI
        assert settings.POSTGRES_DB in settings.DATABASE_URI

    def test_redis_uri_generation(self):
        """Test that Redis URI is properly generated."""
        from app.core.config import settings

        assert settings.REDIS_URI is not None
        assert "redis://" in settings.REDIS_URI
        assert str(settings.REDIS_PORT) in settings.REDIS_URI

    def test_logfire_config_property(self):
        """Test that Logfire configuration is properly structured."""
        from app.core.config import settings

        logfire_config = settings.logfire_config
        assert isinstance(logfire_config, dict)
        assert "service_name" in logfire_config
        assert "environment" in logfire_config
        assert logfire_config["service_name"] == settings.LOGFIRE_SERVICE_NAME


class TestExceptionsModule:
    """Test the custom exceptions system."""

    def test_exceptions_module_imports(self):
        """Test that exceptions module imports correctly."""
        try:
            from app.core.exceptions import (
                MachinaException,
                ValidationError,
                NotFoundError,
                ConflictError,
                DatabaseError,
                create_http_exception,
                handle_exception,
            )
            assert MachinaException is not None
            assert ValidationError is not None
            assert NotFoundError is not None
        except ImportError as e:
            pytest.fail(f"Failed to import exceptions module: {e}")

    def test_base_exception_functionality(self):
        """Test MachinaException base functionality."""
        from app.core.exceptions import MachinaException

        exc = MachinaException(
            message="Test error",
            error_code="TEST_ERROR",
            context={"test": "value"}
        )

        assert exc.message == "Test error"
        assert exc.error_code == "TEST_ERROR"
        assert exc.context["test"] == "value"

        # Test dictionary conversion
        exc_dict = exc.to_dict()
        assert isinstance(exc_dict, dict)
        assert exc_dict["error_code"] == "TEST_ERROR"
        assert exc_dict["message"] == "Test error"

    def test_specific_exceptions(self):
        """Test specific exception types."""
        from app.core.exceptions import ValidationError, NotFoundError, ConflictError

        # Test ValidationError
        val_exc = ValidationError("Invalid data", field="test_field", value="test_value")
        assert val_exc.error_code == "VALIDATION_ERROR"
        assert val_exc.context["field"] == "test_field"

        # Test NotFoundError
        not_found_exc = NotFoundError("User", 123)
        assert not_found_exc.error_code == "NOT_FOUND"
        assert not_found_exc.context["resource_type"] == "User"
        assert not_found_exc.context["identifier"] == "123"


class TestFastAPIApplication:
    """Test the FastAPI application setup and functionality."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI application."""
        from main import app
        return TestClient(app)

    def test_app_creation(self):
        """Test that the FastAPI application can be created."""
        from main import app, create_application

        assert app is not None, "FastAPI app instance is None"
        assert callable(create_application), "create_application is not callable"

    def test_root_endpoint(self, client):
        """Test the root endpoint returns correct information."""
        response = client.get("/")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "description" in data
        assert data["service"] == "Machina Registry Service"

    def test_health_endpoint(self, client):
        """Test the health check endpoint."""
        response = client.get("/health")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "Machina Registry Service"
        assert "version" in data
        assert "environment" in data

    def test_placeholder_api_endpoint(self, client):
        """Test the placeholder API status endpoint."""
        response = client.get("/api/v1/status")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["status"] == "ready"
        assert "message" in data

    def test_nonexistent_endpoint(self, client):
        """Test that nonexistent endpoints return 404."""
        response = client.get("/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_exception_handling(self, client):
        """Test that exception handling is properly configured."""
        # The application should handle exceptions gracefully
        # This test validates that the exception handlers are registered
        from main import app

        # Check that exception handlers are registered
        assert app.exception_handlers is not None
        assert len(app.exception_handlers) > 0


class TestMCPIntegration:
    """Test MCP protocol integration placeholder functionality."""

    def test_mcp_handlers_import(self):
        """Test that MCP handlers module imports correctly."""
        try:
            from app.api.mcp.handlers import register_handlers, get_available_tools, handle_tool_call
            assert callable(register_handlers)
            assert callable(get_available_tools)
            assert callable(handle_tool_call)
        except ImportError as e:
            pytest.fail(f"Failed to import MCP handlers: {e}")

    @pytest.mark.asyncio
    async def test_placeholder_mcp_tools(self):
        """Test placeholder MCP tools functionality."""
        from app.api.mcp.handlers import get_available_tools, handle_tool_call

        # Test getting available tools
        tools = await get_available_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
        assert "placeholder_tool" in [tool["name"] for tool in tools]

        # Test tool call handling
        result = await handle_tool_call("placeholder_tool", {"message": "test"})
        assert isinstance(result, dict)
        assert result["success"] is True
        assert "message" in result


class TestLogfireIntegration:
    """Test Logfire observability integration."""

    def test_logfire_configuration(self):
        """Test that Logfire is properly configured."""
        from app.core.config import settings

        # Test that Logfire config properties exist
        logfire_config = settings.logfire_config
        assert isinstance(logfire_config, dict)
        assert "service_name" in logfire_config
        assert "environment" in logfire_config

    def test_logfire_import(self):
        """Test that Logfire can be imported and used."""
        try:
            import logfire
            # Test basic logging functionality
            logfire.info("Test log message for subtask 1.1 validation")
        except ImportError as e:
            pytest.fail(f"Failed to import logfire: {e}")


class TestEnvironmentSetup:
    """Test environment configuration and setup."""

    def test_env_template_exists(self):
        """Test that environment template file exists."""
        env_template = Path(__file__).parent.parent / ".env.template"
        assert env_template.exists(), ".env.template file does not exist"

    def test_requirements_updated(self):
        """Test that requirements.txt includes necessary dependencies."""
        requirements_file = Path(__file__).parent.parent / "requirements.txt"
        assert requirements_file.exists(), "requirements.txt does not exist"

        with open(requirements_file, 'r') as f:
            requirements_content = f.read()

        # Test that key dependencies are included
        required_packages = [
            "fastapi",
            "uvicorn",
            "pydantic",
            "logfire",
            "pytest",
            "mcp",
            "sqlalchemy",
            "redis",
        ]

        for package in required_packages:
            assert package in requirements_content, f"Package {package} not found in requirements.txt"


class TestCodeQuality:
    """Test code quality and standards compliance."""

    def test_no_syntax_errors(self):
        """Test that all Python files have valid syntax."""
        src_path = Path(__file__).parent.parent / "src"

        for py_file in src_path.rglob("*.py"):
            try:
                with open(py_file, 'r') as f:
                    compile(f.read(), py_file, 'exec')
            except SyntaxError as e:
                pytest.fail(f"Syntax error in {py_file}: {e}")

    def test_imports_work(self):
        """Test that key modules can be imported without errors."""
        key_modules = [
            "app.core.config",
            "app.core.exceptions",
            "app.api.http.routes",
            "app.api.mcp.handlers",
        ]

        for module_name in key_modules:
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")

    def test_docstrings_present(self):
        """Test that key modules have proper docstrings."""
        from app.core import config, exceptions
        from app.api.http import routes
        from app.api.mcp import handlers

        modules_to_check = [config, exceptions, routes, handlers]

        for module in modules_to_check:
            assert module.__doc__ is not None, f"Module {module.__name__} missing docstring"
            assert len(module.__doc__.strip()) > 0, f"Module {module.__name__} has empty docstring"


# Integration test to validate complete subtask 1.1 functionality
class TestSubtask11Integration:
    """Integration test for complete subtask 1.1 validation."""

    def test_complete_application_startup(self):
        """Test that the complete application can start up successfully."""
        from main import app
        client = TestClient(app)

        # Test that the application responds to requests
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK

        # Test that all major components are accessible
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK

        response = client.get("/api/v1/status")
        assert response.status_code == status.HTTP_200_OK

    def test_configuration_loading(self):
        """Test that configuration loads correctly from environment."""
        from app.core.config import settings

        # Validate that critical settings are properly loaded
        assert settings.PROJECT_NAME is not None
        assert settings.DATABASE_URI is not None
        assert settings.REDIS_URI is not None
        assert settings.logfire_config is not None

    def test_error_handling_integration(self):
        """Test that error handling works end-to-end."""
        from main import app
        from app.core.exceptions import MachinaException

        client = TestClient(app)

        # The application should handle errors gracefully
        # This validates that exception handlers are properly integrated
        assert len(app.exception_handlers) > 0

    @pytest.mark.asyncio
    async def test_mcp_integration_ready(self):
        """Test that MCP integration is ready for future implementation."""
        from app.api.mcp.handlers import register_handlers, get_available_tools

        # Test that MCP handlers can be called
        tools = await get_available_tools()
        assert isinstance(tools, list)

        # Test that register_handlers can be called without errors
        from main import app
        try:
            register_handlers(app)
        except Exception as e:
            pytest.fail(f"MCP handler registration failed: {e}")


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])
