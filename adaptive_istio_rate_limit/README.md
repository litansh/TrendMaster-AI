# TrendMaster-AI Adaptive Istio Rate Limiting System v3.0

An intelligent, ML-powered adaptive rate limiting system for Istio service mesh that uses Facebook Prophet for traffic forecasting and anomaly detection.

## 🚀 Features

- **ML-Powered Analysis**: Facebook Prophet for traffic forecasting and trend analysis
- **Enhanced v3 Formula**: 2.5x average peak formula with cache considerations and anomaly detection
- **Environment-Aware**: Supports local, testing, orp2, and production environments
- **Kubernetes Integration**: Generates production-ready ConfigMaps for Istio rate limiting
- **Multi-Environment Support**: Different configurations and partner sets per environment
- **Mock Data Mode**: For local development and testing without real Prometheus data
- **Comprehensive Testing**: Full test suite with sanity checks and end-to-end validation

## 📋 Prerequisites

### System Requirements
- Python 3.8+
- Kubernetes cluster (for production deployment)
- Istio service mesh installed
- Prometheus for metrics collection
- Access to Trickster endpoints (for production environments)

### Python Dependencies
```bash
pip install -r requirements.txt
```

Key dependencies:
- `prophet` - Facebook Prophet for ML forecasting
- `kubernetes` - Kubernetes Python client
- `prometheus-api-client` - Prometheus API client
- `pandas`, `numpy` - Data processing
- `pyyaml` - YAML processing
- `requests` - HTTP client

## 🏗️ Architecture

### Components
1. **Enhanced Rate Calculator v3.0**: ML-powered rate calculation with v3 formula
2. **Prophet Analyzer**: Facebook Prophet for traffic forecasting and anomaly detection
3. **ConfigMap Manager**: Kubernetes ConfigMap generation and management
4. **Data Fetcher**: Prometheus metrics collection with mock data support
5. **Prime Time Detector**: Traffic pattern analysis and peak detection

### Environment Behavior
- **Local**: Uses example partners (CUSTOMER_ID_1, CUSTOMER_ID_2, CUSTOMER_ID_3) from `config/config.yaml`
- **Testing/Production**: Reads partners and APIs from existing `ratelimit-config` ConfigMap in `istio-system` namespace

## 🛠️ Installation & Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd TrendMaster-AI/adaptive_istio_rate_limit
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
# Set environment (local, testing, orp2, production)
export KALTURA_ENV=local

# For production environments, ensure Kubernetes access
export KUBECONFIG=/path/to/kubeconfig
```

### 4. Configuration Files
- `config/config.yaml` - Main configuration with environment-specific settings
- `.test.config.yaml` - Test configuration with example partners

## 🧪 Testing

### Run All Tests
```bash
# Run comprehensive test suite
python -m pytest tests/test_sanity.py -v

# Run specific test
python -m pytest tests/test_sanity.py::SanityTests::test_5_end_to_end_configmap_generation -v
```

### Test Coverage
1. **Config Manager Initialization** - Configuration loading and validation
2. **Data Fetcher Mock Data Generation** - Mock data generation for testing
3. **Prophet Analyzer Basic Analysis** - ML analysis and forecasting
4. **Rate Calculator Formula Application** - v3 formula calculations
5. **End-to-End ConfigMap Generation** - Complete system integration

### Manual Testing
```bash
# Show environment information
python scripts/main.py --show-env

# Validate configuration only
python scripts/main.py --validate-only

# Run with verbose output
python scripts/main.py --verbose
```

## 🚀 Deployment

### Local Development
```bash
# Set local environment
export KALTURA_ENV=local

# Run the system (uses example partners from config)
python scripts/main.py

# Generated files will be in output/ directory:
# - local_configmap_YYYYMMDD_HHMMSS.yaml
# - analysis_report_YYYYMMDD_HHMMSS.md
```

### Testing Environment
```bash
# Set testing environment
export KALTURA_ENV=testing

# Ensure Kubernetes access
export KUBECONFIG=/path/to/testing-kubeconfig

# Run the system (reads from ratelimit-config ConfigMap)
python scripts/main.py

# Generated files:
# - testing_configmap_YYYYMMDD_HHMMSS.yaml
# - analysis_report_YYYYMMDD_HHMMSS.md
```

### Production Deployment on EKS

#### 1. EKS Infrastructure Requirements

**EKS Cluster Setup:**
```bash
# Create EKS cluster
eksctl create cluster \
  --name trendmaster-ai-cluster \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 4 \
  --managed
