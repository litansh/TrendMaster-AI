# TrendMaster-AI

**AI-powered forecasting and anomaly detection platform using Prophet, Prometheus, and ChatGPT for operational intelligence.**

Predict infrastructure trends, detect anomalies before they become incidents, and automate Istio rate limiting based on real-time traffic patterns—saving hours of manual tuning and preventing outages.

---

## 🎯 Why It Exists

**Problem:** DevOps and SRE teams struggle with reactive monitoring:
- Anomalies detected after incidents occur (not before)
- Manual rate limit tuning causes service degradation
- No visibility into future resource needs
- Context-switching between monitoring tools
- Alert fatigue from false positives

**Solution:** TrendMaster-AI provides predictive infrastructure intelligence:
- Prophet-based forecasting for trend analysis
- AI-powered anomaly detection with ChatGPT insights
- Adaptive Istio rate limiting based on traffic forecasts
- Unified platform for metrics, forecasting, and recommendations
- Automated workflows to reduce manual interventions

---

## 🚀 What It Does

### Core Capabilities

**1. Anomaly Detection**
- Prophet time-series forecasting on Prometheus metrics
- Automatic detection of deviations (>2σ from forecast)
- ChatGPT integration for root cause analysis
- Customizable sensitivity thresholds per metric
- Grafana dashboards for visualization
- Automated alerting (Slack, Teams, PagerDuty)

**2. Adaptive Istio Rate Limiting**
- Real-time traffic analysis from Prometheus
- Prophet forecasts for traffic patterns
- Cache metrics analysis (hit rates, latency)
- Prime-time detector for peak hours
- Automatic Istio ConfigMap updates
- K8s integration for zero-downtime deployment

**3. Trend Analysis**
- Multi-domain forecasting (system metrics, market trends, resource needs)
- Seasonal pattern detection
- Long-term capacity planning recommendations
- Cost forecasting based on usage trends

---

## 🏗️ Architecture

### High-Level Components

```
┌────────────────────────────────────────────────────┐
│  Data Sources                                      │
│  ├─ Prometheus (metrics collection)                │
│  ├─ Grafana (visualization)                        │
│  └─ Kubernetes (service mesh metrics)              │
└────────────────────────────────────────────────────┘
                        ↓
┌────────────────────────────────────────────────────┐
│  TrendMaster-AI Core                               │
│  ├─ Prophet Analyzer (forecasting engine)         │
│  ├─ Anomaly Detector (deviation detection)        │
│  ├─ ChatGPT Integration (AI insights)             │
│  ├─ Cache Metrics Analyzer                        │
│  ├─ Prime Time Detector                           │
│  └─ Enhanced Rate Calculator                      │
└────────────────────────────────────────────────────┘
                        ↓
┌────────────────────────────────────────────────────┐
│  Actions & Integrations                            │
│  ├─ Istio ConfigMap Manager                       │
│  ├─ Deployment Manager (K8s)                      │
│  ├─ Alert Router (Slack, Teams, PagerDuty)        │
│  └─ Report Generator (CSV, JSON, images)          │
└────────────────────────────────────────────────────┘
```

### Workflow: Anomaly Detection

1. **Data Ingestion:** Fetch Prometheus metrics for specified queries
2. **Forecasting:** Prophet generates time-series forecast with confidence intervals
3. **Detection:** Compare actual values to forecast, flag deviations >threshold
4. **Analysis:** ChatGPT analyzes anomaly context and provides insights
5. **Alerting:** Send notifications with actionable recommendations
6. **Visualization:** Display anomalies in Grafana dashboards

### Workflow: Adaptive Rate Limiting

1. **Metrics Collection:** Gather traffic and cache metrics from Prometheus
2. **Pattern Analysis:** Prophet forecasts traffic patterns, detects prime time
3. **Rate Calculation:** Enhanced calculator determines optimal rate limits
4. **ConfigMap Update:** Generate and apply Istio EnvoyFilter configuration
5. **Deployment:** Rolling update to K8s with zero downtime
6. **Monitoring:** Track rate limit effectiveness and adjust

---

## 🏃 Quickstart

### Prerequisites

- Python 3.10+
- Access to Prometheus instance
- Grafana dashboard (for visualization)
- OpenAI API key (for ChatGPT analysis)
- Kubernetes cluster (for Istio rate limiting)

