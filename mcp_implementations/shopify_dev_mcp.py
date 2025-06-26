#!/usr/bin/env python3
"""
Shopify Dev MCP Server Implementation
Provides MCP interface for Shopify development and store management
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio


class MockShopifyClient:
    """Mock Shopify client for testing without API credentials"""

    def __init__(self, api_key: str, api_secret: str, store_domain: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.store_domain = store_domain
        self.test_mode = True

    async def get_shop_info(self) -> Dict[str, Any]:
        """Get shop information"""
        return {
            "id": 12345678,
            "name": "Test Shop",
            "email": "shop@example.com",
            "domain": self.store_domain,
            "created_at": "2024-01-01T00:00:00Z",
            "currency": "USD",
            "plan_name": "Basic"
        }

    async def create_product(self, title: str, description: str, **kwargs) -> Dict[str, Any]:
        """Create a new product"""
        return {
            "id": f"prod_{int(datetime.now().timestamp())}",
            "title": title,
            "description": description,
            "vendor": kwargs.get("vendor", "Test Vendor"),
            "product_type": kwargs.get("product_type", ""),
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "variants": [{
                "id": f"var_{int(datetime.now().timestamp())}",
                "price": kwargs.get("price", "0.00"),
                "sku": kwargs.get("sku", ""),
                "inventory_quantity": kwargs.get("inventory_quantity", 0)
            }]
        }

    async def list_products(self, limit: int = 10, status: str = "active") -> List[Dict[str, Any]]:
        """List products"""
        products = []
        for i in range(min(limit, 5)):
            products.append({
                "id": f"prod_{i}",
                "title": f"Product {i+1}",
                "status": status,
                "vendor": "Test Vendor",
                "created_at": (datetime.now() - timedelta(days=i)).isoformat()
            })
        return products

    async def create_order(self, line_items: List[Dict], customer: Dict, **kwargs) -> Dict[str, Any]:
        """Create an order"""
        total = sum(float(item.get("price", 0)) * item.get("quantity", 1) for item in line_items)
        return {
            "id": f"order_{int(datetime.now().timestamp())}",
            "order_number": 1000 + int(datetime.now().timestamp()) % 1000,
            "email": customer.get("email", ""),
            "created_at": datetime.now().isoformat(),
            "total_price": str(total),
            "currency": "USD",
            "financial_status": "pending",
            "fulfillment_status": None,
            "line_items": line_items,
            "customer": customer
        }

    async def update_inventory(self, inventory_item_id: str, quantity: int) -> Dict[str, Any]:
        """Update inventory levels"""
        return {
            "inventory_item_id": inventory_item_id,
            "available": quantity,
            "updated_at": datetime.now().isoformat()
        }

    async def create_theme(self, name: str, src: str = "") -> Dict[str, Any]:
        """Create or update theme"""
        return {
            "id": f"theme_{int(datetime.now().timestamp())}",
            "name": name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "role": "unpublished",
            "src": src
        }


class ShopifyDevMCPServer:
    """Shopify Dev MCP Server implementation"""

    def __init__(self):
        self.server = Server("shopify-dev-mcp-server")
        self.shopify_client: Optional[MockShopifyClient] = None
        self._initialized = False

        # Register handlers
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            return self._get_tools()

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Optional[Dict[str, Any]] = None) -> List[types.TextContent]:
            return await self._handle_tool_call(name, arguments or {})

    def _get_tools(self) -> List[types.Tool]:
        """Define available Shopify tools"""
        return [
            types.Tool(
                name="shopify_get_shop_info",
                description="Get information about the Shopify store",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            types.Tool(
                name="shopify_create_product",
                description="Create a new product in the store",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Product title"
                        },
                        "description": {
                            "type": "string",
                            "description": "Product description"
                        },
                        "vendor": {
                            "type": "string",
                            "description": "Product vendor"
                        },
                        "product_type": {
                            "type": "string",
                            "description": "Product type/category"
                        },
                        "price": {
                            "type": "string",
                            "description": "Product price (e.g., '19.99')"
                        },
                        "sku": {
                            "type": "string",
                            "description": "Stock keeping unit"
                        },
                        "inventory_quantity": {
                            "type": "integer",
                            "description": "Initial inventory quantity"
                        }
                    },
                    "required": ["title", "description"]
                }
            ),
            types.Tool(
                name="shopify_list_products",
                description="List products in the store",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Number of products to retrieve",
                            "default": 10
                        },
                        "status": {
                            "type": "string",
                            "description": "Product status filter",
                            "enum": ["active", "archived", "draft"],
                            "default": "active"
                        }
                    }
                }
            ),
            types.Tool(
                name="shopify_create_order",
                description="Create a new order",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "line_items": {
                            "type": "array",
                            "description": "Array of line items",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "variant_id": {"type": "string"},
                                    "quantity": {"type": "integer"},
                                    "price": {"type": "string"}
                                }
                            }
                        },
                        "customer": {
                            "type": "object",
                            "description": "Customer information",
                            "properties": {
                                "email": {"type": "string"},
                                "first_name": {"type": "string"},
                                "last_name": {"type": "string"}
                            }
                        }
                    },
                    "required": ["line_items", "customer"]
                }
            ),
            types.Tool(
                name="shopify_update_inventory",
                description="Update inventory levels for a product variant",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "inventory_item_id": {
                            "type": "string",
                            "description": "Inventory item ID"
                        },
                        "quantity": {
                            "type": "integer",
                            "description": "New available quantity"
                        }
                    },
                    "required": ["inventory_item_id", "quantity"]
                }
            ),
            types.Tool(
                name="shopify_create_theme",
                description="Create or deploy a theme",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Theme name"
                        },
                        "src": {
                            "type": "string",
                            "description": "Theme source URL or path"
                        }
                    },
                    "required": ["name"]
                }
            ),
            types.Tool(
                name="shopify_health_check",
                description="Check Shopify API connectivity and status",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            )
        ]

    async def _handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle tool execution"""
        try:
            # Initialize Shopify client if needed
            if not self.shopify_client:
                api_key = os.getenv("SHOPIFY_API_KEY", "test_key")
                api_secret = os.getenv("SHOPIFY_API_SECRET", "test_secret")
                store_domain = os.getenv("SHOPIFY_STORE_DOMAIN", "test-store.myshopify.com")
                self.shopify_client = MockShopifyClient(api_key, api_secret, store_domain)

            # Route to appropriate handler
            if name == "shopify_get_shop_info":
                result = await self._get_shop_info()
            elif name == "shopify_create_product":
                result = await self._create_product(arguments)
            elif name == "shopify_list_products":
                result = await self._list_products(arguments)
            elif name == "shopify_create_order":
                result = await self._create_order(arguments)
            elif name == "shopify_update_inventory":
                result = await self._update_inventory(arguments)
            elif name == "shopify_create_theme":
                result = await self._create_theme(arguments)
            elif name == "shopify_health_check":
                result = await self._health_check()
            else:
                result = {"error": f"Unknown tool: {name}"}

            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        except Exception as e:
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "error": str(e),
                    "tool": name,
                    "status": "failed"
                }, indent=2)
            )]

    async def _get_shop_info(self) -> Dict[str, Any]:
        """Get shop information"""
        shop_info = await self.shopify_client.get_shop_info()
        return {
            "status": "success",
            "shop": shop_info
        }

    async def _create_product(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a product"""
        product = await self.shopify_client.create_product(**args)
        return {
            "status": "success",
            "product": product
        }

    async def _list_products(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List products"""
        products = await self.shopify_client.list_products(**args)
        return {
            "status": "success",
            "products": products,
            "count": len(products)
        }

    async def _create_order(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create an order"""
        order = await self.shopify_client.create_order(**args)
        return {
            "status": "success",
            "order": order
        }

    async def _update_inventory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Update inventory"""
        result = await self.shopify_client.update_inventory(**args)
        return {
            "status": "success",
            "inventory": result
        }

    async def _create_theme(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update theme"""
        theme = await self.shopify_client.create_theme(**args)
        return {
            "status": "success",
            "theme": theme
        }

    async def _health_check(self) -> Dict[str, Any]:
        """Check Shopify connectivity"""
        try:
            shop_info = await self.shopify_client.get_shop_info()
            return {
                "status": "healthy",
                "service": "shopify-dev-mcp-server",
                "api_status": "connected",
                "store_domain": shop_info["domain"],
                "test_mode": self.shopify_client.test_mode,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "service": "shopify-dev-mcp-server",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def run(self):
        """Run the MCP server"""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="shopify-dev-mcp-server",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


async def main():
    """Main entry point"""
    server = ShopifyDevMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
