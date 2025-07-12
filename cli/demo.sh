#!/bin/bash

# Demo script for DevGen CLI SSH and Web servers
# This script demonstrates the amazing SSH-accessible demo experience for DevQ.ai

set -e

echo "🎯 DevGen CLI Demo - SSH & Web Server Testing"
echo "============================================="
echo ""

# Configuration
SSH_PORT=2222
WEB_PORT=8080
DEMO_USER="demo"
DEMO_PASSWORD="demo"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_header() {
    echo -e "${PURPLE}=== $1 ===${NC}"
}

# Check if devgen binary exists
if [ ! -f "./build/devgen" ]; then
    print_error "DevGen binary not found. Please run 'make build' first."
    exit 1
fi

print_header "Step 1: Build DevGen CLI"
print_status "Building DevGen CLI..."
make build
if [ $? -eq 0 ]; then
    print_success "DevGen CLI built successfully!"
else
    print_error "Failed to build DevGen CLI"
    exit 1
fi

print_header "Step 2: Start SSH Server"
print_status "Starting SSH server on port $SSH_PORT..."

# Kill any existing devgen processes
pkill -f "devgen ssh" || true
pkill -f "devgen web" || true

# Start SSH server in background
./build/devgen ssh --ssh-host localhost --ssh-port $SSH_PORT &
SSH_PID=$!

# Wait for SSH server to start
sleep 2

if kill -0 $SSH_PID 2>/dev/null; then
    print_success "SSH server started successfully (PID: $SSH_PID)"
    print_status "SSH server listening on localhost:$SSH_PORT"
else
    print_error "Failed to start SSH server"
    exit 1
fi

print_header "Step 3: Start Web Server"
print_status "Starting web server on port $WEB_PORT..."

# Start web server in background
./build/devgen web --web-port $WEB_PORT --allow-origin "*" &
WEB_PID=$!

# Wait for web server to start
sleep 2

if kill -0 $WEB_PID 2>/dev/null; then
    print_success "Web server started successfully (PID: $WEB_PID)"
    print_status "Web server listening on localhost:$WEB_PORT"
else
    print_error "Failed to start web server"
    kill $SSH_PID 2>/dev/null || true
    exit 1
fi

print_header "Step 4: Test Web API Endpoints"
print_status "Testing web API endpoints..."

# Test health endpoint
print_status "Testing health endpoint..."
if curl -s "http://localhost:$WEB_PORT/api/v1/health" > /dev/null; then
    print_success "Health endpoint is working"
else
    print_error "Health endpoint is not responding"
fi

# Test registry endpoint
print_status "Testing registry endpoint..."
if curl -s "http://localhost:$WEB_PORT/api/v1/mcp/registry" > /dev/null; then
    print_success "Registry endpoint is working"
else
    print_error "Registry endpoint is not responding"
fi

# Test servers endpoint
print_status "Testing servers endpoint..."
if curl -s "http://localhost:$WEB_PORT/api/v1/mcp/servers" > /dev/null; then
    print_success "Servers endpoint is working"
else
    print_error "Servers endpoint is not responding"
fi

print_header "Step 5: Demo Information"
echo ""
print_success "🚀 DevGen Demo Servers Are Running!"
echo ""
echo -e "${CYAN}SSH Server:${NC}"
echo "  • Host: localhost"
echo "  • Port: $SSH_PORT"
echo "  • Username: $DEMO_USER"
echo "  • Password: $DEMO_PASSWORD"
echo ""
echo -e "${CYAN}Web Server:${NC}"
echo "  • Base URL: http://localhost:$WEB_PORT"
echo "  • Health: http://localhost:$WEB_PORT/api/v1/health"
echo "  • Registry: http://localhost:$WEB_PORT/api/v1/mcp/registry"
echo "  • Servers: http://localhost:$WEB_PORT/api/v1/mcp/servers"
echo ""