### Anomaly Detection Setup (~5 minutes)

```bash
git clone https://github.com/litansh/TrendMaster-AI.git
cd TrendMaster-AI/anomaly_detection

# Create config
mkdir -p config
cat > config/config.yaml <<EOF
# Required
PROMETHEUS_URL: 'https://your-prometheus-url'
GRAFANA_DASHBOARD_URL: 'https://your-grafana-url'

# Optional
DAYS_TO_INSPECT: 7
DEVIATION_THRESHOLD: 0.5
EXCESS_DEVIATION_THRESHOLD: 1.0
K8S_SPIKE_THRESHOLD: 0.1
CSV_OUTPUT: false
IMG_OUTPUT: true
DOCKER: false

# GPT Analysis (optional)
GPT_ON: true
OPENAI_API_KEY: 'sk-your-key-here'

# Queries to monitor
QUERIES:
  - 'rate(http_requests_total[5m])'
  - 'container_memory_usage_bytes'
  - 'container_cpu_usage_seconds_total'
EOF

# Install dependencies
pip install -r requirements.txt

# Run anomaly detection
cd scripts
python anomaly_detection.py
```

**Output:** Anomaly report with images, CSV (optional), and ChatGPT insights (if enabled).

### Adaptive Istio Rate Limiting Setup (~10 minutes)

```bash
cd TrendMaster-AI/adaptive_istio_rate_limit

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp config.example.yaml config.yaml
# Edit config.yaml with Prometheus URL, K8s context

# Run rate limiter
python main.py --mode adaptive --interval 300  # Adjust every 5 minutes
```

**Result:** Istio ConfigMaps updated automatically based on traffic forecasts.

---

## ⚙️ Configuration

### Anomaly Detection (config/config.yaml)

```yaml
# Prometheus & Grafana
PROMETHEUS_URL: 'https://prometheus.example.com'
GRAFANA_DASHBOARD_URL: 'https://grafana.example.com'

# Detection Settings
DAYS_TO_INSPECT: 7              # Historical data window
DEVIATION_THRESHOLD: 0.5        # Standard deviations for anomaly (0.5 = mild, 1.0 = moderate, 2.0 = severe)
EXCESS_DEVIATION_THRESHOLD: 1.0 # Threshold for "critical" anomalies
K8S_SPIKE_THRESHOLD: 0.1        # Spike detection sensitivity

# Output Options
CSV_OUTPUT: false
IMG_OUTPUT: true                # Generate PNG charts
DOCKER: false

# ChatGPT Analysis
GPT_ON: true
OPENAI_API_KEY: 'sk-xxx'

# Metrics to Monitor
QUERIES:
  - 'rate(http_requests_total{job="api"}[5m])'
  - 'container_memory_usage_bytes{namespace="production"}'
  - 'container_cpu_usage_seconds_total{namespace="production"}'
  - 'istio_requests_total{destination_service="backend"}'
```

### Adaptive Rate Limiting (config.yaml)

```yaml
# Prometheus
prometheus:
  url: 'https://prometheus.example.com'
  queries:
    traffic: 'rate(istio_requests_total[5m])'
    cache_hit_rate: 'redis_cache_hit_rate'
    latency: 'histogram_quantile(0.95, istio_request_duration_milliseconds_bucket)'

# Prophet Settings
prophet:
  changepoint_prior_scale: 0.05
  seasonality_mode: 'multiplicative'
  forecast_periods: 288  # 24 hours at 5-minute intervals

# Rate Limiting
rate_limiting:
  base_rate: 1000        # Requests per second
  max_rate: 10000
  min_rate: 100
  adjustment_factor: 1.5  # Multiply by this during peak times

# Istio Integration
istio:
  namespace: 'istio-system'
  configmap_name: 'envoyfilter-rate-limit'

# Kubernetes
kubernetes:
  context: 'production'
  apply_changes: true    # Set to false for dry-run
```

---

## 📊 Observability

### Metrics Generated

**Anomaly Detection:**
- `trendmaster_anomalies_detected_total` - Count of anomalies detected
- `trendmaster_forecast_accuracy` - Forecast vs actual accuracy (MAPE)
- `trendmaster_processing_time_seconds` - Time to analyze metrics
- `trendmaster_chatgpt_insights_total` - ChatGPT API calls made

