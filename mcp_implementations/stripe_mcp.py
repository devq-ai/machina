#!/usr/bin/env python3
"""
Stripe MCP Server - Production Implementation
Real Stripe API integration for payment processing
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from decimal import Decimal
import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

# Real Stripe SDK
try:
    import stripe
except ImportError:
    print("ERROR: stripe package not installed. Run: pip install stripe", file=sys.stderr)
    sys.exit(1)

# Logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StripeMCPServer:
    """Production Stripe MCP Server implementation"""

    def __init__(self):
        self.server = Server("stripe-mcp")
        self.stripe = stripe
        self._initialized = False

        # Validate API key
        api_key = os.getenv("STRIPE_API_KEY")
        if not api_key:
            raise ValueError("STRIPE_API_KEY environment variable is required")

        # Configure Stripe
        self.stripe.api_key = api_key
        self.stripe.api_version = "2024-06-20"  # Latest stable version

        # Check if in test mode
        self.test_mode = api_key.startswith("sk_test_")

        # Register handlers
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            return self._get_tools()

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Optional[Dict[str, Any]] = None) -> List[types.TextContent]:
            return await self._handle_tool_call(name, arguments or {})

    def _get_tools(self) -> List[types.Tool]:
        """Define available Stripe tools"""
        return [
            types.Tool(
                name="stripe_create_payment_intent",
                description="Create a new payment intent for processing payments",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "amount": {
                            "type": "integer",
                            "description": "Amount in cents (e.g., 1000 = $10.00)"
                        },
                        "currency": {
                            "type": "string",
                            "description": "Three-letter ISO currency code (e.g., 'usd')",
                            "default": "usd"
                        },
                        "description": {
                            "type": "string",
                            "description": "Payment description"
                        },
                        "customer": {
                            "type": "string",
                            "description": "Customer ID (optional)"
                        },
                        "payment_method_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Payment method types to accept",
                            "default": ["card"]
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Additional metadata"
                        },
                        "setup_future_usage": {
                            "type": "string",
                            "enum": ["on_session", "off_session"],
                            "description": "Save payment method for future use"
                        }
                    },
                    "required": ["amount"]
                }
            ),
            types.Tool(
                name="stripe_retrieve_payment_intent",
                description="Retrieve an existing payment intent",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "payment_intent_id": {
                            "type": "string",
                            "description": "Payment intent ID (e.g., 'pi_...')"
                        }
                    },
                    "required": ["payment_intent_id"]
                }
            ),
            types.Tool(
                name="stripe_confirm_payment_intent",
                description="Confirm a payment intent",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "payment_intent_id": {
                            "type": "string",
                            "description": "Payment intent ID to confirm"
                        },
                        "payment_method": {
                            "type": "string",
                            "description": "Payment method ID"
                        }
                    },
                    "required": ["payment_intent_id"]
                }
            ),
            types.Tool(
                name="stripe_create_customer",
                description="Create a new Stripe customer",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "Customer email address"
                        },
                        "name": {
                            "type": "string",
                            "description": "Customer full name"
                        },
                        "phone": {
                            "type": "string",
                            "description": "Customer phone number"
                        },
                        "description": {
                            "type": "string",
                            "description": "Customer description"
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Additional metadata"
                        },
                        "payment_method": {
                            "type": "string",
                            "description": "Default payment method ID"
                        }
                    },
                    "required": ["email"]
                }
            ),
            types.Tool(
                name="stripe_retrieve_customer",
                description="Retrieve customer details",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Customer ID (e.g., 'cus_...')"
                        }
                    },
                    "required": ["customer_id"]
                }
            ),
            types.Tool(
                name="stripe_list_customers",
                description="List customers with optional filters",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "Filter by email"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of customers to retrieve (1-100)",
                            "default": 10
                        },
                        "created": {
                            "type": "object",
                            "properties": {
                                "gte": {"type": "integer", "description": "Created on or after (timestamp)"},
                                "lte": {"type": "integer", "description": "Created on or before (timestamp)"}
                            }
                        }
                    }
                }
            ),
            types.Tool(
                name="stripe_create_subscription",
                description="Create a subscription for a customer",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "customer": {
                            "type": "string",
                            "description": "Customer ID (e.g., 'cus_...')"
                        },
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "price": {"type": "string", "description": "Price ID"},
                                    "quantity": {"type": "integer", "default": 1}
                                }
                            },
                            "description": "Subscription items"
                        },
                        "trial_period_days": {
                            "type": "integer",
                            "description": "Number of trial days"
                        },
                        "payment_behavior": {
                            "type": "string",
                            "enum": ["allow_incomplete", "default_incomplete", "error_if_incomplete", "pending_if_incomplete"],
                            "default": "default_incomplete"
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Additional metadata"
                        }
                    },
                    "required": ["customer", "items"]
                }
            ),
            types.Tool(
                name="stripe_cancel_subscription",
                description="Cancel a subscription",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "subscription_id": {
                            "type": "string",
                            "description": "Subscription ID (e.g., 'sub_...')"
                        },
                        "cancel_at_period_end": {
                            "type": "boolean",
                            "description": "Cancel at end of current period",
                            "default": false
                        },
                        "cancellation_details": {
                            "type": "object",
                            "properties": {
                                "comment": {"type": "string"},
                                "feedback": {
                                    "type": "string",
                                    "enum": ["customer_service", "low_quality", "missing_features", "other", "switched_service", "too_complex", "too_expensive", "unused"]
                                }
                            }
                        }
                    },
                    "required": ["subscription_id"]
                }
            ),
            types.Tool(
                name="stripe_create_refund",
                description="Create a refund for a payment",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "charge": {
                            "type": "string",
                            "description": "Charge ID to refund (ch_...)"
                        },
                        "payment_intent": {
                            "type": "string",
                            "description": "Payment intent ID to refund (pi_...)"
                        },
                        "amount": {
                            "type": "integer",
                            "description": "Amount in cents to refund (partial refund)"
                        },
                        "reason": {
                            "type": "string",
                            "enum": ["duplicate", "fraudulent", "requested_by_customer"],
                            "description": "Reason for refund"
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Additional metadata"
                        }
                    }
                }
            ),
            types.Tool(
                name="stripe_retrieve_balance",
                description="Get current Stripe account balance",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            types.Tool(
                name="stripe_list_payment_intents",
                description="List recent payment intents",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Number of payment intents to retrieve (1-100)",
                            "default": 10
                        },
                        "customer": {
                            "type": "string",
                            "description": "Filter by customer ID"
                        },
                        "created": {
                            "type": "object",
                            "properties": {
                                "gte": {"type": "integer
