"""
MCP Tools Implementation
"""

from typing import Dict, Any, List
import mcp.types as types
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

def get_tools() -> List[types.Tool]:
    """Define available tools"""
    return [
        types.Tool(
            name="s3_list_buckets",
            description="Lists all S3 buckets.",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        ),
        types.Tool(
            name="ec2_list_instances",
            description="Lists all EC2 instances.",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        ),
        types.Tool(
            name="iam_list_users",
            description="Lists all IAM users.",
            inputSchema={
                "type": "object",
                "properties": {},
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
    if name == "s3_list_buckets":
        try:
            s3 = boto3.client("s3", region_name="us-east-1")
            response = s3.list_buckets()
            buckets = [bucket["Name"] for bucket in response["Buckets"]]
            return {
                "status": "success",
                "buckets": buckets,
                "timestamp": str(datetime.now())
            }
        except ClientError as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": str(datetime.now())
            }
    elif name == "ec2_list_instances":
        try:
            ec2 = boto3.client("ec2", region_name="us-east-1")
            response = ec2.describe_instances()
            instances = []
            for reservation in response["Reservations"]:
                for instance in reservation["Instances"]:
                    instances.append(instance["InstanceId"])
            return {
                "status": "success",
                "instances": instances,
                "timestamp": str(datetime.now())
            }
        except ClientError as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": str(datetime.now())
            }
    elif name == "iam_list_users":
        try:
            iam = boto3.client("iam", region_name="us-east-1")
            response = iam.list_users()
            users = [user["UserName"] for user in response["Users"]]
            return {
                "status": "success",
                "users": users,
                "timestamp": str(datetime.now())
            }
        except ClientError as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": str(datetime.now())
            }
    elif name == "health_check":
        return {
            "status": "healthy",
            "service": "aws-core-mcp-server",
            "timestamp": str(datetime.now())
        }
    else:
        return {"error": f"Unknown tool: {name}"}
