#!/usr/bin/env python3
"""
Crawl4AI MCP Server

A comprehensive web crawling and content extraction server implementing the MCP protocol.
Provides intelligent web scraping, content processing, knowledge acquisition, and RAG
capabilities using the Crawl4AI library for AI-enhanced development workflows.

This implementation follows DevQ.ai standards with comprehensive MCP integration,
async operations, structured logging, and robust error handling.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Set
from pathlib import Path
import sys
import os
from urllib.parse import urljoin, urlparse

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from mcp import types
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from pydantic import BaseModel, Field, field_validator
    from crawl4ai import AsyncWebCrawler, CrawlResult
    from crawl4ai.extraction_strategy import (
        LLMExtractionStrategy,
        JsonCssExtractionStrategy,
        RegexExtractionStrategy
    )
    from crawl4ai.chunking_strategy import RegexChunking
    from crawl4ai.content_filter_strategy import BM25ContentFilter
    from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, DFSDeepCrawlStrategy
    import aiofiles
    import asyncio
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure crawl4ai, mcp, and pydantic are installed")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CrawlMode:
    """Crawling mode constants"""
    SIMPLE = "simple"
    DEEP = "deep"
    BATCH = "batch"
    EXTRACT = "extract"


class ExtractStrategy:
    """Content extraction strategy constants"""
    LLM = "llm"
    CSS = "css"
    XPATH = "xpath"
    REGEX = "regex"
    MARKDOWN = "markdown"


class CrawlConfig(BaseModel):
    """Configuration for crawl operations"""
    url: str
    mode: str = CrawlMode.SIMPLE
    max_depth: int = Field(default=2, ge=1, le=10)
    max_pages: int = Field(default=10, ge=1, le=100)
    delay: float = Field(default=1.0, ge=0.1, le=10.0)
    timeout: int = Field(default=30, ge=5, le=120)
    follow_redirects: bool = True
    extract_strategy: Optional[str] = None
    extraction_config: Dict[str, Any] = Field(default_factory=dict)
    content_filter: Optional[str] = None
    chunking_enabled: bool = False
    user_agent: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)

    @field_validator('mode')
    @classmethod
    def validate_mode(cls, v):
        valid_modes = [CrawlMode.SIMPLE, CrawlMode.DEEP, CrawlMode.BATCH, CrawlMode.EXTRACT]
        if v not in valid_modes:
            raise ValueError(f"Mode must be one of: {valid_modes}")
        return v


class CrawlStorage:
    """Simple file-based storage for crawl results and session management"""

    def __init__(self, storage_dir: str = "crawl_data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.results_file = self.storage_dir / "crawl_results.json"
        self.sessions_file = self.storage_dir / "sessions.json"
        self.results = {}
        self.sessions = {}
        self._load_data()

    def _load_data(self):
        """Load stored crawl results and sessions"""
        try:
            if self.results_file.exists():
                with open(self.results_file, 'r') as f:
                    stored_data = json.load(f)
                    # Convert string keys back to original format
                    for key, value in stored_data.items():
                        if isinstance(value, dict) and 'timestamp' in value:
                            value['timestamp'] = datetime.fromisoformat(value['timestamp'])
                        self.results[key] = value

            if self.sessions_file.exists():
                with open(self.sessions_file, 'r') as f:
                    stored_sessions = json.load(f)
                    for key, value in stored_sessions.items():
                        if isinstance(value, dict) and 'created_at' in value:
                            value['created_at'] = datetime.fromisoformat(value['created_at'])
                        self.sessions[key] = value

        except Exception as e:
            logger.error(f"Error loading stored data: {e}")

    async def _save_data(self):
        """Save crawl results and sessions to files"""
        try:
            # Prepare data for JSON serialization
            serializable_results = {}
            for key, value in self.results.items():
                if isinstance(value, dict) and 'timestamp' in value:
                    serialized_value = value.copy()
                    serialized_value['timestamp'] = value['timestamp'].isoformat()
                    serializable_results[key] = serialized_value
                else:
                    serializable_results[key] = value

            async with aiofiles.open(self.results_file, 'w') as f:
                await f.write(json.dumps(serializable_results, indent=2, default=str))

            # Prepare sessions for JSON serialization
            serializable_sessions = {}
            for key, value in self.sessions.items():
                if isinstance(value, dict) and 'created_at' in value:
                    serialized_value = value.copy()
                    serialized_value['created_at'] = value['created_at'].isoformat()
                    serializable_sessions[key] = serialized_value
                else:
                    serializable_sessions[key] = value

            async with aiofiles.open(self.sessions_file, 'w') as f:
                await f.write(json.dumps(serializable_sessions, indent=2, default=str))

        except Exception as e:
            logger.error(f"Error saving data: {e}")

    async def store_result(self, crawl_id: str, result_data: Dict[str, Any]) -> bool:
        """Store crawl result"""
        try:
            result_data['timestamp'] = datetime.now()
            result_data['crawl_id'] = crawl_id
            self.results[crawl_id] = result_data
            await self._save_data()
            return True
        except Exception as e:
            logger.error(f"Error storing result {crawl_id}: {e}")
            return False

    async def get_result(self, crawl_id: str) -> Optional[Dict[str, Any]]:
        """Get crawl result by ID"""
        return self.results.get(crawl_id)

    async def list_results(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent crawl results"""
        results = list(self.results.values())
        results.sort(key=lambda x: x.get('timestamp', datetime.min), reverse=True)
        return results[:limit]

    async def create_session(self, session_name: str, config: Dict[str, Any]) -> str:
        """Create a new crawl session"""
        session_id = str(uuid.uuid4())
        session_data = {
            'session_id': session_id,
            'name': session_name,
            'config': config,
            'created_at': datetime.now(),
            'crawl_ids': []
        }
        self.sessions[session_id] = session_data
        await self._save_data()
        return session_id

    async def add_to_session(self, session_id: str, crawl_id: str) -> bool:
        """Add crawl result to session"""
        if session_id in self.sessions:
            self.sessions[session_id]['crawl_ids'].append(crawl_id)
            await self._save_data()
            return True
        return False


