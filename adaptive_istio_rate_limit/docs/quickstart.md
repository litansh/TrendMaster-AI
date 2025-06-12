---
layout: default
title: Quick Start Guide
nav_order: 2
---

# Quick Start Guide

Get TrendMaster-AI up and running in minutes with this step-by-step guide.

## 🚀 1-Minute Setup

```bash
# Clone the repository
git clone https://github.com/your-org/TrendMaster-AI.git
cd TrendMaster-AI/adaptive_istio_rate_limit

# Install dependencies
pip install -r requirements.txt

# Run tests to verify installation
python tests/test_sanity.py

# Set environment and run
ENVIRONMENT=testing python scripts/main.py --show-env
```

## 📋 Prerequisites

Before you begin, ensure you have:

- **Python 3.11+** installed
- **pip** package manager
- **kubectl** configured (for Kubernetes integration)
- **Docker** (optional, for containerized deployment)

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **Python** | 3.11 | 3.11+ |
| **Memory** | 256Mi | 512Mi |
| **CPU** | 100m | 500m |
| **Disk** | 100MB | 500MB |

## 🔧 Installation

### Option 1: Standard Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-org/TrendMaster-AI.git
cd TrendMaster-AI/adaptive_istio_rate_limit

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify installation
python tests/test_sanity.py
```

### Option 2: Docker Installation

```bash
# Build Docker image
docker build -t trendmaster-ai:latest .

# Run with Docker
docker run -e ENVIRONMENT=testing \
           -v ~/.kube/config:/root/.kube/config:ro \
           trendmaster-ai:latest
```

## 🧪 Verify Installation

Run the comprehensive test suite to ensure everything is working:

```bash
# Basic sanity tests
python tests/test_sanity.py

# Comprehensive validation tests
ENVIRONMENT=testing python tests/test_rate_calculation_validation.py
```

Expected output:
```
🎉 ALL SANITY TESTS PASSED!
✅ Tests run: 5
✅ Failures: 0
✅ Errors: 0

🚀 System is ready for use!
```

## 🌍 Environment Configuration

TrendMaster-AI supports multiple environments:

### Local Development
```bash
# Use local environment with mock data
ENVIRONMENT=local python scripts/main.py --show-env
```

### Testing Environment
```bash
# Use testing environment with configured partners
ENVIRONMENT=testing python scripts/main.py --show-env
```

### Production Environment
```bash
# Use production environment (requires proper configuration)
ENVIRONMENT=production python scripts/main.py --validate-only
```

## 📊 First Run

### 1. Check Environment Configuration

```bash
ENVIRONMENT=testing python scripts/main.py --show-env
```

Expected output:
```
================================================================================
TrendMaster-AI Adaptive Istio Rate Limiting System v3.0
================================================================================
Environment: testing
Deployment Mode: testing
Trickster Environment: testing
Partners: 3 configured
APIs: 4 configured
Dry Run: True
================================================================================
```

### 2. Run Analysis

```bash
# Run with specific partners
ENVIRONMENT=testing python scripts/main.py --partners partner_313 --verbose

# Run with specific APIs
ENVIRONMENT=testing python scripts/main.py --apis /api/v3/service/configurations/action/servebydevice

# Run full analysis
ENVIRONMENT=testing python scripts/main.py
```

### 3. Check Generated Output

```bash
# View generated ConfigMaps
ls -la output/

