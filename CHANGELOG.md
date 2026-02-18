# Changelog

All notable changes to TrendMaster-AI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned (Production Hardening)
- Web UI for configuration and monitoring
- Slack/Teams notification integrations
- Alert rule templates
- Historical anomaly database
- ML model versioning and rollback
- Multi-cluster support
- Docker containerization

## [0.2.0] - 2026-02-17

### Added
- Complete documentation restructure
- Product-grade README with quickstart
- Architecture documentation (docs/design.md planned)
- CONTRIBUTING.md
- CHANGELOG.md
- CODE_OF_CONDUCT.md

### Changed
- README refactored to showcase standard
- Emphasis on production-readiness
- Clear setup instructions (<5 minutes for anomaly detection)

## [0.1.0] - 2025-06-13

### Added
- **Anomaly Detection System** (~8,000 lines)
  - Prophet-based time-series forecasting
  - Automatic anomaly detection with configurable thresholds
  - ChatGPT integration for root cause analysis
  - Prometheus metrics ingestion
  - Grafana dashboard integration
  - CSV and image output options
  - Configurable sensitivity (deviation thresholds, K8s spike detection)

- **Adaptive Istio Rate Limiting** (~8,400 lines)
  - Real-time traffic analysis from Prometheus
  - Prophet forecasting for traffic patterns
  - Cache metrics analyzer (hit rates, latency)
  - Prime-time detector for peak hour identification
  - Enhanced rate calculator with multiple strategies
  - Automatic Istio ConfigMap generation
  - Kubernetes integration for zero-downtime deployment
  - Comprehensive test suite (45+ tests)

### Core Components Implemented
- **Prophet Analyzer:** Forecasting engine with seasonal decomposition
- **Data Fetcher:** Prometheus query interface
- **Config Manager:** YAML-based configuration
- **Cache Metrics Analyzer:** Redis/cache performance analysis
- **Prime Time Detector:** Peak hour identification
- **Enhanced Rate Calculator:** Multi-strategy rate limit computation
- **ConfigMap Manager:** K8s Istio EnvoyFilter automation
- **Deployment Manager:** Safe rollout orchestration

### Architecture Decisions
- Prophet for forecasting (vs ARIMA, LSTM)
- ChatGPT for insights (augments alerting)
- Prometheus as data source (standard in K8s)
- YAML configuration (vs database)
- K8s ConfigMap for Istio (vs Istio API)
- Python for implementation (ecosystem + Prophet)
- Modular design (anomaly detection + rate limiting separate)

### Testing
- Comprehensive test coverage (~45 tests)
- Local sanity tests
- Environment integration tests
- Selective update tests

## [0.0.1] - 2024-11-01

### Initial
- Project structure and repository setup
- Initial concept and architecture

[Unreleased]: https://github.com/litansh/TrendMaster-AI/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/litansh/TrendMaster-AI/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/litansh/TrendMaster-AI/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/litansh/TrendMaster-AI/releases/tag/v0.0.1
