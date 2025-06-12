import yaml
import os
import logging
from typing import Dict, Any

class ConfigManager:
    """
    Configuration manager for handling environment-specific configurations
    """
    
    def __init__(self, config_path: str = 'config/config.yaml'):
        self.config_path = config_path
        self.config = self.load_configuration()
        self.deployment_mode = self.config['DEPLOYMENT']['MODE']
        self.environment_config = self.merge_environment_config()
        
        # Setup logging
        self.setup_logging()
    
    def load_configuration(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as file:
            config = yaml.safe_load(file)
        
        # Validate required sections
        required_sections = ['DEPLOYMENT', 'ENVIRONMENTS', 'COMMON']
        for section in required_sections:
            if section not in config:
                raise KeyError(f"Required configuration section missing: {section}")
        
        return config
    
    def merge_environment_config(self) -> Dict[str, Any]:
        """Merge common config with environment-specific config"""
        mode = self.deployment_mode
        
        if mode not in self.config['ENVIRONMENTS']:
            raise ValueError(f"Unknown deployment mode: {mode}")
        
        # Start with common configuration
        merged_config = self.config['COMMON'].copy()
        
        # Override with environment-specific settings
        env_config = self.config['ENVIRONMENTS'][mode]
        merged_config.update(env_config)
        
        # Add deployment metadata
        merged_config['DEPLOYMENT_MODE'] = mode
        merged_config['ENVIRONMENT'] = self.config['DEPLOYMENT'].get('ENVIRONMENT', mode)
        
        return merged_config
    
    def setup_logging(self):
        """Setup logging based on configuration"""
        log_level = self.environment_config.get('LOG_LEVEL', 'INFO')
        verbose = self.environment_config.get('VERBOSE_LOGGING', False)
        
        if verbose:
            log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        else:
            log_format = '%(asctime)s - %(levelname)s - %(message)s'
        
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format=log_format,
            force=True  # Override any existing logging configuration
        )
    
    def get_config(self) -> Dict[str, Any]:
        """Get the merged configuration"""
        return self.environment_config
    
    def is_local_mode(self) -> bool:
        """Check if running in local mode"""
        return self.deployment_mode == 'local'
    
    def is_testing_mode(self) -> bool:
        """Check if running in testing mode"""
        return self.deployment_mode == 'testing'
    
    def is_production_mode(self) -> bool:
        """Check if running in production mode"""
        return self.deployment_mode == 'production'
    
    def should_preview_only(self) -> bool:
        """Check if system should run in preview-only mode"""
        return self.environment_config.get('PREVIEW_ONLY', True)
    
    def should_update_configmap(self) -> bool:
        """Check if system should update ConfigMaps"""
        return (
            not self.environment_config.get('DRY_RUN', True) and
            self.environment_config.get('ENABLE_UPDATES', False)
        )
    
    def get_prometheus_url(self) -> str:
        """Get Prometheus URL for current environment"""
        return self.environment_config.get('PROMETHEUS_URL')
    
    def get_kubernetes_config(self) -> Dict[str, str]:
        """Get Kubernetes configuration"""
        return {
            'config_file': self.environment_config.get('KUBERNETES_CONFIG'),
            'context': self.environment_config.get('KUBERNETES_CONTEXT'),
            'namespace': self.environment_config.get('CONFIGMAP_NAMESPACE', 'istio-system')
        }
    
    def get_rate_calculation_config(self) -> Dict[str, Any]:
        """Get rate calculation configuration"""
        return self.environment_config.get('RATE_CALCULATION', {})
    
    def get_prophet_config(self) -> Dict[str, Any]:
        """Get Prophet configuration"""
        return self.environment_config.get('PROPHET_CONFIG', {})
    
    def get_anomaly_config(self) -> Dict[str, Any]:
        """Get anomaly detection configuration"""
        return self.environment_config.get('ANOMALY_CONFIG', {})
    
    def get_prime_time_config(self) -> Dict[str, Any]:
        """Get prime time detection configuration"""
        return self.environment_config.get('PRIME_TIME_CONFIG', {})
    
    def get_exclusions_config(self) -> Dict[str, Any]:
        """Get exclusions configuration"""
        return self.environment_config.get('EXCLUSIONS', {})
    
    def log_configuration_summary(self):
        """Log configuration summary"""
        logger = logging.getLogger(__name__)
        logger.info(f"=== Configuration Summary ===")
        logger.info(f"Deployment Mode: {self.deployment_mode.upper()}")
        logger.info(f"Environment: {self.environment_config.get('ENVIRONMENT')}")
        logger.info(f"Prometheus URL: {self.get_prometheus_url()}")
        logger.info(f"Kubernetes Context: {self.get_kubernetes_config()['context']}")
        logger.info(f"Preview Only: {self.should_preview_only()}")
        logger.info(f"ConfigMap Updates: {self.should_update_configmap()}")
        logger.info(f"Use Mock Data: {self.environment_config.get('USE_MOCK_DATA', False)}")
        logger.info(f"Prophet Enabled: {self.get_prophet_config().get('enabled', False)}")
        logger.info(f"Days to Inspect: {self.environment_config.get('DAYS_TO_INSPECT', 7)}")
        logger.info(f"================================")