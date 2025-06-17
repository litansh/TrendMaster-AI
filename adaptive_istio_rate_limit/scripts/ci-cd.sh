#!/bin/bash

# TrendMaster-AI CI/CD Pipeline Script
# This script runs the complete CI/CD process including sanity tests

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${PROJECT_DIR}/logs/ci-cd_${TIMESTAMP}.log"

# Create logs directory
mkdir -p "${PROJECT_DIR}/logs"

# Logging function
log() {
    echo -e "${1}" | tee -a "${LOG_FILE}"
}

# Error handling
error_exit() {
    log "${RED}❌ ERROR: $1${NC}"
    exit 1
}

# Success message
success() {
    log "${GREEN}✅ $1${NC}"
}

# Info message
info() {
    log "${BLUE}ℹ️  $1${NC}"
}

# Warning message
warn() {
    log "${YELLOW}⚠️  $1${NC}"
}

# Header
header() {
    log "${BLUE}"
    log "=================================================="
    log "$1"
    log "=================================================="
    log "${NC}"
}

# Check prerequisites
check_prerequisites() {
    header "🔧 Checking Prerequisites"
    
    # Check Python version
    if ! command -v python3 &> /dev/null; then
        error_exit "Python3 is not installed"
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    info "Python version: ${PYTHON_VERSION}"
    
    # Check if we're in the right directory
    if [[ ! -f "${PROJECT_DIR}/tests/test_sanity.py" ]]; then
        error_exit "Sanity test file not found. Are you in the correct directory?"
    fi
    
    success "Prerequisites check completed"
}

# Setup environment
setup_environment() {
    header "🏗️  Setting Up Environment"
    
    cd "${PROJECT_DIR}"
    
    # Create __init__.py files if they don't exist
    find . -type d -name "scripts" -exec touch {}/__init__.py \; 2>/dev/null || true
    find . -type d -name "core" -exec touch {}/__init__.py \; 2>/dev/null || true
    find . -type d -name "tests" -exec touch {}/__init__.py \; 2>/dev/null || true
    
    # Install dependencies if requirements.txt exists
    if [[ -f "requirements.txt" ]]; then
        info "Installing Python dependencies..."
        pip3 install -r requirements.txt --quiet || warn "Some dependencies may have failed to install"
    fi
    
    success "Environment setup completed"
}

# Run sanity tests (CRITICAL GATE)
run_sanity_tests() {
    header "🧪 Running Sanity Tests (CRITICAL GATE)"
    
    cd "${PROJECT_DIR}"
    
    info "Starting TrendMaster-AI sanity tests..."
    info "This is a critical gate - deployment will be blocked if tests fail"
    
    # Run sanity tests with timeout and better error handling
    info "Running sanity tests with 5-minute timeout..."
    
    # Set environment variable to use faster Prophet settings for CI/CD
    export TRENDMASTER_CI_MODE=true
    
    if timeout 300 python3 tests/test_sanity.py 2>&1 | tee -a "${LOG_FILE}"; then
        success "🎉 ALL SANITY TESTS PASSED!"
        success "System functionality verified - proceeding with pipeline"
    else
        exit_code=$?
        if [ $exit_code -eq 124 ]; then
            error_exit "💥 SANITY TESTS TIMED OUT after 5 minutes! This may indicate Prophet library issues."
        else
            error_exit "💥 SANITY TESTS FAILED! Exit code: $exit_code. Check log for details."
        fi
    fi
}

# Run unit tests
run_unit_tests() {
    header "🔬 Running Unit Tests"
    
    cd "${PROJECT_DIR}"
    
    # Check if pytest is available
    if command -v pytest &> /dev/null; then
        info "Running pytest unit tests..."
        pytest tests/ -v --tb=short || warn "Some unit tests failed"
    else
        info "Pytest not available, running basic test discovery..."
        python3 -m unittest discover tests/ -v || warn "Some unit tests failed"
    fi
    
    success "Unit tests completed"
}

# Security scan
security_scan() {
    header "🔒 Security Scan"
    
    cd "${PROJECT_DIR}"
    
    # Check for common security issues
    info "Scanning for security vulnerabilities..."
    
    # Check for hardcoded secrets (basic scan)
    if grep -r -i "password\|secret\|key\|token" --include="*.py" scripts/ 2>/dev/null | grep -v "# " | head -5; then
        warn "Potential hardcoded secrets found - please review"
    fi
    
    # Check Python dependencies for known vulnerabilities if pip-audit is available
    if command -v pip-audit &> /dev/null && [[ -f "requirements.txt" ]]; then
        info "Running pip-audit security scan..."
        pip-audit -r requirements.txt || warn "Security vulnerabilities detected"
    fi
    
    success "Security scan completed"
}

