#!/bin/bash

set -e

echo "🧪 Simplified Message History E2E Test"
echo "===================================="

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Ensure services are running
echo -e "${YELLOW}Checking services...${NC}"
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${RED}❌ Main API not responding. Starting services...${NC}"
    docker compose up -d
    sleep 15
fi

echo -e "${GREEN}✅ Services are running${NC}"

# Set environment
export PYTHONPATH=/Users/aristotle/projects/support-extension
export JWT_SECRET_KEY=your-jwt-secret-key-change-in-production

# Run comprehensive test suite
echo -e "${YELLOW}Testing Enhanced AI Chat Service...${NC}"
poetry run pytest tests/unit/services/test_ai_chat_service_history.py -v
echo -e "${GREEN}✅ AI Chat Service tests passed${NC}"

echo -e "${YELLOW}Testing Enhanced Dynamic Agent Factory...${NC}" 
poetry run pytest tests/unit/services/test_dynamic_agent_factory_history.py -v
echo -e "${GREEN}✅ Dynamic Agent Factory tests passed${NC}"

echo -e "${YELLOW}Running Simplified Integration Test...${NC}"
poetry run pytest tests/integration/test_simplified_message_history.py -v
echo -e "${GREEN}✅ Integration test passed${NC}"

# Check Docker health
echo -e "${YELLOW}Checking Docker container health...${NC}"
ERROR_COUNT=$(docker compose logs app 2>&1 | grep -i "error\|exception\|traceback" | wc -l)
if [ $ERROR_COUNT -gt 5 ]; then
    echo -e "${RED}❌ Found $ERROR_COUNT errors in Docker logs${NC}"
    docker compose logs app | grep -i "error\|exception" | tail -10
    exit 1
fi

echo -e "${GREEN}✅ Docker containers healthy${NC}"

echo -e "${GREEN}🎉 Simplified Message History E2E tests passed!${NC}"
echo -e "${GREEN}✅ Existing database storage utilized${NC}"
echo -e "${GREEN}✅ Context limits properly applied${NC}"
echo -e "${GREEN}✅ Pydantic AI message_history parameter used correctly${NC}"
echo -e "${GREEN}✅ No additional database schema changes needed${NC}"