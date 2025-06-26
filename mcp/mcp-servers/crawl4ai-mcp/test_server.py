#!/usr/bin/env python3
"""
Comprehensive Test Suite for Crawl4AI MCP Server

This test suite validates all functionality of the Crawl4AI MCP server including:
- Basic URL crawling
- Deep crawling strategies
- Content extraction and analysis
- Batch processing
- Search functionality
- Session management
- Error handling and edge cases

Following DevQ.ai testing standards with async support and comprehensive coverage.
"""

import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
import sys
import os

# Add the server directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from server import (
    Crawl4aiMCP,
    CrawlStorage,
    ContentProcessor,
    CrawlConfig,
    CrawlMode,
    ExtractStrategy
)


class MockCrawlResult:
    """Mock CrawlResult for testing"""
    def __init__(self, success=True, url="https://example.com", markdown="Test content", links=None):
        self.success = success
        self.url = url
        self.markdown = markdown
        if links is None:
            self.links = [
                {"href": "/internal-link", "text": "Internal Link"},
                {"href": "https://external.com", "text": "External Link"}
            ]
        else:
            self.links = links
        self.title = "Test Page"
        self.description = "Test description"
        self.status_code = 200
        self.response_time = 0.5


@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory for tests"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def storage(temp_storage_dir):
    """Create CrawlStorage instance with temporary directory"""
    return CrawlStorage(storage_dir=temp_storage_dir)


@pytest.fixture
def processor():
    """Create ContentProcessor instance"""
    return ContentProcessor()


@pytest.fixture
def mock_crawler():
    """Create mock AsyncWebCrawler"""
    mock = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock


class TestCrawlConfig:
    """Test CrawlConfig validation"""

    def test_valid_config(self):
        """Test valid configuration creation"""
        config = CrawlConfig(
            url="https://example.com",
            mode=CrawlMode.SIMPLE,
            max_depth=3,
            timeout=60
        )
        assert config.url == "https://example.com"
        assert config.mode == CrawlMode.SIMPLE
        assert config.max_depth == 3
        assert config.timeout == 60

    def test_invalid_mode(self):
        """Test invalid mode validation"""
        with pytest.raises(ValueError):
            CrawlConfig(url="https://example.com", mode="invalid_mode")

    def test_default_values(self):
        """Test default configuration values"""
        config = CrawlConfig(url="https://example.com")
        assert config.mode == CrawlMode.SIMPLE
        assert config.max_depth == 2
        assert config.max_pages == 10
        assert config.delay == 1.0
        assert config.timeout == 30


class TestCrawlStorage:
    """Test CrawlStorage functionality"""

    @pytest.mark.asyncio
    async def test_store_and_retrieve_result(self, storage):
        """Test storing and retrieving crawl results"""
        crawl_id = "test-crawl-123"
        result_data = {
            "url": "https://example.com",
            "markdown": "Test content",
            "success": True
        }

        # Store result
        success = await storage.store_result(crawl_id, result_data)
        assert success is True

        # Retrieve result
        retrieved = await storage.get_result(crawl_id)
        assert retrieved is not None
        assert retrieved["url"] == "https://example.com"
        assert retrieved["markdown"] == "Test content"
        assert retrieved["crawl_id"] == crawl_id

    @pytest.mark.asyncio
    async def test_list_results(self, storage):
        """Test listing stored results"""
        # Store multiple results
        for i in range(5):
            await storage.store_result(f"crawl-{i}", {"url": f"https://example{i}.com"})

        # List results
        results = await storage.list_results(limit=3)
        assert len(results) == 3
        assert all("url" in result for result in results)

    @pytest.mark.asyncio
    async def test_create_session(self, storage):
        """Test session creation and management"""
        session_name = "test-session"
        config = {"max_depth": 3, "delay": 2.0}

        # Create session
        session_id = await storage.create_session(session_name, config)
        assert session_id is not None

        # Verify session exists
        session = storage.sessions.get(session_id)
        assert session is not None
        assert session["name"] == session_name
        assert session["config"] == config

    @pytest.mark.asyncio
    async def test_add_to_session(self, storage):
        """Test adding crawl results to sessions"""
        # Create session
        session_id = await storage.create_session("test-session", {})

        # Add crawl to session
        crawl_id = "test-crawl"
        success = await storage.add_to_session(session_id, crawl_id)
        assert success is True

        # Verify crawl was added
        session = storage.sessions.get(session_id)
        assert crawl_id in session["crawl_ids"]

    @pytest.mark.asyncio
    async def test_nonexistent_result(self, storage):
        """Test retrieving non-existent result"""
        result = await storage.get_result("nonexistent-id")
        assert result is None


