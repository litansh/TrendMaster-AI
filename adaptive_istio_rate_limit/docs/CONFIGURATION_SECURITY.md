# TrendMaster-AI Configuration Security Guide

## 🔒 Security-First Configuration Architecture

The TrendMaster-AI system implements a **security-first configuration approach** that completely separates sensitive data from tracked code, ensuring no partner IDs, API paths, URLs, or other sensitive information is ever committed to version control.

## 📁 Configuration File Structure

```
TrendMaster-AI/adaptive_istio_rate_limit/
├── config/
│   └── config.yaml              # ✅ Sanitized config (tracked in git)
├── .local.config.yaml           # 🔒 Sensitive config (NOT tracked in git)
├── .gitignore                   # 🛡️ Excludes sensitive files
└── k8s/
    └── deployment.yaml          # 🚀 Environment variable injection
```

## 🛡️ Security Layers

### Layer 1: Sanitized Main Configuration
**File**: `config/config.yaml`
- ✅ **Tracked in Git**: Safe to commit and share
- ✅ **No Sensitive Data**: Contains only structure and placeholders
- ✅ **Environment Variables**: Uses `${VARIABLE}` placeholders

```yaml
# config/config.yaml - Safe for git
PARTNER_CONFIGS:
  staging:
    partners: []  # Loaded from .local.config.yaml or ConfigMap
    apis: []      # Loaded from .local.config.yaml or ConfigMap

DEPLOYMENT_OVERRIDES:
  local:
    prometheus_url: "${PROMETHEUS_URL}"  # Injected from environment
```

### Layer 2: Hidden Local Configuration
**File**: `.local.config.yaml`
- 🔒 **NOT Tracked in Git**: Excluded via `.gitignore`
- 🔒 **Contains Sensitive Data**: Partner IDs, API paths, URLs
- 🔒 **Local Development Only**: Used for local development environment

```yaml
# .local.config.yaml - NOT tracked in git
PARTNER_CONFIGS:
  local:
    partners: ["000", "111", "222", "333"]  # Actual partner IDs
    apis:
      - "/some/example/api"        # Actual API paths
      - "/some/example/api"
      # ... more sensitive API paths
```

### Layer 3: Environment Variable Injection
**Source**: Kubernetes/EKS environment variables
- 🚀 **Production/Testing**: All sensitive data injected from EKS
- 🚀 **No Hardcoded Values**: Everything comes from environment variables
- 🚀 **Environment-Specific**: Different values per environment

## 🌍 Environment-Specific Data Sources

| Environment | Partner/API Source | URL Source | Purpose |
|-------------|-------------------|------------|---------|
| **Local** | `.local.config.yaml` | Environment Variables | Development |
| **Testing** | Kubernetes ConfigMap | EKS Environment Variables | Integration Tests |
| **Production** | Kubernetes ConfigMap | EKS Environment Variables | Live Production |

## 🔧 Implementation Details

### ConfigManager Security Features

The `ConfigManager` class implements multiple security layers:

```python
class ConfigManager:
    def __init__(self):
        # Load sanitized main config
        self._load_config()          # config/config.yaml
        
        # Load sensitive local config (if exists)
        self._load_local_config()    # .local.config.yaml
        
        # Apply environment variable overrides
        self._apply_env_var_overrides()

    def _get_local_partner_config(self):
        """Load from .local.config.yaml for local development"""
        if self.local_config and 'PARTNER_CONFIGS' in self.local_config:
            return self.local_config['PARTNER_CONFIGS']['local']
        return {}

    def _get_configmap_partner_config(self):
        """Load from Kubernetes ConfigMap for production/testing"""
        # Discovers partners/APIs from existing Istio ConfigMaps
        return self._discover_from_configmap()
```

### Environment Variable Priority

The system checks environment variables in this order:

1. `PROMETHEUS_URL` - Direct URL override
2. `ENVIRONMENT` - Environment detection
3. `DEPLOYMENT_MODE` - Deployment mode override
4. `KUBERNETES_CONTEXT` - K8s context
5. `LOG_LEVEL` - Logging configuration

## 🚀 Deployment Security

### Kubernetes Deployment Template

All sensitive data is injected via environment variables:

