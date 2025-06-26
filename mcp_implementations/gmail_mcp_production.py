#!/usr/bin/env python3
"""
Gmail MCP Server - Production Implementation
Provides Gmail operations including sending, reading, searching, and managing emails.
"""

import os
import json
import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import mimetypes

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call(["pip", "install", "google-api-python-client", "google-auth-httplib2", "google-auth-oauthlib"])
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MCP Protocol Constants
JSONRPC_VERSION = "2.0"
MCP_VERSION = "2024-11-05"

# Gmail API scope
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.compose'
]


class MCPError:
    """Standard MCP error codes"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


class GmailClient:
    """Gmail API client wrapper"""

    def __init__(self, credentials_file: Optional[str] = None, token_file: Optional[str] = None):
        self.credentials_file = credentials_file or os.getenv("GMAIL_CREDENTIALS_FILE", "gmail_credentials.json")
        self.token_file = token_file or os.getenv("GMAIL_TOKEN_FILE", "gmail_token.json")
        self.service = None
        self.creds = None

    def authenticate(self):
        """Authenticate with Gmail API"""
        if os.path.exists(self.token_file):
            self.creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)

        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(f"Credentials file not found: {self.credentials_file}")
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                self.creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(self.token_file, 'w') as token:
                token.write(self.creds.to_json())

        self.service = build('gmail', 'v1', credentials=self.creds)

    def create_message(self, to: str, subject: str, body: str,
                      cc: Optional[List[str]] = None,
                      bcc: Optional[List[str]] = None,
                      attachments: Optional[List[Dict[str, Any]]] = None) -> Dict[str, str]:
        """Create a message for an email"""
        message = MIMEMultipart() if attachments else MIMEText(body)
        message['to'] = to
        message['subject'] = subject

        if cc:
            message['cc'] = ', '.join(cc)
        if bcc:
            message['bcc'] = ', '.join(bcc)

        if attachments:
            # Add body as first part
            message.attach(MIMEText(body))

            # Add attachments
            for attachment in attachments:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(base64.b64decode(attachment['data']))
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename={attachment["filename"]}'
                )
                message.attach(part)

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {'raw': raw_message}

    async def send_email(self, to: str, subject: str, body: str,
                        cc: Optional[List[str]] = None,
                        bcc: Optional[List[str]] = None,
                        attachments: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Send an email"""
        try:
            message = self.create_message(to, subject, body, cc, bcc, attachments)
            sent_message = self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            return sent_message
        except HttpError as error:
            logger.error(f"Error sending email: {error}")
            raise

    async def list_messages(self, query: Optional[str] = None,
                          max_results: int = 10,
                          label_ids: Optional[List[str]] = None,
                          include_spam_trash: bool = False) -> List[Dict[str, Any]]:
        """List messages matching the query"""
        try:
            messages = []
            request = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results,
                labelIds=label_ids,
                includeSpamTrash=include_spam_trash
            )

            while request and len(messages) < max_results:
                response = request.execute()
                messages.extend(response.get('messages', []))
                request = self.service.users().messages().list_next(request, response)

                if len(messages) >= max_results:
                    messages = messages[:max_results]
                    break

            return messages
        except HttpError as error:
            logger.error(f"Error listing messages: {error}")
            raise

    async def get_message(self, message_id: str, format: str = 'full') -> Dict[str, Any]:
        """Get a specific message"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format=format
            ).execute()
            return message
        except HttpError as error:
            logger.error(f"Error getting message: {error}")
            raise

    async def modify_message(self, message_id: str,
                           add_labels: Optional[List[str]] = None,
                           remove_labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """Modify message labels"""
        try:
            body = {}
            if add_labels:
                body['addLabelIds'] = add_labels
            if remove_labels:
                body['removeLabelIds'] = remove_labels

            modified_message = self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body=body
            ).execute()
            return modified_message
        except HttpError as error:
            logger.error(f"Error modifying message: {error}")
            raise

    async def trash_message(self, message_id: str) -> Dict[str, Any]:
        """Move message to trash"""
        try:
            result = self.service.users().messages().trash(
                userId='me',
                id=message_id
            ).execute()
            return result
        except HttpError as error:
            logger.error(f"Error trashing message: {error}")
            raise

    async def untrash_message(self, message_id: str) -> Dict[str, Any]:
        """Remove message from trash"""
        try:
            result = self.service.users().messages().untrash(
                userId='me',
                id=message_id
            ).execute()
            return result
        except HttpError as error:
            logger.error(f"Error untrashing message: {error}")
            raise

    async def delete_message(self, message_id: str) -> Dict[str, Any]:
        """Permanently delete a message"""
        try:
            self.service.users().messages().delete(
                userId='me',
                id=message_id
            ).execute()
            return {"deleted": True, "message_id": message_id}
        except HttpError as error:
            logger.error(f"Error deleting message: {error}")
            raise

    async def list_labels(self) -> List[Dict[str, Any]]:
        """List all labels"""
        try:
            results = self.service.users().labels().list(userId='me').execute()
            return results.get('labels', [])
        except HttpError as error:
            logger.error(f"Error listing labels: {error}")
            raise

    async def create_label(self, name: str,
                         label_list_visibility: str = 'labelShow',
                         message_list_visibility: str = 'show') -> Dict[str, Any]:
        """Create a new label"""
        try:
            label_object = {
                'name': name,
                'labelListVisibility': label_list_visibility,
                'messageListVisibility': message_list_visibility
            }

            created_label = self.service.users().labels().create(
                userId='me',
                body=label_object
            ).execute()
            return created_label
        except HttpError as error:
            logger.error(f"Error creating label: {error}")
            raise

    async def create_draft(self, to: str, subject: str, body: str,
                         cc: Optional[List[str]] = None,
                         bcc: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a draft email"""
        try:
            message = self.create_message(to, subject, body, cc, bcc)
            draft = self.service.users().drafts().create(
                userId='me',
                body={'message': message}
            ).execute()
            return draft
        except HttpError as error:
            logger.error(f"Error creating draft: {error}")
            raise

    def parse_message_parts(self, parts: List[Dict[str, Any]], parent_type: str = '') -> Dict[str, Any]:
        """Parse message parts recursively"""
        result = {
            'text': '',
            'html': '',
            'attachments': []
        }

        for part in parts:
            mime_type = part.get('mimeType', '')

            if 'parts' in part:
                # Multipart, recurse
                sub_result = self.parse_message_parts(part['parts'], mime_type)
                result['text'] += sub_result['text']
                result['html'] += sub_result['html']
                result['attachments'].extend(sub_result['attachments'])
            else:
                # Single part
                body = part.get('body', {})
                data = body.get('data', '')

                if mime_type == 'text/plain':
                    result['text'] += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                elif mime_type == 'text/html':
                    result['html'] += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                elif body.get('attachmentId'):
                    # It's an attachment
                    result['attachments'].append({
                        'filename': part.get('filename', 'unknown'),
                        'mimeType': mime_type,
                        'attachmentId': body['attachmentId'],
                        'size': body.get('size', 0)
                    })

        return result


