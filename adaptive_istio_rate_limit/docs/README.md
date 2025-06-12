# Adaptive Istio Rate Limiting System

A sophisticated, AI-driven system that automatically adjusts Istio rate limits based on real-time traffic analysis, Prophet-based forecasting, and intelligent anomaly detection.

## 🚀 Features

- **Prophet-Based Forecasting**: Uses Facebook Prophet for advanced time series analysis and trend detection
- **Dynamic Prime Time Detection**: Automatically identifies high-traffic periods from historical data
- **Intelligent Anomaly Detection**: Filters out anomalous spikes to prevent skewed rate limit calculations
- **Enhanced Rate Calculation**: Improved formulas with cache ratio integration and partner-specific adjustments
- **Multi-Environment Support**: Local development, testing preview, and production deployment modes
- **Kubernetes Integration**: Direct ConfigMap management with backup and rollback capabilities
- **Comprehensive Monitoring**: Detailed logging, reporting, and change tracking

## 🏗️ Architecture

The system consists of several core components:

- **Config Manager**: Handles environment-specific configurations
- **Data Fetcher**: Retrieves metrics from Prometheus (with mock data support for local dev)
- **Prophet Analyzer**: Performs time series forecasting and anomaly detection
- **Prime Time Detector**: Identifies peak traffic periods dynamically
- **Enhanced Rate Calculator**: Calculates optimal rate limits using advanced formulas
- **ConfigMap Manager**: Manages Kubernetes ConfigMap updates with safety checks

## 📋 Prerequisites

- Python 3.8+
- Kubernetes cluster access (for testing/production modes)
- Prometheus endpoint (for real data)

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd adaptive_istio_rate_limit
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the system**:
   ```bash
   cp config/config.yaml.example config/config.yaml
   # Edit config/config.yaml with your settings
   ```

## ⚙️ Configuration

The system supports three deployment modes configured in `config/config.yaml`:

### Local Mode (Development)
```yaml
DEPLOYMENT:
  MODE: "local"

ENVIRONMENTS:
  local:
    USE_MOCK_DATA: true
    PROMETHEUS_URL: "http://localhost:9090"
    KUBERNETES_CONTEXT: "minikube"
    PREVIEW_ONLY: true
```

### Testing Mode (EKS Preview)
```yaml
DEPLOYMENT:
  MODE: "testing"

ENVIRONMENTS:
  testing:
    PROMETHEUS_URL: "https://your-prometheus-url"
    KUBERNETES_CONTEXT: "eks-testing"
    PREVIEW_ONLY: true
    GENERATE_REPORTS: true
```

### Production Mode (EKS Deployment)
```yaml
DEPLOYMENT:
  MODE: "production"

ENVIRONMENTS:
  production:
    PROMETHEUS_URL: "https://your-prometheus-url"
    KUBERNETES_CONTEXT: "eks-production"
    ENABLE_UPDATES: true
    MONITORING_ENABLED: true
```

### Key Configuration Options

- **Prophet Settings**:
  ```yaml
  PROPHET_CONFIG:
    enabled: true
    seasonality_mode: 'multiplicative'
    weekly_seasonality: true
    daily_seasonality: true
  ```

- **Rate Calculation**:
  ```yaml
  RATE_CALCULATION:
    cache_ratio: 1.2
    formula_version: "v2"
    safety_margin: 1.3
    rounding_method: "nearest_hundred"
  ```

- **Anomaly Detection**:
  ```yaml
  ANOMALY_CONFIG:
    methods: ['prophet', 'statistical']
    sensitivity: 'medium'
    spike_threshold_multiplier: 3.0
  ```

## 🚀 Usage

### Quick Start (Local Mode)

1. **Test the system**:
   ```bash
   python3 test_local.py
   ```

2. **Run the system**:
   ```bash
   python3 scripts/main.py
   ```

3. **Check outputs**:
   ```bash
   ls output/  # Generated ConfigMaps and reports
   ```

### Testing Mode (EKS Preview)

1. **Update configuration**:
   ```yaml
   DEPLOYMENT:
     MODE: "testing"
   ```

2. **Run with real data**:
   ```bash
   python3 scripts/main.py
   ```

3. **Review reports**:
   ```bash
   ls reports/  # Detailed analysis reports
   ```

### Production Mode (EKS Deployment)

1. **Update configuration**:
   ```yaml
   DEPLOYMENT:
     MODE: "production"
   ENVIRONMENTS:
     production:
       ENABLE_UPDATES: true
   ```

