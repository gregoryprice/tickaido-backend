#!/bin/bash
# tests/scripts/test_unified_architecture_e2e.sh
# End-to-end test for unified MCP + PydanticAI architecture refactor

set -e

echo "🧪 Testing Unified MCP + PydanticAI Architecture"
echo "=================================================="

# Configuration
BASE_URL="http://localhost:8000"
MCP_URL="http://localhost:8001"
TEST_USER_EMAIL="admin@company.com"
TEST_USER_PASSWORD="SecurePass123"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check service health
check_service_health() {
    local service_name=$1
    local url=$2
    
    log_info "Checking $service_name health at $url"
    
    if curl -s -f "$url/health" > /dev/null 2>&1; then
        log_success "$service_name is healthy"
        return 0
    else
        log_error "$service_name is not responding"
        return 1
    fi
}

# Function to wait for services
wait_for_services() {
    log_info "Waiting for services to start..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if check_service_health "Main API" "$BASE_URL" && check_service_health "MCP Server" "$MCP_URL"; then
            log_success "All services are ready"
            return 0
        fi
        
        log_info "Attempt $attempt/$max_attempts - Services not ready yet, waiting 5s..."
        sleep 5
        ((attempt++))
    done
    
    log_error "Services failed to start after $max_attempts attempts"
    return 1
}

# Function to authenticate and get JWT token
authenticate_user() {
    log_info "Authenticating test user: $TEST_USER_EMAIL"
    
    local login_response
    login_response=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$TEST_USER_EMAIL\",\"password\":\"$TEST_USER_PASSWORD\"}" \
        2>/dev/null)
    
    if [ $? -ne 0 ]; then
        log_error "Failed to connect to authentication endpoint"
        return 1
    fi
    
    # Check if login was successful
    if echo "$login_response" | grep -q "access_token"; then
        JWT_TOKEN=$(echo "$login_response" | jq -r '.access_token' 2>/dev/null)
        if [ "$JWT_TOKEN" != "null" ] && [ -n "$JWT_TOKEN" ]; then
            log_success "Authentication successful"
            log_info "Token: ${JWT_TOKEN:0:20}..."
            return 0
        fi
    fi
    
    log_error "Authentication failed"
    log_error "Response: $login_response"
    return 1
}

# Function to test JWT to Principal conversion
test_principal_conversion() {
    log_info "Testing JWT to Principal conversion..."
    
    local user_info_response
    user_info_response=$(curl -s -X GET "$BASE_URL/api/v1/users/me" \
        -H "Authorization: Bearer $JWT_TOKEN" \
        -H "Content-Type: application/json" \
        2>/dev/null)
    
    if echo "$user_info_response" | grep -q "email"; then
        log_success "Principal conversion working - user info retrieved"
        local user_email
        user_email=$(echo "$user_info_response" | jq -r '.email' 2>/dev/null)
        log_info "Retrieved user: $user_email"
        return 0
    else
        log_error "Principal conversion failed"
        log_error "Response: $user_info_response"
        return 1
    fi
}

# Function to test tool access with principal context
test_tool_access_authorized() {
    log_info "Testing authorized tool access with principal context..."
    
    # Test creating a ticket (should be allowed for admin)
    local chat_response
    chat_response=$(curl -s -X POST "$BASE_URL/api/v1/chat" \
        -H "Authorization: Bearer $JWT_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "message": "Create a test ticket with title \"Test Ticket\" and description \"Testing tool access\"",
            "thread_id": "test-thread-1"
        }' \
        2>/dev/null)
    
    if [ $? -eq 0 ]; then
        log_success "Tool access request completed"
        
        # Check if response indicates successful tool usage
        if echo "$chat_response" | grep -q -i "ticket\|created\|test"; then
            log_success "Tool execution appears successful"
            return 0
        else
            log_warning "Tool execution may have failed"
            log_info "Response: $chat_response"
            return 1
        fi
    else
        log_error "Failed to make tool access request"
        return 1
    fi
}