class GmailMCPServer:
    """Gmail MCP Server implementation"""

    def __init__(self):
        self.client: Optional[GmailClient] = None
        self.server_info = {
            "name": "gmail-mcp",
            "version": "1.0.0",
            "description": "Gmail operations MCP server",
            "author": "DevQ.ai Team"
        }

    async def initialize(self):
        """Initialize the server"""
        self.client = GmailClient()
        try:
            self.client.authenticate()
            logger.info("Gmail MCP Server initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Gmail client: {e}")
            self.client = None

    def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools"""
        return [
            {
                "name": "send_email",
                "description": "Send an email",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "Recipient email address"},
                        "subject": {"type": "string", "description": "Email subject"},
                        "body": {"type": "string", "description": "Email body"},
                        "cc": {"type": "array", "items": {"type": "string"}, "description": "CC recipients"},
                        "bcc": {"type": "array", "items": {"type": "string"}, "description": "BCC recipients"},
                        "attachments": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "filename": {"type": "string"},
                                    "data": {"type": "string", "description": "Base64 encoded file data"}
                                }
                            }
                        }
                    },
                    "required": ["to", "subject", "body"]
                }
            },
            {
                "name": "search_emails",
                "description": "Search for emails",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Gmail search query"},
                        "max_results": {"type": "integer", "description": "Maximum results (default: 10)"},
                        "label_ids": {"type": "array", "items": {"type": "string"}, "description": "Label IDs to filter"},
                        "include_spam_trash": {"type": "boolean", "description": "Include spam and trash"}
                    }
                }
            },
            {
                "name": "read_email",
                "description": "Read a specific email",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "string", "description": "Message ID"},
                        "format": {"type": "string", "enum": ["minimal", "full", "raw", "metadata"], "description": "Response format"}
                    },
                    "required": ["message_id"]
                }
            },
            {
                "name": "modify_labels",
                "description": "Add or remove labels from an email",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "string", "description": "Message ID"},
                        "add_labels": {"type": "array", "items": {"type": "string"}, "description": "Labels to add"},
                        "remove_labels": {"type": "array", "items": {"type": "string"}, "description": "Labels to remove"}
                    },
                    "required": ["message_id"]
                }
            },
            {
                "name": "trash_email",
                "description": "Move email to trash",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "string", "description": "Message ID"}
                    },
                    "required": ["message_id"]
                }
            },
            {
                "name": "untrash_email",
                "description": "Remove email from trash",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "string", "description": "Message ID"}
                    },
                    "required": ["message_id"]
                }
            },
            {
                "name": "delete_email",
                "description": "Permanently delete an email",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "string", "description": "Message ID"}
                    },
                    "required": ["message_id"]
                }
            },
            {
                "name": "list_labels",
                "description": "List all email labels",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "create_label",
                "description": "Create a new label",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Label name"},
                        "label_list_visibility": {"type": "string", "enum": ["labelShow", "labelHide"], "description": "Show in label list"},
                        "message_list_visibility": {"type": "string", "enum": ["show", "hide"], "description": "Show in message list"}
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "create_draft",
                "description": "Create a draft email",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "Recipient email address"},
                        "subject": {"type": "string", "description": "Email subject"},
                        "body": {"type": "string", "description": "Email body"},
                        "cc": {"type": "array", "items": {"type": "string"}, "description": "CC recipients"},
                        "bcc": {"type": "array", "items": {"type": "string"}, "description": "BCC recipients"}
                    },
                    "required": ["to", "subject", "body"]
                }
            }
        ]

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool execution"""
        if not self.client:
            return {"error": "Gmail client not initialized. Please provide credentials."}

        try:
            if tool_name == "send_email":
                result = await self.client.send_email(**arguments)
                return {
                    "message_id": result.get("id"),
                    "thread_id": result.get("threadId"),
                    "labels": result.get("labelIds", []),
                    "sent": True
                }

            elif tool_name == "search_emails":
                messages = await self.client.list_messages(**arguments)

                # Get basic info for each message
                results = []
                for msg in messages[:10]:  # Limit to 10 for performance
                    try:
                        full_msg = await self.client.get_message(msg['id'], format='metadata')
                        headers = full_msg.get('payload', {}).get('headers', [])

                        # Extract key headers
                        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                        from_email = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                        date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')

                        results.append({
                            "id": msg['id'],
                            "threadId": msg.get('threadId'),
                            "subject": subject,
                            "from": from_email,
                            "date": date,
                            "snippet": full_msg.get('snippet', '')
                        })
                    except Exception as e:
                        logger.error(f"Error fetching message {msg['id']}: {e}")

                return {
                    "messages": results,
                    "total": len(results),
                    "query": arguments.get("query", "")
                }

            elif tool_name == "read_email":
                message = await self.client.get_message(**arguments)

                # Parse message content
                payload = message.get('payload', {})
                headers = payload.get('headers', [])

                # Extract headers
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                from_email = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                to_email = next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')

                # Parse body
                body_data = {'text': '', 'html': '', 'attachments': []}
                if 'parts' in payload:
                    body_data = self.client.parse_message_parts(payload['parts'])
                else:
                    # Single part message
                    body = payload.get('body', {})
                    data = body.get('data', '')
                    if data:
                        body_data['text'] = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

                return {
                    "id": message.get('id'),
                    "threadId": message.get('threadId'),
                    "subject": subject,
                    "from": from_email,
                    "to": to_email,
                    "date": date,
                    "snippet": message.get('snippet', ''),
                    "body": body_data['text'] or body_data['html'],
                    "attachments": body_data['attachments'],
                    "labels": message.get('labelIds', [])
                }

            elif tool_name == "modify_labels":
                result = await self.client.modify_message(**arguments)
                return {
                    "message_id": result.get('id'),
                    "labels": result.get('labelIds', []),
                    "modified": True
                }

            elif tool_name == "trash_email":
                result = await self.client.trash_message(**arguments)
                return {
                    "message_id": result.get('id'),
                    "trashed": True
                }

            elif tool_name == "untrash_email":
                result = await self.client.untrash_message(**arguments)
                return {
                    "message_id": result.get('id'),
                    "untrashed": True
                }

            elif tool_name == "delete_email":
                result = await self.client.delete_message(**arguments)
                return result

            elif tool_name == "list_labels":
                labels = await self.client.list_labels()
                return {
                    "labels": [{
                        "id": label.get('id'),
                        "name": label.get('name'),
                        "type": label.get('type'),
                        "messageListVisibility": label.get('messageListVisibility'),
                        "labelListVisibility": label.get('labelListVisibility')
                    } for label in labels]
                }

            elif tool_name == "create_label":
                label = await self.client.create_label(**arguments)
                return {
                    "id": label.get('id'),
                    "name": label.get('name'),
                    "created": True
                }

            elif tool_name == "create_draft":
                draft = await self.client.create_draft(**arguments)
                return {
                    "draft_id": draft.get('id'),
                    "message_id": draft.get('message', {}).get('id'),
                    "created": True
                }

            else:
                raise ValueError(f"Unknown tool: {tool_name}")

        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {"error": str(e)}

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle JSON-RPC request"""
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        try:
            if method == "initialize":
                await self.initialize()
                result = {
                    "protocolVersion": MCP_VERSION,
                    "serverInfo": self.server_info,
                    "capabilities": {
                        "tools": True,
                        "resources": False,
                        "prompts": False,
                        "logging": False
                    },
                    "instructions": "Gmail MCP server for email operations"
                }
            elif method == "tools/list":
                result = {"tools": self.list_tools()}
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                result = await self.handle_tool_call(tool_name, arguments)
            elif method == "health":
                result = {
                    "status": "healthy" if self.client else "no_auth",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "authenticated": self.client is not None
                }
            else:
                return {
                    "jsonrpc": JSONRPC_VERSION,
                    "id": request_id,
                    "error": {
                        "code": MCPError.METHOD_NOT_FOUND,
                        "message": f"Method not found: {method}"
                    }
                }

            return {
                "jsonrpc": JSONRPC_VERSION,
                "id": request_id,
                "result": result
            }

        except Exception as e:
            logger.error(f"Request handling error: {e}")
            return {
                "jsonrpc": JSONRPC_VERSION,
                "id": request_id,
                "error": {
                    "code": MCPError.INTERNAL_ERROR,
                    "message": str(e)
                }
            }

    async def run_stdio(self):
        """Run the server in stdio mode"""
        logger.info("Starting Gmail MCP Server in stdio mode")

        try:
            while True:
                # Read request from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, input
                )

                if not line:
                    continue

                try:
                    request = json.loads(line)
                    response = await self.handle_request(request)

                    # Write response to stdout
                    print(json.dumps(response))

                except json.JSONDecodeError as e:
                    error_response = {
                        "jsonrpc": JSONRPC_VERSION,
                        "id": None,
                        "error": {
                            "code": MCPError.PARSE_ERROR,
                            "message": f"Parse error: {e}"
                        }
                    }
                    print(json.dumps(error_response))

        except KeyboardInterrupt:
            logger.info("Server shutdown requested")
        except Exception as e:
            logger.error(f"Server error: {e}")


async def main():
    """Main entry point"""
    server = GmailMCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