```

**Required AWS IAM Permissions:**
- `eks:DescribeCluster`
- `ec2:DescribeInstances`
- `iam:GetRole`
- `iam:ListAttachedRolePolicies`

#### 2. Istio Installation
```bash
# Install Istio
curl -L https://istio.io/downloadIstio | sh -
cd istio-*
export PATH=$PWD/bin:$PATH

# Install Istio on EKS
istioctl install --set values.pilot.env.EXTERNAL_ISTIOD=true

# Enable Istio injection
kubectl label namespace default istio-injection=enabled
```

#### 3. Rate Limiting Setup
```bash
# Install Envoy rate limiting service
kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.19/samples/ratelimit/rate-limit-service.yaml

# Create initial ratelimit-config ConfigMap in istio-system namespace
kubectl create configmap ratelimit-config -n istio-system --from-literal=config.yaml="
domain: global-ratelimit
descriptors:
- key: PARTNER
  value: 'CUSTOMER_ID_1'
  descriptors:
  - key: PATH
    value: /api/v3/service/ENDPOINT_1
    rate_limit:
      unit: minute
      requests_per_unit: 100
"
```

#### 4. TrendMaster-AI Deployment

**Create Kubernetes Resources:**
```yaml
# trendmaster-ai-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: trendmaster-ai
  namespace: istio-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: trendmaster-ai
  template:
    metadata:
      labels:
        app: trendmaster-ai
    spec:
      serviceAccountName: trendmaster-ai
      containers:
      - name: trendmaster-ai
        image: your-registry/trendmaster-ai:latest
        env:
        - name: KALTURA_ENV
          value: "production"
        - name: PROMETHEUS_URL
          value: "https://prometheus.production.ott.YOUR_COMPANY.com"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        volumeMounts:
        - name: config
          mountPath: /app/config
      volumes:
      - name: config
        configMap:
          name: trendmaster-ai-config
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: trendmaster-ai
  namespace: istio-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: trendmaster-ai
rules:
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "list", "create", "update", "patch"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: trendmaster-ai
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: trendmaster-ai
subjects:
- kind: ServiceAccount
  name: trendmaster-ai
  namespace: istio-system
```

**Deploy to EKS:**
```bash
# Apply deployment
kubectl apply -f trendmaster-ai-deployment.yaml

# Create ConfigMap with production configuration
kubectl create configmap trendmaster-ai-config -n istio-system \
  --from-file=config.yaml=config/config.yaml

# Verify deployment
kubectl get pods -n istio-system -l app=trendmaster-ai
kubectl logs -n istio-system -l app=trendmaster-ai
```

#### 5. Automated Execution with CronJob
```yaml
# trendmaster-ai-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: trendmaster-ai-scheduler
  namespace: istio-system
spec:
  schedule: "0 */6 * * *"  # Run every 6 hours
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: trendmaster-ai
          containers:
          - name: trendmaster-ai
            image: your-registry/trendmaster-ai:latest
            command: ["python", "scripts/main.py"]
            env:
            - name: KALTURA_ENV
              value: "production"
          restartPolicy: OnFailure
```

#### 6. Monitoring and Alerting
```yaml
# monitoring-setup.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: trendmaster-ai-alerts
  namespace: istio-system
data:
  alerts.yaml: |
    groups:
    - name: trendmaster-ai-production
      rules:
      - alert: HighRateLimitViolations
        expr: rate(envoy_http_local_rate_limiter_rate_limited_total[5m]) > 10
        for: 5m
        labels:
          severity: warning
          environment: production
        annotations:
          summary: "High rate limit violations detected"
          description: "Rate limit violations exceed threshold"
      
      - alert: TrendMasterAIJobFailed
        expr: kube_job_status_failed{job_name=~"trendmaster-ai-.*"} > 0
        for: 1m
        labels:
          severity: critical
          environment: production
        annotations:
          summary: "TrendMaster-AI job failed"
          description: "TrendMaster-AI analysis job has failed"
