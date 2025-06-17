# TrendMaster-AI Usage Modes

The TrendMaster-AI system supports two calculation modes to fit different operational needs and complexity requirements. Both modes use the same configuration files but with different `calculation_mode` flags.

## 🎯 Mode Overview

### FIXED Mode - Simple & Conservative
- **Purpose**: Straightforward 2.5x prime time peak calculation
- **Best for**: Production environments requiring predictable, conservative rate limits
- **Complexity**: Low - minimal configuration required
- **Performance**: Fast execution (0.25-0.30 seconds)
- **Safety**: High - conservative approach with production best practices

### ADAPTIVE Mode - Advanced & Optimized
- **Purpose**: Full analysis with cache awareness, anomaly detection, and optimization
- **Best for**: Environments requiring intelligent, dynamic rate limiting
- **Complexity**: High - comprehensive analysis and configuration
- **Performance**: Moderate execution (0.25-0.45 seconds)
- **Safety**: Intelligent - adaptive safety based on traffic patterns

## 🚀 Quick Start

### Fixed Mode (Recommended for Production)
```bash
# Simple execution with fixed formula (uses config flag)
python scripts/main.py --mode fixed

# With specific partners and APIs
python scripts/main.py --mode fixed \
  --partners 313,9020,439 \
  --apis "/api/v3/service/configurations/action/servebydevice"
```

### Adaptive Mode (Advanced Users)
```bash
# Full analysis with best practices (uses config flag)
python scripts/main.py --mode adaptive

# With Prophet analysis enabled
python scripts/main.py --mode adaptive \
  --partners 313,9020 \
  --apis "/api/v3/service/configurations/action/servebydevice"
```

## 📊 Comparison Table

| Feature | Fixed Mode | Adaptive Mode |
|---------|------------|---------------|
| **Formula** | 2.5x prime time peak | 2.5x prime time peak + optimizations |
| **Cache Analysis** | ❌ Disabled | ✅ Enabled |
| **Anomaly Detection** | ❌ Disabled | ✅ Enabled |
| **Prophet ML** | ❌ Disabled | ✅ Optional |
| **Traffic Pattern Analysis** | ❌ Basic | ✅ Advanced |
| **Safety Margin** | 1.5x (Fixed) | 1.2-1.5x (Adaptive) |
| **Cache Adjustment** | 1.0x (None) | 1.2x (Dynamic) |
| **Configuration Complexity** | Low | High |
| **Execution Time** | ~0.25s | ~0.25-0.45s |
| **Resource Usage** | Low | Moderate |

## 🔧 Configuration Files

### Fixed Mode Configuration (`config-fixed-mode.yaml`)
```yaml
RATE_CALCULATION:
  calculation_mode: 'fixed'          # Simple mode
  peak_multiplier: 2.5               # Core formula
  cache_adjustment_factor: 1.0       # No cache adjustment
  safety_margin: 1.5                 # Conservative safety
  enable_cache_adjustment: false     # Disable complexity
  
PROPHET_CONFIG:
  enabled: false                     # No ML analysis
  
ANOMALY_CONFIG:
  methods: []                        # No anomaly detection
```

### Adaptive Mode Configuration (`config-adaptive-mode.yaml`)
```yaml
RATE_CALCULATION:
  calculation_mode: 'adaptive'       # Advanced mode
  peak_multiplier: 2.5               # Core formula
  cache_adjustment_factor: 1.2       # Dynamic cache adjustment
  safety_margin: 1.5                 # Intelligent safety
  enable_cache_adjustment: true      # Enable complexity
  
PROPHET_CONFIG:
  enabled: true                      # ML analysis
  
ANOMALY_CONFIG:
  methods: ['prophet', 'statistical'] # Multiple detection methods
```

## 📈 Expected Results

### Fixed Mode Results
```json
{
  "partner": "313",
  "api": "/api/v3/service/configurations/action/servebydevice",
  "rate_limit": 500,
  "rationale": "Applied v3 formula: 2.5x average prime time peak (126.7) with variable traffic pattern. Default cache adjustment factor 1.0x applied. Safety margin 1.5x applied (from 331 to 500)",
  "calculation_method": "enhanced_formula_v3"
}
```

### Adaptive Mode Results
```json
{
  "partner": "313", 
  "api": "/api/v3/service/configurations/action/servebydevice",
  "rate_limit": 500,
  "rationale": "Applied v3 formula: 2.5x average prime time peak (126.9) with moderately_spiky traffic pattern. Default cache adjustment factor 1.2x applied. Safety margin 1.5x applied (from 362 to 500)",
  "calculation_method": "enhanced_formula_v3"
}
```

## 🎯 When to Use Which Mode

### Use FIXED Mode When:
- ✅ You need predictable, conservative rate limits
- ✅ Production environment requires stability over optimization
- ✅ Minimal configuration complexity is preferred
- ✅ Fast execution time is critical
- ✅ You want to avoid ML/statistical analysis overhead

### Use ADAPTIVE Mode When:
- ✅ You want intelligent, optimized rate limits
- ✅ Cache hit ratios vary significantly across APIs
- ✅ Traffic patterns are complex and variable
- ✅ You have resources for comprehensive analysis
- ✅ You want anomaly detection and trend analysis

## 🛡️ Production Best Practices

### Fixed Mode Production Deployment
```bash
# Conservative production deployment
ENVIRONMENT=production python scripts/main.py \
  --mode fixed \
  --config config-fixed-mode.yaml \
  --partners ${PRODUCTION_PARTNERS} \
  --apis ${PRODUCTION_APIS}
```

### Adaptive Mode Production Deployment
```bash
# Advanced production deployment
ENVIRONMENT=production python scripts/main.py \
  --mode adaptive \
  --config config-adaptive-mode.yaml \
  --partners ${PRODUCTION_PARTNERS} \
  --apis ${PRODUCTION_APIS}
```

## 🔍 Troubleshooting

### Fixed Mode Issues
- **Low rate limits**: Check if safety_margin is too high (reduce from 1.5 to 1.2)
- **Inconsistent results**: Verify prime time data quality
- **Performance issues**: Should not occur - contact support

### Adaptive Mode Issues  
- **High execution time**: Disable Prophet analysis with `TRENDMASTER_SKIP_PROPHET=true`
- **Complex configuration**: Start with fixed mode and gradually enable features
- **Memory usage**: Reduce `uncertainty_samples` in Prophet config

## 📞 Support

For questions about mode selection or configuration:
- Fixed Mode: Straightforward implementation questions
- Adaptive Mode: Advanced configuration and optimization questions

Both modes implement the same core **2.5x average prime time peak formula** - the difference is in the sophistication of analysis and optimization features.