2. **Deploy changes**:
   ```bash
   python3 scripts/main.py
   ```

## 📊 System Workflow

1. **Data Collection**: Fetches metrics from Prometheus using configurable queries
2. **Data Processing**: Cleans and validates the collected metrics data
3. **Prophet Analysis**: Performs time series forecasting and anomaly detection
4. **Prime Time Detection**: Identifies high-traffic periods dynamically
5. **Rate Calculation**: Computes optimal rate limits using enhanced formulas
6. **ConfigMap Generation**: Creates updated Istio rate limit configurations
7. **Deployment**: Applies changes based on the configured mode

## 🔧 Advanced Features

### Enhanced Rate Calculation Formula V2

The system uses an improved formula that considers:
- Traffic pattern classification (stable, variable, spiky)
- Cache ratio integration
- Prime time vs. overall traffic analysis
- Partner-specific adjustments
- Trend-based growth predictions

### Dynamic Prime Time Detection

Automatically identifies peak traffic periods by:
- Analyzing hourly traffic patterns
- Calculating dynamic percentile thresholds
- Validating consistency across multiple days
- Accounting for partner-specific patterns

### Intelligent Anomaly Detection

Multi-layered approach using:
- Prophet's uncertainty intervals
- Statistical outlier detection (IQR, Z-score)
- Contextual anomaly identification
- Configurable sensitivity levels

## 📈 Monitoring and Reporting

### Local Mode Outputs
- `output/local_configmap_TIMESTAMP.yaml`: Generated ConfigMap
- `output/analysis_report_TIMESTAMP.md`: Detailed analysis report

### Testing Mode Outputs
- `reports/testing_report_TIMESTAMP.md`: Comprehensive testing report
- Console output with change previews and impact analysis

### Production Mode Outputs
- `backups/configmap_backup_TIMESTAMP.yaml`: Automatic backups
- Kubernetes ConfigMap updates with proper validation
- Comprehensive logging and monitoring

## 🛡️ Safety Features

- **Backup and Rollback**: Automatic ConfigMap backups before updates
- **Validation**: Comprehensive YAML and structure validation
- **Bounds Checking**: Prevents extreme rate limit values
- **Dry Run Mode**: Test changes without applying them
- **Gradual Rollout**: Support for phased deployments

## 🔍 Troubleshooting

### Common Issues

1. **Prophet Import Error**:
   ```bash
   pip install prophet
   # On macOS, you might need: conda install prophet
   ```

2. **Kubernetes Connection Issues**:
   ```bash
   kubectl config current-context  # Verify context
   kubectl get configmaps -n istio-system  # Test access
   ```

3. **Prometheus Connection Issues**:
   - Verify the Prometheus URL in configuration
   - Check network connectivity and authentication
   - Test with a simple query first

### Debug Mode

Enable detailed logging:
```yaml
COMMON:
  LOG_LEVEL: "DEBUG"
  VERBOSE_LOGGING: true
```

## 📝 Configuration Examples

### Minimal Local Configuration
```yaml
DEPLOYMENT:
  MODE: "local"

COMMON:
  DAYS_TO_INSPECT: 3
  RATE_CALCULATION:
    cache_ratio: 1.2
    formula_version: "v2"
```

### Production Configuration
```yaml
DEPLOYMENT:
  MODE: "production"

ENVIRONMENTS:
  production:
    PROMETHEUS_URL: "https://prometheus.company.com"
    KUBERNETES_CONTEXT: "eks-prod"
    ENABLE_UPDATES: true

COMMON:
  DAYS_TO_INSPECT: 7
  PROPHET_CONFIG:
    enabled: true
  RATE_CALCULATION:
    cache_ratio: 1.3
    safety_margin: 1.4
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite: `python3 test_local.py`
6. Submit a pull request

## 📄 License

[Add your license information here]

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the logs in debug mode
3. Create an issue with detailed information about your setup

## 🗺️ Roadmap

- [ ] Machine learning-based traffic prediction
- [ ] Integration with additional monitoring systems
- [ ] Advanced alerting and notification systems
- [ ] Web-based dashboard for monitoring and control
- [ ] Support for additional rate limiting backends
- [ ] Automated A/B testing for rate limit changes

---

**Note**: This system is designed to work with your existing TrendMaster-AI infrastructure and enhances it with sophisticated rate limiting capabilities. Always test in a non-production environment first.