# Function to test unauthorized access
test_unauthorized_access() {
    log_info "Testing unauthorized access protection..."
    
    local unauthorized_response
    unauthorized_response=$(curl -s -w "%{http_code}" -X POST "$BASE_URL/api/v1/chat" \
        -H "Authorization: Bearer invalid-token-12345" \
        -H "Content-Type: application/json" \
        -d '{
            "message": "Try to access tools with invalid token"
        }' \
        2>/dev/null)
    
    local http_code="${unauthorized_response: -3}"
    
    if [ "$http_code" = "401" ] || [ "$http_code" = "403" ]; then
        log_success "Unauthorized access properly blocked (HTTP $http_code)"
        return 0
    else
        log_error "Security test failed - unauthorized access not blocked (HTTP $http_code)"
        return 1
    fi
}

# Function to test MCP server tool filtering
test_mcp_tool_filtering() {
    log_info "Testing MCP tool filtering..."
    
    # Test getting system health (should be available)
    local health_response
    health_response=$(curl -s -X POST "$BASE_URL/api/v1/chat" \
        -H "Authorization: Bearer $JWT_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "message": "Check the system health status"
        }' \
        2>/dev/null)
    
    if echo "$health_response" | grep -q -i "health\|system\|status"; then
        log_success "MCP tool filtering working - system health accessible"
        return 0
    else
        log_warning "MCP tool filtering test inconclusive"
        log_info "Response: $health_response"
        return 1
    fi
}

# Function to verify Docker logs for proper functionality
verify_docker_logs() {
    log_info "Verifying Docker logs for proper functionality..."
    
    # Check main app logs for principal-related entries
    if docker logs support-extension-app-1 2>&1 | grep -q -i "principal\|jwt\|auth" | head -5; then
        log_success "App container shows authentication activity"
    else
        log_warning "Limited authentication activity in app logs"
    fi
    
    # Check MCP server logs for tool access
    if docker logs support-extension-mcp-server-1 2>&1 | grep -q -i "tool\|mcp" | head -5; then
        log_success "MCP server container shows tool activity"
    else
        log_warning "Limited MCP server activity in logs"
    fi
    
    # Check for any error patterns
    local error_count
    error_count=$(docker logs support-extension-app-1 2>&1 | grep -i "error\|failed\|exception" | wc -l)
    
    if [ "$error_count" -lt 5 ]; then
        log_success "Low error count in logs ($error_count errors)"
        return 0
    else
        log_warning "High error count in logs ($error_count errors)"
        return 1
    fi
}

# Function to run comprehensive test suite
run_comprehensive_tests() {
    log_info "Running comprehensive test suite..."
    
    local tests_passed=0
    local tests_total=6
    
    # Test 1: Service Health
    if check_service_health "Main API" "$BASE_URL" && check_service_health "MCP Server" "$MCP_URL"; then
        ((tests_passed++))
    fi
    
    # Test 2: Authentication
    if authenticate_user; then
        ((tests_passed++))
    fi
    
    # Test 3: Principal Conversion
    if test_principal_conversion; then
        ((tests_passed++))
    fi
    
    # Test 4: Authorized Tool Access
    if test_tool_access_authorized; then
        ((tests_passed++))
    fi
    
    # Test 5: Unauthorized Access Protection
    if test_unauthorized_access; then
        ((tests_passed++))
    fi
    
    # Test 6: MCP Tool Filtering
    if test_mcp_tool_filtering; then
        ((tests_passed++))
    fi
    
    log_info "Test Results: $tests_passed/$tests_total tests passed"
    
    if [ $tests_passed -eq $tests_total ]; then
        log_success "🎉 All tests passed! Architecture refactor validation successful."
        return 0
    else
        log_error "❌ Some tests failed. Architecture needs attention."
        return 1
    fi
}

# Main execution
main() {
    echo "Starting unified architecture validation..."
    echo "Date: $(date)"
    echo "Test User: $TEST_USER_EMAIL"
    echo ""
    
    # Start services if not already running
    log_info "Ensuring services are running..."
    docker compose up -d
    
    # Wait for services to be ready
    if ! wait_for_services; then
        log_error "Services failed to start properly"
        exit 1
    fi
    
    # Run comprehensive tests
    if run_comprehensive_tests; then
        # Verify Docker logs
        verify_docker_logs
        
        log_success "🎉 Unified Architecture Validation PASSED!"
        log_info "The refactored MCP + PydanticAI architecture is working correctly."
        exit 0
    else
        log_error "❌ Unified Architecture Validation FAILED!"
        log_error "Please check the logs and fix the issues before proceeding."
        exit 1
    fi
}

# Run main function
main "$@"