# TrendMaster-AI Production Deployment Guide

This guide provides step-by-step instructions for deploying TrendMaster-AI to YOUR_COMPANY's production Kubernetes environments using ArgoCD and Helm.

## 📋 Overview

TrendMaster-AI has been fully integrated with YOUR_COMPANY's existing infrastructure:

- **ArgoCD GitOps** deployment following company patterns
- **Helm charts** with environment-specific configurations  
- **ECR integration** for container images
- **Istio rate limiting** integration with existing ConfigMaps
- **Multi-environment support** (local, orp2, prd1)

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   ArgoCD        │    │   Helm Chart     │    │  TrendMaster-AI │
│   Application   ├────┤   Templates      ├────┤   Container     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Environment     │    │   ConfigMaps     │    │  Istio Rate     │
│ Values Files    │    │   & Secrets      │    │  Limiting       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### 1. Build and Push Container Image

```bash
cd TrendMaster-AI/adaptive_istio_rate_limit
./k8s/production-integration/docker-build.sh v1.0.0
```

### 2. Copy Helm Chart to Company Repository

```bash
# Copy the Helm chart to your be-charts directory
cp -r k8s/helm-chart /path/to/ott-rnd-k8s/be-charts/trendmaster-ai
```

### 3. Update Environment Values Files

Add TrendMaster-AI configuration to your existing values files:

**For ORP2 (`values-orp2.yaml`):**
```yaml
trendmaster_ai:
  enabled: "true"
  prometheus_url: "https://trickster.orp2.ott.YOUR_COMPANY.com"
  dry_run: "false"
  log_level: "INFO"
  schedule: "0 */6 * * *"
```

**For PRD1 (`values-prd1.yaml`):**
```yaml
trendmaster_ai:
  enabled: "true"
  prometheus_url: "https://trickster.prd1.ott.YOUR_COMPANY.com"
  dry_run: "false"
  log_level: "INFO"
  schedule: "0 */4 * * *"
```

### 4. Deploy via ArgoCD

```bash
kubectl apply -f k8s/argocd-application.yaml
```

## 📁 File Structure

```
TrendMaster-AI/adaptive_istio_rate_limit/
├── k8s/
│   ├── helm-chart/                     # Helm chart for Kubernetes deployment
│   │   ├── Chart.yaml                  # Chart metadata
│   │   ├── values.yaml                 # Default values
│   │   └── templates/
│   │       ├── deployment.yaml         # Main application deployment
│   │       ├── cronjob.yaml           # Scheduled execution
│   │       ├── rbac.yaml              # Service account & permissions
│   │       └── configmap.yaml         # Application configuration
│   ├── argocd-application.yaml         # ArgoCD application template
│   └── production-integration/
│       ├── values-orp2-example.yaml    # ORP2 environment config
│       ├── values-prd1-example.yaml    # PRD1 environment config
│       ├── docker-build.sh            # Container build script
│       └── README.md                  # Integration guide
├── config/
│   └── config.yaml                    # Enhanced with K8s integration
├── Dockerfile                         # Production container image
└── DEPLOYMENT_GUIDE.md               # This file
```

## 🔧 Configuration Details

### Environment Detection

The system automatically detects the environment using:

1. **Environment Variables**: `KALTURA_ENV`, `ENVIRONMENT`, `DEPLOYMENT_ENV`
2. **Kubernetes Service Detection**: Trickster service names
3. **Helm Values**: Environment-specific configurations

### Kubernetes Integration

- **In-cluster Configuration**: Uses service account tokens
- **RBAC**: Minimal permissions for ConfigMap management
- **Namespace**: Deploys to `default`, manages `istio-system` ConfigMaps
- **Security**: Non-root container, read-only filesystem

### Rate Limit Integration

TrendMaster-AI integrates seamlessly with existing Istio rate limiting:

1. **Reads** current `ratelimit-config` ConfigMap
2. **Analyzes** traffic patterns from Prometheus/Trickster
3. **Calculates** optimal rates using Facebook Prophet ML
4. **Updates** ConfigMap with new rate limits
5. **Monitors** effectiveness and alerts on changes

## 🎯 Deployment Scenarios

### Scenario 1: New Environment Setup

```bash
# 1. Build and push image
./k8s/production-integration/docker-build.sh v1.0.0

# 2. Create Helm chart in be-charts
cp -r k8s/helm-chart /path/to/ott-rnd-k8s/be-charts/trendmaster-ai

# 3. Add configuration to values file
# (See examples in production-integration/)

# 4. Deploy via ArgoCD
kubectl apply -f k8s/argocd-application.yaml
```

### Scenario 2: Update Existing Deployment