class TestContentProcessor:
    """Test ContentProcessor functionality"""

    def test_extract_metadata(self, processor):
        """Test metadata extraction from crawl result"""
        mock_result = MockCrawlResult()
        metadata = processor.extract_metadata(mock_result)

        assert metadata["url"] == "https://example.com"
        assert metadata["title"] == "Test Page"
        assert metadata["description"] == "Test description"
        assert metadata["success"] is True
        assert metadata["content_length"] == len("Test content")
        assert metadata["links_count"] == 2

    def test_analyze_links(self, processor):
        """Test link analysis functionality"""
        mock_result = MockCrawlResult()
        analysis = processor.analyze_links(mock_result, "https://example.com")

        assert analysis["total"] == 2
        assert analysis["internal_count"] == 1
        assert analysis["external_count"] == 1
        assert len(analysis["internal"]) == 1
        assert len(analysis["external"]) == 1

    def test_chunk_content(self, processor):
        """Test content chunking"""
        content = "This is a test content that should be chunked into smaller pieces."
        chunks = processor.chunk_content(content, chunk_size=20)

        assert len(chunks) > 1
        assert all("content" in chunk for chunk in chunks)
        assert all("index" in chunk for chunk in chunks)
        assert chunks[0]["start_pos"] == 0

    def test_empty_links_analysis(self, processor):
        """Test link analysis with empty links"""
        mock_result = MockCrawlResult(links=[])
        analysis = processor.analyze_links(mock_result, "https://example.com")

        assert analysis["total"] == 0
        assert analysis["internal_count"] == 0
        assert analysis["external_count"] == 0


