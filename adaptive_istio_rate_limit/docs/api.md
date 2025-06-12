---
layout: default
title: API Reference
nav_order: 4
---

# API Reference

Complete API documentation for TrendMaster-AI components and interfaces.

## 🏗️ Core Components

### ConfigManager

The central configuration management system with environment-aware capabilities.

```python
from scripts.utils.config_manager import ConfigManager

# Initialize with auto-detection
config_manager = ConfigManager()

# Initialize with specific environment
config_manager = ConfigManager(environment='testing')
```

#### Methods

##### `get_config() -> Dict`
Returns the complete configuration dictionary.

```python
config = config_manager.get_config()
print(config['COMMON']['RATE_CALCULATION']['formula_version'])  # 'v3'
```

##### `get_current_environment() -> str`
Returns the currently detected environment.

```python
env = config_manager.get_current_environment()  # 'testing'
```

##### `get_deployment_mode() -> str`
Returns the deployment mode.

```python
mode = config_manager.get_deployment_mode()  # 'testing'
```

##### `get_partners() -> List[str]`
Returns configured partners for current environment.

```python
partners = config_manager.get_partners()
# ['partner_313', 'partner_439', 'partner_9020']
```

##### `get_apis() -> List[str]`
Returns configured APIs for current environment.

```python
apis = config_manager.get_apis()
# ['/api/v3/service/configurations/action/servebydevice', ...]
```

### DataFetcher

Handles data collection from Prometheus and mock data generation.

```python
from scripts.core.data_fetcher import DataFetcher

# Initialize
data_fetcher = DataFetcher(config)

# Enable mock data for testing
data_fetcher.use_mock_data = True
```

#### Methods

##### `fetch_prometheus_metrics(days: int = 7) -> Dict`
Fetches metrics from Prometheus or generates mock data.

```python
# Fetch 7 days of data
metrics = data_fetcher.fetch_prometheus_metrics(days=7)

# Fetch 3 days of data
metrics = data_fetcher.fetch_prometheus_metrics(days=3)
```

**Returns**: Dictionary containing metric series data

##### `process_prometheus_results(metrics_data: Dict) -> pd.DataFrame`
Processes raw metrics into structured DataFrame.

```python
processed_data = data_fetcher.process_prometheus_results(metrics_data)
print(processed_data.columns)
# ['partner', 'path', 'timestamp', 'value']
```

**Returns**: Pandas DataFrame with columns:
- `partner`: Partner identifier
- `path`: API path
- `timestamp`: Timestamp of measurement
- `value`: Metric value

### ProphetAnalyzer

ML-powered traffic analysis using Facebook Prophet.

```python
from scripts.core.prophet_analyzer import ProphetAnalyzer

# Initialize
prophet_analyzer = ProphetAnalyzer(config)
```

#### Methods

##### `analyze_traffic_patterns(data: pd.DataFrame, partner: str, path: str) -> Dict`
Performs comprehensive traffic analysis.

```python
analysis = prophet_analyzer.analyze_traffic_patterns(
    data=traffic_data,
    partner='partner_313',
    path='/api/v3/service/configurations/action/servebydevice'
)
```

**Parameters**:
- `data`: DataFrame with timestamp and value columns
- `partner`: Partner identifier
- `path`: API path

**Returns**: Analysis dictionary containing:
```python
{
    'analysis_method': 'prophet',  # or 'statistical'
    'trend_info': {
        'direction': 'increasing',  # 'increasing', 'decreasing', 'stable'
        'slope': 0.081195,
        'mean': 157.465,
        'std': 3.937
    },
    'seasonal_components': {
        'daily': {'mean': 0.0, 'std': 0.203},
        'weekly': {'mean': 0.0, 'std': 0.023}
    },
    'anomalies': [
        {
            'timestamp': '2025-06-13T01:21:18',
            'actual_value': 100.0,
            'predicted_value': 131.47,
            'severity': 'low',
            'type': 'prophet_uncertainty'
        }
    ]
}
```

### EnhancedRateCalculator

Advanced rate limit calculation with v3 formula.

```python
from scripts.core.enhanced_rate_calculator import EnhancedRateCalculator

# Initialize
rate_calculator = EnhancedRateCalculator(config)
```

#### Methods

##### `calculate_optimal_rate_limit(...) -> RateCalculationResult`
Calculates optimal rate limit using v3 formula.

