#!/usr/bin/env python3
"""
Calendar MCP Server - Production Implementation
Provides Google Calendar integration for event management and scheduling.
"""

import os
import json
import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone
from dateutil import parser

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import pytz
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call(["pip", "install", "google-api-python-client", "google-auth-httplib2",
                          "google-auth-oauthlib", "python-dateutil", "pytz"])
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import pytz

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MCP Protocol Constants
JSONRPC_VERSION = "2.0"
MCP_VERSION = "2024-11-05"

# Google Calendar API scope
SCOPES = ['https://www.googleapis.com/auth/calendar']


class MCPError:
    """Standard MCP error codes"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


class CalendarClient:
    """Google Calendar API client"""

    def __init__(self, credentials_file: Optional[str] = None, token_file: Optional[str] = None):
        self.credentials_file = credentials_file or os.getenv("GOOGLE_CALENDAR_CREDENTIALS_FILE", "credentials.json")
        self.token_file = token_file or os.getenv("GOOGLE_CALENDAR_TOKEN_FILE", "token.json")
        self.service = None
        self.creds = None

    def authenticate(self):
        """Authenticate with Google Calendar API"""
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

        self.service = build('calendar', 'v3', credentials=self.creds)

    def _parse_datetime(self, dt_string: str, timezone_str: str = "UTC") -> Dict[str, str]:
        """Parse datetime string and return Google Calendar format"""
        try:
            # Parse the datetime
            dt = parser.parse(dt_string)

            # If no timezone info, add the specified timezone
            if dt.tzinfo is None:
                tz = pytz.timezone(timezone_str)
                dt = tz.localize(dt)

            # Return in Google Calendar format
            return {
                "dateTime": dt.isoformat(),
                "timeZone": timezone_str
            }
        except Exception as e:
            logger.error(f"Error parsing datetime: {e}")
            raise ValueError(f"Invalid datetime format: {dt_string}")

    async def list_calendars(self) -> List[Dict[str, Any]]:
        """List all calendars"""
        try:
            calendar_list = self.service.calendarList().list().execute()
            return calendar_list.get('items', [])
        except HttpError as error:
            logger.error(f"Error listing calendars: {error}")
            raise

    async def list_events(self, calendar_id: str = 'primary',
                         time_min: Optional[str] = None,
                         time_max: Optional[str] = None,
                         max_results: int = 10,
                         query: Optional[str] = None) -> List[Dict[str, Any]]:
        """List calendar events"""
        try:
            # Default to next 7 days if no time range specified
            if not time_min:
                time_min = datetime.now(timezone.utc).isoformat()
            if not time_max:
                time_max = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime',
                q=query
            ).execute()

            return events_result.get('items', [])
        except HttpError as error:
            logger.error(f"Error listing events: {error}")
            raise

    async def create_event(self,
                          summary: str,
                          start_time: str,
                          end_time: str,
                          description: Optional[str] = None,
                          location: Optional[str] = None,
                          attendees: Optional[List[str]] = None,
                          timezone: str = "UTC",
                          calendar_id: str = 'primary',
                          reminders: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Create a calendar event"""
        try:
            event = {
                'summary': summary,
                'start': self._parse_datetime(start_time, timezone),
                'end': self._parse_datetime(end_time, timezone),
            }

            if description:
                event['description'] = description

            if location:
                event['location'] = location

            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]

            if reminders:
                event['reminders'] = {
                    'useDefault': False,
                    'overrides': reminders
                }
            else:
                event['reminders'] = {'useDefault': True}

            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=event,
                sendNotifications=True
            ).execute()

            return created_event
        except HttpError as error:
            logger.error(f"Error creating event: {error}")
            raise

    async def update_event(self,
                          event_id: str,
                          calendar_id: str = 'primary',
                          **kwargs) -> Dict[str, Any]:
        """Update an existing event"""
        try:
            # Get the existing event
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()

            # Update fields
            if 'summary' in kwargs:
                event['summary'] = kwargs['summary']
            if 'description' in kwargs:
                event['description'] = kwargs['description']
            if 'location' in kwargs:
                event['location'] = kwargs['location']
            if 'start_time' in kwargs and 'timezone' in kwargs:
                event['start'] = self._parse_datetime(kwargs['start_time'], kwargs['timezone'])
            if 'end_time' in kwargs and 'timezone' in kwargs:
                event['end'] = self._parse_datetime(kwargs['end_time'], kwargs['timezone'])
            if 'attendees' in kwargs:
                event['attendees'] = [{'email': email} for email in kwargs['attendees']]

            updated_event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event,
                sendNotifications=True
            ).execute()

            return updated_event
        except HttpError as error:
            logger.error(f"Error updating event: {error}")
            raise

    async def delete_event(self, event_id: str, calendar_id: str = 'primary') -> Dict[str, Any]:
        """Delete a calendar event"""
        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id,
                sendNotifications=True
            ).execute()

            return {
                "success": True,
                "event_id": event_id,
                "calendar_id": calendar_id
            }
        except HttpError as error:
            logger.error(f"Error deleting event: {error}")
            raise

    async def find_free_slots(self,
                             duration_minutes: int,
                             start_date: str,
                             end_date: str,
                             calendar_ids: Optional[List[str]] = None,
                             working_hours_start: str = "09:00",
                             working_hours_end: str = "17:00",
                             timezone: str = "UTC") -> List[Dict[str, Any]]:
        """Find available time slots"""
        try:
            if not calendar_ids:
                calendar_ids = ['primary']

            # Parse dates
            start_dt = parser.parse(start_date)
            end_dt = parser.parse(end_date)

            # Get all events in the time range
            all_busy_times = []
            for cal_id in calendar_ids:
                events = await self.list_events(
                    calendar_id=cal_id,
                    time_min=start_dt.isoformat(),
                    time_max=end_dt.isoformat(),
                    max_results=100
                )

                for event in events:
                    if 'start' in event and 'end' in event:
                        start = event['start'].get('dateTime', event['start'].get('date'))
                        end = event['end'].get('dateTime', event['end'].get('date'))
                        if start and end:
                            all_busy_times.append({
                                'start': parser.parse(start),
                                'end': parser.parse(end)
                            })

            # Sort busy times
            all_busy_times.sort(key=lambda x: x['start'])

            # Find free slots
            free_slots = []
            current_date = start_dt.date()

            while current_date <= end_dt.date():
                # Set working hours for this day
                work_start = parser.parse(f"{current_date} {working_hours_start}")
                work_end = parser.parse(f"{current_date} {working_hours_end}")

                # Add timezone
                tz = pytz.timezone(timezone)
                work_start = tz.localize(work_start)
                work_end = tz.localize(work_end)

                # Find free slots in this day
                current_time = work_start

                for busy in all_busy_times:
                    if busy['start'].date() > current_date:
                        break

                    if busy['end'] <= current_time:
                        continue

                    if busy['start'] > current_time:
                        # Found a gap
                        gap_duration = (busy['start'] - current_time).total_seconds() / 60
                        if gap_duration >= duration_minutes:
                            free_slots.append({
                                'start': current_time.isoformat(),
                                'end': busy['start'].isoformat(),
                                'duration_minutes': int(gap_duration)
                            })

                    current_time = max(current_time, busy['end'])

                # Check if there's time at the end of the day
                if current_time < work_end:
                    gap_duration = (work_end - current_time).total_seconds() / 60
                    if gap_duration >= duration_minutes:
                        free_slots.append({
                            'start': current_time.isoformat(),
                            'end': work_end.isoformat(),
                            'duration_minutes': int(gap_duration)
                        })

                current_date += timedelta(days=1)

            return free_slots
        except Exception as e:
            logger.error(f"Error finding free slots: {e}")
            raise