```bash
# 1. Build new version
./k8s/production-integration/docker-build.sh v1.1.0

# 2. Update values file with new image tag
# 3. ArgoCD will automatically sync changes
```

### Scenario 3: Emergency Rollback

```bash
# 1. Disable TrendMaster-AI
# Set enabled: "false" in values file

# 2. Restore original ConfigMap
kubectl get configmap ratelimit-config -n istio-system -o yaml > backup.yaml
kubectl apply -f original-configmap.yaml

# 3. Force ArgoCD sync
argocd app sync trendmaster-ai
```

## 🔍 Monitoring and Troubleshooting

### Check Deployment Status

```bash
# Check pods
kubectl get pods -l app=trendmaster-ai

# Check logs
kubectl logs -l app=trendmaster-ai -f

# Check CronJob
kubectl get cronjobs
kubectl get jobs
```

### Verify Rate Limit Updates

```bash
# Check current rate limit configuration
kubectl get configmap ratelimit-config -n istio-system -o yaml

# Check TrendMaster-AI configuration
kubectl get configmap trendmaster-ai-config -o yaml
```

### Debug Issues

```bash
# Check RBAC permissions
kubectl auth can-i get configmaps --namespace=istio-system --as=system:serviceaccount:default:trendmaster-ai

# Manual job execution for testing
kubectl create job --from=cronjob/trendmaster-ai-cronjob manual-test-$(date +%s)

# Check ArgoCD application status
argocd app get trendmaster-ai
```

## 📊 Performance Tuning

### Resource Allocation

| Environment | Memory Request | Memory Limit | CPU Request | CPU Limit |
|-------------|----------------|--------------|-------------|-----------|
| Local       | 256Mi         | 512Mi        | 100m        | 250m      |
| ORP2        | 512Mi         | 1Gi          | 250m        | 500m      |
| PRD1        | 1Gi           | 2Gi          | 500m        | 1000m     |

### Schedule Frequency

| Environment | Schedule      | Frequency    | Rationale                    |
|-------------|---------------|--------------|------------------------------|
| Local       | Manual        | On-demand    | Development testing          |
| ORP2        | 0 */6 * * *   | Every 6h     | Staging validation           |
| PRD1        | 0 */4 * * *   | Every 4h     | Production optimization      |

## 🛡️ Security Considerations

### Container Security

- **Non-root user**: Runs as UID 1001
- **Read-only filesystem**: Except `/tmp` and `/var/tmp`
- **Minimal base image**: Python slim image
- **No shell access**: ENTRYPOINT only

### Kubernetes Security

- **Service Account**: Dedicated `trendmaster-ai` account
- **RBAC**: Minimal permissions (ConfigMaps in istio-system only)
- **Network Policies**: Restrict egress to Prometheus/Trickster
- **Secrets**: Use Kubernetes secrets for sensitive data

### Operational Security

- **Dry Run Mode**: Test changes before applying
- **Backup Strategy**: ConfigMap backups before updates
- **Audit Logging**: All changes logged and monitored
- **Rollback Plan**: Quick rollback procedures documented

## 🔄 CI/CD Integration

### GitOps Workflow

1. **Code Changes** → Push to repository
2. **Container Build** → Automated via CI/CD pipeline
3. **Image Push** → ECR registry
4. **Values Update** → Update image tag in values files
5. **ArgoCD Sync** → Automatic deployment
6. **Monitoring** → Verify deployment success

### Automation Scripts

```bash
# Full deployment pipeline
./scripts/deploy-pipeline.sh --env=orp2 --version=v1.0.0

# Rollback script
./scripts/rollback.sh --env=orp2 --version=v0.9.0

# Health check
./scripts/health-check.sh --env=orp2
```

## 📞 Support and Maintenance

### Regular Maintenance

- **Weekly**: Review rate limit effectiveness
- **Monthly**: Update ML models and thresholds
- **Quarterly**: Performance optimization review

### Emergency Contacts

- **Platform Team**: #platform-team Slack channel
- **On-call Engineer**: Escalation via PagerDuty
- **Documentation**: Internal wiki and runbooks

### Monitoring Dashboards

- **Grafana**: TrendMaster-AI performance metrics
- **ArgoCD UI**: Deployment status and history
- **Kubernetes Dashboard**: Resource utilization
- **Slack Alerts**: Real-time notifications

---

## 🎉 Conclusion

TrendMaster-AI is now fully integrated with YOUR_COMPANY's production infrastructure, following established patterns and best practices. The system provides intelligent, ML-driven rate limiting that adapts to traffic patterns while maintaining operational excellence.

For questions or support, reach out via the #platform-team Slack channel.