```python
result = rate_calculator.calculate_optimal_rate_limit(
    clean_metrics=metrics_df,
    prime_time_data=prime_df,
    prophet_analysis=analysis_result,
    partner='partner_313',
    path='/api/v3/service/configurations/action/servebydevice',
    cache_metrics=cache_data
)
```

**Parameters**:
- `clean_metrics`: DataFrame with processed metrics
- `prime_time_data`: DataFrame with prime time traffic
- `prophet_analysis`: Analysis result from ProphetAnalyzer
- `partner`: Partner identifier
- `path`: API path
- `cache_metrics`: Optional cache performance data

**Returns**: `RateCalculationResult` object with:
```python
result.recommended_rate_limit  # int: Calculated rate limit
result.confidence_score       # float: Confidence in calculation
result.calculation_method     # str: Method used
result.applied_multipliers    # dict: Applied multipliers
```

### AdaptiveRateLimiter

Main system orchestrator.

```python
from scripts.main import AdaptiveRateLimiter

# Initialize
rate_limiter = AdaptiveRateLimiter()

# Run the system
results = rate_limiter.run()
```

#### Methods

##### `run() -> Dict`
Executes the complete rate limiting analysis workflow.

```python
results = rate_limiter.run()
```

**Returns**: Results dictionary with execution summary

##### `validate_environment() -> bool`
Validates current environment configuration.

```python
is_valid = rate_limiter.validate_environment()
```

## 🎯 CLI Interface

### Command Line Options

```bash
python scripts/main.py [OPTIONS]
```

| Option | Description | Example |
|--------|-------------|---------|
| `--show-env` | Display environment information | `--show-env` |
| `--partners` | Comma-separated partner IDs | `--partners partner_313,partner_439` |
| `--apis` | Comma-separated API paths | `--apis /api/v3/service/multirequest` |
| `--validate-only` | Only validate configuration | `--validate-only` |
| `--verbose` | Enable verbose logging | `--verbose` |
| `--output-format` | Output format (json/yaml) | `--output-format json` |
| `--config` | Custom configuration file | `--config /path/to/config.yaml` |

### Environment Variables

| Variable | Type | Description | Default |
|----------|------|-------------|---------|
| `ENVIRONMENT` | string | Target environment | auto-detected |
| `PROMETHEUS_URL` | string | Prometheus endpoint | from config |
| `DRY_RUN` | boolean | Enable dry run mode | `true` |
| `USE_MOCK_DATA` | boolean | Use mock data | `false` |
| `LOG_LEVEL` | string | Logging level | `INFO` |

### Usage Examples

```bash
# Show environment information
ENVIRONMENT=testing python scripts/main.py --show-env

# Analyze specific partners
ENVIRONMENT=testing python scripts/main.py --partners partner_313 --verbose

# Validate configuration
python scripts/main.py --validate-only

# Generate JSON output
python scripts/main.py --output-format json

# Debug mode
LOG_LEVEL=DEBUG python scripts/main.py --verbose
```

## 📊 Data Structures

### Configuration Schema

```yaml
DEPLOYMENT:
  MODE: "testing"
  ENVIRONMENT: "testing"

ENVIRONMENTS:
  testing:
    PROMETHEUS_URL: "http://prometheus:9090"
    DRY_RUN: true
    USE_MOCK_DATA: false

PARTNER_CONFIGS:
  testing:
    partners: ['partner_313', 'partner_439', 'partner_9020']
    apis: ['/api/v3/service/configurations/action/servebydevice']
    partner_multipliers:
      partner_313: 1.5

COMMON:
  RATE_CALCULATION:
    formula_version: "v3"
    peak_multiplier: 2.5
    safety_margin: 1.5
    min_rate_limit: 100
    max_rate_limit: 50000
```

### Metrics Data Format

```python
# DataFrame structure for metrics
{
    'partner': ['313', '313', '439'],
    'path': ['/api/v3/service/multirequest', '/api/v3/service/multirequest', '/api/v3/service/asset/action/list'],
    'timestamp': ['2025-06-13T01:00:00', '2025-06-13T01:01:00', '2025-06-13T01:00:00'],
    'value': [150.5, 142.3, 89.7]
}
```

### Rate Calculation Result

