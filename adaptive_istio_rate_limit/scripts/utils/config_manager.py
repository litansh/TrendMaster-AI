#!/usr/bin/env python3
"""
TrendMaster-AI Configuration Manager
Environment-Aware Configuration Loading and Management

This module provides centralized configuration management with:
- Environment variable integration
- Multi-environment support
- Configuration validation
- Dynamic configuration loading
- Production-ready defaults
"""

import os
import sys
import yaml
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass
from enum import Enum


class Environment(Enum):
    """Supported environments"""
    LOCAL = "local"
    TESTING = "testing"
    PRODUCTION = "production"


@dataclass
class EnvironmentInfo:
    """Environment information structure"""
    name: str
    deployment_mode: str
    trickster_env: str
    prometheus_url: str
    kubernetes_context: str
    dry_run: bool
    partners: List[str]
    apis: List[str]


class ConfigManager:
    """
    Production-ready configuration manager with environment awareness
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager"""
        self.logger = logging.getLogger(__name__)
        
        # Determine config file paths
        if config_path is None:
            # Default to config/config.yaml relative to project root
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "config.yaml"
        
        self.config_path = Path(config_path)
        self.local_config_path = self.config_path.parent.parent / ".local.config.yaml"
        self.raw_config = {}
        self.local_config = {}
        self.processed_config = {}
        
        # Load and process configuration
        self._load_config()
        self._load_local_config()
        self._process_environment_config()
        
        self.logger.info(f"Configuration loaded from: {self.config_path}")
        if self.local_config:
            self.logger.info(f"Local configuration loaded from: {self.local_config_path}")
        self.logger.info(f"Current environment: {self.get_current_environment()}")
    
    def _load_config(self) -> None:
        """Load configuration from YAML file"""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
            with open(self.config_path, 'r') as f:
                self.raw_config = yaml.safe_load(f)
            
            self.logger.debug(f"Raw configuration loaded: {len(self.raw_config)} sections")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _load_local_config(self) -> None:
        """Load local configuration from hidden file"""
        try:
            if self.local_config_path.exists():
                with open(self.local_config_path, 'r') as f:
                    self.local_config = yaml.safe_load(f) or {}
                self.logger.debug(f"Local configuration loaded from: {self.local_config_path}")
            else:
                self.logger.debug(f"Local configuration file not found: {self.local_config_path}")
                self.local_config = {}
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing local YAML configuration: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to load local configuration: {e}")
            raise
    
    def _process_environment_config(self) -> None:
        """Process configuration with environment variable overrides"""
        # Start with raw config
        self.processed_config = self.raw_config.copy()
        
        # Get current environment from environment variables
        current_env = self._get_environment_from_env_vars()
        deployment_mode = self._determine_deployment_mode(current_env)
        
        # Override deployment configuration
        if 'DEPLOYMENT' not in self.processed_config:
            self.processed_config['DEPLOYMENT'] = {}
        
        self.processed_config['DEPLOYMENT']['MODE'] = deployment_mode
        self.processed_config['DEPLOYMENT']['ENVIRONMENT'] = current_env
        
        # Apply environment-specific overrides
        self._apply_environment_overrides(current_env, deployment_mode)
        
        # Apply environment variable overrides
        self._apply_env_var_overrides()
        
        # Apply deployment-specific overrides
        self._apply_deployment_overrides(deployment_mode)
        
        self.logger.info(f"Configuration processed for environment: {current_env}, mode: {deployment_mode}")
    
    def _get_environment_from_env_vars(self) -> str:
        """Get current environment from environment variables"""
        env_vars_to_check = [
            'ENVIRONMENT',
            'ENV',
            'DEPLOYMENT_ENV',
            'KALTURA_ENV',
            'TRICKSTER_ENV',
            'APP_ENV',
            'NODE_ENV'
        ]
        
        for env_var in env_vars_to_check:
            env_value = os.environ.get(env_var)
            if env_value:
                self.logger.info(f"Environment detected from {env_var}: {env_value}")
                return env_value.lower()
        
        # Default fallback
        default_env = 'orp2'
        self.logger.warning(f"No environment variable found, defaulting to: {default_env}")
        return default_env
    
    def _determine_deployment_mode(self, environment: str) -> str:
        """Determine deployment mode based on environment"""
        # Check for explicit deployment mode in environment variables
        deployment_mode = os.environ.get('DEPLOYMENT_MODE')
        if deployment_mode:
            return deployment_mode.lower()
        
        # Map environment to deployment mode
        env_to_mode_mapping = {
            'orp2': 'local',
            'local': 'local',
            'development': 'local',
            'dev': 'local',
            'testing': 'testing',
            'test': 'testing',
            'staging': 'testing',
            'production': 'production',
            'prod': 'production'
        }
        
        return env_to_mode_mapping.get(environment, 'local')
    
    def _apply_environment_overrides(self, environment: str, deployment_mode: str) -> None:
        """Apply environment-specific configuration overrides"""
        environments_config = self.processed_config.get('ENVIRONMENTS', {})
        
        if deployment_mode in environments_config:
            env_specific_config = environments_config[deployment_mode]
            
            # Update common configuration with environment-specific values
            common_config = self.processed_config.get('COMMON', {})
            
            # Override ENV setting
            common_config['ENV'] = environment
            
            self.logger.debug(f"Applied environment overrides for {deployment_mode}")
    
    def _apply_env_var_overrides(self) -> None:
        """Apply environment variable overrides to configuration"""
        deployment_mode = self.processed_config['DEPLOYMENT']['MODE']
        
        # Ensure environments section exists
        if 'ENVIRONMENTS' not in self.processed_config:
            self.processed_config['ENVIRONMENTS'] = {}
        if deployment_mode not in self.processed_config['ENVIRONMENTS']:
            self.processed_config['ENVIRONMENTS'][deployment_mode] = {}
        
        env_config = self.processed_config['ENVIRONMENTS'][deployment_mode]
        
        # Prometheus URL override
        prometheus_url = os.environ.get('PROMETHEUS_URL')
        if prometheus_url:
            env_config['PROMETHEUS_URL'] = prometheus_url
            self.logger.info(f"Prometheus URL overridden from environment variable: {prometheus_url}")
        
        # Trickster environment override
        trickster_env = os.environ.get('TRICKSTER_ENV')
        if trickster_env:
            env_config['TRICKSTER_ENV'] = trickster_env
            self.logger.info(f"Trickster environment overridden from environment variable: {trickster_env}")
        
        # Kubernetes context override
        k8s_context = os.environ.get('KUBERNETES_CONTEXT')
        if k8s_context:
            env_config['KUBERNETES_CONTEXT'] = k8s_context
            self.logger.info(f"Kubernetes context overridden from environment variable: {k8s_context}")
        
        # Kubernetes namespace override
        k8s_namespace = os.environ.get('KUBERNETES_NAMESPACE', os.environ.get('CONFIGMAP_NAMESPACE'))
        if k8s_namespace:
            env_config['CONFIGMAP_NAMESPACE'] = k8s_namespace
            self.logger.info(f"Kubernetes namespace overridden from environment variable: {k8s_namespace}")
        
        # Log level override
        log_level = os.environ.get('LOG_LEVEL')
        if log_level:
            if 'COMMON' not in self.processed_config:
                self.processed_config['COMMON'] = {}
            self.processed_config['COMMON']['LOG_LEVEL'] = log_level.upper()
            self.logger.info(f"Log level overridden from environment variable: {log_level}")
        
        # Dry run override
        dry_run = os.environ.get('DRY_RUN')
        if dry_run:
            env_config['DRY_RUN'] = dry_run.lower() in ['true', '1', 'yes']
            self.logger.info(f"Dry run overridden from environment variable: {dry_run}")
        
        # Production-specific environment variables
        if deployment_mode == 'production':
            # Prometheus token for production
            prometheus_token = os.environ.get('PROMETHEUS_TOKEN')
            if prometheus_token:
                env_config['PROMETHEUS_TOKEN'] = prometheus_token
                self.logger.info("Prometheus token loaded from environment variable")
            
            # EKS cluster name
            eks_cluster = os.environ.get('EKS_CLUSTER_NAME', os.environ.get('CLUSTER_NAME'))
            if eks_cluster:
                env_config['EKS_CLUSTER_NAME'] = eks_cluster
                self.logger.info(f"EKS cluster name: {eks_cluster}")
            
            # AWS region
            aws_region = os.environ.get('AWS_REGION', os.environ.get('AWS_DEFAULT_REGION'))
            if aws_region:
                env_config['AWS_REGION'] = aws_region
                self.logger.info(f"AWS region: {aws_region}")
    
    def _apply_deployment_overrides(self, deployment_mode: str) -> None:
        """Apply deployment-specific overrides"""
        overrides = self.processed_config.get('DEPLOYMENT_OVERRIDES', {}).get(deployment_mode, {})
        
        if overrides:
            self.logger.info(f"Applying deployment overrides for {deployment_mode}")
            
            # Apply common overrides
            common_overrides = overrides.get('COMMON', {})
            if common_overrides:
                common_config = self.processed_config.get('COMMON', {})
                self._deep_merge_dict(common_config, common_overrides)
                self.processed_config['COMMON'] = common_config
    
    def _deep_merge_dict(self, base_dict: Dict, override_dict: Dict) -> None:
        """Deep merge override dictionary into base dictionary"""
        for key, value in override_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_merge_dict(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def get_config(self) -> Dict[str, Any]:
        """Get processed configuration"""
        return self.processed_config
    
    def get_current_environment(self) -> str:
        """Get current environment name"""
        return self.processed_config.get('DEPLOYMENT', {}).get('ENVIRONMENT', 'unknown')
    
    def get_deployment_mode(self) -> str:
        """Get current deployment mode"""
        return self.processed_config.get('DEPLOYMENT', {}).get('MODE', 'local')
    
    def get_environment_config(self, deployment_mode: Optional[str] = None) -> Dict[str, Any]:
        """Get environment-specific configuration"""
        if deployment_mode is None:
            deployment_mode = self.get_deployment_mode()
        
        return self.processed_config.get('ENVIRONMENTS', {}).get(deployment_mode, {})
    
    def get_partner_config(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """Get partner configuration for specified environment"""
        if environment is None:
            environment = self.get_current_environment()
        
        deployment_mode = self.get_deployment_mode()
        
        # For production/testing environments, get partners/APIs from existing ConfigMap
        if deployment_mode in ['production', 'testing']:
            return self._get_configmap_partner_config(deployment_mode)
        else:
            # For local development, use config.yaml defaults (orp2)
            return self._get_local_partner_config()
    
    def _get_configmap_partner_config(self, deployment_mode: str) -> Dict[str, Any]:
        """Get partner configuration from existing Istio rate limit ConfigMap"""
        config = {
            'partners': [],
            'apis': [],
            'source': f'{deployment_mode}_configmap'
        }
        
        # In production/testing environments, partners and APIs come from existing ConfigMap
        # This will be populated by the ConfigMapManager when it reads the existing ConfigMap
        self.logger.info(f"Partners/APIs will be loaded from existing Istio ConfigMap in {deployment_mode} environment")
        
        # Note: The actual partners/APIs will be discovered at runtime by reading the existing ConfigMap
        # This is handled by the ConfigMapManager.fetch_current_configmap() method
        
        return config
    
    def _get_local_partner_config(self) -> Dict[str, Any]:
        """Get partner configuration for local development from local config file"""
        # First try to get from local config file (hidden file with sensitive data)
        if self.local_config and 'PARTNER_CONFIGS' in self.local_config:
            local_partner_configs = self.local_config['PARTNER_CONFIGS']
            orp2_config = local_partner_configs.get('orp2', {})
            if orp2_config:
                orp2_config['source'] = 'local_config_yaml'
                self.logger.info(f"Local development using .local.config.yaml: {len(orp2_config.get('partners', []))} partners, {len(orp2_config.get('apis', []))} APIs")
                return orp2_config
        
        # Fallback to main config.yaml (sanitized version)
        partner_configs = self.processed_config.get('PARTNER_CONFIGS', {})
        orp2_config = partner_configs.get('orp2', {})
        orp2_config['source'] = 'config_yaml'
        
        self.logger.info(f"Local development using orp2 config.yaml: {len(orp2_config.get('partners', []))} partners, {len(orp2_config.get('apis', []))} APIs")
        
        return orp2_config
    
    def get_environment_info(self) -> EnvironmentInfo:
        """Get comprehensive environment information"""
        current_env = self.get_current_environment()
        deployment_mode = self.get_deployment_mode()
        env_config = self.get_environment_config(deployment_mode)
        partner_config = self.get_partner_config(current_env)
        
        return EnvironmentInfo(
            name=current_env,
            deployment_mode=deployment_mode,
            trickster_env=env_config.get('TRICKSTER_ENV', 'unknown'),
            prometheus_url=env_config.get('PROMETHEUS_URL', ''),
            kubernetes_context=env_config.get('KUBERNETES_CONTEXT', ''),
            dry_run=env_config.get('DRY_RUN', True),
            partners=partner_config.get('partners', []),
            apis=partner_config.get('apis', [])
        )
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate current configuration and return validation results"""
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'info': []
        }
        
        try:
            # Check required sections
            required_sections = ['DEPLOYMENT', 'ENVIRONMENTS', 'COMMON', 'PARTNER_CONFIGS']
            for section in required_sections:
                if section not in self.processed_config:
                    validation_results['errors'].append(f"Missing required section: {section}")
                    validation_results['valid'] = False
            
            # Check deployment configuration
            deployment_config = self.processed_config.get('DEPLOYMENT', {})
            if 'MODE' not in deployment_config:
                validation_results['errors'].append("Missing DEPLOYMENT.MODE")
                validation_results['valid'] = False
            
            # Check environment-specific configuration
            deployment_mode = deployment_config.get('MODE')
            if deployment_mode:
                env_config = self.get_environment_config(deployment_mode)
                if not env_config:
                    validation_results['warnings'].append(f"No configuration found for deployment mode: {deployment_mode}")
                else:
                    # Check required environment settings
                    required_env_settings = ['PROMETHEUS_URL']
                    for setting in required_env_settings:
                        if setting not in env_config:
                            validation_results['warnings'].append(f"Missing {setting} in {deployment_mode} environment config")
            
            # Check partner configuration
            current_env = self.get_current_environment()
            partner_config = self.get_partner_config(current_env)
            if not partner_config:
                validation_results['warnings'].append(f"No partner configuration found for environment: {current_env}")
            else:
                if not partner_config.get('partners'):
                    validation_results['warnings'].append("No partners configured")
                if not partner_config.get('apis'):
                    validation_results['warnings'].append("No APIs configured")
            
            # Add info about current configuration
            validation_results['info'].append(f"Environment: {current_env}")
            validation_results['info'].append(f"Deployment Mode: {deployment_mode}")
            validation_results['info'].append(f"Partners: {len(partner_config.get('partners', []))}")
            validation_results['info'].append(f"APIs: {len(partner_config.get('apis', []))}")
            
        except Exception as e:
            validation_results['valid'] = False
            validation_results['errors'].append(f"Configuration validation error: {e}")
        
        return validation_results
    
    def reload_config(self) -> None:
        """Reload configuration from file"""
        self.logger.info("Reloading configuration...")
        self._load_config()
        self._load_local_config()
        self._process_environment_config()
        self.logger.info("Configuration reloaded successfully")
    
    def get_prometheus_url(self) -> str:
        """Get Prometheus URL for current environment"""
        env_config = self.get_environment_config()
        return env_config.get('PROMETHEUS_URL', '')
    
    def get_kubernetes_config(self) -> Dict[str, str]:
        """Get Kubernetes configuration for current environment"""
        env_config = self.get_environment_config()
        return {
            'config_path': env_config.get('KUBERNETES_CONFIG', '~/.kube/config'),
            'context': env_config.get('KUBERNETES_CONTEXT', ''),
            'namespace': env_config.get('CONFIGMAP_NAMESPACE', 'default')
        }
    
    def is_dry_run(self) -> bool:
        """Check if dry run mode is enabled"""
        env_config = self.get_environment_config()
        return env_config.get('DRY_RUN', True)
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.get_deployment_mode() == 'production'
    
    def get_rate_calculation_config(self) -> Dict[str, Any]:
        """Get rate calculation configuration"""
        return self.processed_config.get('COMMON', {}).get('RATE_CALCULATION', {})
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration"""
        return self.processed_config.get('COMMON', {}).get('MONITORING', {})


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """Get global configuration manager instance"""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    
    return _config_manager


def get_config() -> Dict[str, Any]:
    """Get processed configuration"""
    return get_config_manager().get_config()


def get_current_environment() -> str:
    """Get current environment name"""
    return get_config_manager().get_current_environment()


def get_environment_info() -> EnvironmentInfo:
    """Get comprehensive environment information"""
    return get_config_manager().get_environment_info()


if __name__ == "__main__":
    # CLI for configuration validation and testing
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='TrendMaster-AI Configuration Manager')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--validate', action='store_true', help='Validate configuration')
    parser.add_argument('--show-env', action='store_true', help='Show environment information')
    parser.add_argument('--show-config', action='store_true', help='Show processed configuration')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    try:
        config_manager = ConfigManager(args.config)
        
        if args.validate:
            validation = config_manager.validate_configuration()
            print("Configuration Validation Results:")
            print(json.dumps(validation, indent=2))
        
        if args.show_env:
            env_info = config_manager.get_environment_info()
            print("Environment Information:")
            print(f"  Name: {env_info.name}")
            print(f"  Deployment Mode: {env_info.deployment_mode}")
            print(f"  Trickster Environment: {env_info.trickster_env}")
            print(f"  Prometheus URL: {env_info.prometheus_url}")
            print(f"  Kubernetes Context: {env_info.kubernetes_context}")
            print(f"  Dry Run: {env_info.dry_run}")
            print(f"  Partners: {len(env_info.partners)} ({', '.join(env_info.partners)})")
            print(f"  APIs: {len(env_info.apis)}")
        
        if args.show_config:
            config = config_manager.get_config()
            print("Processed Configuration:")
            print(json.dumps(config, indent=2, default=str))
        
        if not any([args.validate, args.show_env, args.show_config]):
            print("Configuration loaded successfully!")
            print(f"Environment: {config_manager.get_current_environment()}")
            print(f"Deployment Mode: {config_manager.get_deployment_mode()}")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)