class TestCrawl4aiMCP:
    """Test main MCP server functionality"""

    @pytest.fixture
    def server(self, temp_storage_dir):
        """Create MCP server instance with temporary storage"""
        with patch('server.CrawlStorage') as mock_storage_class:
            mock_storage = AsyncMock()
            mock_storage_class.return_value = mock_storage
            server = Crawl4aiMCP()
            server.storage = mock_storage
            return server

    @pytest.mark.asyncio
    async def test_crawl_url_success(self, server):
        """Test successful URL crawling"""
        mock_result = MockCrawlResult()

        with patch('server.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun.return_value = mock_result
            mock_crawler.__aenter__.return_value = mock_crawler
            mock_crawler.__aexit__.return_value = None
            mock_crawler_class.return_value = mock_crawler

            result = await server.crawl_url("https://example.com")

            assert result["success"] is True
            assert "crawl_id" in result
            assert result["result"]["url"] == "https://example.com"
            assert result["result"]["success"] is True

    @pytest.mark.asyncio
    async def test_crawl_url_with_extraction_strategy(self, server):
        """Test URL crawling with extraction strategy"""
        mock_result = MockCrawlResult()

        with patch('server.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun.return_value = mock_result
            mock_crawler.__aenter__.return_value = mock_crawler
            mock_crawler.__aexit__.return_value = None
            mock_crawler_class.return_value = mock_crawler

            result = await server.crawl_url(
                "https://example.com",
                extract_strategy="css",
                extraction_config={"title": "h1"}
            )

            assert result["success"] is True
            assert result["result"]["extraction_strategy"] == "css"

    @pytest.mark.asyncio
    async def test_crawl_url_error_handling(self, server):
        """Test error handling in URL crawling"""
        with patch('server.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler_class.side_effect = Exception("Network error")

            result = await server.crawl_url("https://example.com")

            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_batch_crawl(self, server):
        """Test batch crawling functionality"""
        urls = ["https://example1.com", "https://example2.com", "https://example3.com"]

        # Mock the crawl_url method to return success
        async def mock_crawl_url(url, **kwargs):
            return {
                "success": True,
                "result": {
                    "crawl_id": f"crawl-{url.split('/')[-1]}",
                    "url": url
                }
            }

        server.crawl_url = mock_crawl_url
        server.storage.create_session.return_value = "session-123"
        server.storage.add_to_session.return_value = True

        result = await server.batch_crawl(urls, concurrent_limit=2, session_name="test-batch")

        assert result["success"] is True
        assert result["total_urls"] == 3
        assert result["successful"] == 3
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_search_content(self, server):
        """Test content search functionality"""
        # Mock stored results
        mock_results = [
            {
                "crawl_id": "1",
                "url": "https://example1.com",
                "markdown": "This is a test document about Python programming",
                "timestamp": "2024-01-01T00:00:00"
            },
            {
                "crawl_id": "2",
                "url": "https://example2.com",
                "markdown": "JavaScript tutorial for beginners",
                "timestamp": "2024-01-02T00:00:00"
            }
        ]

        server.storage.list_results.return_value = mock_results

        result = await server.search_content("Python", limit=10)

        assert result["success"] is True
        assert result["query"] == "Python"
        assert result["total_matches"] == 1
        assert "Python" in result["results"][0]["snippet"]

    @pytest.mark.asyncio
    async def test_analyze_page(self, server):
        """Test comprehensive page analysis"""
        # Mock crawl_url to return analysis data
        async def mock_crawl_url(url, **kwargs):
            return {
                "success": True,
                "result": {
                    "crawl_id": "analysis-123",
                    "url": url,
                    "metadata": {
                        "title": "Test Page",
                        "description": "Test description",
                        "content_length": 1000,
                        "success": True
                    },
                    "links_analysis": {
                        "internal_count": 5,
                        "external_count": 3,
                        "total": 8
                    }
                }
            }

        server.crawl_url = mock_crawl_url

        result = await server.analyze_page("https://example.com", include_seo=True)

        assert result["success"] is True
        assert "analysis" in result
        assert "seo_analysis" in result["analysis"]
        assert result["analysis"]["seo_analysis"]["internal_links"] == 5

    @pytest.mark.asyncio
    async def test_get_crawl_result(self, server):
        """Test retrieving stored crawl results"""
        mock_result = {
            "crawl_id": "test-123",
            "url": "https://example.com",
            "markdown": "Test content",
            "metadata": {"title": "Test Page"}
        }

        server.storage.get_result.return_value = mock_result

        result = await server.get_crawl_result("test-123", include_content=True)

        assert result["success"] is True
        assert result["crawl_id"] == "test-123"
        assert "content" in result
        assert "metadata" in result

    @pytest.mark.asyncio
    async def test_get_nonexistent_crawl_result(self, server):
        """Test retrieving non-existent crawl result"""
        server.storage.get_result.return_value = None

        result = await server.get_crawl_result("nonexistent-id")

        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_list_crawl_results(self, server):
        """Test listing crawl results"""
        mock_results = [
            {"crawl_id": "1", "url": "https://example1.com", "success": True},
            {"crawl_id": "2", "url": "https://example2.com", "success": True}
        ]

        server.storage.list_results.return_value = mock_results

        result = await server.list_crawl_results(limit=10)

        assert result["success"] is True
        assert result["total_results"] == 2
        assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_create_session(self, server):
        """Test session creation"""
        server.storage.create_session.return_value = "session-123"

        result = await server.create_session("test-session", description="Test session")

        assert result["success"] is True
        assert result["session_id"] == "session-123"
        assert result["session_name"] == "test-session"

    @pytest.mark.asyncio
    async def test_get_page_links(self, server):
        """Test page link extraction"""
        # Mock crawl_url to return links data
        async def mock_crawl_url(url, **kwargs):
            return {
                "success": True,
                "result": {
                    "links_analysis": {
                        "internal": [{"url": "/page1", "text": "Page 1", "type": "internal"}],
                        "external": [{"url": "https://external.com", "text": "External", "type": "external"}],
                        "internal_count": 1,
                        "external_count": 1,
                        "total": 2
                    }
                }
            }

        server.crawl_url = mock_crawl_url

        result = await server.get_page_links("https://example.com", categorize=True)

        assert result["success"] is True
        assert result["total_links"] == 2
        assert "summary" in result
        assert result["summary"]["internal_count"] == 1

    def test_extract_snippet(self, server):
        """Test snippet extraction functionality"""
        content = "This is a long piece of content that contains the word Python in the middle and should be properly truncated."
        snippet = server._extract_snippet(content, "Python", 50)

        assert "Python" in snippet
        assert len(snippet) <= 65  # Adjusted for ellipsis and word boundaries
        assert "..." in snippet


class TestIntegration:
    """Integration tests for full workflows"""

    @pytest.fixture
    def server(self, temp_storage_dir):
        """Create server with real storage for integration tests"""
        server = Crawl4aiMCP()
        server.storage = CrawlStorage(storage_dir=temp_storage_dir)
        return server

    @pytest.mark.asyncio
    async def test_complete_crawl_workflow(self, server):
        """Test complete crawling workflow with real storage"""
        mock_result = MockCrawlResult()

        with patch('server.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun.return_value = mock_result
            mock_crawler.__aenter__.return_value = mock_crawler
            mock_crawler.__aexit__.return_value = None
            mock_crawler_class.return_value = mock_crawler

            # 1. Create session
            session_result = await server.create_session("integration-test")
            assert session_result["success"] is True
            session_id = session_result["session_id"]

            # 2. Crawl URL
            crawl_result = await server.crawl_url("https://example.com")
            assert crawl_result["success"] is True
            crawl_id = crawl_result["crawl_id"]

            # 3. Add to session
            await server.storage.add_to_session(session_id, crawl_id)

            # 4. Retrieve result
            get_result = await server.get_crawl_result(crawl_id)
            assert get_result["success"] is True

            # 5. Search content
            search_result = await server.search_content("Test", session_id=session_id)
            assert search_result["success"] is True

    @pytest.mark.asyncio
    async def test_error_recovery(self, server):
        """Test error recovery and handling"""
        # Test with invalid URL
        with patch('server.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler_class.side_effect = Exception("Invalid URL")

            result = await server.crawl_url("invalid-url")
            assert result["success"] is False
            assert "error" in result

        # Test with crawl failure but continue processing
        with patch('server.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_result = MockCrawlResult(success=False)
            mock_crawler.arun.return_value = mock_result
            mock_crawler.__aenter__.return_value = mock_crawler
            mock_crawler.__aexit__.return_value = None
            mock_crawler_class.return_value = mock_crawler

            result = await server.crawl_url("https://example.com")
            # Should still process even if crawl reports failure
            assert "crawl_id" in result


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