class CalendarMCPServer:
    """Calendar MCP Server implementation"""

    def __init__(self):
        self.client: Optional[CalendarClient] = None
        self.server_info = {
            "name": "calendar-mcp",
            "version": "1.0.0",
            "description": "Google Calendar integration for event management",
            "author": "DevQ.ai Team"
        }

    async def initialize(self):
        """Initialize the server"""
        self.client = CalendarClient()
        try:
            self.client.authenticate()
            logger.info("Calendar MCP Server initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Calendar client: {e}")
            self.client = None

    def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools"""
        return [
            {
                "name": "list_calendars",
                "description": "List all available calendars",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "list_events",
                "description": "List calendar events",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "calendar_id": {"type": "string", "description": "Calendar ID (default: primary)"},
                        "time_min": {"type": "string", "description": "Start time (ISO format)"},
                        "time_max": {"type": "string", "description": "End time (ISO format)"},
                        "max_results": {"type": "integer", "description": "Maximum results (default: 10)"},
                        "query": {"type": "string", "description": "Search query"}
                    }
                }
            },
            {
                "name": "create_event",
                "description": "Create a new calendar event",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string", "description": "Event title"},
                        "start_time": {"type": "string", "description": "Start time"},
                        "end_time": {"type": "string", "description": "End time"},
                        "description": {"type": "string", "description": "Event description"},
                        "location": {"type": "string", "description": "Event location"},
                        "attendees": {"type": "array", "items": {"type": "string"}, "description": "Attendee emails"},
                        "timezone": {"type": "string", "description": "Timezone (default: UTC)"},
                        "calendar_id": {"type": "string", "description": "Calendar ID (default: primary)"},
                        "reminders": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "method": {"type": "string", "enum": ["email", "popup"]},
                                    "minutes": {"type": "integer"}
                                }
                            }
                        }
                    },
                    "required": ["summary", "start_time", "end_time"]
                }
            },
            {
                "name": "update_event",
                "description": "Update an existing calendar event",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "event_id": {"type": "string", "description": "Event ID"},
                        "calendar_id": {"type": "string", "description": "Calendar ID (default: primary)"},
                        "summary": {"type": "string", "description": "Event title"},
                        "start_time": {"type": "string", "description": "Start time"},
                        "end_time": {"type": "string", "description": "End time"},
                        "description": {"type": "string", "description": "Event description"},
                        "location": {"type": "string", "description": "Event location"},
                        "attendees": {"type": "array", "items": {"type": "string"}, "description": "Attendee emails"},
                        "timezone": {"type": "string", "description": "Timezone"}
                    },
                    "required": ["event_id"]
                }
            },
            {
                "name": "delete_event",
                "description": "Delete a calendar event",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "event_id": {"type": "string", "description": "Event ID"},
                        "calendar_id": {"type": "string", "description": "Calendar ID (default: primary)"}
                    },
                    "required": ["event_id"]
                }
            },
            {
                "name": "find_free_slots",
                "description": "Find available time slots",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "duration_minutes": {"type": "integer", "description": "Required duration in minutes"},
                        "start_date": {"type": "string", "description": "Start date for search"},
                        "end_date": {"type": "string", "description": "End date for search"},
                        "calendar_ids": {"type": "array", "items": {"type": "string"}, "description": "Calendar IDs to check"},
                        "working_hours_start": {"type": "string", "description": "Working hours start (HH:MM)"},
                        "working_hours_end": {"type": "string", "description": "Working hours end (HH:MM)"},
                        "timezone": {"type": "string", "description": "Timezone (default: UTC)"}
                    },
                    "required": ["duration_minutes", "start_date", "end_date"]
                }
            }
        ]

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool execution"""
        if not self.client:
            return {"error": "Calendar client not initialized. Please provide credentials."}

        try:
            if tool_name == "list_calendars":
                calendars = await self.client.list_calendars()
                return {
                    "calendars": [{
                        "id": cal.get("id"),
                        "summary": cal.get("summary"),
                        "primary": cal.get("primary", False),
                        "accessRole": cal.get("accessRole")
                    } for cal in calendars]
                }

            elif tool_name == "list_events":
                events = await self.client.list_events(**arguments)
                return {
                    "events": [{
                        "id": event.get("id"),
                        "summary": event.get("summary"),
                        "start": event.get("start"),
                        "end": event.get("end"),
                        "location": event.get("location"),
                        "attendees": [a.get("email") for a in event.get("attendees", [])]
                    } for event in events]
                }

            elif tool_name == "create_event":
                event = await self.client.create_event(**arguments)
                return {
                    "event_id": event.get("id"),
                    "summary": event.get("summary"),
                    "htmlLink": event.get("htmlLink"),
                    "created": True
                }

            elif tool_name == "update_event":
                event = await self.client.update_event(**arguments)
                return {
                    "event_id": event.get("id"),
                    "summary": event.get("summary"),
                    "updated": True
                }

            elif tool_name == "delete_event":
                result = await self.client.delete_event(**arguments)
                return result

            elif tool_name == "find_free_slots":
                slots = await self.client.find_free_slots(**arguments)
                return {
                    "free_slots": slots,
                    "count": len(slots)
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
                    "instructions": "Calendar MCP server for Google Calendar integration"
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
        logger.info("Starting Calendar MCP Server in stdio mode")

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
    server = CalendarMCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
