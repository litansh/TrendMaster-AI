# Deployment Guide - Adaptive Istio Rate Limiting System

## 🚀 Quick Start

### Local Development
```bash
# Test the system
python3 test_local.py

# Run locally
python3 scripts/main.py
```

### CI/CD Deployment
```bash
# Deploy as a one-time job
./ci-cd.sh

# Deploy as a continuous service
DEPLOYMENT_MODE=deployment ./ci-cd.sh
```

## 📋 CI/CD Pipeline Overview

The updated `ci-cd.sh` script now supports the new Adaptive Rate Limiting System with the following features:

### Pipeline Steps

1. **🧪 Automated Testing**
   - Runs `test_local.py` to validate system components
   - Fails deployment if tests don't pass

2. **🐳 Docker Build & Push**
   - Builds `litanshamir/adaptive-rate-limiter:latest`
   - Pushes to Docker registry

3. **⚙️ Prerequisites Deployment**
   - Applies RBAC configuration (`infra/rbac.yaml`)
   - Applies ConfigMap (`config/istio_ratelimit_configmap.yaml`)

4. **🚀 Application Deployment**
   - **Job Mode**: One-time execution with completion tracking
   - **Deployment Mode**: Continuous running service

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEPLOYMENT_MODE` | `job` | `job` or `deployment` |
| `DOCKER_IMAGE` | `litanshamir/adaptive-rate-limiter:latest` | Docker image to deploy |
| `K8S_NAMESPACE` | `istio-system` | Kubernetes namespace |

## 🛠️ Deployment Options

### Option 1: One-Time Job (Recommended for Rate Limit Updates)

```bash
# Default mode - runs once and completes
./ci-cd.sh
```

**Use Case**: Regular rate limit updates, scheduled maintenance

**Features**:
- Runs to completion
- Automatic cleanup
- Job history tracking
- Timeout protection (30 minutes)

### Option 2: Continuous Deployment (For Monitoring/Operator Mode)

```bash
# Runs as a continuous service
DEPLOYMENT_MODE=deployment ./ci-cd.sh
```

**Use Case**: Continuous monitoring, operator-style deployment

**Features**:
- Always running
- Automatic restarts
- Rolling updates
- Health checks

### Option 3: Scheduled CronJob

```bash
# Deploy the CronJob for automatic execution
kubectl apply -f infra/istio_ratelimit_values_cron.yaml
```

**Use Case**: Automated rate limit updates every 6 hours

**Features**:
- Runs every 6 hours
- Automatic scheduling
- Job history management
- Failure retry logic

## 📁 Updated Infrastructure Files

### Core Deployment Files

| File | Purpose | Type |
|------|---------|------|
| `infra/rbac.yaml` | ServiceAccount & RBAC permissions | Prerequisites |
| `config/istio_ratelimit_configmap.yaml` | System configuration | Prerequisites |
| `infra/adaptive_rate_limiter_job.yaml` | One-time job execution | Job Mode |
| `infra/istio_ratelimit_values_deployment.yaml` | Continuous service | Deployment Mode |
| `infra/istio_ratelimit_values_cron.yaml` | Scheduled execution | CronJob Mode |

### Configuration Updates

All infrastructure files have been updated with:
- ✅ New Docker image: `litanshamir/adaptive-rate-limiter:latest`
- ✅ Updated command: `python3 scripts/main.py`
- ✅ Proper RBAC permissions for ConfigMap management
- ✅ Resource limits and requests
- ✅ Timeout and retry configurations
- ✅ ServiceAccount integration

## 🔧 Manual Deployment Steps

If you prefer manual deployment over the CI/CD script:

### Step 1: Build and Push Image
```bash
docker build -t litanshamir/adaptive-rate-limiter:latest .
docker push litanshamir/adaptive-rate-limiter:latest
```

### Step 2: Deploy Prerequisites
```bash
kubectl apply -f infra/rbac.yaml
kubectl apply -f config/istio_ratelimit_configmap.yaml
```

### Step 3: Choose Deployment Method

**For One-Time Execution:**
```bash
kubectl apply -f infra/adaptive_rate_limiter_job.yaml
kubectl logs -f job/adaptive-rate-limiter-job -n istio-system
```

**For Continuous Service:**
```bash
kubectl apply -f infra/istio_ratelimit_values_deployment.yaml
kubectl rollout status deployment/adaptive-rate-limiter -n istio-system
```

**For Scheduled Execution:**
```bash
kubectl apply -f infra/istio_ratelimit_values_cron.yaml
kubectl get cronjobs -n istio-system
```

## 🔍 Monitoring & Troubleshooting

### Check Deployment Status

```bash
# For Jobs
kubectl get jobs -n istio-system
kubectl describe job adaptive-rate-limiter-job -n istio-system

