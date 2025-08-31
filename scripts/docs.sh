#!/bin/bash

# AI Ticket Creator Backend - Documentation Management Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "openapi.yaml" ]; then
    print_error "openapi.yaml not found. Please run this script from the project root."
    exit 1
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for required tools
check_dependencies() {
    print_status "Checking dependencies..."
    
    if ! command_exists npx; then
        print_error "npx not found. Please install Node.js and npm."
        exit 1
    fi
    
    if ! command_exists docker; then
        print_warning "Docker not found. Some features may not work."
    fi
    
    print_success "Dependencies check completed"
}

# Validate OpenAPI specification
validate_openapi() {
    print_status "Validating OpenAPI specification..."
    
    if npx @redocly/cli lint openapi.yaml --config redocly.yaml; then
        print_success "OpenAPI specification is valid"
        return 0
    else
        print_error "OpenAPI specification has validation errors"
        return 1
    fi
}

# Generate static documentation
generate_docs() {
    print_status "Generating static documentation..."
    
    mkdir -p docs/generated
    
    # Generate ReDoc documentation
    if npx @redocly/cli build-docs openapi.yaml --output docs/generated/index.html --config redocly.yaml; then
        print_success "Static documentation generated at docs/generated/index.html"
    else
        print_error "Failed to generate static documentation"
        return 1
    fi
    
    # Generate OpenAPI spec in JSON format
    if npx @redocly/cli bundle openapi.yaml --output docs/generated/openapi.json --config redocly.yaml; then
        print_success "OpenAPI JSON generated at docs/generated/openapi.json"
    else
        print_error "Failed to generate OpenAPI JSON"
        return 1
    fi
}

# Preview documentation locally
preview_docs() {
    print_status "Starting documentation preview server..."
    print_status "Documentation will be available at http://localhost:8080"
    print_status "Press Ctrl+C to stop the server"
    
    npx @redocly/cli preview-docs openapi.yaml --config redocly.yaml
}

# Start the API server for testing
start_api_server() {
    print_status "Starting AI Ticket Creator API server..."
    
    if [ -f "compose.yml" ]; then
        print_status "Using Docker Compose..."
        docker compose up -d
        
        print_status "Waiting for services to start..."
        sleep 10
        
        print_status "API server should be available at:"
        print_status "- Main API: http://localhost:8000"
        print_status "- Swagger UI: http://localhost:8000/docs"
        print_status "- ReDoc: http://localhost:8000/redoc"
        print_status "- Health Check: http://localhost:8000/health"
    else
        print_warning "compose.yml not found. Please start the API server manually."
    fi
}

# Stop the API server
stop_api_server() {
    print_status "Stopping AI Ticket Creator API server..."
    
    if [ -f "compose.yml" ]; then
        docker compose down
        print_success "API server stopped"
    else
        print_warning "compose.yml not found. Please stop the API server manually."
    fi
}

# Generate code samples
generate_code_samples() {
    print_status "Generating code samples..."
    
    mkdir -p docs/generated/samples
    
    # This would require additional tools/scripts
    print_warning "Code sample generation not yet implemented"
    print_status "You can use the interactive docs at /docs to generate code samples"
}

# Test API endpoints
test_api() {
    print_status "Testing API endpoints..."
    
    local base_url="http://localhost:8000"
    
    # Test health endpoint
    print_status "Testing health endpoint..."
    if curl -f -s "${base_url}/health" > /dev/null; then
        print_success "Health endpoint is responding"
    else
        print_error "Health endpoint is not responding"
        return 1
    fi
    
    # Test OpenAPI spec endpoint
    print_status "Testing OpenAPI spec endpoint..."
    if curl -f -s "${base_url}/openapi.json" > /dev/null; then
        print_success "OpenAPI spec endpoint is responding"
    else
        print_error "OpenAPI spec endpoint is not responding"
        return 1
    fi
    
    # Test documentation endpoints
    print_status "Testing documentation endpoints..."
    if curl -f -s "${base_url}/docs" > /dev/null; then
        print_success "Swagger UI endpoint is responding"
    else
        print_error "Swagger UI endpoint is not responding"
    fi
    
    if curl -f -s "${base_url}/redoc" > /dev/null; then
        print_success "ReDoc endpoint is responding"
    else
        print_error "ReDoc endpoint is not responding"
    fi
}

# Clean generated files
clean() {
    print_status "Cleaning generated documentation files..."
    
    if [ -d "docs/generated" ]; then
        rm -rf docs/generated
        print_success "Cleaned generated files"
    else
        print_status "No generated files to clean"
    fi
}

# Show help
show_help() {
    echo "AI Ticket Creator Backend - Documentation Management"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  validate      Validate OpenAPI specification"
    echo "  generate      Generate static documentation"
    echo "  preview       Preview documentation locally"
    echo "  start         Start API server for testing"
    echo "  stop          Stop API server"
    echo "  test          Test API endpoints"
    echo "  samples       Generate code samples"
    echo "  clean         Clean generated files"
    echo "  all           Run validate, generate, and test"
    echo "  help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 validate                 # Validate OpenAPI spec"
    echo "  $0 generate                 # Generate static docs"
    echo "  $0 preview                  # Start preview server"
    echo "  $0 start && $0 test         # Start server and test"
    echo "  $0 all                      # Complete workflow"
    echo ""
}

# Main script logic
main() {
    case "${1:-help}" in
        "validate")
            check_dependencies
            validate_openapi
            ;;
        "generate")
            check_dependencies
            validate_openapi && generate_docs
            ;;
        "preview")
            check_dependencies
            preview_docs
            ;;
        "start")
            start_api_server
            ;;
        "stop")
            stop_api_server
            ;;
        "test")
            test_api
            ;;
        "samples")
            generate_code_samples
            ;;
        "clean")
            clean
            ;;
        "all")
            check_dependencies
            validate_openapi
            generate_docs
            start_api_server
            sleep 5
            test_api
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# Run main function with all arguments
main "$@"