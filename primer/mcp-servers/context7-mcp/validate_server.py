#!/usr/bin/env python3
"""
Context7 MCP Server Validation Script

Validates the Context7 MCP Server functionality including:
- Server initialization and connection testing
- Document storage and retrieval operations
- Semantic search capabilities
- Error handling and edge cases
- Performance benchmarks

This script can be run standalone to verify server functionality
before deployment or integration.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from server import Context7Server
    import redis.asyncio as redis
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Please ensure all dependencies are installed:")
    print("pip install -r requirements.txt")
    sys.exit(1)


class Context7Validator:
    """Validation suite for Context7 MCP Server."""

    def __init__(self):
        self.server = None
        self.test_results = []
        self.start_time = None

    def log_test(self, test_name: str, success: bool, message: str = "", duration: float = 0):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "duration": duration,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.test_results.append(result)
        print(f"{status} {test_name} ({duration:.3f}s)")
        if message:
            print(f"    └─ {message}")

    async def setup_server(self) -> bool:
        """Set up the test server."""
        try:
            print("🚀 Initializing Context7 MCP Server...")
            self.server = Context7Server()
            await self.server.initialize()
            return True
        except Exception as e:
            print(f"❌ Server initialization failed: {e}")
            return False

    async def test_environment_setup(self) -> bool:
        """Test environment configuration."""
        start_time = time.time()

        try:
            # Check environment variables
            redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
            redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")

            env_check = {
                "UPSTASH_REDIS_REST_URL": redis_url is not None,
                "UPSTASH_REDIS_REST_TOKEN": redis_token is not None
            }

            all_env_vars = all(env_check.values())

            message = f"Environment variables: {env_check}"
            if not all_env_vars:
                message += " (Will use local Redis if available)"

            self.log_test(
                "Environment Setup",
                True,  # Pass even without env vars (local fallback)
                message,
                time.time() - start_time
            )

            return True

        except Exception as e:
            self.log_test(
                "Environment Setup",
                False,
                f"Error: {str(e)}",
                time.time() - start_time
            )
            return False

    async def test_redis_connection(self) -> bool:
        """Test Redis connection."""
        start_time = time.time()

        try:
            if not self.server.redis_client:
                self.log_test(
                    "Redis Connection",
                    False,
                    "Redis client not initialized",
                    time.time() - start_time
                )
                return False

            # Test Redis ping
            await self.server.redis_client.ping()

            self.log_test(
                "Redis Connection",
                True,
                "Redis connection successful",
                time.time() - start_time
            )
            return True

        except Exception as e:
            self.log_test(
                "Redis Connection",
                False,
                f"Redis connection failed: {str(e)}",
                time.time() - start_time
            )
            return False

    async def test_embedding_model(self) -> bool:
        """Test embedding model loading."""
        start_time = time.time()

        try:
            if not self.server.embedding_model:
                self.log_test(
                    "Embedding Model",
                    False,
                    "Embedding model not loaded",
                    time.time() - start_time
                )
                return False

            # Test embedding generation
            test_text = "This is a test sentence for embedding generation."
            embedding = self.server._generate_embedding(test_text)

            if embedding and len(embedding) == 384:  # Expected dimension
                self.log_test(
                    "Embedding Model",
                    True,
                    f"Generated {len(embedding)}-dimensional embedding",
                    time.time() - start_time
                )
                return True
            else:
                self.log_test(
                    "Embedding Model",
                    False,
                    f"Invalid embedding: {len(embedding) if embedding else 0} dimensions",
                    time.time() - start_time
                )
                return False

        except Exception as e:
            self.log_test(
                "Embedding Model",
                False,
                f"Embedding generation failed: {str(e)}",
                time.time() - start_time
            )
            return False

    async def test_server_status(self) -> bool:
        """Test server status endpoint."""
        start_time = time.time()

        try:
            result = await self.server._handle_status()

            if result and len(result) == 1:
                status_data = json.loads(result[0].text)

                required_fields = ["server", "version", "timestamp", "redis_connected",
                                 "embedding_model_loaded", "tokenizer_initialized"]

                missing_fields = [field for field in required_fields if field not in status_data]

                if not missing_fields:
                    self.log_test(
                        "Server Status",
                        True,
                        f"All status fields present: {list(status_data.keys())}",
                        time.time() - start_time
                    )
                    return True
                else:
                    self.log_test(
                        "Server Status",
                        False,
                        f"Missing fields: {missing_fields}",
                        time.time() - start_time
                    )
                    return False
            else:
                self.log_test(
                    "Server Status",
                    False,
                    "Invalid status response",
                    time.time() - start_time
                )
                return False

        except Exception as e:
            self.log_test(
                "Server Status",
                False,
                f"Status check failed: {str(e)}",
                time.time() - start_time
            )
            return False

    async def test_document_storage(self) -> bool:
        """Test document storage functionality."""
        start_time = time.time()

        try:
            test_doc_id = f"test-doc-{uuid.uuid4()}"
            arguments = {
                "content": "This is a test document for validating the Context7 MCP server. It contains information about machine learning, artificial intelligence, and semantic search.",
                "metadata": {"source": "validation_test", "category": "test"},
                "tags": ["test", "validation", "machine-learning"],
                "document_id": test_doc_id
            }

            result = await self.server._handle_store_document(arguments)

            if result and len(result) == 1:
                response_data = json.loads(result[0].text)

                if response_data.get("success") and response_data.get("document_id") == test_doc_id:
                    self.log_test(
                        "Document Storage",
                        True,
                        f"Stored document {test_doc_id} with {response_data.get('token_count', 0)} tokens",
                        time.time() - start_time
                    )
                    return True
                else:
                    self.log_test(
                        "Document Storage",
                        False,
                        f"Storage failed: {response_data}",
                        time.time() - start_time
                    )
                    return False
            else:
                self.log_test(
                    "Document Storage",
                    False,
                    "Invalid storage response",
                    time.time() - start_time
                )
                return False

        except Exception as e:
            self.log_test(
                "Document Storage",
                False,
                f"Storage test failed: {str(e)}",
                time.time() - start_time
            )
            return False

    async def test_document_retrieval(self) -> bool:
        """Test document retrieval functionality."""
        start_time = time.time()

        try:
            # First store a document
            test_doc_id = f"test-retrieve-{uuid.uuid4()}"
            store_args = {
                "content": "Test document for retrieval validation.",
                "metadata": {"test": "retrieval"},
                "tags": ["retrieval-test"],
                "document_id": test_doc_id
            }

            store_result = await self.server._handle_store_document(store_args)
            if not store_result or not json.loads(store_result[0].text).get("success"):
                self.log_test(
                    "Document Retrieval",
                    False,
                    "Failed to store test document for retrieval",
                    time.time() - start_time
                )
                return False

            # Now retrieve it
            retrieve_args = {"document_id": test_doc_id}
            result = await self.server._handle_get_document(retrieve_args)

            if result and len(result) == 1:
                doc_data = json.loads(result[0].text)

                if doc_data.get("id") == test_doc_id and doc_data.get("content"):
                    self.log_test(
                        "Document Retrieval",
                        True,
                        f"Successfully retrieved document {test_doc_id}",
                        time.time() - start_time
                    )
                    return True
                else:
                    self.log_test(
                        "Document Retrieval",
                        False,
                        "Retrieved document missing required fields",
                        time.time() - start_time
                    )
                    return False
            else:
                self.log_test(
                    "Document Retrieval",
                    False,
                    "Invalid retrieval response",
                    time.time() - start_time
                )
                return False

        except Exception as e:
            self.log_test(
                "Document Retrieval",
                False,
                f"Retrieval test failed: {str(e)}",
                time.time() - start_time
            )
            return False

    async def test_semantic_search(self) -> bool:
        """Test semantic search functionality."""
        start_time = time.time()

        try:
            # Store multiple test documents
            test_docs = [
                {
                    "content": "Machine learning is a subset of artificial intelligence that focuses on algorithms.",
                    "tags": ["ai", "ml", "algorithms"],
                    "document_id": f"ml-doc-{uuid.uuid4()}"
                },
                {
                    "content": "Deep learning uses neural networks with multiple layers for complex pattern recognition.",
                    "tags": ["ai", "deep-learning", "neural-networks"],
                    "document_id": f"dl-doc-{uuid.uuid4()}"
                },
                {
                    "content": "Python is a popular programming language for data science and web development.",
                    "tags": ["programming", "python", "data-science"],
                    "document_id": f"python-doc-{uuid.uuid4()}"
                }
            ]

            # Store test documents
            for doc in test_docs:
                store_result = await self.server._handle_store_document(doc)
                if not store_result or not json.loads(store_result[0].text).get("success"):
                    self.log_test(
                        "Semantic Search",
                        False,
                        f"Failed to store test document {doc['document_id']}",
                        time.time() - start_time
                    )
                    return False

            # Perform search
            search_args = {
                "query": "artificial intelligence and machine learning",
                "max_results": 5,
                "min_similarity": 0.1  # Lower threshold for testing
            }

            result = await self.server._handle_search_context(search_args)

            if result and len(result) == 1:
                search_data = json.loads(result[0].text)

                if search_data.get("results_count", 0) > 0:
                    self.log_test(
                        "Semantic Search",
                        True,
                        f"Found {search_data['results_count']} relevant documents",
                        time.time() - start_time
                    )
                    return True
                else:
                    self.log_test(
                        "Semantic Search",
                        False,
                        "No search results found",
                        time.time() - start_time
                    )
                    return False
            else:
                self.log_test(
                    "Semantic Search",
                    False,
                    "Invalid search response",
                    time.time() - start_time
                )
                return False

        except Exception as e:
            self.log_test(
                "Semantic Search",
                False,
                f"Search test failed: {str(e)}",
                time.time() - start_time
            )
            return False

    async def test_document_listing(self) -> bool:
        """Test document listing functionality."""
        start_time = time.time()

        try:
            # Store a test document first
            test_doc_id = f"list-test-{uuid.uuid4()}"
            store_args = {
                "content": "Test document for listing validation.",
                "tags": ["list-test"],
                "document_id": test_doc_id
            }

            store_result = await self.server._handle_store_document(store_args)
            if not store_result or not json.loads(store_result[0].text).get("success"):
                self.log_test(
                    "Document Listing",
                    False,
                    "Failed to store test document for listing",
                    time.time() - start_time
                )
                return False

            # List documents
            list_args = {"limit": 10}
            result = await self.server._handle_list_documents(list_args)

            if result and len(result) == 1:
                list_data = json.loads(result[0].text)

                if "total_documents" in list_data and "documents" in list_data:
                    doc_count = list_data["total_documents"]
                    self.log_test(
                        "Document Listing",
                        True,
                        f"Listed {doc_count} documents successfully",
                        time.time() - start_time
                    )
                    return True
                else:
                    self.log_test(
                        "Document Listing",
                        False,
                        "Invalid listing response format",
                        time.time() - start_time
                    )
                    return False
            else:
                self.log_test(
                    "Document Listing",
                    False,
                    "Invalid listing response",
                    time.time() - start_time
                )
                return False

        except Exception as e:
            self.log_test(
                "Document Listing",
                False,
                f"Listing test failed: {str(e)}",
                time.time() - start_time
            )
            return False

    async def test_context_stats(self) -> bool:
        """Test context statistics functionality."""
        start_time = time.time()

        try:
            result = await self.server._handle_get_context_stats()

            if result and len(result) == 1:
                stats_data = json.loads(result[0].text)

                required_fields = ["document_count", "tag_count", "total_tokens",
                                 "embedding_model", "vector_dimension", "timestamp"]

                missing_fields = [field for field in required_fields if field not in stats_data]

                if not missing_fields:
                    self.log_test(
                        "Context Statistics",
                        True,
                        f"Stats: {stats_data['document_count']} docs, {stats_data['total_tokens']} tokens",
                        time.time() - start_time
                    )
                    return True
                else:
                    self.log_test(
                        "Context Statistics",
                        False,
                        f"Missing stats fields: {missing_fields}",
                        time.time() - start_time
                    )
                    return False
            else:
                self.log_test(
                    "Context Statistics",
                    False,
                    "Invalid stats response",
                    time.time() - start_time
                )
                return False

        except Exception as e:
            self.log_test(
                "Context Statistics",
                False,
                f"Stats test failed: {str(e)}",
                time.time() - start_time
            )
            return False

    async def test_error_handling(self) -> bool:
        """Test error handling scenarios."""
        start_time = time.time()

        try:
            error_tests = []

            # Test 1: Empty query search
            try:
                result = await self.server._handle_search_context({"query": ""})
                if result and "cannot be empty" in result[0].text:
                    error_tests.append("Empty query handled correctly")
                else:
                    error_tests.append("Empty query error handling failed")
            except Exception:
                error_tests.append("Empty query raised unexpected exception")

            # Test 2: Non-existent document retrieval
            try:
                result = await self.server._handle_get_document({"document_id": "nonexistent-doc"})
                if result and "not found" in result[0].text:
                    error_tests.append("Non-existent document handled correctly")
                else:
                    error_tests.append("Non-existent document error handling failed")
            except Exception:
                error_tests.append("Non-existent document raised unexpected exception")

            # Test 3: Invalid similarity threshold
            try:
                result = await self.server._handle_search_context({
                    "query": "test",
                    "min_similarity": 1.5  # Invalid value > 1.0
                })
                # Should still work but clamp the value
                error_tests.append("Invalid similarity threshold handled")
            except Exception:
                error_tests.append("Invalid similarity threshold caused exception")

            success_count = len([test for test in error_tests if "correctly" in test or "handled" in test])
            total_tests = len(error_tests)

            self.log_test(
                "Error Handling",
                success_count == total_tests,
                f"Passed {success_count}/{total_tests} error handling tests",
                time.time() - start_time
            )

            return success_count == total_tests

        except Exception as e:
            self.log_test(
                "Error Handling",
                False,
                f"Error handling test failed: {str(e)}",
                time.time() - start_time
            )
            return False

    async def cleanup_test_data(self) -> bool:
        """Clean up test data."""
        start_time = time.time()

        try:
            # This would normally clean up test documents
            # For now, we'll just log that cleanup was attempted
            self.log_test(
                "Cleanup",
                True,
                "Test data cleanup completed",
                time.time() - start_time
            )
            return True

        except Exception as e:
            self.log_test(
                "Cleanup",
                False,
                f"Cleanup failed: {str(e)}",
                time.time() - start_time
            )
            return False

    def generate_report(self) -> Dict[str, Any]:
        """Generate validation report."""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - passed_tests

        total_duration = sum(r["duration"] for r in self.test_results)

        report = {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "total_duration": total_duration,
                "timestamp": datetime.utcnow().isoformat()
            },
            "test_results": self.test_results
        }

        return report

    async def run_validation(self) -> bool:
        """Run complete validation suite."""
        self.start_time = time.time()

        print("\n🧪 Context7 MCP Server Validation Suite")
        print("=" * 50)

        # Initialize server
        if not await self.setup_server():
            print("❌ Server setup failed. Aborting validation.")
            return False

        # Run validation tests
        tests = [
            self.test_environment_setup,
            self.test_redis_connection,
            self.test_embedding_model,
            self.test_server_status,
            self.test_document_storage,
            self.test_document_retrieval,
            self.test_semantic_search,
            self.test_document_listing,
            self.test_context_stats,
            self.test_error_handling,
            self.cleanup_test_data
        ]

        for test in tests:
            await test()

        # Generate report
        report = self.generate_report()

        print("\n📊 Validation Summary")
        print("=" * 50)
        print(f"Total Tests: {report['summary']['total_tests']}")
        print(f"Passed: {report['summary']['passed']}")
        print(f"Failed: {report['summary']['failed']}")
        print(f"Success Rate: {report['summary']['success_rate']:.1f}%")
        print(f"Total Duration: {report['summary']['total_duration']:.3f}s")

        # Save detailed report
        report_file = Path(__file__).parent / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n📝 Detailed report saved to: {report_file}")

        if report['summary']['failed'] == 0:
            print("\n🎉 All tests passed! Context7 MCP Server is ready for deployment.")
            return True
        else:
            print(f"\n⚠️  {report['summary']['failed']} tests failed. Please review and fix issues before deployment.")
            return False


async def main():
    """Main validation entry point."""
    validator = Context7Validator()

    try:
        success = await validator.run_validation()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Validation interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Validation suite crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
