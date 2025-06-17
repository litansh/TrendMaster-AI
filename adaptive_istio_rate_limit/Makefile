# TrendMaster-AI Adaptive Istio Rate Limiting System
# Production-Ready Makefile

.PHONY: help install install-dev test test-unit test-integration lint format clean build deploy validate config-check env-check docker-build docker-run

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := pip3
PROJECT_NAME := trendmaster-ai-adaptive-rate-limiter
VERSION := 3.0.0
DOCKER_IMAGE := $(PROJECT_NAME):$(VERSION)
ENVIRONMENT := $(shell echo $$ENVIRONMENT | tr '[:upper:]' '[:lower:]')

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m

help: ## Show this help message
	@echo "$(BLUE)TrendMaster-AI Adaptive Istio Rate Limiting System$(NC)"
	@echo "$(BLUE)=================================================$(NC)"
	@echo ""
	@echo "$(GREEN)Available targets:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Install production dependencies
	@echo "$(GREEN)Installing production dependencies...$(NC)"
	$(PIP) install -r requirements.txt

install-dev: ## Install development dependencies
	@echo "$(GREEN)Installing development dependencies...$(NC)"
	$(PIP) install -r requirements.txt
	$(PIP) install pytest black flake8 mypy pre-commit

env-check: ## Check environment configuration
	@echo "$(GREEN)Checking environment configuration...$(NC)"
	@$(PYTHON) scripts/utils/config_manager.py --validate --show-env

config-check: ## Validate configuration files
	@echo "$(GREEN)Validating configuration files...$(NC)"
	@$(PYTHON) scripts/utils/config_manager.py --validate

test: ## Run all tests
	@echo "$(GREEN)Running all tests...$(NC)"
	$(PYTHON) -m pytest tests/ -v

test-unit: ## Run unit tests
	@echo "$(GREEN)Running unit tests...$(NC)"
	$(PYTHON) -m pytest tests/test_*.py -v

test-integration: ## Run integration tests
	@echo "$(GREEN)Running integration tests...$(NC)"
	$(PYTHON) -m pytest tests/test_*integration*.py -v

test-local: ## Run local environment tests
	@echo "$(GREEN)Running local environment tests...$(NC)"
	ENVIRONMENT=local $(PYTHON) -m pytest tests/test_local*.py -v

lint: ## Run code linting
	@echo "$(GREEN)Running code linting...$(NC)"
	flake8 scripts/ tests/ --max-line-length=120 --ignore=E203,W503
	mypy scripts/ --ignore-missing-imports

format: ## Format code with black
	@echo "$(GREEN)Formatting code...$(NC)"
	black scripts/ tests/ --line-length=120

