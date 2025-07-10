#!/usr/bin/env python3
"""
Crawl4AI MCP Server
Web crawling and RAG capabilities for AI agents and AI coding assistants using FastMCP framework.
"""

import asyncio
import json
import os
import hashlib
import re
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

# Add parent directory to path for FastMCP imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastmcp import FastMCP
import logfire

try:
    import httpx
    import aiofiles
    from bs4 import BeautifulSoup
    from pydantic import BaseModel, Field, HttpUrl
    CRAWL4AI_DEPS_AVAILABLE = True
except ImportError:
    CRAWL4AI_DEPS_AVAILABLE = False
    httpx = None
    aiofiles = None
    BeautifulSoup = None
    BaseModel = object
    def Field(*args, **kwargs):
        return None
    HttpUrl = str


class CrawlResult(BaseModel if CRAWL4AI_DEPS_AVAILABLE else object):
    """Crawl result model"""
    url: str = Field(..., description="Crawled URL")
    title: Optional[str] = Field(None, description="Page title")
    content: str = Field(..., description="Extracted content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Page metadata")
    links: List[str] = Field(default_factory=list, description="Extracted links")
    images: List[str] = Field(default_factory=list, description="Extracted images")
    crawled_at: str = Field(..., description="Crawl timestamp")
    status_code: int = Field(..., description="HTTP status code")
    content_type: Optional[str] = Field(None, description="Content type")


