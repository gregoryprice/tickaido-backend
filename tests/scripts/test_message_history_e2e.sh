#!/bin/bash

set -e  # Exit on any error

echo "🧪 Message History E2E Test"
echo "=========================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if services are running
echo -e "${YELLOW}Checking services...${NC}"
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${RED}❌ Main API not responding. Starting services...${NC}"
    docker compose up -d
    sleep 10
fi

if ! curl -s http://localhost:8001/health > /dev/null; then
    echo -e "${RED}❌ MCP Server not responding${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Services are running${NC}"

# Run the test
export PYTHONPATH=/Users/aristotle/projects/support-extension
export JWT_SECRET_KEY=your-jwt-secret-key-change-in-production

echo -e "${YELLOW}Running comprehensive test suite...${NC}"

# 1. Test token counter service
echo -e "${YELLOW}Testing Token Counter Service...${NC}"
poetry run pytest tests/unit/services/test_token_counter_service.py -v
echo -e "${GREEN}✅ Token Counter tests passed${NC}"

# 2. Test message history service
echo -e "${YELLOW}Testing Message History Service...${NC}"
poetry run pytest tests/unit/services/test_message_history_service.py -v
echo -e "${GREEN}✅ Message History tests passed${NC}"

# 3. Test dynamic agent factory with history
echo -e "${YELLOW}Testing Dynamic Agent Factory with History...${NC}"
poetry run pytest tests/unit/services/test_dynamic_agent_factory_history.py -v
echo -e "${GREEN}✅ Dynamic Agent Factory tests passed${NC}"

# 4. Integration tests
echo -e "${YELLOW}Running Integration Tests...${NC}"
poetry run pytest tests/integration/services/test_message_history_integration_simple.py -v
echo -e "${GREEN}✅ Integration tests passed${NC}"

# 5. Check for Docker errors (excluding expected warnings)
echo -e "${YELLOW}Checking Docker logs for errors...${NC}"
CRITICAL_ERRORS=$(docker compose logs app 2>&1 | grep -i error | grep -v "bcrypt" | grep -v "Could not validate credentials" | grep -v "SSE message" | grep -v "CancelledError" | grep -v "JWT decode error" | grep -v "Signature has expired" | wc -l)
if [ $CRITICAL_ERRORS -gt 0 ]; then
    echo -e "${RED}❌ Found $CRITICAL_ERRORS critical errors in Docker logs${NC}"
    docker compose logs app | grep -i error | grep -v "bcrypt" | grep -v "Could not validate credentials" | tail -5
    exit 1
fi
echo -e "${GREEN}✅ No critical errors in Docker logs${NC}"

# 6. Test actual API endpoint (if available)
echo -e "${YELLOW}Testing API health...${NC}"
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
if echo "$HEALTH_RESPONSE" | grep -q '"status":"healthy"'; then
    echo -e "${GREEN}✅ API health check passed${NC}"
else
    echo -e "${RED}❌ API health check failed${NC}"
    echo "Response: $HEALTH_RESPONSE"
    exit 1
fi

echo -e "${GREEN}🎉 All Message History E2E tests passed!${NC}"
echo -e "${GREEN}✅ Token counting works correctly${NC}"
echo -e "${GREEN}✅ Message history retrieval works${NC}"
echo -e "${GREEN}✅ Context limits are respected${NC}"
echo -e "${GREEN}✅ Agent factory integrates properly${NC}"
echo -e "${GREEN}✅ No Docker errors detected${NC}"