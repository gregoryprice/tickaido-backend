#!/bin/bash
set -e

echo "🔧 Testing Agent-Specific Tool Filtering End-to-End"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Start all services
print_status "Starting Docker services..."
docker compose up -d

# Wait for services to be ready
print_status "Waiting for services to start..."
sleep 15

# Function to check service health
check_service() {
    local service_name="$1"
    local health_url="$2"
    local max_attempts=30
    local attempt=1
    
    print_status "Checking $service_name health..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$health_url" > /dev/null 2>&1; then
            print_success "$service_name is healthy"
            return 0
        fi
        
        print_status "Attempt $attempt/$max_attempts: $service_name not ready yet..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "$service_name failed to become healthy after $max_attempts attempts"
    return 1
}

# Test MCP server health
if ! check_service "MCP server" "http://localhost:8001/health"; then
    print_error "MCP server health check failed"
    exit 1
fi

# Test backend health
if ! check_service "Backend API" "http://localhost:8000/health"; then
    print_error "Backend API health check failed"
    exit 1
fi

# Function to run tests with better error handling
run_tests() {
    local test_path="$1"
    local test_description="$2"
    
    print_status "Running $test_description..."
    
    if docker compose exec -T app poetry run pytest "$test_path" -v --tb=short; then
        print_success "$test_description passed"
        return 0
    else
        print_error "$test_description failed"
        return 1
    fi
}

# Run tool filtering specific tests
TEST_FAILURES=0

# Run unit tests
if ! run_tests "tests/unit/test_tool_filter.py" "unit tests for tool filtering"; then
    TEST_FAILURES=$((TEST_FAILURES + 1))
fi

# Run integration tests
if ! run_tests "tests/integration/mcp/test_agent_tool_filtering.py" "integration tests for tool filtering"; then
    TEST_FAILURES=$((TEST_FAILURES + 1))
fi

# Run E2E tests
if ! run_tests "tests/e2e/test_agent_tool_restrictions.py" "E2E tests for agent tool restrictions"; then
    TEST_FAILURES=$((TEST_FAILURES + 1))
fi

# Test with real agent data (if jq is available)
if command -v jq &> /dev/null; then
    print_status "Testing with real agent data..."
    
    # Use the specific agent ID from the PRP
    AGENT_ID="5c690a6f-4751-419f-bcb5-168b2ac76f7f"
    
    # Register user and get auth token
    print_status "Registering test user and getting auth token..."
    AUTH_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/register" \
      -H "Content-Type: application/json" \
      -d "{\"email\": \"test-$(date +%s)@example.com\", \"full_name\": \"Test User\", \"password\": \"TestPass123\", \"organization_name\": \"Test Org $(date +%s)\"}")
    
    if echo "$AUTH_RESPONSE" | jq -e '.access_token' > /dev/null 2>&1; then
        TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.access_token')
        print_success "Authentication successful"
        
        # Create conversation
        print_status "Creating test conversation..."
        CONV_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/chat/conversations" \
          -H "Authorization: Bearer $TOKEN" \
          -H "Content-Type: application/json" \
          -d '{"title": "Tool Filtering Test"}')
        
        if echo "$CONV_RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
            CONVERSATION_ID=$(echo "$CONV_RESPONSE" | jq -r '.id')
            print_success "Test conversation created: $CONVERSATION_ID"
            
            # Test allowed tool (should work)
            print_status "Testing allowed tool (system health check)..."
            ALLOWED_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/chat/conversations/$CONVERSATION_ID/messages" \
              -H "Authorization: Bearer $TOKEN" \
              -H "Content-Type: application/json" \
              -d "{\"content\": \"Please check the system health status\", \"agent_id\": \"$AGENT_ID\"}")
            
            if echo "$ALLOWED_RESPONSE" | jq -e '.content' > /dev/null 2>&1; then
                print_success "Allowed tool test completed"
                echo "Response preview: $(echo "$ALLOWED_RESPONSE" | jq -r '.content' | head -c 100)..."
            else
                print_warning "Allowed tool test may have failed: $ALLOWED_RESPONSE"
            fi
            
            # Test disallowed tool (should be blocked or handled gracefully)
            print_status "Testing disallowed tool (ticket creation)..."
            BLOCKED_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/chat/conversations/$CONVERSATION_ID/messages" \
              -H "Authorization: Bearer $TOKEN" \
              -H "Content-Type: application/json" \
              -d "{\"content\": \"Please create a ticket for me: System is slow\", \"agent_id\": \"$AGENT_ID\"}")
            
            if echo "$BLOCKED_RESPONSE" | jq -e '.content' > /dev/null 2>&1; then
                BLOCKED_CONTENT=$(echo "$BLOCKED_RESPONSE" | jq -r '.content' | tr '[:upper:]' '[:lower:]')
                
                if [[ "$BLOCKED_CONTENT" == *"cannot"* ]] || [[ "$BLOCKED_CONTENT" == *"not available"* ]] || [[ "$BLOCKED_CONTENT" == *"unable"* ]]; then
                    print_success "Disallowed tool correctly blocked/handled"
                else
                    print_warning "Agent response may not indicate proper tool restriction"
                fi
                echo "Response preview: $(echo "$BLOCKED_RESPONSE" | jq -r '.content' | head -c 100)..."
            else
                print_warning "Disallowed tool test may have failed: $BLOCKED_RESPONSE"
            fi
        else
            print_warning "Failed to create test conversation: $CONV_RESPONSE"
        fi
    else
        print_warning "Failed to authenticate test user: $AUTH_RESPONSE"
    fi
else
    print_warning "jq not available, skipping real agent data tests"
fi

# Check for errors in logs
print_status "Checking for critical errors in logs..."
ERROR_COUNT=0

# Check app logs
APP_ERRORS=$(docker compose logs app 2>&1 | grep -i "error" | grep -v "404" | grep -v "test" | tail -20)
if [ -n "$APP_ERRORS" ]; then
    ERROR_COUNT=$((ERROR_COUNT + 1))
    print_warning "Found errors in app logs:"
    echo "$APP_ERRORS"
fi

# Check MCP server logs  
MCP_ERRORS=$(docker compose logs mcp-server 2>&1 | grep -i "error" | tail -10)
if [ -n "$MCP_ERRORS" ]; then
    ERROR_COUNT=$((ERROR_COUNT + 1))
    print_warning "Found errors in MCP server logs:"
    echo "$MCP_ERRORS"
fi

# Final summary
echo ""
echo "=========================="
echo "    FINAL SUMMARY"
echo "=========================="

if [ $TEST_FAILURES -eq 0 ]; then
    print_success "All tests passed!"
else
    print_error "$TEST_FAILURES test suite(s) failed"
fi

if [ $ERROR_COUNT -eq 0 ]; then
    print_success "No critical errors found in logs"
else
    print_warning "$ERROR_COUNT service(s) have errors in logs (may be non-critical)"
fi

# Overall result
if [ $TEST_FAILURES -eq 0 ] && [ $ERROR_COUNT -eq 0 ]; then
    print_success "✨ Tool filtering implementation validation PASSED! ✨"
    exit 0
elif [ $TEST_FAILURES -eq 0 ]; then
    print_warning "⚠️  Tests passed but some errors found in logs"
    exit 0
else
    print_error "💥 Tool filtering implementation validation FAILED!"
    exit 1
fi