#!/usr/bin/env python3
import os
import sys
sys.path.append('src')

# Set environment
os.environ['LOGFIRE_TOKEN'] = os.getenv('LOGFIRE_WRITE_TOKEN', '')

import logfire

# Configure and test
logfire.configure()
print("Testing logfire integration...")

# Send test log
logfire.info("Logfire integration test - CLI dashboard integration restored", 
             component="test", 
             source="machina-cli",
             test_successful=True)

print("✅ Logfire test completed - check your Logfire dashboard!")
print(f"Project URL: https://logfire-us.pydantic.dev/devq-ai/devq-ai")