# For Deployments  
kubectl get deployments -n istio-system
kubectl describe deployment adaptive-rate-limiter -n istio-system

# For CronJobs
kubectl get cronjobs -n istio-system
kubectl describe cronjob adaptive-rate-limiter-cronjob -n istio-system
```

### View Logs

```bash
# Get pod name
kubectl get pods -n istio-system -l app=adaptive-rate-limiter

# View logs
kubectl logs -f <pod-name> -n istio-system

# View previous logs (if pod restarted)
kubectl logs <pod-name> -n istio-system --previous
```

### Common Issues

#### 1. RBAC Permission Errors
```bash
# Ensure RBAC is applied
kubectl apply -f infra/rbac.yaml

# Check ServiceAccount
kubectl get serviceaccount adaptive-rate-limiter -n istio-system
```

#### 2. ConfigMap Issues
```bash
# Check ConfigMap exists
kubectl get configmap rate-limit-values-config -n istio-system

# View ConfigMap content
kubectl describe configmap rate-limit-values-config -n istio-system
```

#### 3. Image Pull Issues
```bash
# Check if image exists
docker pull litanshamir/adaptive-rate-limiter:latest

# Check pod events
kubectl describe pod <pod-name> -n istio-system
```

## 🔄 Rollback Procedures

### For Deployments
```bash
# View rollout history
kubectl rollout history deployment/adaptive-rate-limiter -n istio-system

# Rollback to previous version
kubectl rollout undo deployment/adaptive-rate-limiter -n istio-system
```

### For Jobs
```bash
# Delete failed job
kubectl delete job adaptive-rate-limiter-job -n istio-system

# Rerun with previous image
kubectl apply -f infra/adaptive_rate_limiter_job.yaml
```

### Emergency ConfigMap Restore
```bash
# Check backup directory (created by the system)
ls backups/

# Restore from backup
kubectl apply -f backups/configmap_backup_TIMESTAMP.yaml
```

## 📊 Performance Tuning

### Resource Adjustments

Edit the deployment files to adjust resources:

```yaml
resources:
  requests:
    memory: "512Mi"  # Increase for large datasets
    cpu: "200m"      # Increase for faster processing
  limits:
    memory: "1Gi"    # Increase if OOM errors occur
    cpu: "1000m"     # Increase for CPU-intensive operations
```

### Timeout Adjustments

For longer processing times:

```yaml
activeDeadlineSeconds: 3600  # 1 hour timeout
```

## 🚨 Production Considerations

### Security
- ✅ RBAC configured with minimal required permissions
- ✅ ServiceAccount isolation
- ✅ Optional kubeconfig secret for external cluster access

### Reliability
- ✅ Resource limits prevent resource exhaustion
- ✅ Timeout protection prevents hanging jobs
- ✅ Retry logic for transient failures
- ✅ Automatic backup of ConfigMaps before updates

### Monitoring
- ✅ Structured logging for observability
- ✅ Job completion status tracking
- ✅ Error reporting and alerting ready

## 📈 Scaling Considerations

### Horizontal Scaling
The system is designed to run as a single instance to avoid conflicts in ConfigMap updates. For higher frequency updates, consider:

1. **Reduce CronJob interval** (but ensure jobs complete before next run)
2. **Use Job parallelism** for processing multiple partners simultaneously
3. **Implement leader election** for multi-instance deployments

### Vertical Scaling
Increase resources for:
- **Memory**: Large datasets or long time periods
- **CPU**: Complex Prophet calculations or many partner/path combinations

This deployment guide ensures your Adaptive Istio Rate Limiting System is production-ready with comprehensive CI/CD support! 🎉