print_header "Step 6: SSH Connection Examples"
echo ""
echo -e "${YELLOW}Try these SSH commands:${NC}"
echo ""
echo "1. Connect to SSH server:"
echo "   ssh -p $SSH_PORT $DEMO_USER@localhost"
echo ""
echo "2. Available SSH commands once connected:"
echo "   • list        - List all MCP servers"
echo "   • health      - Check server health"
echo "   • status <name> - Show server status"
echo "   • toggle <name> - Toggle server on/off"
echo "   • help        - Show available commands"
echo "   • exit        - Close connection"
echo ""

print_header "Step 7: Web API Examples"
echo ""
echo -e "${YELLOW}Try these web API calls:${NC}"
echo ""
echo "1. Check system health:"
echo "   curl http://localhost:$WEB_PORT/api/v1/health"
echo ""
echo "2. Get MCP registry:"
echo "   curl http://localhost:$WEB_PORT/api/v1/mcp/registry"
echo ""
echo "3. List servers:"
echo "   curl http://localhost:$WEB_PORT/api/v1/mcp/servers"
echo ""
echo "4. Toggle a server:"
echo "   curl -X POST http://localhost:$WEB_PORT/api/v1/mcp/servers/context7-mcp \\"
echo "        -H 'Content-Type: application/json' \\"
echo "        -d '{\"action\": \"toggle\"}'"
echo ""

print_header "Step 8: DevQ.ai Website Integration"
echo ""
echo -e "${YELLOW}For DevQ.ai website integration:${NC}"
echo ""
echo "1. Web Dashboard Integration:"
echo "   • Add to devq.ai website: <LiveMCPDemo endpoint=\"http://localhost:$WEB_PORT/api/v1\" />"
echo "   • CORS is enabled for all origins (*)"
echo "   • Real-time server status and controls"
echo ""
echo "2. SSH Terminal Access:"
echo "   • Visitors can SSH directly: ssh -p $SSH_PORT demo@your-server.com"
echo "   • Authentic terminal experience"
echo "   • Real CLI commands, not mocked"
echo ""

print_header "Step 9: Production Deployment"
echo ""
echo -e "${YELLOW}For production deployment:${NC}"
echo ""
echo "1. SSH Tunneling:"
echo "   ssh -R $SSH_PORT:localhost:$SSH_PORT user@devq.ai"
echo ""
echo "2. Web Server Proxy:"
echo "   # Add to nginx config:"
echo "   location /api/ {"
echo "       proxy_pass http://localhost:$WEB_PORT;"
echo "       add_header Access-Control-Allow-Origin \"https://devq.ai\";"
echo "   }"
echo ""
echo "3. Using ngrok for demos:"
echo "   ngrok http $WEB_PORT"
echo ""

print_header "Step 10: Interactive Demo"
echo ""
read -p "Press Enter to continue, or 'q' to quit and cleanup: " -r
if [[ $REPLY =~ ^[Qq]$ ]]; then
    print_status "Cleaning up..."
    kill $SSH_PID 2>/dev/null || true
    kill $WEB_PID 2>/dev/null || true
    print_success "Demo completed and cleaned up!"
    exit 0
fi

print_status "Servers will continue running in background..."
print_status "SSH PID: $SSH_PID"
print_status "Web PID: $WEB_PID"
echo ""
print_warning "To stop servers later, run:"
echo "  kill $SSH_PID $WEB_PID"
echo ""
print_success "🎉 Demo setup complete! Both SSH and Web servers are running."
echo ""
echo -e "${CYAN}Quick Test:${NC}"
echo "• SSH: ssh -p $SSH_PORT $DEMO_USER@localhost"
echo "• Web: curl http://localhost:$WEB_PORT/api/v1/health"
echo ""
echo -e "${PURPLE}This creates the perfect demo experience for DevQ.ai!${NC}"
echo "• ${GREEN}Real MCP servers${NC} (not mocked)"
echo "• ${GREEN}Authentic terminal experience${NC} via SSH"
echo "• ${GREEN}Modern web integration${NC} for website"
echo "• ${GREEN}Live server management${NC} and monitoring"
echo ""
print_success "Ready to showcase DevQ.ai's unique development environment! 🚀"
