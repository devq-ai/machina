#!/bin/bash

# Test script to run Machina dashboard with proper TTY and capture behavior
# This script helps troubleshoot the empty dashboard issue

set -e

echo "=== Machina Dashboard Test Script ==="
echo "Testing dashboard with proper TTY..."
echo

# Build the latest version
echo "Building devgen..."
go build -o build/devgen . 2>&1

# Check if build was successful
if [ ! -f "build/devgen" ]; then
    echo "ERROR: Build failed - devgen binary not found"
    exit 1
fi

echo "✅ Build successful"
echo

# Test registry loading first
echo "Testing registry loading..."
./build/devgen debug-registry | head -20
echo

# Test list command to confirm 11 servers
echo "Testing list command..."
server_count=$(./build/devgen list 2>/dev/null | grep -c "^[0-9]")
echo "✅ List command shows $server_count servers"
echo

# Now test the dashboard with timeout and input
echo "Testing dashboard with TTY..."
echo "This will run the dashboard for 5 seconds then quit automatically"
echo "Look for:"
echo "  - Loading message"
echo "  - Debug output"
echo "  - Server grid display"
echo "  - Any error messages"
echo

# Create a script to send 'q' after a delay
(sleep 5; echo "q") | script -q /dev/null ./build/devgen dashboard 2>&1 | head -50

echo
echo "=== Test Complete ==="
echo "If you see a completely blank screen above, the issue is confirmed."
echo "If you see debug output, the dashboard is working but may have rendering issues."
