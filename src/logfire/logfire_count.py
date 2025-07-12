#!/usr/bin/env python3
"""
Query Logfire for log count in the last hour
"""
import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_logfire_log_count():
    """Get count of logs sent to Logfire in the last hour."""
    
    read_token = os.getenv('LOGFIRE_READ_TOKEN')
    if not read_token:
        return {"error": "LOGFIRE_READ_TOKEN not found"}
    
    # Try different possible API endpoints
    endpoints_to_try = [
        "https://logfire-api.pydantic.dev/v1/query",
        "https://api.logfire.dev/v1/query", 
        "https://logfire-us.pydantic.dev/api/query",
        "https://logfire-api.pydantic.dev/api/v1/query"
    ]
    
    # Calculate time range (last hour)
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)
    
    query_payload = {
        "query": f"SELECT count(*) as log_count FROM spans WHERE start_time >= '{one_hour_ago.isoformat()}Z'",
        "project": "devq-ai-ptolemies"
    }
    
    headers = {
        'Authorization': f'Bearer {read_token}',
        'Content-Type': 'application/json'
    }
    
    results = []
    
    for endpoint in endpoints_to_try:
        try:
            print(f"Trying endpoint: {endpoint}")
            response = requests.post(endpoint, json=query_payload, headers=headers, timeout=10)
            
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "endpoint": endpoint,
                    "data": response.json()
                }
            else:
                results.append({
                    "endpoint": endpoint,
                    "status": response.status_code,
                    "response": response.text[:100]
                })
                
        except Exception as e:
            print(f"Error with {endpoint}: {str(e)}")
            results.append({
                "endpoint": endpoint,
                "error": str(e)
            })
    
    # If no endpoints worked, try a simple GET to dashboard
    try:
        dashboard_url = "https://logfire-us.pydantic.dev/devq-ai/devq-ai-ptolemies"
        response = requests.get(dashboard_url, headers={'Authorization': f'Bearer {read_token}'}, timeout=10)
        print(f"Dashboard access status: {response.status_code}")
    except Exception as e:
        print(f"Dashboard access error: {e}")
    
    return {
        "success": False,
        "message": "No working API endpoint found",
        "attempts": results,
        "note": "Logfire API might use different authentication or endpoints"
    }

if __name__ == "__main__":
    result = get_logfire_log_count()
    print(f"\nFinal result: {result}")