clean: ## Clean up generated files
	@echo "$(GREEN)Cleaning up...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf output/*.yaml output/*.md
	rm -rf logs/*.log
	rm -rf .pytest_cache
	rm -rf .mypy_cache

run-local: ## Run in local environment
	@echo "$(GREEN)Running in local environment...$(NC)"
	ENVIRONMENT=local $(PYTHON) scripts/main.py

run-testing: ## Run in testing environment
	@echo "$(GREEN)Running in testing environment...$(NC)"
	ENVIRONMENT=testing $(PYTHON) scripts/main.py

run-production: ## Run in production environment (dry-run by default)
	@echo "$(GREEN)Running in production environment (dry-run)...$(NC)"
	ENVIRONMENT=production DRY_RUN=true $(PYTHON) scripts/main.py

deploy-local: ## Deploy to local environment
	@echo "$(GREEN)Deploying to local environment...$(NC)"
	ENVIRONMENT=local $(PYTHON) scripts/deployment_manager.py --environment local --action deploy

deploy-testing: ## Deploy to testing environment
	@echo "$(GREEN)Deploying to testing environment...$(NC)"
	ENVIRONMENT=testing $(PYTHON) scripts/deployment_manager.py --environment testing --action deploy --dry-run

deploy-production: ## Deploy to production environment (requires confirmation)
	@echo "$(RED)WARNING: This will deploy to PRODUCTION environment!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo ""; \
		echo "$(GREEN)Deploying to production...$(NC)"; \
		ENVIRONMENT=production $(PYTHON) scripts/deployment_manager.py --environment production --action deploy; \
	else \
		echo ""; \
		echo "$(YELLOW)Deployment cancelled.$(NC)"; \
	fi

validate-deployment: ## Validate current deployment
	@echo "$(GREEN)Validating deployment...$(NC)"
	$(PYTHON) scripts/deployment_manager.py --environment $(ENVIRONMENT) --action validate

rollback: ## Rollback deployment
	@echo "$(GREEN)Rolling back deployment...$(NC)"
	$(PYTHON) scripts/deployment_manager.py --environment $(ENVIRONMENT) --action rollback

docker-build: ## Build Docker image
	@echo "$(GREEN)Building Docker image...$(NC)"
	docker build -t $(DOCKER_IMAGE) .
	docker tag $(DOCKER_IMAGE) $(PROJECT_NAME):latest

docker-run: ## Run Docker container
	@echo "$(GREEN)Running Docker container...$(NC)"
	docker run --rm -it \
		-e ENVIRONMENT=$(ENVIRONMENT) \
		-e LOG_LEVEL=INFO \
		-v $(PWD)/output:/app/output \
		-v $(PWD)/logs:/app/logs \
		$(DOCKER_IMAGE)

docker-push: ## Push Docker image to registry
	@echo "$(GREEN)Pushing Docker image...$(NC)"
	docker push $(DOCKER_IMAGE)
	docker push $(PROJECT_NAME):latest

setup-dev: ## Setup development environment
	@echo "$(GREEN)Setting up development environment...$(NC)"
	$(MAKE) install-dev
	pre-commit install
	@echo "$(GREEN)Development environment ready!$(NC)"

ci-test: ## Run CI tests
	@echo "$(GREEN)Running CI tests...$(NC)"
	$(MAKE) lint
	$(MAKE) test
	$(MAKE) config-check

show-env: ## Show current environment information
	@echo "$(GREEN)Current Environment Information:$(NC)"
	@$(PYTHON) scripts/main.py --show-env

generate-report: ## Generate analysis report
	@echo "$(GREEN)Generating analysis report...$(NC)"
	ENVIRONMENT=$(ENVIRONMENT) $(PYTHON) scripts/main.py --output-format yaml > output/latest_report.yaml
	@echo "$(GREEN)Report generated: output/latest_report.yaml$(NC)"

monitor: ## Show monitoring dashboard (if available)
	@echo "$(GREEN)Opening monitoring dashboard...$(NC)"
	@if command -v open >/dev/null 2>&1; then \
		open http://localhost:3000/d/trendmaster-ai; \
	elif command -v xdg-open >/dev/null 2>&1; then \
		xdg-open http://localhost:3000/d/trendmaster-ai; \
	else \
		echo "$(YELLOW)Please open http://localhost:3000/d/trendmaster-ai in your browser$(NC)"; \
	fi

backup: ## Backup current configuration and data
	@echo "$(GREEN)Creating backup...$(NC)"
	@mkdir -p backups
	@tar -czf backups/backup_$(shell date +%Y%m%d_%H%M%S).tar.gz \
		config/ output/ logs/ --exclude='logs/*.log' --exclude='output/*.yaml'
	@echo "$(GREEN)Backup created in backups/$(NC)"

restore: ## Restore from backup (specify BACKUP_FILE)
	@echo "$(GREEN)Restoring from backup...$(NC)"
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "$(RED)Please specify BACKUP_FILE=path/to/backup.tar.gz$(NC)"; \
		exit 1; \
	fi
	@tar -xzf $(BACKUP_FILE)
	@echo "$(GREEN)Restore completed$(NC)"

health-check: ## Perform system health check
	@echo "$(GREEN)Performing health check...$(NC)"
	@$(PYTHON) -c "
	import sys
	sys.path.append('scripts')
	from utils.config_manager import ConfigManager
	try:
		cm = ConfigManager()
		validation = cm.validate_configuration()
		if validation['valid']:
			print('✅ System health check passed')
			sys.exit(0)
		else:
			print('❌ System health check failed')
			for error in validation.get('errors', []):
				print(f'  Error: {error}')
			sys.exit(1)
	except Exception as e:
		print(f'❌ Health check failed: {e}')
		sys.exit(1)
	"

update-deps: ## Update dependencies
	@echo "$(GREEN)Updating dependencies...$(NC)"
	$(PIP) install --upgrade -r requirements.txt

security-check: ## Run security checks
	@echo "$(GREEN)Running security checks...$(NC)"
	$(PIP) install safety bandit
	safety check
	bandit -r scripts/ -f json -o security_report.json || true
	@echo "$(GREEN)Security check completed. Report: security_report.json$(NC)"

performance-test: ## Run performance tests
	@echo "$(GREEN)Running performance tests...$(NC)"
	ENVIRONMENT=local $(PYTHON) -m pytest tests/test_*performance*.py -v

stress-test: ## Run stress tests
	@echo "$(GREEN)Running stress tests...$(NC)"
	@echo "$(YELLOW)This will generate high load. Continue? [y/N]$(NC)"
	@read -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		ENVIRONMENT=local $(PYTHON) tests/stress_test.py; \
	fi

docs: ## Generate documentation
	@echo "$(GREEN)Generating documentation...$(NC)"
	@mkdir -p docs/generated
	@$(PYTHON) -c "
	import sys
	sys.path.append('scripts')
	from utils.config_manager import ConfigManager
	cm = ConfigManager()
	config = cm.get_config()
	import yaml
	with open('docs/generated/config_reference.yaml', 'w') as f:
		yaml.dump(config, f, default_flow_style=False)
	"
	@echo "$(GREEN)Documentation generated in docs/generated/$(NC)"

version: ## Show version information
	@echo "$(GREEN)Version Information:$(NC)"
	@echo "  Project: $(PROJECT_NAME)"
	@echo "  Version: $(VERSION)"
	@echo "  Python: $(shell $(PYTHON) --version)"
	@echo "  Environment: $(ENVIRONMENT)"

info: ## Show project information
	@echo "$(BLUE)TrendMaster-AI Adaptive Istio Rate Limiting System$(NC)"
	@echo "$(BLUE)=================================================$(NC)"
	@echo ""
	@echo "$(GREEN)Project Information:$(NC)"
	@echo "  Name: $(PROJECT_NAME)"
	@echo "  Version: $(VERSION)"
	@echo "  Environment: $(ENVIRONMENT)"
	@echo ""
	@echo "$(GREEN)Key Features:$(NC)"
	@echo "  • Environment-aware configuration management"
	@echo "  • 2.5x average peaks formula with cache considerations"
	@echo "  • Prophet-based ML analysis with anomaly detection"
	@echo "  • Multi-environment support (local, testing, production)"
	@echo "  • Production-ready optimizations and monitoring"
	@echo ""
	@echo "$(GREEN)Quick Start:$(NC)"
	@echo "  1. make install          # Install dependencies"
	@echo "  2. make env-check        # Check environment"
	@echo "  3. make run-local        # Run in local mode"
	@echo "  4. make deploy-local     # Deploy locally"
	@echo ""

# Development shortcuts
dev-setup: setup-dev ## Alias for setup-dev
dev-test: test ## Alias for test
dev-run: run-local ## Alias for run-local

# Production shortcuts  
prod-check: ## Production readiness check
	@echo "$(GREEN)Checking production readiness...$(NC)"
	$(MAKE) lint
	$(MAKE) test
	$(MAKE) security-check
	$(MAKE) config-check
	@echo "$(GREEN)Production readiness check completed$(NC)"

prod-deploy: deploy-production ## Alias for deploy-production

# Maintenance
maintenance: ## Run maintenance tasks
	@echo "$(GREEN)Running maintenance tasks...$(NC)"
	$(MAKE) clean
	$(MAKE) update-deps
	$(MAKE) backup
	@echo "$(GREEN)Maintenance completed$(NC)"

# Emergency procedures
emergency-rollback: ## Emergency rollback (no confirmation)
	@echo "$(RED)EMERGENCY ROLLBACK IN PROGRESS...$(NC)"
	$(PYTHON) scripts/deployment_manager.py --environment $(ENVIRONMENT) --action rollback

emergency-stop: ## Emergency stop (disable rate limiting)
	@echo "$(RED)EMERGENCY STOP - DISABLING RATE LIMITING...$(NC)"
	@echo "$(YELLOW)This will remove all rate limiting configurations$(NC)"
	kubectl delete configmap ratelimit-config -n istio-system --ignore-not-found=true