```

## 🔧 Configuration

### Environment Variables
- `KALTURA_ENV`: Environment name (local, testing, orp2, production)
- `PROMETHEUS_URL`: Prometheus endpoint URL
- `KUBECONFIG`: Kubernetes configuration file path

### Configuration Files
- `config/config.yaml`: Main configuration with environment-specific settings
- Partners and APIs are loaded differently per environment:
  - **Local**: From config file (CUSTOMER_ID_1, CUSTOMER_ID_2, CUSTOMER_ID_3)
  - **Testing/Production**: From `ratelimit-config` ConfigMap in `istio-system` namespace

### Rate Limiting Formula v3
```
EffectivePeak = max(average_peak, percentile_95) * 2.5
BaseRate = EffectivePeak * 2.5
CacheMultiplier = 1.2 (if caching detected)
PatternMultiplier = 1.1 (for regular patterns)
TrendMultiplier = 0.95-1.05 (based on trend analysis)
FinalRate = BaseRate * CacheMultiplier * PatternMultiplier * TrendMultiplier
```

## 📊 Output Files

### Generated ConfigMaps
- `local_configmap_YYYYMMDD_HHMMSS.yaml` - Local environment
- `testing_configmap_YYYYMMDD_HHMMSS.yaml` - Testing environment
- `production_configmap_YYYYMMDD_HHMMSS.yaml` - Production environment

### Analysis Reports
- `analysis_report_YYYYMMDD_HHMMSS.md` - Detailed analysis with ML insights
- Contains partner-by-partner analysis, confidence levels, and recommendations

### ConfigMap Structure
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ratelimit-config
  namespace: istio-system
data:
  config.yaml: |
    domain: global-ratelimit
    descriptors:
    - key: PARTNER
      value: 'CUSTOMER_ID_1'
      descriptors:
      - key: PATH
        value: /api/v3/service/ENDPOINT_1
        rate_limit:
          unit: minute
          requests_per_unit: 300
```

## 🔍 Troubleshooting

### Common Issues

**1. Kubernetes Connection Issues**
```bash
# Check cluster access
kubectl cluster-info

# Verify service account permissions
kubectl auth can-i get configmaps --as=system:serviceaccount:istio-system:trendmaster-ai
```

**2. Prometheus Connection Issues**
```bash
# Test Prometheus connectivity
curl -k "https://prometheus.production.ott.YOUR_COMPANY.com/api/v1/query?query=up"
```

**3. ConfigMap Not Found**
```bash
# Check if ratelimit-config exists
kubectl get configmap ratelimit-config -n istio-system

# Create if missing
kubectl create configmap ratelimit-config -n istio-system --from-literal=config.yaml="domain: global-ratelimit"
```

**4. Mock Data Mode**
- System automatically falls back to mock data if Prometheus is unavailable
- Check logs for "Using mock data mode" messages

### Debug Commands
```bash
# Show environment information
python scripts/main.py --show-env

# Validate configuration
python scripts/main.py --validate-only

# Run with verbose logging
python scripts/main.py --verbose

# Check generated files
ls -la output/

# View latest ConfigMap
cat output/$(ls -t output/*configmap*.yaml | head -1)
```

## 🏃‍♂️ Quick Start

### 1. Local Development
```bash
export KALTURA_ENV=local
python scripts/main.py
```

### 2. Testing Environment
```bash
export KALTURA_ENV=testing
export KUBECONFIG=/path/to/testing-kubeconfig
python scripts/main.py
```

### 3. Production Deployment
```bash
# Build and push Docker image
docker build -t your-registry/trendmaster-ai:latest .
docker push your-registry/trendmaster-ai:latest

# Deploy to EKS
kubectl apply -f k8s/trendmaster-ai-deployment.yaml
kubectl apply -f k8s/trendmaster-ai-cronjob.yaml
```

## 📈 Performance & Scaling

### Resource Requirements
- **Memory**: 512Mi - 1Gi (depending on partner count)
- **CPU**: 250m - 500m
- **Storage**: Minimal (logs and temporary files)

### Scaling Considerations
- System processes partners sequentially for data consistency
- Processing time scales linearly with partner/API count
- Typical execution time: 20-30 seconds for 3 partners with 4 APIs each

## 🔐 Security

### RBAC Permissions
- Read access to `ratelimit-config` ConfigMap in `istio-system`
- Write access to create/update ConfigMaps
- Pod listing permissions for health checks

### Network Security
- HTTPS connections to Prometheus endpoints
- Kubernetes API access via service accounts
- No external network access required (except Prometheus)

## 📚 Additional Resources

- [Istio Rate Limiting Documentation](https://istio.io/latest/docs/tasks/policy-enforcement/rate-limiting/)
- [Facebook Prophet Documentation](https://facebook.github.io/prophet/)
- [EKS User Guide](https://docs.aws.amazon.com/eks/latest/userguide/)
- [Kubernetes ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests: `python -m pytest tests/test_sanity.py -v`
4. Submit a pull request

## 📄 License

[Add your license information here]

---

**TrendMaster-AI v3.0** - Intelligent, ML-powered adaptive rate limiting for Istio service mesh.