**Adaptive Rate Limiting:**
- `trendmaster_rate_limit_adjustments_total` - ConfigMap updates applied
- `trendmaster_forecast_traffic_rate` - Predicted traffic rate
- `trendmaster_actual_traffic_rate` - Measured traffic rate
- `trendmaster_cache_hit_rate` - Cache efficiency
- `trendmaster_prime_time_active` - Boolean (1 = peak hours detected)

### Dashboards

**Grafana Dashboards Included:**
1. **Anomaly Overview** - All detected anomalies with severity, forecast vs actual
2. **Traffic Forecasting** - Prophet forecasts with confidence intervals
3. **Rate Limiting** - Current limits, traffic trends, adjustment history

**Import:** See `dashboards/` directory for JSON exports.

### Logs

```bash
# Anomaly detection logs
tail -f logs/anomaly_detection.log

# Rate limiting logs
tail -f logs/adaptive_rate_limit.log

# Key events logged:
# - Anomalies detected (severity, metric, timestamp)
# - ChatGPT insights (query, response, cost)
# - Rate limit adjustments (old limit, new limit, reason)
# - ConfigMap updates (success/failure)
```

---

## 🗺️ Roadmap

### ✅ Phase 1: Foundation (Complete)
- [x] Prophet-based anomaly detection
- [x] ChatGPT integration for insights
- [x] Prometheus metrics ingestion
- [x] Grafana dashboard integration
- [x] Adaptive Istio rate limiting
- [x] Cache metrics analysis
- [x] Prime-time traffic detection
- [x] Kubernetes ConfigMap automation
- [x] Comprehensive test suite (~45 tests)

### 🔄 Phase 2: Production Hardening (In Progress)
- [ ] Web UI for configuration and monitoring
- [ ] Slack/Teams notification integrations
- [ ] Alert rule templates
- [ ] Historical anomaly database
- [ ] ML model versioning and rollback
- [ ] Multi-cluster support
- [ ] Docker containerization

### 📋 Phase 3: Advanced Features (Q2 2026)
- [ ] Auto-remediation workflows (self-healing)
- [ ] Custom Prophet model tuning per metric
- [ ] A/B testing for rate limit strategies
- [ ] Cost forecasting for cloud resources
- [ ] Natural language queries ("Show me anomalies in last week")
- [ ] Integration with incident management (PagerDuty, Opsgenie)
- [ ] Anomaly correlation analysis (multi-metric)

### 🚀 Phase 4: Enterprise (Q3 2026)
- [ ] Multi-tenant architecture
- [ ] RBAC for access control
- [ ] Audit logging
- [ ] Compliance reporting (SOC2, HIPAA)
- [ ] On-premises deployment option
- [ ] Enterprise support tier

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file

Copyright (c) 2026 Litan Shamir

---

## ⚠️ Disclaimer

**Development Status:** Production-ready anomaly detection. Adaptive rate limiting tested in staging environments.

**Recommended Use:**
- Test anomaly detection in non-production first
- Start with conservative deviation thresholds (1.0+)
- Dry-run mode for rate limiting before applying to production
- Monitor ChatGPT API costs (typically $1-5/day depending on volume)
- Review all automated rate limit changes before enabling

**Security:**
- Protect Prometheus URLs (contain sensitive metrics)
- Never commit `.env` or `config.yaml` with real credentials
- Rotate OpenAI API keys quarterly
- Use Kubernetes RBAC for ConfigMap access

**Cost Awareness:**
- OpenAI API: ~$0.01-0.05 per anomaly analysis
- Prophet forecasting: CPU-intensive (consider resource limits)
- Prometheus queries: Can impact performance if too frequent

---

## 📚 Documentation

- **[docs/ORIGINAL_README.md](docs/ORIGINAL_README.md)** - Original documentation
- **[docs/design.md](docs/design.md)** - Architectural decisions (coming soon)
- **[dashboards/](dashboards/)** - Grafana dashboard JSON exports
- **[examples/](examples/)** - Example configurations

---

**Status:** 🟢 Production-ready anomaly detection | 16,464 lines across 45 Python modules

**Target:** Predictive infrastructure intelligence with <5% false positive rate