# View analysis reports
ls -la output/*.md

# View logs
ls -la logs/
```

## 🎯 Common Use Cases

### Development and Testing

```bash
# Quick development test
ENVIRONMENT=local python scripts/main.py --show-env

# Integration testing
ENVIRONMENT=testing python scripts/main.py --validate-only

# Performance testing with verbose output
ENVIRONMENT=testing python scripts/main.py --verbose
```

### Configuration Validation

```bash
# Validate configuration only
python scripts/main.py --validate-only

# Check specific environment
ENVIRONMENT=production python scripts/main.py --validate-only

# Debug configuration issues
LOG_LEVEL=DEBUG python scripts/main.py --show-env
```

### Rate Limit Analysis

```bash
# Analyze specific partner
ENVIRONMENT=testing python scripts/main.py --partners partner_313

# Analyze specific API
ENVIRONMENT=testing python scripts/main.py --apis /api/v3/service/configurations/action/servebydevice

# Generate reports only
ENVIRONMENT=testing python scripts/main.py --output-format json
```

## 🔧 Configuration

### Basic Configuration

The system uses a layered configuration approach:

1. **Main Config**: `config/config.yaml` (tracked in git)
2. **Local Config**: `.local.config.yaml` (not tracked, for development)
3. **Environment Variables**: Override specific settings

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ENVIRONMENT` | Target environment | `testing` |
| `PROMETHEUS_URL` | Prometheus endpoint | `http://prometheus:9090` |
| `DRY_RUN` | Enable dry run mode | `true` |
| `USE_MOCK_DATA` | Use mock data | `true` |
| `LOG_LEVEL` | Logging level | `DEBUG` |

### Example Local Configuration

Create `.local.config.yaml` for local development:

```yaml
PARTNER_CONFIGS:
  local:
    partners: ['test_partner_1', 'test_partner_2']
    apis: [
      '/api/v1/content',
      '/api/v1/user/login'
    ]
    prometheus_url: "http://localhost:9090"
```

## 📈 Understanding Output

### ConfigMap Generation

The system generates Kubernetes ConfigMaps for Istio rate limiting:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ratelimit-config
  namespace: istio-system
data:
  config.yaml: |
    descriptors:
    - key: partner_id
      value: "313"
      rate_limit:
        requests_per_unit: 500
        unit: minute
```

### Analysis Reports

Detailed analysis reports are generated in Markdown format:

```markdown
# TrendMaster-AI Analysis Report

## Environment: testing
- Partners: 3 configured
- APIs: 4 configured
- Formula: v3 (2.5x average peaks)

## Results
- Partner 313: 500 req/min (confidence: 76.25%)
- Applied v3 formula with cache adjustment
```

## 🚨 Troubleshooting

### Common Issues

#### Issue: "No environment variable found"
```bash
# Problem: Environment not detected
# Solution: Set explicit environment variable
ENVIRONMENT=testing python scripts/main.py
```

#### Issue: "No partners configured"
```bash
# Problem: Missing partner configuration
# Solution: Check configuration file
grep -A 10 "testing:" config/config.yaml
```

#### Issue: "Failed to setup Kubernetes client"
```bash
# Problem: Kubernetes not configured
# Solution: Configure kubectl or use dry run mode
DRY_RUN=true python scripts/main.py
```

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
LOG_LEVEL=DEBUG ENVIRONMENT=testing python scripts/main.py --verbose
```

### Health Checks

Verify system health:

```bash
# Check configuration
python scripts/main.py --validate-only

# Check environment detection
python scripts/main.py --show-env

# Run sanity tests
python tests/test_sanity.py
```

## 🎉 Next Steps

Now that you have TrendMaster-AI running:

1. **Explore Configuration**: Review [Configuration Guide](./configuration.md)
2. **Run Tests**: Follow the [Testing Guide](./testing.md)
3. **Deploy to Production**: See [Deployment Guide](./deployment.md)
4. **Customize**: Check [API Reference](./api.md)

## 📞 Getting Help

If you encounter issues:

- **Documentation**: Browse the complete [documentation](./index.md)
- **GitHub Issues**: Report bugs or request features
- **Discussions**: Join the community discussions
- **Logs**: Check the `logs/` directory for detailed error information

---

**🚀 You're ready to start using TrendMaster-AI!**

Continue to the [Configuration Guide](./configuration.md) to learn about advanced configuration options.