class ContentProcessor:
    """Content processing and analysis utilities"""

    @staticmethod
    def extract_metadata(result: CrawlResult) -> Dict[str, Any]:
        """Extract comprehensive metadata from crawl result"""
        return {
            'url': result.url,
            'title': getattr(result, 'title', ''),
            'description': getattr(result, 'description', ''),
            'keywords': getattr(result, 'keywords', []),
            'language': getattr(result, 'language', ''),
            'content_length': len(result.markdown) if result.markdown else 0,
            'links_count': len(result.links) if result.links else 0,
            'images_count': len(result.media) if hasattr(result, 'media') and result.media else 0,
            'success': result.success,
            'status_code': getattr(result, 'status_code', None),
            'response_time': getattr(result, 'response_time', None)
        }

    @staticmethod
    def analyze_links(result: CrawlResult, base_url: str) -> Dict[str, Any]:
        """Analyze and categorize links from crawl result"""
        if not result.links:
            return {
                'internal': [],
                'external': [],
                'total': 0,
                'internal_count': 0,
                'external_count': 0
            }

        base_domain = urlparse(base_url).netloc
        internal_links = []
        external_links = []

        for link in result.links:
            if isinstance(link, dict):
                href = link.get('href', '')
                text = link.get('text', '')
            else:
                href = str(link)
                text = ''

            if href:
                parsed = urlparse(href)
                if not parsed.netloc or parsed.netloc == base_domain:
                    internal_links.append({'url': href, 'text': text, 'type': 'internal'})
                else:
                    external_links.append({'url': href, 'text': text, 'type': 'external'})

        return {
            'internal': internal_links,
            'external': external_links,
            'total': len(internal_links) + len(external_links),
            'internal_count': len(internal_links),
            'external_count': len(external_links)
        }

    @staticmethod
    def chunk_content(content: str, chunk_size: int = 1000) -> List[Dict[str, Any]]:
        """Chunk content for processing"""
        chunks = []
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i + chunk_size]
            chunks.append({
                'index': len(chunks),
                'content': chunk,
                'length': len(chunk),
                'start_pos': i,
                'end_pos': min(i + chunk_size, len(content))
            })
        return chunks