```yaml
# k8s/deployment.yaml
env:
# Environment Detection (Injected from EKS)
- name: ENVIRONMENT
  value: "${ENVIRONMENT}"  # production/testing/local

# Prometheus Configuration (Injected from EKS)
- name: PROMETHEUS_URL
  value: "${PROMETHEUS_URL}"  # Environment-specific URL

# Kubernetes Configuration (Injected from EKS)
- name: KUBERNETES_CONTEXT
  value: "${KUBERNETES_CONTEXT}"
```

### Secret Management

Sensitive tokens are managed via Kubernetes Secrets:

```bash
# Create secret separately (not in deployment YAML)
kubectl create secret generic prometheus-credentials \
  --from-literal=token=${PROMETHEUS_TOKEN} \
  --namespace=istio-system
```

## 📝 Developer Workflow

### 1. Local Development Setup

```bash
# 1. Clone repository (no sensitive data in git)
git clone https://github.com/your-org/TrendMaster-AI.git
cd TrendMaster-AI/adaptive_istio_rate_limit

# 2. Create local configuration with sensitive data
cp .local.config.yaml.template .local.config.yaml
vim .local.config.yaml  # Add actual partner IDs and API paths

# 3. Set environment variables
export PROMETHEUS_URL="https://your-actual-trickster-url.com"
export ENVIRONMENT=local

# 4. Run with injected configuration
python scripts/main.py --show-env
```

### 2. Testing Environment

```bash
# All sensitive data comes from EKS environment variables
export ENVIRONMENT=testing
export PROMETHEUS_URL="${TESTING_PROMETHEUS_URL}"  # From EKS
export KUBERNETES_CONTEXT="${TESTING_K8S_CONTEXT}"  # From EKS

# Partners/APIs discovered from existing ConfigMaps
python scripts/main.py --validate-only
```

### 3. Production Environment

```bash
# Complete environment variable injection from EKS
export ENVIRONMENT=production
export PROMETHEUS_URL="${PROD_PROMETHEUS_URL}"      # From EKS
export KUBERNETES_CONTEXT="${PROD_K8S_CONTEXT}"    # From EKS
export PROMETHEUS_TOKEN="${PROD_PROMETHEUS_TOKEN}"  # From EKS Secret

# All configuration injected from EKS cluster
kubectl apply -f k8s/deployment.yaml
```

## ✅ Security Validation

### What's Protected

- ✅ **Partner IDs**: Never in git, only in `.local.config.yaml` or EKS
- ✅ **API Paths**: Never in git, only in `.local.config.yaml` or EKS
- ✅ **URLs**: Never hardcoded, always from environment variables
- ✅ **Tokens**: Only in Kubernetes Secrets, never in code
- ✅ **Environment Names**: Generic placeholders in git

### What's Safe to Commit

- ✅ **config/config.yaml**: Sanitized structure only
- ✅ **k8s/deployment.yaml**: Environment variable placeholders only
- ✅ **Source Code**: No hardcoded sensitive values
- ✅ **Documentation**: Generic examples only

### Git Protection

```bash
# .gitignore automatically excludes:
.local.config.yaml          # Local sensitive configuration
*.key                       # Private keys
*.pem                       # Certificates
secrets/                    # Secret directories
credentials/                # Credential files
```

## 🔍 Security Audit Checklist

- [ ] No partner IDs in tracked files
- [ ] No API paths in tracked files  
- [ ] No URLs containing company names in tracked files
- [ ] All sensitive data in `.local.config.yaml` (not tracked)
- [ ] Environment variables used for all runtime configuration
- [ ] Kubernetes Secrets used for tokens
- [ ] `.gitignore` properly excludes sensitive files

## 🆘 Security Incident Response

If sensitive data is accidentally committed:

```bash
# 1. Immediately remove from git history
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch path/to/sensitive/file' \
  --prune-empty --tag-name-filter cat -- --all

# 2. Force push to remove from remote
git push origin --force --all

# 3. Rotate any exposed credentials
# 4. Update .gitignore to prevent future incidents
# 5. Notify security team
```

## 📞 Support

For security-related questions or incidents:
- **Security Team**: security@company.com
- **DevOps Team**: devops@company.com
- **Documentation**: [Security Wiki](https://wiki.company.com/security)

---

**🔒 Security First - No Sensitive Data in Git - Environment Variable Injection Only**