class Crawl4AIMCP:
    """
    Crawl4AI MCP Server using FastMCP framework

    Provides comprehensive web crawling and RAG capabilities including:
    - Web page crawling and content extraction
    - Content cleaning and preprocessing
    - Link discovery and sitemap parsing
    - Image extraction and analysis
    - Content chunking for RAG applications
    - Search engine friendly crawling
    - Rate limiting and politeness
    """

    def __init__(self):
        self.mcp = FastMCP("crawl4ai-mcp", version="1.0.0",
                          description="Web crawling and RAG capabilities for AI agents")
        self.user_agent = os.getenv("CRAWL4AI_USER_AGENT",
                                   "Crawl4AI-MCP/1.0 (+https://github.com/devq-ai/machina)")
        self.max_content_length = int(os.getenv("CRAWL4AI_MAX_CONTENT_LENGTH", "10485760"))  # 10MB
        self.request_timeout = int(os.getenv("CRAWL4AI_TIMEOUT", "30"))
        self.crawl_delay = float(os.getenv("CRAWL4AI_DELAY", "1.0"))
        self.storage_path = os.getenv("CRAWL4AI_STORAGE_PATH", "./crawl_cache")
        self.http_client: Optional[httpx.AsyncClient] = None
        self.crawl_cache: Dict[str, CrawlResult] = {}
        self._setup_tools()
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Crawl4AI HTTP client"""
        if not CRAWL4AI_DEPS_AVAILABLE:
            logfire.warning("Crawl4AI dependencies not available. Install with: pip install httpx aiofiles beautifulsoup4 pydantic")
            return

        try:
            # Create storage directory
            os.makedirs(self.storage_path, exist_ok=True)

            # Initialize HTTP client with proper headers
            self.http_client = httpx.AsyncClient(
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1"
                },
                timeout=self.request_timeout,
                follow_redirects=True
            )
            logfire.info("Crawl4AI HTTP client initialized successfully")
        except Exception as e:
            logfire.error(f"Failed to initialize Crawl4AI client: {str(e)}")

    def _clean_url(self, url: str) -> str:
        """Clean and normalize URL"""
        try:
            parsed = urlparse(url)
            if not parsed.scheme:
                url = "https://" + url
            return url.strip()
        except Exception:
            return url

    def _extract_content(self, html: str, url: str) -> Dict[str, Any]:
        """Extract content from HTML using BeautifulSoup"""
        if not BeautifulSoup:
            return {
                "title": "N/A",
                "content": html[:1000] + "..." if len(html) > 1000 else html,
                "links": [],
                "images": [],
                "metadata": {}
            }

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "aside"]):
                script.decompose()

            # Extract title
            title = soup.find('title')
            title_text = title.get_text().strip() if title else "No title"

            # Extract main content
            content_selectors = [
                'main', 'article', '.content', '#content', '.main-content',
                '.post-content', '.entry-content', '.article-body'
            ]

            content = ""
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    content = content_elem.get_text(separator='\n', strip=True)
                    break

            if not content:
                # Fallback to body content
                body = soup.find('body')
                if body:
                    content = body.get_text(separator='\n', strip=True)
                else:
                    content = soup.get_text(separator='\n', strip=True)

            # Clean content
            content = re.sub(r'\n\s*\n', '\n\n', content)
            content = content.strip()

            # Extract links
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(url, href)
                if absolute_url not in links:
                    links.append(absolute_url)

            # Extract images
            images = []
            for img in soup.find_all('img', src=True):
                src = img['src']
                absolute_url = urljoin(url, src)
                if absolute_url not in images:
                    images.append(absolute_url)

            # Extract metadata
            metadata = {}

            # Meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                metadata['description'] = meta_desc.get('content', '')

            # Meta keywords
            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            if meta_keywords:
                metadata['keywords'] = meta_keywords.get('content', '')

            # Open Graph data
            og_tags = soup.find_all('meta', property=lambda x: x and x.startswith('og:'))
            for tag in og_tags:
                property_name = tag.get('property', '').replace('og:', '')
                content_value = tag.get('content', '')
                if property_name and content_value:
                    metadata[f'og_{property_name}'] = content_value

            return {
                "title": title_text,
                "content": content,
                "links": links[:50],  # Limit links
                "images": images[:20],  # Limit images
                "metadata": metadata
            }

        except Exception as e:
            logfire.error(f"Failed to extract content: {str(e)}")
            return {
                "title": "Extraction failed",
                "content": html[:1000] + "..." if len(html) > 1000 else html,
                "links": [],
                "images": [],
                "metadata": {"error": str(e)}
            }

    def _generate_cache_key(self, url: str) -> str:
        """Generate cache key for URL"""
        return hashlib.md5(url.encode()).hexdigest()

    async def _save_to_cache(self, url: str, result: CrawlResult):
        """Save crawl result to cache"""
        try:
            cache_key = self._generate_cache_key(url)
            cache_file = os.path.join(self.storage_path, f"{cache_key}.json")

            if CRAWL4AI_DEPS_AVAILABLE and hasattr(result, 'dict'):
                data = result.dict()
            else:
                data = result

            if aiofiles:
                async with aiofiles.open(cache_file, 'w') as f:
                    await f.write(json.dumps(data, indent=2))
            else:
                with open(cache_file, 'w') as f:
                    json.dump(data, f, indent=2)

            self.crawl_cache[url] = result
        except Exception as e:
            logfire.error(f"Failed to save to cache: {str(e)}")

    async def _load_from_cache(self, url: str) -> Optional[CrawlResult]:
        """Load crawl result from cache"""
        try:
            if url in self.crawl_cache:
                return self.crawl_cache[url]

            cache_key = self._generate_cache_key(url)
            cache_file = os.path.join(self.storage_path, f"{cache_key}.json")

            if not os.path.exists(cache_file):
                return None

            if aiofiles:
                async with aiofiles.open(cache_file, 'r') as f:
                    data = json.loads(await f.read())
            else:
                with open(cache_file, 'r') as f:
                    data = json.load(f)

            if CRAWL4AI_DEPS_AVAILABLE:
                result = CrawlResult(**data)
            else:
                result = data

            self.crawl_cache[url] = result
            return result

        except Exception as e:
            logfire.error(f"Failed to load from cache: {str(e)}")
            return None

    def _setup_tools(self):
        """Setup Crawl4AI MCP tools"""

        @self.mcp.tool(
            name="crawl_url",
            description="Crawl a single URL and extract content",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to crawl"},
                    "use_cache": {"type": "boolean", "description": "Use cached result if available", "default": True},
                    "extract_links": {"type": "boolean", "description": "Extract links from page", "default": True},
                    "extract_images": {"type": "boolean", "description": "Extract images from page", "default": True}
                },
                "required": ["url"]
            }
        )
        async def crawl_url(url: str, use_cache: bool = True, extract_links: bool = True,
                          extract_images: bool = True) -> Dict[str, Any]:
            """Crawl a single URL and extract content"""
            if not self._check_client():
                return {"error": "Crawl4AI client not available"}

            try:
                url = self._clean_url(url)

                # Check cache first
                if use_cache:
                    cached_result = await self._load_from_cache(url)
                    if cached_result:
                        logfire.info(f"Returning cached result for {url}")
                        if CRAWL4AI_DEPS_AVAILABLE and hasattr(cached_result, 'dict'):
                            return {"status": "success", "cached": True, **cached_result.dict()}
                        else:
                            return {"status": "success", "cached": True, **cached_result}

                # Add crawl delay
                await asyncio.sleep(self.crawl_delay)

                # Make HTTP request
                response = await self.http_client.get(url)
                response.raise_for_status()

                # Check content length
                content_length = len(response.content)
                if content_length > self.max_content_length:
                    return {"error": f"Content too large: {content_length} bytes (max: {self.max_content_length})"}

                # Extract content
                html = response.text
                extracted = self._extract_content(html, url)

                if not extract_links:
                    extracted["links"] = []
                if not extract_images:
                    extracted["images"] = []

                # Create crawl result
                crawl_data = {
                    "url": url,
                    "title": extracted["title"],
                    "content": extracted["content"],
                    "metadata": extracted["metadata"],
                    "links": extracted["links"],
                    "images": extracted["images"],
                    "crawled_at": datetime.utcnow().isoformat(),
                    "status_code": response.status_code,
                    "content_type": response.headers.get("content-type", "")
                }

                if CRAWL4AI_DEPS_AVAILABLE:
                    result = CrawlResult(**crawl_data)
                else:
                    result = crawl_data

                # Save to cache
                await self._save_to_cache(url, result)

                return {
                    "status": "success",
                    "cached": False,
                    **crawl_data
                }

            except httpx.HTTPStatusError as e:
                error_msg = f"HTTP {e.response.status_code}: {str(e)}"
                logfire.error(f"HTTP error crawling {url}: {error_msg}")
                return {"error": error_msg, "status_code": e.response.status_code}
            except Exception as e:
                error_msg = f"Crawling failed: {str(e)}"
                logfire.error(f"Error crawling {url}: {error_msg}")
                return {"error": error_msg}

        @self.mcp.tool(
            name="crawl_multiple_urls",
            description="Crawl multiple URLs concurrently",
            input_schema={
                "type": "object",
                "properties": {
                    "urls": {"type": "array", "items": {"type": "string"}, "description": "URLs to crawl"},
                    "max_concurrent": {"type": "integer", "description": "Maximum concurrent requests", "default": 3},
                    "use_cache": {"type": "boolean", "description": "Use cached results if available", "default": True}
                },
                "required": ["urls"]
            }
        )
        async def crawl_multiple_urls(urls: List[str], max_concurrent: int = 3, use_cache: bool = True) -> Dict[str, Any]:
            """Crawl multiple URLs concurrently"""
            if not self._check_client():
                return {"error": "Crawl4AI client not available"}

            try:
                semaphore = asyncio.Semaphore(max_concurrent)

                async def crawl_with_semaphore(url: str) -> Dict[str, Any]:
                    async with semaphore:
                        result = await crawl_url(url, use_cache=use_cache)
                        return {"url": url, "result": result}

                tasks = [crawl_with_semaphore(url) for url in urls]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                success_count = 0
                error_count = 0
                crawl_results = []

                for result in results:
                    if isinstance(result, Exception):
                        error_count += 1
                        crawl_results.append({
                            "url": "unknown",
                            "result": {"error": str(result)}
                        })
                    else:
                        if "error" not in result["result"]:
                            success_count += 1
                        else:
                            error_count += 1
                        crawl_results.append(result)

                return {
                    "status": "completed",
                    "total_urls": len(urls),
                    "successful": success_count,
                    "failed": error_count,
                    "results": crawl_results
                }

            except Exception as e:
                logfire.error(f"Failed to crawl multiple URLs: {str(e)}")
                return {"error": f"Multiple URL crawling failed: {str(e)}"}

        @self.mcp.tool(
            name="extract_links_from_page",
            description="Extract all links from a webpage",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to extract links from"},
                    "filter_domain": {"type": "boolean", "description": "Only return links from same domain", "default": False},
                    "max_links": {"type": "integer", "description": "Maximum number of links to return", "default": 100}
                },
                "required": ["url"]
            }
        )
        async def extract_links_from_page(url: str, filter_domain: bool = False, max_links: int = 100) -> Dict[str, Any]:
            """Extract all links from a webpage"""
            try:
                crawl_result = await crawl_url(url, extract_images=False)

                if "error" in crawl_result:
                    return crawl_result

                links = crawl_result.get("links", [])

                if filter_domain:
                    parsed_url = urlparse(url)
                    domain = parsed_url.netloc
                    links = [link for link in links if urlparse(link).netloc == domain]

                # Limit results
                links = links[:max_links]

                return {
                    "url": url,
                    "total_links": len(links),
                    "links": links,
                    "filtered_by_domain": filter_domain
                }

            except Exception as e:
                logfire.error(f"Failed to extract links: {str(e)}")
                return {"error": f"Link extraction failed: {str(e)}"}

        @self.mcp.tool(
            name="chunk_content_for_rag",
            description="Chunk webpage content for RAG applications",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to chunk content from"},
                    "chunk_size": {"type": "integer", "description": "Maximum characters per chunk", "default": 1000},
                    "overlap": {"type": "integer", "description": "Character overlap between chunks", "default": 100},
                    "include_metadata": {"type": "boolean", "description": "Include metadata with chunks", "default": True}
                },
                "required": ["url"]
            }
        )
        async def chunk_content_for_rag(url: str, chunk_size: int = 1000, overlap: int = 100,
                                       include_metadata: bool = True) -> Dict[str, Any]:
            """Chunk webpage content for RAG applications"""
            try:
                crawl_result = await crawl_url(url, extract_links=False, extract_images=False)

                if "error" in crawl_result:
                    return crawl_result

                content = crawl_result.get("content", "")
                title = crawl_result.get("title", "")
                metadata = crawl_result.get("metadata", {})

                if not content:
                    return {"error": "No content found to chunk"}

                # Simple chunking algorithm
                chunks = []
                start = 0
                chunk_id = 0

                while start < len(content):
                    end = start + chunk_size

                    # Try to break at sentence boundary
                    if end < len(content):
                        # Look for sentence endings
                        for i in range(end, max(start + chunk_size // 2, end - 200), -1):
                            if content[i] in '.!?':
                                end = i + 1
                                break

                    chunk_text = content[start:end].strip()

                    if chunk_text:
                        chunk_data = {
                            "chunk_id": chunk_id,
                            "content": chunk_text,
                            "start_position": start,
                            "end_position": end,
                            "length": len(chunk_text)
                        }

                        if include_metadata:
                            chunk_data["metadata"] = {
                                "source_url": url,
                                "source_title": title,
                                "crawled_at": crawl_result.get("crawled_at"),
                                **metadata
                            }

                        chunks.append(chunk_data)
                        chunk_id += 1

                    start = end - overlap

                return {
                    "url": url,
                    "total_chunks": len(chunks),
                    "chunk_size": chunk_size,
                    "overlap": overlap,
                    "original_length": len(content),
                    "chunks": chunks
                }

            except Exception as e:
                logfire.error(f"Failed to chunk content: {str(e)}")
                return {"error": f"Content chunking failed: {str(e)}"}

        @self.mcp.tool(
            name="search_content",
            description="Search within crawled content",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "urls": {"type": "array", "items": {"type": "string"}, "description": "URLs to search within (optional)"},
                    "case_sensitive": {"type": "boolean", "description": "Case sensitive search", "default": False}
                },
                "required": ["query"]
            }
        )
        async def search_content(query: str, urls: List[str] = None, case_sensitive: bool = False) -> Dict[str, Any]:
            """Search within crawled content"""
            try:
                search_query = query if case_sensitive else query.lower()
                results = []

                # Search in cache
                search_urls = urls if urls else list(self.crawl_cache.keys())

                for url in search_urls:
                    cached_result = await self._load_from_cache(url)
                    if not cached_result:
                        continue

                    if CRAWL4AI_DEPS_AVAILABLE and hasattr(cached_result, 'content'):
                        content = cached_result.content
                        title = cached_result.title
                        crawled_at = cached_result.crawled_at
                    else:
                        content = cached_result.get('content', '')
                        title = cached_result.get('title', '')
                        crawled_at = cached_result.get('crawled_at', '')

                    search_content = content if case_sensitive else content.lower()

                    if search_query in search_content:
                        # Find context around matches
                        matches = []
                        start = 0
                        while True:
                            pos = search_content.find(search_query, start)
                            if pos == -1:
                                break

                            # Extract context
                            context_start = max(0, pos - 100)
                            context_end = min(len(content), pos + len(query) + 100)
                            context = content[context_start:context_end]

                            matches.append({
                                "position": pos,
                                "context": context.strip()
                            })

                            start = pos + len(search_query)

                            # Limit matches per page
                            if len(matches) >= 5:
                                break

                        if matches:
                            results.append({
                                "url": url,
                                "title": title,
                                "crawled_at": crawled_at,
                                "match_count": len(matches),
                                "matches": matches
                            })

                results.sort(key=lambda x: x["match_count"], reverse=True)

                return {
                    "query": query,
                    "total_results": len(results),
                    "case_sensitive": case_sensitive,
                    "searched_urls": len(search_urls),
                    "results": results
                }

            except Exception as e:
                logfire.error(f"Failed to search content: {str(e)}")
                return {"error": f"Content search failed: {str(e)}"}

        @self.mcp.tool(
            name="get_crawl_stats",
            description="Get crawling statistics and cache information",
            input_schema={
                "type": "object",
                "properties": {}
            }
        )
        async def get_crawl_stats() -> Dict[str, Any]:
            """Get crawling statistics"""
            try:
                cache_files = []
                if os.path.exists(self.storage_path):
                    cache_files = [f for f in os.listdir(self.storage_path) if f.endswith('.json')]

                total_cached = len(cache_files)
                memory_cached = len(self.crawl_cache)

                # Calculate cache size
                cache_size = 0
                if os.path.exists(self.storage_path):
                    for file in cache_files:
                        file_path = os.path.join(self.storage_path, file)
                        cache_size += os.path.getsize(file_path)

                return {
                    "total_cached_pages": total_cached,
                    "memory_cached_pages": memory_cached,
                    "cache_size_bytes": cache_size,
                    "cache_size_mb": round(cache_size / (1024 * 1024), 2),
                    "storage_path": self.storage_path,
                    "user_agent": self.user_agent,
                    "max_content_length": self.max_content_length,
                    "request_timeout": self.request_timeout,
                    "crawl_delay": self.crawl_delay,
                    "dependencies_available": CRAWL4AI_DEPS_AVAILABLE
                }

            except Exception as e:
                logfire.error(f"Failed to get crawl stats: {str(e)}")
                return {"error": f"Stats query failed: {str(e)}"}

    def _check_client(self) -> bool:
        """Check if Crawl4AI client is available"""
        return CRAWL4AI_DEPS_AVAILABLE and self.http_client is not None

    async def run(self):
        """Run the Crawl4AI MCP server"""
        try:
            await self.mcp.run_stdio()
        finally:
            if self.http_client:
                await self.http_client.aclose()


async def main():
    """Main entry point"""
    server = Crawl4AIMCP()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
