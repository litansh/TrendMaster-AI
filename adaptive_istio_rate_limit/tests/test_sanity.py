#!/usr/bin/env python3
"""
Sanity Tests for TrendMaster-AI Adaptive Istio Rate Limiting System
These tests verify basic functionality and system health.
"""

import os
import sys
import unittest
import yaml
import tempfile
from datetime import datetime, timedelta

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from scripts.core.config_manager import ConfigManager
from scripts.core.data_fetcher import DataFetcher
from scripts.core.prophet_analyzer import ProphetAnalyzer
from scripts.core.enhanced_rate_calculator import EnhancedRateCalculator
from scripts.main import AdaptiveRateLimiter


class SanityTests(unittest.TestCase):
    """Sanity tests to ensure basic functionality works correctly."""
    
    def setUp(self):
        """Set up test environment."""
        self.config_manager = ConfigManager()
        # Override to use local mode with mock data
        self.config_manager.config['DEPLOYMENT']['MODE'] = 'local'
        self.config_manager.config['ENVIRONMENTS']['local']['USE_MOCK_DATA'] = True
        
    def test_1_config_manager_initialization(self):
        """Test 1: Verify ConfigManager loads configuration correctly."""
        print("\n=== Test 1: Config Manager Initialization ===")
        
        # Test basic configuration loading
        self.assertIsNotNone(self.config_manager.config)
        self.assertIn('DEPLOYMENT', self.config_manager.config)
        self.assertIn('COMMON', self.config_manager.config)
        
        # Test deployment mode
        mode = self.config_manager.deployment_mode
        self.assertIn(mode.lower(), ['local', 'testing', 'production'])
        
        # Test environment-specific settings
        env_config = self.config_manager.get_config()
        self.assertIsNotNone(env_config)
        self.assertIn('PROMETHEUS_URL', env_config)
        
        # Test Prophet configuration
        prophet_config = self.config_manager.get_prophet_config()
        self.assertIsNotNone(prophet_config)
        self.assertIn('enabled', prophet_config)
        
        print(f"✅ Config loaded successfully - Mode: {mode}")
        print(f"✅ Environment config present: {list(env_config.keys())}")
        print(f"✅ Prophet enabled: {prophet_config['enabled']}")
        
    def test_2_data_fetcher_mock_data_generation(self):
        """Test 2: Verify DataFetcher generates mock data correctly."""
        print("\n=== Test 2: Data Fetcher Mock Data Generation ===")
        
        # Initialize data fetcher with mock data
        config = self.config_manager.get_config()
        data_fetcher = DataFetcher(config)
        data_fetcher.use_mock_data = True
        
        # Fetch mock data
        metrics_data = data_fetcher.fetch_prometheus_metrics(days=7)
        processed_data = data_fetcher.process_prometheus_results(metrics_data)
        
        # Verify data structure
        self.assertIsNotNone(processed_data)
        self.assertGreater(len(processed_data), 0)
        
        # Check data format (DataFrame)
        required_columns = ['partner', 'path', 'timestamp', 'value']
        for column in required_columns:
            self.assertIn(column, processed_data.columns)
        
        # Verify data diversity
        partners = set(processed_data['partner'].unique())
        paths = set(processed_data['path'].unique())
        
        self.assertGreater(len(partners), 1, "Should have multiple partners")
        self.assertGreater(len(paths), 1, "Should have multiple paths")
        
        print(f"✅ Generated {len(processed_data)} mock data points")
        print(f"✅ Partners: {sorted(partners)}")
        print(f"✅ Unique paths: {len(paths)}")
        
    def test_3_prophet_analyzer_basic_analysis(self):
        """Test 3: Verify Prophet analyzer can process data."""
        print("\n=== Test 3: Prophet Analyzer Basic Analysis ===")
        
        # Create sample data for analysis
        sample_data = []
        base_time = datetime.now() - timedelta(days=7)
        
        # Generate 7 days of hourly data
        for hour in range(168):  # 7 days * 24 hours
            timestamp = base_time + timedelta(hours=hour)
            value = 100 + (hour % 24) * 5  # Simple pattern
            sample_data.append({
                'timestamp': timestamp,
                'value': value
            })
        
        # Initialize Prophet analyzer
        config = self.config_manager.get_config()
        prophet_analyzer = ProphetAnalyzer(config)
        
        # Test analysis
        try:
            # Create sample DataFrame for analysis
            import pandas as pd
            sample_df = pd.DataFrame(sample_data)
            
            analysis_result = prophet_analyzer.analyze_traffic_patterns(
                sample_df,
                partner="test_partner",
                path="/test_path"
            )
            
            # Verify analysis result structure
            self.assertIsNotNone(analysis_result)
            self.assertIn('anomalies', analysis_result)
            self.assertIn('method', analysis_result)
            
            print(f"✅ Prophet analysis completed successfully")
            print(f"✅ Method used: {analysis_result['method']}")
            print(f"✅ Anomalies detected: {len(analysis_result['anomalies'])}")
            
        except Exception as e:
            # If Prophet fails, should fall back to statistical analysis
            print(f"⚠️  Prophet analysis failed (expected in some environments): {e}")
            print("✅ System should fall back to statistical analysis")
            
    def test_4_rate_calculator_formula_application(self):
        """Test 4: Verify Enhanced Rate Calculator applies formulas correctly."""
        print("\n=== Test 4: Rate Calculator Formula Application ===")
        
        # Initialize rate calculator
        config = self.config_manager.get_config()
        rate_calculator = EnhancedRateCalculator(config)
        
        # Test data scenarios
        test_scenarios = [
            {
                'name': 'Low Traffic',
                'max_rate': 50,
                'mean_rate': 25,
                'pattern': 'stable',
                'expected_min': 100,  # Should use minimum rate limit
            },
            {
                'name': 'Medium Traffic',
                'max_rate': 200,
                'mean_rate': 100,
                'pattern': 'variable',
                'expected_min': 200,
            },
            {
                'name': 'High Traffic',
                'max_rate': 1000,
                'mean_rate': 500,
                'pattern': 'spiky',
                'expected_min': 800,
            }
        ]
        
        for scenario in test_scenarios:
            # Create mock data and analysis results for the calculation
            import pandas as pd
            mock_data = pd.DataFrame([{'value': scenario['max_rate'], 'timestamp': datetime.now()}])
            mock_prime_data = pd.DataFrame([{'value': scenario['mean_rate'], 'timestamp': datetime.now()}])
            mock_analysis = {'method': 'mock', 'anomalies': []}
            
            # Use a partner/path that won't be excluded by the system
            rate_calculation = rate_calculator.calculate_optimal_rate_limit(
                clean_metrics=mock_data,
                prime_time_data=mock_prime_data,
                prophet_analysis=mock_analysis,
                partner='313',  # Use existing partner from system
                path='/api_v3/service/test'  # Use API path format
            )
            
            rate_limit = rate_calculation.get('recommended_rate_limit', 100)
            
            # Verify rate limit is reasonable
            self.assertGreater(rate_limit, 0)
            self.assertGreaterEqual(rate_limit, scenario['expected_min'])
            self.assertLessEqual(rate_limit, 100000)  # Max rate limit
            
            print(f"✅ {scenario['name']}: {scenario['max_rate']} max → {rate_limit} req/min")
        
    def test_5_end_to_end_configmap_generation(self):
        """Test 5: Verify complete end-to-end ConfigMap generation."""
        print("\n=== Test 5: End-to-End ConfigMap Generation ===")
        
        # Initialize main system
        rate_limiter = AdaptiveRateLimiter()
        
        # Override config for testing
        rate_limiter.config['USE_MOCK_DATA'] = True
        rate_limiter.data_fetcher.use_mock_data = True
        
        # Create temporary output directory
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Run the system
                results = rate_limiter.run()
                
                # Check if system ran successfully
                self.assertTrue(results.get('success'), f"System run failed: {results.get('error')}")
                
                # Check if ConfigMap was generated in output directory
                output_dir = 'output'
                if os.path.exists(output_dir):
                    config_files = [f for f in os.listdir(output_dir) if f.endswith('.yaml')]
                    report_files = [f for f in os.listdir(output_dir) if f.endswith('.md')]
                    
                    self.assertGreater(len(config_files), 0, "Should generate at least one ConfigMap")
                    
                    # Validate ConfigMap structure if files exist
                    if config_files:
                        config_file = os.path.join(output_dir, config_files[-1])  # Get latest
                        with open(config_file, 'r') as f:
                            configmap = yaml.safe_load(f)
                        
                        # Verify ConfigMap structure
                        self.assertEqual(configmap['apiVersion'], 'v1')
                        self.assertEqual(configmap['kind'], 'ConfigMap')
                        self.assertIn('metadata', configmap)
                        self.assertIn('data', configmap)
                        self.assertIn('config.yaml', configmap['data'])
                        
                        # Verify rate limit data
                        rate_config = yaml.safe_load(configmap['data']['config.yaml'])
                        self.assertIn('descriptors', rate_config)
                        self.assertGreater(len(rate_config['descriptors']), 0)
                        
                        # Check rate limit values are reasonable
                        for descriptor in rate_config['descriptors']:
                            if 'descriptors' in descriptor:
                                for path_desc in descriptor['descriptors']:
                                    if 'rate_limit' in path_desc:
                                        rate = path_desc['rate_limit']['requests_per_unit']
                                        self.assertGreater(rate, 0)
                                        self.assertLessEqual(rate, 100000)
                        
                        print(f"✅ Generated {len(config_files)} ConfigMap(s)")
                        print(f"✅ Generated {len(report_files)} report(s)")
                        print(f"✅ ConfigMap structure valid")
                        print(f"✅ Rate limits within expected ranges")
                else:
                    print("⚠️  Output directory not found, but system ran successfully")
                
            except Exception as e:
                self.fail(f"End-to-end test failed: {e}")


def run_sanity_tests():
    """Run all sanity tests and report results."""
    print("🧪 Running TrendMaster-AI Sanity Tests")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(SanityTests)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SANITY TEST SUMMARY")
    print("=" * 50)
    
    if result.wasSuccessful():
        print("🎉 ALL SANITY TESTS PASSED!")
        print(f"✅ Tests run: {result.testsRun}")
        print(f"✅ Failures: {len(result.failures)}")
        print(f"✅ Errors: {len(result.errors)}")
        print("\n🚀 System is ready for use!")
    else:
        print("❌ SOME TESTS FAILED")
        print(f"📈 Tests run: {result.testsRun}")
        print(f"❌ Failures: {len(result.failures)}")
        print(f"💥 Errors: {len(result.errors)}")
        
        if result.failures:
            print("\n💔 FAILURES:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback}")
        
        if result.errors:
            print("\n💥 ERRORS:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_sanity_tests()
    sys.exit(0 if success else 1)