"""
MCP Tools Implementation
"""

from typing import Dict, Any, List
import mcp.types as types
from datetime import datetime
import shopify
import os

def get_shopify_session():
    """Get a Shopify session."""
    shop_url = f"https://{os.environ.get('SHOPIFY_API_KEY')}:{os.environ.get('SHOPIFY_PASSWORD')}@{os.environ.get('SHOPIFY_STORE_NAME')}.myshopify.com/admin"
    shopify.ShopifyResource.set_site(shop_url)
    return shopify

def get_tools() -> List[types.Tool]:
    """Define available tools"""
    return [
        types.Tool(
            name="get_products",
            description="Gets a list of products.",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        ),
        types.Tool(
            name="get_orders",
            description="Gets a list of orders.",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        ),
        types.Tool(
            name="create_product",
            description="Creates a new product.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title of the product."
                    },
                    "body_html": {
                        "type": "string",
                        "description": "The description of the product."
                    }
                },
                "required": ["title"]
            }
        ),
        types.Tool(
            name="health_check",
            description="Check server health",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


async def handle_tool_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tool execution"""
    shopify_session = get_shopify_session()
    if name == "get_products":
        try:
            products = shopify_session.Product.find()
            return {
                "status": "success",
                "products": [product.to_dict() for product in products],
                "timestamp": str(datetime.now())
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": str(datetime.now())
            }
    elif name == "get_orders":
        try:
            orders = shopify_session.Order.find()
            return {
                "status": "success",
                "orders": [order.to_dict() for order in orders],
                "timestamp": str(datetime.now())
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": str(datetime.now())
            }
    elif name == "create_product":
        try:
            product = shopify_session.Product()
            product.title = arguments["title"]
            product.body_html = arguments.get("body_html", "")
            product.save()
            return {
                "status": "success",
                "product": product.to_dict(),
                "timestamp": str(datetime.now())
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": str(datetime.now())
            }
    elif name == "health_check":
        return {
            "status": "healthy",
            "service": "shopify-mcp",
            "timestamp": str(datetime.now())
        }
    else:
        return {"error": f"Unknown tool: {name}"}
