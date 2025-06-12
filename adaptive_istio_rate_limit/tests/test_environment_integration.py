#!/usr/bin/env python3
"""
TrendMaster-AI Environment Integration Tests
Comprehensive tests for environment-aware functionality
"""

import os
import sys
import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils.config_manager import ConfigManager
from scripts.core.enhanced_rate_calculator import EnhancedRateCalculator
from scripts.main import AdaptiveRateLimiter


class TestEnvironmentIntegration:
    """Test environment-aware functionality integration"""
    
    def setup_method(self):
        """Setup for each test"""
        # Create temporary config for testing
        self.temp_config = {
            'DEPLOYMENT': {
                'MODE': 'local',
                'ENVIRONMENT': 'orp2'
            },
            'ENVIRONMENTS': {
                'local': {
                    'PROMETHEUS_URL': 'http://localhost:9090',
                    'KUBERNETES_CONTEXT': 'minikube',
                    'DRY_RUN': True,
                    'USE_MOCK_DATA': True,
                    'ENV_NAME': 'orp2',
                    'TRICKSTER_ENV': 'orp2'
                },
                'testing': {
                    'PROMETHEUS_URL': 'https://trickster.orp2.ott.kaltura.com',
                    'KUBERNETES_CONTEXT': 'eks-testing',
                    'DRY_RUN': True,
                    'ENV_NAME': 'orp2',
                    'TRICKSTER_ENV': 'orp2'
                },
                'production': {
                    'PROMETHEUS_URL': 'https://trickster.production.ott.kaltura.com',
                    'KUBERNETES_CONTEXT': 'eks-production',
                    'DRY_RUN': False,
                    'ENV_NAME': 'production',
                    'TRICKSTER_ENV': 'production'
                }
            },
            'PARTNER_CONFIGS': {
                'orp2': {
                    'partners': ['313', '439', '3079'],
                    'apis': [
                        '/api_v3/service/asset/action/getplaybackcontext',
                        '/api_v3/service/multirequest'
                    ],
                    'partner_multipliers': {
                        '313': 1.0,
                        '439': 0.9,
                        '3079': 1.0
                    }
                },
                'production': {
                    'partners': ['101', '201', '301'],
                    'apis': [
                        '/api_v3/service/asset/action/getplaybackcontext',
                        '/api_v3/service/multirequest',
                        '/api_v3/service/session/action/start'
                    ],
                    'partner_multipliers': {
                        '101': 1.2,
                        '201': 1.0,
                        '301': 0.9
                    }
                }
            },
            'COMMON': {
                'LOG_LEVEL': 'DEBUG',
                'RATE_CALCULATION': {
                    'formula_version': 'v3',
                    'peak_multiplier': 2.5,
                    'cache_adjustment_factor': 1.2,
                    'safety_margin': 1.2,
                    'min_rate_limit': 100,
                    'max_rate_limit': 50000
                },
                'PATH_MULTIPLIERS': {
                    '/api_v3/service/multirequest': 1.5,
                    '/api_v3/service/asset/action/getplaybackcontext': 1.1
                },
                'EXCLUSIONS': {
                    'global_partners': ['test_partner'],
                    'global_paths': ['/health', '/status']
                }
            },
            'DEPLOYMENT_OVERRIDES': {
                'local': {
                    'COMMON': {
                        'LOG_LEVEL': 'DEBUG',
                        'RATE_CALCULATION': {
                            'safety_margin': 1.5
                        }
                    }
                }
            }
        }
    
    def create_temp_config_file(self, config_data):
        """Create temporary configuration file"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        yaml.dump(config_data, temp_file, default_flow_style=False)
        temp_file.close()
        return temp_file.name
    
    def test_config_manager_environment_detection(self):
        """Test configuration manager environment detection"""
        config_file = self.create_temp_config_file(self.temp_config)
        
        try:
            # Test with environment variable
            with patch.dict(os.environ, {'ENVIRONMENT': 'orp2'}):
                config_manager = ConfigManager(config_file)
                assert config_manager.get_current_environment() == 'orp2'
                assert config_manager.get_deployment_mode() == 'local'
            
            # Test with different environment variable
            with patch.dict(os.environ, {'KALTURA_ENV': 'production'}):
                config_manager = ConfigManager(config_file)
                assert config_manager.get_current_environment() == 'production'
                assert config_manager.get_deployment_mode() == 'production'
        
        finally:
            os.unlink(config_file)
    
    def test_config_manager_partner_config_selection(self):
        """Test partner configuration selection based on environment"""
        config_file = self.create_temp_config_file(self.temp_config)
        
        try:
            # Test orp2 environment
            with patch.dict(os.environ, {'ENVIRONMENT': 'orp2'}):
                config_manager = ConfigManager(config_file)
                partner_config = config_manager.get_partner_config()
                
                assert '313' in partner_config['partners']
                assert '439' in partner_config['partners']
                assert partner_config['partner_multipliers']['439'] == 0.9
            
            # Test production environment
            with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
                config_manager = ConfigManager(config_file)
                partner_config = config_manager.get_partner_config()
                
                assert '101' in partner_config['partners']
                assert '201' in partner_config['partners']
                assert partner_config['partner_multipliers']['101'] == 1.2
        
        finally:
            os.unlink(config_file)
    
    def test_config_manager_deployment_overrides(self):
        """Test deployment-specific configuration overrides"""
        config_file = self.create_temp_config_file(self.temp_config)
        
        try:
            with patch.dict(os.environ, {'DEPLOYMENT_MODE': 'local'}):
                config_manager = ConfigManager(config_file)
                config = config_manager.get_config()
                
                # Check that local overrides are applied
                rate_config = config['COMMON']['RATE_CALCULATION']
                assert rate_config['safety_margin'] == 1.5  # Overridden from 1.2
                assert config['COMMON']['LOG_LEVEL'] == 'DEBUG'  # Overridden
        
        finally:
            os.unlink(config_file)
    
    def test_enhanced_rate_calculator_environment_awareness(self):
        """Test enhanced rate calculator environment awareness"""
        config_file = self.create_temp_config_file(self.temp_config)
        
        try:
            with patch.dict(os.environ, {'ENVIRONMENT': 'orp2'}):
                config_manager = ConfigManager(config_file)
                config = config_manager.get_config()
                
                rate_calculator = EnhancedRateCalculator(config, None)
                
                # Test environment detection
                assert rate_calculator.current_environment == 'orp2'
                assert rate_calculator.deployment_mode == 'local'
                
                # Test partner configuration loading
                partner_config = rate_calculator.partner_config
                assert '313' in partner_config['partners']
                assert partner_config['partner_multipliers']['313'] == 1.0
                
                # Test partner/path validation
                validation = rate_calculator.validate_partner_path('313', '/api_v3/service/multirequest')
                assert validation['valid'] == True
                assert validation['partner_supported'] == True
                assert validation['path_supported'] == True
                
                # Test invalid partner
                validation = rate_calculator.validate_partner_path('999', '/api_v3/service/multirequest')
                assert validation['valid'] == False
                assert validation['partner_supported'] == False
        
        finally:
            os.unlink(config_file)
    
    def test_enhanced_rate_calculator_different_environments(self):
        """Test rate calculator behavior in different environments"""
        config_file = self.create_temp_config_file(self.temp_config)
        
        try:
            # Test orp2 environment
            with patch.dict(os.environ, {'ENVIRONMENT': 'orp2'}):
                config_manager = ConfigManager(config_file)
                config = config_manager.get_config()
                rate_calculator = EnhancedRateCalculator(config, None)
                
                # Validate orp2 partner
                validation = rate_calculator.validate_partner_path('313', '/api_v3/service/multirequest')
                assert validation['valid'] == True
                
                # Production partner should not be valid in orp2
                validation = rate_calculator.validate_partner_path('101', '/api_v3/service/multirequest')
                assert validation['valid'] == False
            
            # Test production environment
            with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
                config_manager = ConfigManager(config_file)
                config = config_manager.get_config()
                rate_calculator = EnhancedRateCalculator(config, None)
                
                # Validate production partner
                validation = rate_calculator.validate_partner_path('101', '/api_v3/service/multirequest')
                assert validation['valid'] == True
                
                # orp2 partner should not be valid in production
                validation = rate_calculator.validate_partner_path('313', '/api_v3/service/multirequest')
                assert validation['valid'] == False
        
        finally:
            os.unlink(config_file)
    
    @patch('scripts.main.DataFetcher')
    @patch('scripts.main.ProphetAnalyzer')
    @patch('scripts.main.PrimeTimeDetector')
    @patch('scripts.main.CacheMetricsAnalyzer')
    @patch('scripts.main.ConfigMapManager')
    def test_adaptive_rate_limiter_integration(self, mock_configmap, mock_cache, 
                                             mock_prime, mock_prophet, mock_data):
        """Test full adaptive rate limiter integration"""
        config_file = self.create_temp_config_file(self.temp_config)
        
        try:
            # Mock the components
            mock_data_instance = MagicMock()
            mock_data.return_value = mock_data_instance
            mock_data_instance.generate_mock_data.return_value = (
                MagicMock(),  # clean_metrics
                MagicMock()   # prime_time_data
            )
            
            mock_prophet_instance = MagicMock()
            mock_prophet.return_value = mock_prophet_instance
            mock_prophet_instance.analyze_traffic_patterns.return_value = {
                'trend_info': {'direction': 'stable', 'slope': 0}
            }
            
            mock_prime_instance = MagicMock()
            mock_prime.return_value = mock_prime_instance
            mock_prime_instance.detect_prime_time_periods.return_value = []
            
            mock_cache_instance = MagicMock()
            mock_cache.return_value = mock_cache_instance
            mock_cache_instance.get_cache_metrics.return_value = None
            
            mock_configmap_instance = MagicMock()
            mock_configmap.return_value = mock_configmap_instance
            mock_configmap_instance.create_rate_limit_configmap.return_value = {
                'apiVersion': 'v1',
                'kind': 'ConfigMap',
                'metadata': {'name': 'test-config'}
            }
            
            with patch.dict(os.environ, {'ENVIRONMENT': 'orp2'}):
                # Initialize adaptive rate limiter
                rate_limiter = AdaptiveRateLimiter(config_file)
                
                # Test environment information
                env_info = rate_limiter.env_info
                assert env_info.name == 'orp2'
                assert env_info.deployment_mode == 'local'
                assert '313' in env_info.partners
                
                # Test validation
                validation = rate_limiter.validate_environment()
                assert validation['valid'] == True
                
                # Test run with specific partners
                results = rate_limiter.run(partners=['313'], apis=['/api_v3/service/multirequest'])
                
                # Verify results structure
                assert 'environment' in results
                assert results['environment'] == 'orp2'
                assert 'deployment_mode' in results
                assert results['deployment_mode'] == 'local'
                
        finally:
            os.unlink(config_file)
    
    def test_environment_variable_overrides(self):
        """Test environment variable overrides"""
        config_file = self.create_temp_config_file(self.temp_config)
        
        try:
            with patch.dict(os.environ, {
                'ENVIRONMENT': 'orp2',
                'LOG_LEVEL': 'ERROR',
                'DRY_RUN': 'false',
                'PROMETHEUS_URL': 'http://custom-prometheus:9090'
            }):
                config_manager = ConfigManager(config_file)
                config = config_manager.get_config()
                
                # Check environment variable overrides
                assert config['COMMON']['LOG_LEVEL'] == 'ERROR'
                
                # Check Prometheus URL override
                env_config = config_manager.get_environment_config()
                assert env_config.get('PROMETHEUS_URL') == 'http://custom-prometheus:9090'
                
                # Check dry run override
                assert env_config.get('DRY_RUN') == False
        
        finally:
            os.unlink(config_file)
    
    def test_configuration_validation(self):
        """Test configuration validation"""
        config_file = self.create_temp_config_file(self.temp_config)
        
        try:
            config_manager = ConfigManager(config_file)
            validation = config_manager.validate_configuration()
            
            assert validation['valid'] == True
            assert len(validation['errors']) == 0
            assert 'Environment: orp2' in validation['info']
            
        finally:
            os.unlink(config_file)
    
    def test_invalid_configuration(self):
        """Test handling of invalid configuration"""
        # Create invalid config (missing required sections)
        invalid_config = {
            'DEPLOYMENT': {
                'MODE': 'local'
            }
            # Missing ENVIRONMENTS, COMMON, PARTNER_CONFIGS
        }
        
        config_file = self.create_temp_config_file(invalid_config)
        
        try:
            config_manager = ConfigManager(config_file)
            validation = config_manager.validate_configuration()
            
            assert validation['valid'] == False
            assert len(validation['errors']) > 0
            assert any('Missing required section' in error for error in validation['errors'])
            
        finally:
            os.unlink(config_file)
    
    def test_environment_info_structure(self):
        """Test environment info structure"""
        config_file = self.create_temp_config_file(self.temp_config)
        
        try:
            with patch.dict(os.environ, {'ENVIRONMENT': 'orp2'}):
                config_manager = ConfigManager(config_file)
                env_info = config_manager.get_environment_info()
                
                # Check all required fields
                assert hasattr(env_info, 'name')
                assert hasattr(env_info, 'deployment_mode')
                assert hasattr(env_info, 'trickster_env')
                assert hasattr(env_info, 'prometheus_url')
                assert hasattr(env_info, 'kubernetes_context')
                assert hasattr(env_info, 'dry_run')
                assert hasattr(env_info, 'partners')
                assert hasattr(env_info, 'apis')
                
                # Check values
                assert env_info.name == 'orp2'
                assert env_info.deployment_mode == 'local'
                assert env_info.trickster_env == 'orp2'
                assert env_info.dry_run == True
                assert isinstance(env_info.partners, list)
                assert isinstance(env_info.apis, list)
                
        finally:
            os.unlink(config_file)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])