```python
class RateCalculationResult:
    recommended_rate_limit: int      # Final calculated rate limit
    confidence_score: float          # Confidence (0.0-1.0)
    calculation_method: str          # 'v3_formula'
    base_calculation: float          # Before multipliers
    applied_multipliers: dict        # Applied multipliers
    safety_margin: float            # Applied safety margin
    cache_adjustment: float         # Cache-based adjustment
    anomaly_count: int              # Number of anomalies detected
    trend_direction: str            # 'increasing', 'decreasing', 'stable'
```

## 🔧 Configuration API

### Environment Detection

```python
from scripts.utils.config_manager import ConfigManager

# Automatic detection
config = ConfigManager()
env = config.get_current_environment()

# Manual override
config = ConfigManager(environment='production')
```

### Dynamic Configuration

```python
# Get environment-specific settings
env_config = config.get_environment_config('testing')
prometheus_url = env_config.get('PROMETHEUS_URL')

# Get partner configuration
partners = config.get_partners_for_environment('testing')
apis = config.get_apis_for_environment('testing')
```

### Configuration Validation

```python
# Validate configuration
is_valid = config.validate_configuration()

# Get validation errors
errors = config.get_validation_errors()
```

## 📈 Rate Calculation API

### v3 Formula Implementation

```python
def calculate_v3_rate_limit(metrics_data, analysis_result, partner, path):
    """
    v3 Formula: 2.5x Average Peak with Cache Adjustment
    """
    # Step 1: Calculate average peak (excluding anomalies)
    effective_peak = calculate_average_peak_excluding_anomalies(metrics_data)
    
    # Step 2: Apply base multiplier
    base_rate = effective_peak * 2.5
    
    # Step 3: Cache adjustment
    cache_hit_ratio = get_cache_metrics(partner, path)
    cache_adjustment = 1.0 + (cache_hit_ratio * 0.2)
    adjusted_rate = base_rate * cache_adjustment
    
    # Step 4: Safety margin
    safety_margin = get_environment_safety_margin()
    final_rate = adjusted_rate * safety_margin
    
    # Step 5: Apply bounds and rounding
    return apply_bounds_and_rounding(final_rate)
```

### Multiplier System

```python
# Partner-specific multipliers
partner_multipliers = {
    'partner_313': 1.5,  # High-traffic partner
    'partner_439': 1.0,  # Standard partner
    'partner_9020': 2.0  # Premium partner
}

# Path-specific multipliers
path_multipliers = {
    '/api/v3/service/multirequest': 3.0,    # High-capacity endpoint
    '/api/v1/user/login': 0.5,              # Security-sensitive endpoint
    '/api/v2/analytics': 1.5                # Analytics endpoint
}
```

## 🚨 Error Handling

### Exception Types

```python
class TrendMasterError(Exception):
    """Base exception for TrendMaster-AI"""
    pass

class ConfigurationError(TrendMasterError):
    """Configuration-related errors"""
    pass

class DataFetchError(TrendMasterError):
    """Data fetching errors"""
    pass

class AnalysisError(TrendMasterError):
    """Analysis-related errors"""
    pass

class RateCalculationError(TrendMasterError):
    """Rate calculation errors"""
    pass
```

### Error Handling Patterns

```python
try:
    config = ConfigManager()
    partners = config.get_partners()
except ConfigurationError as e:
    logger.error(f"Configuration error: {e}")
    # Handle gracefully with defaults
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # Log and re-raise
    raise
```

## 🔍 Logging API

### Logger Configuration

```python
import logging

# Get TrendMaster logger
logger = logging.getLogger('trendmaster_ai')

# Log levels
logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical error")
```

### Structured Logging

```python
# Include context in logs
logger.info("Rate calculation completed", extra={
    'partner': 'partner_313',
    'path': '/api/v3/service/multirequest',
    'rate_limit': 500,
    'confidence': 0.85
})
```

## 📊 Monitoring API

### Health Checks

```python
from scripts.utils.health_check import HealthChecker

# Initialize health checker
health = HealthChecker(config)

# Check system health
status = health.check_system_health()
print(status.is_healthy)  # True/False
print(status.checks)      # Detailed check results
```

### Metrics Collection

```python
from scripts.utils.metrics import MetricsCollector

# Collect system metrics
metrics = MetricsCollector()
metrics.record_calculation_time(duration_seconds)
metrics.record_rate_limit_generated(partner, path, rate_limit)
metrics.increment_analysis_counter()
```

---

**📚 This API reference covers all major components and interfaces in TrendMaster-AI v3.0**

For more detailed examples, see the [Testing Guide](./testing.md) which demonstrates practical usage of these APIs.