class Crawl4aiMCP:
    """Main Crawl4AI MCP Server class"""

    def __init__(self):
        self.server = Server("crawl4ai-mcp")
        self.storage = CrawlStorage()
        self.processor = ContentProcessor()
        self._setup_handlers()
        logger.info("Crawl4AI MCP Server initialized")

    def _setup_handlers(self):
        """Set up MCP tool handlers"""

        @self.server.list_tools()
        async def list_tools() -> List[types.Tool]:
            """List all available tools"""
            return [
                types.Tool(
                    name="crawl_url",
                    description="Crawl a single URL and extract content with various options",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to crawl"},
                            "extract_strategy": {"type": "string", "enum": ["markdown", "llm", "css", "regex"], "default": "markdown"},
                            "follow_redirects": {"type": "boolean", "default": True},
                            "timeout": {"type": "integer", "default": 30, "minimum": 5, "maximum": 120},
                            "user_agent": {"type": "string", "description": "Custom user agent"},
                            "headers": {"type": "object", "description": "Custom HTTP headers"},
                            "wait_for": {"type": "string", "description": "CSS selector to wait for"},
                            "extraction_config": {"type": "object", "description": "Strategy-specific configuration"}
                        },
                        "required": ["url"]
                    }
                ),
                types.Tool(
                    name="crawl_deep",
                    description="Perform deep crawling with configurable depth and strategy",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "Starting URL for deep crawl"},
                            "max_depth": {"type": "integer", "default": 2, "minimum": 1, "maximum": 5},
                            "max_pages": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                            "strategy": {"type": "string", "enum": ["bfs", "dfs"], "default": "bfs"},
                            "delay": {"type": "number", "default": 1.0, "minimum": 0.1, "maximum": 10.0},
                            "include_patterns": {"type": "array", "items": {"type": "string"}},
                            "exclude_patterns": {"type": "array", "items": {"type": "string"}},
                            "session_name": {"type": "string", "description": "Optional session name for grouping"}
                        },
                        "required": ["url"]
                    }
                ),
                types.Tool(
                    name="extract_structured_data",
                    description="Extract structured data using CSS selectors, XPath, or LLM",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to extract data from"},
                            "strategy": {"type": "string", "enum": ["css", "xpath", "llm"], "default": "css"},
                            "extraction_config": {
                                "type": "object",
                                "description": "Extraction configuration (CSS selectors, XPath expressions, or LLM prompt)"
                            },
                            "schema": {"type": "object", "description": "Expected output schema for validation"}
                        },
                        "required": ["url", "extraction_config"]
                    }
                ),
                types.Tool(
                    name="batch_crawl",
                    description="Crawl multiple URLs in batch with progress tracking",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "urls": {"type": "array", "items": {"type": "string"}, "description": "List of URLs to crawl"},
                            "concurrent_limit": {"type": "integer", "default": 3, "minimum": 1, "maximum": 10},
                            "delay": {"type": "number", "default": 1.0, "minimum": 0.1, "maximum": 5.0},
                            "session_name": {"type": "string", "description": "Session name for grouping results"},
                            "extract_strategy": {"type": "string", "enum": ["markdown", "llm", "css"], "default": "markdown"},
                            "continue_on_error": {"type": "boolean", "default": True}
                        },
                        "required": ["urls"]
                    }
                ),
                types.Tool(
                    name="search_content",
                    description="Search through crawled content using BM25 or semantic search",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "search_type": {"type": "string", "enum": ["bm25", "semantic"], "default": "bm25"},
                            "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                            "session_id": {"type": "string", "description": "Search within specific session"},
                            "url_filter": {"type": "string", "description": "Filter by URL pattern"}
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="analyze_page",
                    description="Comprehensive page analysis including SEO, performance, and content metrics",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to analyze"},
                            "include_links": {"type": "boolean", "default": True},
                            "include_seo": {"type": "boolean", "default": True},
                            "include_performance": {"type": "boolean", "default": True},
                            "link_depth": {"type": "integer", "default": 1, "minimum": 1, "maximum": 3}
                        },
                        "required": ["url"]
                    }
                ),
                types.Tool(
                    name="get_crawl_result",
                    description="Retrieve stored crawl result by ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "crawl_id": {"type": "string", "description": "Crawl result ID"},
                            "include_content": {"type": "boolean", "default": True},
                            "include_metadata": {"type": "boolean", "default": True}
                        },
                        "required": ["crawl_id"]
                    }
                ),
                types.Tool(
                    name="list_crawl_results",
                    description="List recent crawl results with filtering options",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
                            "session_id": {"type": "string", "description": "Filter by session"},
                            "url_pattern": {"type": "string", "description": "Filter by URL pattern"},
                            "include_content": {"type": "boolean", "default": False}
                        }
                    }
                ),
                types.Tool(
                    name="create_session",
                    description="Create a new crawl session for organizing related crawls",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_name": {"type": "string", "description": "Name for the session"},
                            "description": {"type": "string", "description": "Session description"},
                            "config": {"type": "object", "description": "Default configuration for session"}
                        },
                        "required": ["session_name"]
                    }
                ),
                types.Tool(
                    name="get_page_links",
                    description="Extract and analyze all links from a page",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to extract links from"},
                            "categorize": {"type": "boolean", "default": True},
                            "filter_internal": {"type": "boolean", "default": False},
                            "filter_external": {"type": "boolean", "default": False},
                            "include_anchors": {"type": "boolean", "default": True}
                        },
                        "required": ["url"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
            """Handle tool calls"""
            try:
                if name == "crawl_url":
                    result = await self.crawl_url(**arguments)
                elif name == "crawl_deep":
                    result = await self.crawl_deep(**arguments)
                elif name == "extract_structured_data":
                    result = await self.extract_structured_data(**arguments)
                elif name == "batch_crawl":
                    result = await self.batch_crawl(**arguments)
                elif name == "search_content":
                    result = await self.search_content(**arguments)
                elif name == "analyze_page":
                    result = await self.analyze_page(**arguments)
                elif name == "get_crawl_result":
                    result = await self.get_crawl_result(**arguments)
                elif name == "list_crawl_results":
                    result = await self.list_crawl_results(**arguments)
                elif name == "create_session":
                    result = await self.create_session(**arguments)
                elif name == "get_page_links":
                    result = await self.get_page_links(**arguments)
                else:
                    result = {"success": False, "error": f"Unknown tool: {name}"}

                return [types.TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}")
                error_result = {"success": False, "error": str(e)}
                return [types.TextContent(type="text", text=json.dumps(error_result, indent=2))]

    async def crawl_url(self, url: str, **kwargs) -> Dict[str, Any]:
        """Crawl a single URL with comprehensive options"""
        try:
            crawl_id = str(uuid.uuid4())

            # Configure crawler
            crawler_config = {
                'headless': True,
                'verbose': False
            }

            # Set up extraction strategy
            extraction_strategy = kwargs.get('extract_strategy', 'markdown')
            extraction_config = kwargs.get('extraction_config', {})

            async with AsyncWebCrawler(**crawler_config) as crawler:
                # Configure crawl parameters
                crawl_params = {
                    'url': url,
                    'bypass_cache': True,
                    'wait_for': kwargs.get('wait_for'),
                    'timeout': kwargs.get('timeout', 30)
                }

                # Add custom headers if provided
                if kwargs.get('headers'):
                    crawl_params['headers'] = kwargs['headers']

                # Set up extraction strategy
                if extraction_strategy == 'llm' and extraction_config:
                    crawl_params['extraction_strategy'] = LLMExtractionStrategy(
                        provider="openai",
                        api_token=os.getenv("OPENAI_API_KEY"),
                        instruction=extraction_config.get('instruction', 'Extract the main content')
                    )
                elif extraction_strategy == 'css' and extraction_config:
                    crawl_params['extraction_strategy'] = JsonCssExtractionStrategy(
                        extraction_config
                    )
                elif extraction_strategy == 'regex' and extraction_config:
                    crawl_params['extraction_strategy'] = RegexExtractionStrategy(
                        patterns=extraction_config.get('patterns', [])
                    )

                # Perform crawl
                result = await crawler.arun(**crawl_params)

                # Process result
                processed_result = {
                    'crawl_id': crawl_id,
                    'url': url,
                    'success': result.success,
                    'markdown': result.markdown,
                    'cleaned_html': getattr(result, 'cleaned_html', ''),
                    'extracted_content': getattr(result, 'extracted_content', ''),
                    'metadata': self.processor.extract_metadata(result),
                    'links_analysis': self.processor.analyze_links(result, url),
                    'timestamp': datetime.now().isoformat(),
                    'extraction_strategy': extraction_strategy
                }

                # Store result
                await self.storage.store_result(crawl_id, processed_result)

                return {
                    'success': True,
                    'crawl_id': crawl_id,
                    'result': processed_result
                }

        except Exception as e:
            logger.error(f"Error crawling URL {url}: {e}")
            return {'success': False, 'error': str(e)}

    async def crawl_deep(self, url: str, **kwargs) -> Dict[str, Any]:
        """Perform deep crawling with configurable strategy"""
        try:
            session_name = kwargs.get('session_name', f"deep_crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            session_id = await self.storage.create_session(session_name, kwargs)

            max_depth = kwargs.get('max_depth', 2)
            max_pages = kwargs.get('max_pages', 10)
            strategy = kwargs.get('strategy', 'bfs')
            delay = kwargs.get('delay', 1.0)

            crawl_results = []
            crawled_urls = set()

            # Initialize strategy
            if strategy == 'bfs':
                crawl_strategy = BFSDeepCrawlStrategy(
                    max_depth=max_depth,
                    max_pages=max_pages,
                    delay=delay
                )
            else:
                crawl_strategy = DFSDeepCrawlStrategy(
                    max_depth=max_depth,
                    max_pages=max_pages,
                    delay=delay
                )

            async with AsyncWebCrawler(headless=True, verbose=False) as crawler:
                # Start deep crawl
                urls_to_crawl = [(url, 0)]  # (url, depth)

                while urls_to_crawl and len(crawl_results) < max_pages:
                    current_url, depth = urls_to_crawl.pop(0) if strategy == 'bfs' else urls_to_crawl.pop()

                    if current_url in crawled_urls or depth > max_depth:
                        continue

                    crawled_urls.add(current_url)

                    # Crawl current URL
                    result = await crawler.arun(url=current_url, bypass_cache=True)

                    if result.success:
                        crawl_id = str(uuid.uuid4())
                        processed_result = {
                            'crawl_id': crawl_id,
                            'url': current_url,
                            'depth': depth,
                            'success': result.success,
                            'markdown': result.markdown,
                            'metadata': self.processor.extract_metadata(result),
                            'links_analysis': self.processor.analyze_links(result, current_url),
                            'timestamp': datetime.now().isoformat()
                        }

                        crawl_results.append(processed_result)
                        await self.storage.store_result(crawl_id, processed_result)
                        await self.storage.add_to_session(session_id, crawl_id)

                        # Add internal links for next level
                        if depth < max_depth and result.links:
                            base_domain = urlparse(url).netloc
                            for link in result.links:
                                link_url = link.get('href', '') if isinstance(link, dict) else str(link)
                                if link_url and urlparse(link_url).netloc == base_domain:
                                    full_url = urljoin(current_url, link_url)
                                    if full_url not in crawled_urls:
                                        urls_to_crawl.append((full_url, depth + 1))

                    # Respect delay
                    if delay > 0:
                        await asyncio.sleep(delay)

            return {
                'success': True,
                'session_id': session_id,
                'session_name': session_name,
                'total_pages': len(crawl_results),
                'max_depth_reached': max(r.get('depth', 0) for r in crawl_results) if crawl_results else 0,
                'results_summary': [
                    {
                        'crawl_id': r['crawl_id'],
                        'url': r['url'],
                        'depth': r['depth'],
                        'success': r['success'],
                        'content_length': len(r.get('markdown', ''))
                    }
                    for r in crawl_results
                ]
            }

        except Exception as e:
            logger.error(f"Error in deep crawl: {e}")
            return {'success': False, 'error': str(e)}

    async def extract_structured_data(self, url: str, extraction_config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Extract structured data using various strategies"""
        try:
            strategy = kwargs.get('strategy', 'css')
            schema = kwargs.get('schema', {})

            async with AsyncWebCrawler(headless=True, verbose=False) as crawler:
                # Set up extraction strategy
                if strategy == 'css':
                    extraction_strategy = JsonCssExtractionStrategy(extraction_config)
                elif strategy == 'llm':
                    extraction_strategy = LLMExtractionStrategy(
                        provider="openai",
                        api_token=os.getenv("OPENAI_API_KEY"),
                        instruction=extraction_config.get('instruction', 'Extract structured data'),
                        schema=schema
                    )
                elif strategy == 'regex':
                    extraction_strategy = RegexExtractionStrategy(
                        patterns=extraction_config.get('patterns', [])
                    )
                else:
                    return {'success': False, 'error': f'Unsupported extraction strategy: {strategy}'}

                # Perform extraction
                result = await crawler.arun(
                    url=url,
                    extraction_strategy=extraction_strategy,
                    bypass_cache=True
                )

                crawl_id = str(uuid.uuid4())
                processed_result = {
                    'crawl_id': crawl_id,
                    'url': url,
                    'success': result.success,
                    'extracted_content': getattr(result, 'extracted_content', ''),
                    'extraction_strategy': strategy,
                    'extraction_config': extraction_config,
                    'metadata': self.processor.extract_metadata(result),
                    'timestamp': datetime.now().isoformat()
                }

                await self.storage.store_result(crawl_id, processed_result)

                return {
                    'success': True,
                    'crawl_id': crawl_id,
                    'extracted_data': processed_result['extracted_content'],
                    'metadata': processed_result['metadata']
                }

        except Exception as e:
            logger.error(f"Error extracting structured data: {e}")
            return {'success': False, 'error': str(e)}

    async def batch_crawl(self, urls: List[str], **kwargs) -> Dict[str, Any]:
        """Crawl multiple URLs in batch with concurrency control"""
        try:
            session_name = kwargs.get('session_name', f"batch_crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            session_id = await self.storage.create_session(session_name, kwargs)

            concurrent_limit = kwargs.get('concurrent_limit', 3)
            delay = kwargs.get('delay', 1.0)
            continue_on_error = kwargs.get('continue_on_error', True)

            semaphore = asyncio.Semaphore(concurrent_limit)
            results = []

            async def crawl_single_url(url: str):
                async with semaphore:
                    try:
                        result = await self.crawl_url(url, **kwargs)
                        if delay > 0:
                            await asyncio.sleep(delay)
                        return result
                    except Exception as e:
                        error_result = {'success': False, 'url': url, 'error': str(e)}
                        if continue_on_error:
                            return error_result
                        raise

            # Execute batch crawl
            tasks = [crawl_single_url(url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=continue_on_error)

            # Process results
            successful = [r for r in results if isinstance(r, dict) and r.get('success')]
            failed = [r for r in results if isinstance(r, dict) and not r.get('success')]

            # Add successful results to session
            for result in successful:
                if 'result' in result and 'crawl_id' in result['result']:
                    await self.storage.add_to_session(session_id, result['result']['crawl_id'])

            return {
                'success': True,
                'session_id': session_id,
                'session_name': session_name,
                'total_urls': len(urls),
                'successful': len(successful),
                'failed': len(failed),
                'results': results
            }

        except Exception as e:
            logger.error(f"Error in batch crawl: {e}")
            return {'success': False, 'error': str(e)}

    async def search_content(self, query: str, **kwargs) -> Dict[str, Any]:
        """Search through crawled content"""
        try:
            search_type = kwargs.get('search_type', 'bm25')
            limit = kwargs.get('limit', 10)
            session_id = kwargs.get('session_id')
            url_filter = kwargs.get('url_filter')

            results = await self.storage.list_results(limit=1000)  # Get all for search

            # Filter by session if specified
            if session_id:
                session = self.storage.sessions.get(session_id)
                if session:
                    session_crawl_ids = set(session.get('crawl_ids', []))
                    results = [r for r in results if r.get('crawl_id') in session_crawl_ids]

            # Filter by URL pattern if specified
            if url_filter:
                results = [r for r in results if url_filter.lower() in r.get('url', '').lower()]

            # Simple text search implementation
            matching_results = []
            query_lower = query.lower()

            for result in results:
                score = 0
                content = result.get('markdown', '') or result.get('extracted_content', '')

                if query_lower in content.lower():
                    # Simple scoring based on frequency
                    score = content.lower().count(query_lower)

                    matching_results.append({
                        'crawl_id': result.get('crawl_id'),
                        'url': result.get('url'),
                        'score': score,
                        'snippet': self._extract_snippet(content, query, 200),
                        'metadata': result.get('metadata', {}),
                        'timestamp': result.get('timestamp')
                    })

            # Sort by score and limit
            matching_results.sort(key=lambda x: x['score'], reverse=True)
            matching_results = matching_results[:limit]

            return {
                'success': True,
                'query': query,
                'total_matches': len(matching_results),
                'results': matching_results
            }

        except Exception as e:
            logger.error(f"Error searching content: {e}")
            return {'success': False, 'error': str(e)}

    def _extract_snippet(self, content: str, query: str, max_length: int = 200) -> str:
        """Extract a snippet of text around the query match"""
        query_lower = query.lower()
        content_lower = content.lower()

        index = content_lower.find(query_lower)
        if index == -1:
            return content[:max_length] + "..." if len(content) > max_length else content

        start = max(0, index - max_length // 2)
        end = min(len(content), index + len(query) + max_length // 2)

        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet

    async def analyze_page(self, url: str, **kwargs) -> Dict[str, Any]:
        """Comprehensive page analysis"""
        try:
            include_links = kwargs.get('include_links', True)
            include_seo = kwargs.get('include_seo', True)
            include_performance = kwargs.get('include_performance', True)

            # First crawl the page
            crawl_result = await self.crawl_url(url)

            if not crawl_result.get('success'):
                return crawl_result

            page_data = crawl_result['result']
            analysis = {
                'url': url,
                'basic_info': page_data['metadata'],
                'timestamp': datetime.now().isoformat()
            }

            # Add links analysis if requested
            if include_links:
                analysis['links_analysis'] = page_data['links_analysis']

            # Add SEO analysis if requested
            if include_seo:
                analysis['seo_analysis'] = {
                    'title_length': len(page_data['metadata'].get('title', '')),
                    'description_length': len(page_data['metadata'].get('description', '')),
                    'has_title': bool(page_data['metadata'].get('title')),
                    'has_description': bool(page_data['metadata'].get('description')),
                    'content_word_count': len(page_data.get('markdown', '').split()),
                    'internal_links': page_data['links_analysis']['internal_count'],
                    'external_links': page_data['links_analysis']['external_count']
                }

            # Add performance analysis if requested
            if include_performance:
                analysis['performance_analysis'] = {
                    'content_size': page_data['metadata']['content_length'],
                    'load_success': page_data['metadata']['success'],
                    'status_code': page_data['metadata'].get('status_code'),
                    'response_time': page_data['metadata'].get('response_time')
                }

            return {
                'success': True,
                'analysis': analysis,
                'crawl_id': page_data['crawl_id']
            }

        except Exception as e:
            logger.error(f"Error analyzing page: {e}")
            return {'success': False, 'error': str(e)}

    async def get_crawl_result(self, crawl_id: str, **kwargs) -> Dict[str, Any]:
        """Retrieve stored crawl result"""
        try:
            include_content = kwargs.get('include_content', True)
            include_metadata = kwargs.get('include_metadata', True)

            result = await self.storage.get_result(crawl_id)

            if not result:
                return {'success': False, 'error': f'Crawl result {crawl_id} not found'}

            response = {'success': True, 'crawl_id': crawl_id}

            if include_metadata:
                response['metadata'] = result.get('metadata', {})
                response['url'] = result.get('url')
                response['timestamp'] = result.get('timestamp')

            if include_content:
                response['content'] = {
                    'markdown': result.get('markdown', ''),
                    'extracted_content': result.get('extracted_content', ''),
                    'links_analysis': result.get('links_analysis', {})
                }

            return response

        except Exception as e:
            logger.error(f"Error getting crawl result: {e}")
            return {'success': False, 'error': str(e)}

    async def list_crawl_results(self, **kwargs) -> Dict[str, Any]:
        """List recent crawl results"""
        try:
            limit = kwargs.get('limit', 20)
            session_id = kwargs.get('session_id')
            url_pattern = kwargs.get('url_pattern')
            include_content = kwargs.get('include_content', False)

            results = await self.storage.list_results(limit=limit * 2)  # Get more for filtering

            # Filter by session if specified
            if session_id:
                session = self.storage.sessions.get(session_id)
                if session:
                    session_crawl_ids = set(session.get('crawl_ids', []))
                    results = [r for r in results if r.get('crawl_id') in session_crawl_ids]

            # Filter by URL pattern if specified
            if url_pattern:
                results = [r for r in results if url_pattern.lower() in r.get('url', '').lower()]

            # Limit results
            results = results[:limit]

            # Format results
            formatted_results = []
            for result in results:
                formatted_result = {
                    'crawl_id': result.get('crawl_id'),
                    'url': result.get('url'),
                    'success': result.get('success'),
                    'timestamp': result.get('timestamp'),
                    'metadata': result.get('metadata', {})
                }

                if include_content:
                    formatted_result['content'] = {
                        'markdown': result.get('markdown', ''),
                        'extracted_content': result.get('extracted_content', '')
                    }

                formatted_results.append(formatted_result)

            return {
                'success': True,
                'total_results': len(formatted_results),
                'results': formatted_results
            }

        except Exception as e:
            logger.error(f"Error listing crawl results: {e}")
            return {'success': False, 'error': str(e)}

    async def create_session(self, session_name: str, **kwargs) -> Dict[str, Any]:
        """Create a new crawl session"""
        try:
            description = kwargs.get('description', '')
            config = kwargs.get('config', {})

            session_config = {
                'session_name': session_name,
                'description': description,
                'config': config
            }

            session_id = await self.storage.create_session(session_name, session_config)

            return {
                'success': True,
                'session_id': session_id,
                'session_name': session_name,
                'description': description
            }

        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return {'success': False, 'error': str(e)}

    async def get_page_links(self, url: str, **kwargs) -> Dict[str, Any]:
        """Extract and analyze links from a page"""
        try:
            categorize = kwargs.get('categorize', True)
            filter_internal = kwargs.get('filter_internal', False)
            filter_external = kwargs.get('filter_external', False)

            # Crawl the page to get links
            crawl_result = await self.crawl_url(url)

            if not crawl_result.get('success'):
                return crawl_result

            links_analysis = crawl_result['result']['links_analysis']

            # Apply filters
            links = []
            if not filter_external:
                links.extend(links_analysis['external'])
            if not filter_internal:
                links.extend(links_analysis['internal'])

            response = {
                'success': True,
                'url': url,
                'total_links': len(links),
                'links': links
            }

            if categorize:
                response['summary'] = {
                    'internal_count': links_analysis['internal_count'],
                    'external_count': links_analysis['external_count'],
                    'total_count': links_analysis['total']
                }

            return response

        except Exception as e:
            logger.error(f"Error getting page links: {e}")
            return {'success': False, 'error': str(e)}


def main():
    """Main entry point for the MCP server"""
    async def run_server():
        server = Crawl4aiMCP()
        async with stdio_server() as (read_stream, write_stream):
            await server.server.run(read_stream, write_stream, server.server.create_initialization_options())

    logger.info("Starting Crawl4AI MCP Server...")
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
