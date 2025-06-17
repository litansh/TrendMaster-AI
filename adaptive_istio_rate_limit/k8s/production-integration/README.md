# TrendMaster-AI Production Integration Guide

This guide explains how to integrate TrendMaster-AI with YOUR_COMPANY's existing Kubernetes infrastructure using ArgoCD and Helm.

## 📋 Prerequisites

- Access to `ott-rnd-k8s` repository
- AWS CLI configured with ECR access
- Docker installed and running
- kubectl configured for target environments

## 🚀 Deployment Steps

### 1. Build and Push Docker Image

```bash
# Build and push to ECR
cd TrendMaster-AI/adaptive_istio_rate_limit
./k8s/production-integration/docker-build.sh v1.0.0
```

### 2. Update Environment Values Files

Add the TrendMaster-AI configuration to your existing values files in `ott-rnd-k8s/be-charts/`:

#### For ORP2 Environment (`values-orp2.yaml`):
```yaml
# Add this section to your existing values-orp2.yaml
trendmaster_ai:
  enabled: "true"
  prometheus_url: "https://trickster.orp2.ott.YOUR_COMPANY.com"
  dry_run: "false"
  log_level: "INFO"
  schedule: "0 */6 * * *"
  resources:
    requests:
      memory: "512Mi"
      cpu: "250m"
    limits:
      memory: "1Gi"
      cpu: "500m"
```

#### For PRD1 Environment (`values-prd1.yaml`):
```yaml
# Add this section to your existing values-prd1.yaml
trendmaster_ai:
  enabled: "true"
  prometheus_url: "https://trickster.prd1.ott.YOUR_COMPANY.com"
  dry_run: "false"
  log_level: "INFO"
  schedule: "0 */4 * * *"
  resources:
    requests:
      memory: "1Gi"
      cpu: "500m"
    limits:
      memory: "2Gi"
      cpu: "1000m"
```

### 3. Deploy Helm Chart

Copy the Helm chart to your charts directory:

```bash
# Copy Helm chart to be-charts
cp -r TrendMaster-AI/adaptive_istio_rate_limit/k8s/helm-chart ott-rnd-k8s/be-charts/trendmaster-ai
```

### 4. Create ArgoCD Application

Apply the ArgoCD application configuration:

```bash
# Update the application template with your specific values
kubectl apply -f TrendMaster-AI/adaptive_istio_rate_limit/k8s/argocd-application.yaml
```

## 🔧 Configuration Details

### Environment Variables

The system automatically configures itself based on Helm values:

- **PROMETHEUS_URL**: Trickster endpoint for metrics collection
- **DRY_RUN**: Set to "true" for testing, "false" for production
- **LOG_LEVEL**: INFO, DEBUG, WARNING, ERROR
- **KUBECONFIG**: Automatically mounted in cluster

### RBAC Permissions

The system requires these permissions:
- `configmaps` in `istio-system` namespace: get, list, watch, create, update, patch
- Service account with appropriate cluster role binding

### Rate Limit Integration

TrendMaster-AI integrates with existing Istio rate limiting by:

1. **Reading current configuration** from `ratelimit-config` ConfigMap
2. **Analyzing traffic patterns** using Prometheus metrics
3. **Calculating optimal rates** using Facebook Prophet ML
4. **Updating ConfigMap** with new rate limits
5. **Monitoring and alerting** on changes

## 📊 Monitoring and Alerting

### Metrics Collection

The system collects metrics on:
- Rate limit effectiveness
- ML model accuracy
- Configuration changes
- System performance

### Slack Integration

Configure Slack notifications in your values files:

```yaml
monitoring:
  trendmaster_ai:
    enabled: "true"
    alerts:
      rate_limit_changes: "true"
      ml_confidence_low: "true"
      system_errors: "true"
    slack_channels:
      - "#alerts"
      - "#platform-team"
```

## 🧪 Testing

### Dry Run Mode

Test the system without making changes:

```yaml
trendmaster_ai:
  dry_run: "true"
```

### Manual Execution

Run the system manually for testing:

```bash
kubectl create job --from=cronjob/trendmaster-ai-cronjob manual-test-$(date +%s)
```

## 🔍 Troubleshooting

### Check Logs

```bash
# View deployment logs
kubectl logs -l app=trendmaster-ai -n default

# View CronJob logs
kubectl logs -l job-name=trendmaster-ai-cronjob -n default
```

### Verify Permissions

```bash
# Test ConfigMap access
kubectl auth can-i get configmaps --namespace=istio-system --as=system:serviceaccount:default:trendmaster-ai
```

### Check Rate Limit Config

```bash
# View current rate limit configuration
kubectl get configmap ratelimit-config -n istio-system -o yaml
```

## 🔄 Rollback

To rollback changes:

1. **Disable TrendMaster-AI**: Set `enabled: "false"` in values files
2. **Restore original ConfigMap**: From backup or previous version
3. **Sync ArgoCD**: Force sync to apply changes

## 📈 Performance Tuning

### Resource Allocation

Adjust resources based on environment:

- **Development**: 256Mi memory, 100m CPU
- **Staging**: 512Mi memory, 250m CPU  
- **Production**: 1-2Gi memory, 500m-1000m CPU

### Schedule Frequency

- **Development**: Every 12 hours
- **Staging**: Every 6 hours
- **Production**: Every 4 hours

## 🛡️ Security Considerations

- **Non-root container**: Runs as user 1001
- **Read-only filesystem**: Except for temporary directories
- **Minimal permissions**: Only required RBAC permissions
- **Secrets management**: Use Kubernetes secrets for sensitive data

## 📞 Support

For issues or questions:
1. Check logs and troubleshooting section
2. Review ArgoCD application status
3. Contact platform team via #platform-team Slack channel