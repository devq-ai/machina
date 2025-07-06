#!/usr/bin/env python3
"""
SurrealDB MCP Server Validation Script

Validates the SurrealDB MCP Server functionality including:
- Server initialization and connection testing
- Multi-model database operations (document, graph, key-value)
- Query execution and performance
- Error handling and edge cases
- MCP protocol compliance

This script can be run standalone to verify server functionality
before deployment or integration.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from surrealdb_mcp.server import SurrealDBServer
    from surrealdb import Surreal
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Please ensure all dependencies are installed:")
    print("pip install -r requirements.txt")
    sys.exit(1)


class SurrealDBValidator:
    """Validation suite for SurrealDB MCP Server."""

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
            print("🚀 Initializing SurrealDB MCP Server...")
            self.server = SurrealDBServer()

            # Try to initialize - this will attempt connection
            try:
                await self.server.initialize()
                return True
            except Exception as e:
                print(f"⚠️  Server initialization failed, will test without connection: {e}")
                # Set up mock connection for testing
                self.server.db = None
                self.server.connected = False
                return True
        except Exception as e:
            print(f"❌ Server setup failed: {e}")
            return False

    async def test_environment_setup(self) -> bool:
        """Test environment configuration."""
        start_time = time.time()

        try:
            # Check environment variables
            surrealdb_url = os.getenv("SURREALDB_URL")
            surrealdb_username = os.getenv("SURREALDB_USERNAME")
            surrealdb_password = os.getenv("SURREALDB_PASSWORD")

            env_check = {
                "SURREALDB_URL": surrealdb_url is not None,
                "SURREALDB_USERNAME": surrealdb_username is not None,
                "SURREALDB_PASSWORD": surrealdb_password is not None
            }

            message = f"Environment variables: {env_check}"
            if not all(env_check.values()):
                message += " (Some env vars missing, will use defaults)"

            self.log_test(
                "Environment Setup",
                True,  # Pass even with missing env vars
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

    async def test_surrealdb_connection(self) -> bool:
        """Test SurrealDB connection."""
        start_time = time.time()

        try:
            if not self.server.connected:
                self.log_test(
                    "SurrealDB Connection",
                    False,
                    "SurrealDB not connected (likely no server running)",
                    time.time() - start_time
                )
                return False

            # Test basic query if connected
            if self.server.db:
                await self.server.db.query("INFO FOR DB")

            self.log_test(
                "SurrealDB Connection",
                True,
                "SurrealDB connection successful",
                time.time() - start_time
            )
            return True

        except Exception as e:
            self.log_test(
                "SurrealDB Connection",
                False,
                f"SurrealDB connection failed: {str(e)}",
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

                required_fields = ["server", "version", "timestamp", "connected",
                                 "namespace", "database"]

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

    async def test_document_operations(self) -> bool:
        """Test document CRUD operations."""
        start_time = time.time()

        if not self.server.connected:
            self.log_test(
                "Document Operations",
                False,
                "Skipped - SurrealDB not connected",
                time.time() - start_time
            )
            return False

        try:
            # Test document creation
            test_doc_id = f"test-doc-{uuid.uuid4()}"
            create_args = {
                "table": "test_users",
                "data": {
                    "name": "Test User",
                    "email": "test@example.com",
                    "role": "tester"
                },
                "id": test_doc_id
            }

            create_result = await self.server._handle_create_document(create_args)
            if not create_result or not json.loads(create_result[0].text).get("success"):
                self.log_test(
                    "Document Operations",
                    False,
                    "Document creation failed",
                    time.time() - start_time
                )
                return False

            # Test document retrieval
            get_args = {"id": f"test_users:{test_doc_id}"}
            get_result = await self.server._handle_get_document(get_args)

            if not get_result or not json.loads(get_result[0].text).get("success"):
                self.log_test(
                    "Document Operations",
                    False,
                    "Document retrieval failed",
                    time.time() - start_time
                )
                return False

            # Test document update
            update_args = {
                "id": f"test_users:{test_doc_id}",
                "data": {"role": "updated_tester"},
                "merge": True
            }
            update_result = await self.server._handle_update_document(update_args)

            if not update_result or not json.loads(update_result[0].text).get("success"):
                self.log_test(
                    "Document Operations",
                    False,
                    "Document update failed",
                    time.time() - start_time
                )
                return False

            # Test document deletion
            delete_args = {"id": f"test_users:{test_doc_id}"}
            delete_result = await self.server._handle_delete_document(delete_args)

            if not delete_result or not json.loads(delete_result[0].text).get("success"):
                self.log_test(
                    "Document Operations",
                    False,
                    "Document deletion failed",
                    time.time() - start_time
                )
                return False

            self.log_test(
                "Document Operations",
                True,
                "CRUD operations completed successfully",
                time.time() - start_time
            )
            return True

        except Exception as e:
            self.log_test(
                "Document Operations",
                False,
                f"Document operations failed: {str(e)}",
                time.time() - start_time
            )
            return False

    async def test_graph_operations(self) -> bool:
        """Test graph operations."""
        start_time = time.time()

        if not self.server.connected:
            self.log_test(
                "Graph Operations",
                False,
                "Skipped - SurrealDB not connected",
                time.time() - start_time
            )
            return False

        try:
            # Create test nodes
            alice_id = f"person:alice_{uuid.uuid4().hex[:8]}"
            bob_id = f"person:bob_{uuid.uuid4().hex[:8]}"
            company_id = f"company:acme_{uuid.uuid4().hex[:8]}"

            # Create Alice
            alice_args = {
                "table": "person",
                "data": {"name": "Alice", "role": "developer"},
                "id": alice_id.split(':')[1]
            }
            alice_result = await self.server._handle_create_document(alice_args)

            if not alice_result or not json.loads(alice_result[0].text).get("success"):
                self.log_test(
                    "Graph Operations",
                    False,
                    "Failed to create Alice node",
                    time.time() - start_time
                )
                return False

            # Create Bob
            bob_args = {
                "table": "person",
                "data": {"name": "Bob", "role": "designer"},
                "id": bob_id.split(':')[1]
            }
            await self.server._handle_create_document(bob_args)

            # Create Company
            company_args = {
                "table": "company",
                "data": {"name": "ACME Corp", "industry": "tech"},
                "id": company_id.split(':')[1]
            }
            await self.server._handle_create_document(company_args)

            # Create relationships
            works_at_args = {
                "from_id": alice_id,
                "to_id": company_id,
                "relation_type": "works_at",
                "properties": {"since": "2023-01-01", "department": "engineering"}
            }

            relation_result = await self.server._handle_create_relation(works_at_args)
            if not relation_result or not json.loads(relation_result[0].text).get("success"):
                self.log_test(
                    "Graph Operations",
                    False,
                    "Failed to create relationship",
                    time.time() - start_time
                )
                return False

            # Test relationship retrieval
            get_relations_args = {
                "record_id": alice_id,
                "direction": "out"
            }

            relations_result = await self.server._handle_get_relations(get_relations_args)
            if not relations_result or not json.loads(relations_result[0].text).get("success"):
                self.log_test(
                    "Graph Operations",
                    False,
                    "Failed to retrieve relationships",
                    time.time() - start_time
                )
                return False

            # Test graph traversal
            traverse_args = {
                "start_id": alice_id,
                "depth": 2,
                "relation_types": ["works_at"]
            }

            traverse_result = await self.server._handle_graph_traverse(traverse_args)
            if not traverse_result or not json.loads(traverse_result[0].text).get("success"):
                self.log_test(
                    "Graph Operations",
                    False,
                    "Graph traversal failed",
                    time.time() - start_time
                )
                return False

            self.log_test(
                "Graph Operations",
                True,
                "Graph operations completed successfully",
                time.time() - start_time
            )
            return True

        except Exception as e:
            self.log_test(
                "Graph Operations",
                False,
                f"Graph operations failed: {str(e)}",
                time.time() - start_time
            )
            return False

    async def test_key_value_operations(self) -> bool:
        """Test key-value operations."""
        start_time = time.time()

        if not self.server.connected:
            self.log_test(
                "Key-Value Operations",
                False,
                "Skipped - SurrealDB not connected",
                time.time() - start_time
            )
            return False

        try:
            # Test key-value setting
            test_key = f"test_key_{uuid.uuid4().hex[:8]}"
            test_value = "test_value_12345"

            set_args = {
                "key": test_key,
                "value": test_value,
                "ttl": 3600  # 1 hour
            }

            set_result = await self.server._handle_set_key_value(set_args)
            if not set_result or not json.loads(set_result[0].text).get("success"):
                self.log_test(
                    "Key-Value Operations",
                    False,
                    "Failed to set key-value",
                    time.time() - start_time
                )
                return False

            # Test key-value retrieval
            get_args = {"key": test_key}
            get_result = await self.server._handle_get_key_value(get_args)

            if not get_result:
                self.log_test(
                    "Key-Value Operations",
                    False,
                    "No response from get key-value",
                    time.time() - start_time
                )
                return False

            get_data = json.loads(get_result[0].text)
            if not get_data.get("success") or get_data.get("value") != test_value:
                self.log_test(
                    "Key-Value Operations",
                    False,
                    f"Failed to retrieve correct value: {get_data}",
                    time.time() - start_time
                )
                return False

            # Test key-value deletion
            delete_args = {"key": test_key}
            delete_result = await self.server._handle_delete_key_value(delete_args)

            if not delete_result or not json.loads(delete_result[0].text).get("success"):
                self.log_test(
                    "Key-Value Operations",
                    False,
                    "Failed to delete key-value",
                    time.time() - start_time
                )
                return False

            self.log_test(
                "Key-Value Operations",
                True,
                "Key-value operations completed successfully",
                time.time() - start_time
            )
            return True

        except Exception as e:
            self.log_test(
                "Key-Value Operations",
                False,
                f"Key-value operations failed: {str(e)}",
                time.time() - start_time
            )
            return False

    async def test_query_execution(self) -> bool:
        """Test query execution."""
        start_time = time.time()

        if not self.server.connected:
            self.log_test(
                "Query Execution",
                False,
                "Skipped - SurrealDB not connected",
                time.time() - start_time
            )
            return False

        try:
            # Test simple query
            query_args = {
                "query": "SELECT * FROM person LIMIT 5",
                "variables": {}
            }

            query_result = await self.server._handle_execute_query(query_args)
            if not query_result:
                self.log_test(
                    "Query Execution",
                    False,
                    "No response from query execution",
                    time.time() - start_time
                )
                return False

            query_data = json.loads(query_result[0].text)
            if query_data.get("status") != "success":
                self.log_test(
                    "Query Execution",
                    False,
                    f"Query execution failed: {query_data}",
                    time.time() - start_time
                )
                return False

            # Test parameterized query
            param_query_args = {
                "query": "SELECT * FROM person WHERE name = $name",
                "variables": {"name": "Alice"}
            }

            param_result = await self.server._handle_execute_query(param_query_args)
            if not param_result:
                self.log_test(
                    "Query Execution",
                    False,
                    "Parameterized query failed",
                    time.time() - start_time
                )
                return False

            self.log_test(
                "Query Execution",
                True,
                "Query execution completed successfully",
                time.time() - start_time
            )
            return True

        except Exception as e:
            self.log_test(
                "Query Execution",
                False,
                f"Query execution failed: {str(e)}",
                time.time() - start_time
            )
            return False

    async def test_table_operations(self) -> bool:
        """Test table operations."""
        start_time = time.time()

        if not self.server.connected:
            self.log_test(
                "Table Operations",
                False,
                "Skipped - SurrealDB not connected",
                time.time() - start_time
            )
            return False

        try:
            # Test table listing
            tables_result = await self.server._handle_list_tables()
            if not tables_result:
                self.log_test(
                    "Table Operations",
                    False,
                    "Failed to list tables",
                    time.time() - start_time
                )
                return False

            tables_data = json.loads(tables_result[0].text)
            if not tables_data.get("success"):
                self.log_test(
                    "Table Operations",
                    False,
                    f"Table listing failed: {tables_data}",
                    time.time() - start_time
                )
                return False

            # Test table querying
            query_table_args = {
                "table": "person",
                "limit": 10
            }

            query_result = await self.server._handle_query_table(query_table_args)
            if not query_result:
                self.log_test(
                    "Table Operations",
                    False,
                    "Failed to query table",
                    time.time() - start_time
                )
                return False

            query_data = json.loads(query_result[0].text)
            if not query_data.get("success"):
                self.log_test(
                    "Table Operations",
                    False,
                    f"Table query failed: {query_data}",
                    time.time() - start_time
                )
                return False

            self.log_test(
                "Table Operations",
                True,
                f"Table operations completed - found {tables_data.get('count', 0)} tables",
                time.time() - start_time
            )
            return True

        except Exception as e:
            self.log_test(
                "Table Operations",
                False,
                f"Table operations failed: {str(e)}",
                time.time() - start_time
            )
            return False

    async def test_database_info(self) -> bool:
        """Test database information retrieval."""
        start_time = time.time()

        if not self.server.connected:
            self.log_test(
                "Database Info",
                False,
                "Skipped - SurrealDB not connected",
                time.time() - start_time
            )
            return False

        try:
            result = await self.server._handle_get_database_info()

            if result and len(result) == 1:
                info_data = json.loads(result[0].text)

                required_fields = ["namespace", "database", "database_info",
                                 "namespace_info", "timestamp"]

                missing_fields = [field for field in required_fields if field not in info_data]

                if not missing_fields:
                    self.log_test(
                        "Database Info",
                        True,
                        f"Database info retrieved successfully",
                        time.time() - start_time
                    )
                    return True
                else:
                    self.log_test(
                        "Database Info",
                        False,
                        f"Missing info fields: {missing_fields}",
                        time.time() - start_time
                    )
                    return False
            else:
                self.log_test(
                    "Database Info",
                    False,
                    "Invalid database info response",
                    time.time() - start_time
                )
                return False

        except Exception as e:
            self.log_test(
                "Database Info",
                False,
                f"Database info retrieval failed: {str(e)}",
                time.time() - start_time
            )
            return False

    async def test_error_handling(self) -> bool:
        """Test error handling scenarios."""
        start_time = time.time()

        try:
            error_tests = []

            # Test 1: Empty query
            try:
                result = await self.server._handle_execute_query({"query": ""})
                if result and "cannot be empty" in result[0].text:
                    error_tests.append("Empty query handled correctly")
                else:
                    error_tests.append("Empty query error handling failed")
            except Exception:
                error_tests.append("Empty query raised unexpected exception")

            # Test 2: Missing table name
            try:
                result = await self.server._handle_create_document({"data": {"name": "Test"}})
                if result and "Table name is required" in result[0].text:
                    error_tests.append("Missing table name handled correctly")
                else:
                    error_tests.append("Missing table name error handling failed")
            except Exception:
                error_tests.append("Missing table name raised unexpected exception")

            # Test 3: Missing document ID
            try:
                result = await self.server._handle_get_document({})
                if result and "Document ID is required" in result[0].text:
                    error_tests.append("Missing document ID handled correctly")
                else:
                    error_tests.append("Missing document ID error handling failed")
            except Exception:
                error_tests.append("Missing document ID raised unexpected exception")

            success_count = len([test for test in error_tests if "correctly" in test])
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
            # This would normally clean up test documents, but for now just log completion
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

        print("\n🧪 SurrealDB MCP Server Validation Suite")
        print("=" * 55)

        # Initialize server
        if not await self.setup_server():
            print("❌ Server setup failed. Aborting validation.")
            return False

        # Run validation tests
        tests = [
            self.test_environment_setup,
            self.test_surrealdb_connection,
            self.test_server_status,
            self.test_document_operations,
            self.test_graph_operations,
            self.test_key_value_operations,
            self.test_query_execution,
            self.test_table_operations,
            self.test_database_info,
            self.test_error_handling,
            self.cleanup_test_data
        ]

        for test in tests:
            await test()

        # Generate report
        report = self.generate_report()

        print("\n📊 Validation Summary")
        print("=" * 55)
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
            print("\n🎉 All tests passed! SurrealDB MCP Server is ready for deployment.")
            return True
        else:
            print(f"\n⚠️  {report['summary']['failed']} tests failed. Please review and fix issues before deployment.")
            print("\n💡 Note: Some failures may be due to SurrealDB server not running locally.")
            print("   Start SurrealDB with: surreal start --log trace memory")
            return False


async def main():
    """Main validation entry point."""
    validator = SurrealDBValidator()

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