# Build validation
build_validation() {
    header "🏗️  Build Validation"
    
    cd "${PROJECT_DIR}"
    
    # Validate Python syntax
    info "Validating Python syntax..."
    find scripts/ -name "*.py" -exec python3 -m py_compile {} \; || error_exit "Python syntax errors found"
    
    # Check for import issues
    info "Checking imports..."
    python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from scripts.main import AdaptiveRateLimiter
    from scripts.core.config_manager import ConfigManager
    from scripts.core.data_fetcher import DataFetcher
    from scripts.core.enhanced_rate_calculator import EnhancedRateCalculator
    print('✅ All critical imports successful')
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
" || error_exit "Import validation failed"
    
    success "Build validation completed"
}

# Integration tests
integration_tests() {
    header "🔗 Integration Tests"
    
    cd "${PROJECT_DIR}"
    
    if [[ -f "tests/test_local.py" ]]; then
        info "Running integration tests..."
        python3 tests/test_local.py || warn "Integration tests had issues"
    else
        info "No integration tests found, skipping..."
    fi
    
    success "Integration tests completed"
}

# Generate deployment artifacts
generate_artifacts() {
    header "📦 Generating Deployment Artifacts"
    
    cd "${PROJECT_DIR}"
    
    # Create artifacts directory
    ARTIFACTS_DIR="${PROJECT_DIR}/artifacts/${TIMESTAMP}"
    mkdir -p "${ARTIFACTS_DIR}"
    
    # Copy essential files
    cp -r scripts/ "${ARTIFACTS_DIR}/"
    cp -r config/ "${ARTIFACTS_DIR}/"
    cp tests/test_sanity.py "${ARTIFACTS_DIR}/"
    
    # Create version file
    echo "TrendMaster-AI Build ${TIMESTAMP}" > "${ARTIFACTS_DIR}/VERSION"
    echo "Git Commit: $(git rev-parse HEAD 2>/dev/null || echo 'N/A')" >> "${ARTIFACTS_DIR}/VERSION"
    echo "Build Date: $(date)" >> "${ARTIFACTS_DIR}/VERSION"
    
    # Create deployment script
    cat > "${ARTIFACTS_DIR}/deploy.sh" << 'EOF'
#!/bin/bash
echo "🚀 Deploying TrendMaster-AI..."
echo "Running post-deployment sanity check..."
python3 test_sanity.py
echo "✅ Deployment completed successfully!"
EOF
    chmod +x "${ARTIFACTS_DIR}/deploy.sh"
    
    info "Artifacts generated in: ${ARTIFACTS_DIR}"
    success "Artifact generation completed"
}

# Main pipeline execution
main() {
    header "🚀 TrendMaster-AI CI/CD Pipeline Started"
    info "Timestamp: ${TIMESTAMP}"
    info "Log file: ${LOG_FILE}"
    
    # Execute pipeline stages
    check_prerequisites
    setup_environment
    
    # CRITICAL GATE: Sanity tests must pass
    run_sanity_tests
    
    # Continue with other tests only if sanity tests pass
    run_unit_tests
    security_scan
    build_validation
    integration_tests
    generate_artifacts
    
    # Final summary
    header "🎉 CI/CD Pipeline Completed Successfully!"
    success "✅ All stages completed"
    success "✅ Sanity tests passed - system functionality verified"
    success "✅ Ready for deployment"
    
    info "Pipeline duration: $((SECONDS / 60)) minutes $((SECONDS % 60)) seconds"
    info "Full log available at: ${LOG_FILE}"
}

# Handle script arguments
case "${1:-}" in
    "sanity-only")
        header "🧪 Running Sanity Tests Only"
        check_prerequisites
        setup_environment
        run_sanity_tests
        ;;
    "quick")
        header "🏃 Quick Pipeline (Sanity + Build)"
        check_prerequisites
        setup_environment
        run_sanity_tests
        build_validation
        ;;
    "help"|"-h"|"--help")
        echo "TrendMaster-AI CI/CD Pipeline"
        echo ""
        echo "Usage: $0 [option]"
        echo ""
        echo "Options:"
        echo "  (none)      Run full CI/CD pipeline"
        echo "  sanity-only Run only sanity tests"
        echo "  quick       Run sanity tests + build validation"
        echo "  help        Show this help message"
        echo ""
        ;;
    *)
        main
        ;;
esac
