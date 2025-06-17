#!/usr/bin/env python3
"""
TrendMaster-AI Deployment Tests
Tests for local, testing, and production deployment scenarios
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from deployment_manager import DeploymentManager


class TestDeploymentManager(unittest.TestCase):
    """Test deployment manager functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.original_cwd = os.getcwd()
        
        # Create test project structure
        (self.test_dir / "scripts").mkdir()
        (self.test_dir / "config").mkdir()
        (self.test_dir / "output").mkdir()
        (self.test_dir / "k8s").mkdir()
        (self.test_dir / "logs").mkdir()
        
        # Create minimal config file
        config_content = """
DEPLOYMENT:
  MODE: "local"
  ENVIRONMENT: "development"

ENVIRONMENTS:
  local:
    PROMETHEUS_URL: "http://localhost:9090"
    KUBERNETES_CONTEXT: "minikube"
    CONFIGMAP_NAMESPACE: "default"
    DRY_RUN: true
    PREVIEW_ONLY: true
    USE_MOCK_DATA: true
    VERBOSE_LOGGING: true
    
  testing:
    PROMETHEUS_URL: "https://trickster.orp2.ott.YOUR_COMPANY.com"
    KUBERNETES_CONTEXT: "eks-testing"
    CONFIGMAP_NAMESPACE: "istio-system"
    DRY_RUN: true
    PREVIEW_ONLY: true
    USE_MOCK_DATA: false
    
  production:
    PROMETHEUS_URL: "https://trickster.orp2.ott.YOUR_COMPANY.com"
    KUBERNETES_CONTEXT: "eks-production"
    CONFIGMAP_NAMESPACE: "istio-system"
    DRY_RUN: false
    PREVIEW_ONLY: false
    ENABLE_UPDATES: true
    MONITORING_ENABLED: true

COMMON:
  ENV: "orp2"
  DAYS_TO_INSPECT: 7
  LOG_LEVEL: "DEBUG"
"""
        
        with open(self.test_dir / "config" / "config.yaml", 'w') as f:
            f.write(config_content)
        
        os.chdir(self.test_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_local_deployment_manager_initialization(self):
        """Test local deployment manager initialization"""
        with patch('scripts.deployment_manager.ConfigManager'):
            dm = DeploymentManager('local')
            self.assertEqual(dm.environment, 'local')
            self.assertIsNotNone(dm.logger)
    
    def test_testing_deployment_manager_initialization(self):
        """Test testing deployment manager initialization"""
        with patch('scripts.deployment_manager.ConfigManager'):
            dm = DeploymentManager('testing')
            self.assertEqual(dm.environment, 'testing')
            self.assertIsNotNone(dm.logger)
    
    def test_production_deployment_manager_initialization(self):
        """Test production deployment manager initialization"""
        with patch('scripts.deployment_manager.ConfigManager'):
            dm = DeploymentManager('production')
            self.assertEqual(dm.environment, 'production')
            self.assertIsNotNone(dm.logger)
    
    @patch('subprocess.run')
    def test_prerequisites_check_local(self, mock_run):
        """Test prerequisites check for local environment"""
        # Mock successful command executions
        mock_run.return_value = MagicMock(returncode=0, stdout="OK")
        
        with patch('scripts.deployment_manager.ConfigManager'):
            dm = DeploymentManager('local')
            prerequisites = dm.check_prerequisites()
            
            # Local environment should not require Docker, Helm, or AWS CLI
            self.assertIn('python', prerequisites)
            self.assertIn('kubectl', prerequisites)
            self.assertTrue(prerequisites['docker'])  # Should be True (not checked)
            self.assertTrue(prerequisites['helm'])    # Should be True (not checked)
            self.assertTrue(prerequisites['aws_cli']) # Should be True (not checked)
    
    @patch('subprocess.run')
    def test_prerequisites_check_testing(self, mock_run):
        """Test prerequisites check for testing environment"""
        # Mock successful command executions
        mock_run.return_value = MagicMock(returncode=0, stdout="OK")
        
        with patch('scripts.deployment_manager.ConfigManager'):
            dm = DeploymentManager('testing')
            prerequisites = dm.check_prerequisites()
            
            # Testing environment should require Docker and AWS CLI
            self.assertIn('python', prerequisites)
            self.assertIn('kubectl', prerequisites)
            self.assertIn('docker', prerequisites)
            self.assertIn('aws_cli', prerequisites)
    
    @patch('subprocess.run')
    def test_prerequisites_check_production(self, mock_run):
        """Test prerequisites check for production environment"""
        # Mock successful command executions
        mock_run.return_value = MagicMock(returncode=0, stdout="OK")
        
        with patch('scripts.deployment_manager.ConfigManager'):
            dm = DeploymentManager('production')
            prerequisites = dm.check_prerequisites()
            
            # Production environment should require all tools
            self.assertIn('python', prerequisites)
            self.assertIn('kubectl', prerequisites)
            self.assertIn('docker', prerequisites)
            self.assertIn('helm', prerequisites)
            self.assertIn('aws_cli', prerequisites)
    
    def test_eks_simulation(self):
        """Test EKS environment simulation"""
        with patch('scripts.deployment_manager.ConfigManager'):
            dm = DeploymentManager('local')
            result = dm.simulate_eks_environment()
            
            self.assertTrue(result)
            
            # Check if simulation directories were created
            sim_dir = self.test_dir / "k8s" / "simulated"
            self.assertTrue(sim_dir.exists())
            
            # Check if namespaces were created
            namespaces = ['istio-system', 'kube-system', 'default', 'monitoring']
            for namespace in namespaces:
                ns_dir = sim_dir / namespace
                self.assertTrue(ns_dir.exists())
                self.assertTrue((ns_dir / 'namespace.yaml').exists())
    
    def test_mock_istio_resources_creation(self):
        """Test creation of mock Istio resources"""
        with patch('scripts.deployment_manager.ConfigManager'):
            dm = DeploymentManager('local')
            dm.simulate_eks_environment()
            
            istio_dir = self.test_dir / "k8s" / "simulated" / "istio-system"
            
            # Check if Istio resources were created
            self.assertTrue((istio_dir / 'envoy-filter.yaml').exists())
            self.assertTrue((istio_dir / 'ratelimit-configmap.yaml').exists())
    
    def test_mock_monitoring_resources_creation(self):
        """Test creation of mock monitoring resources"""
        with patch('scripts.deployment_manager.ConfigManager'):
            dm = DeploymentManager('local')
            dm.simulate_eks_environment()
            
            monitoring_dir = self.test_dir / "k8s" / "simulated" / "monitoring"
            
            # Check if monitoring resources were created
            self.assertTrue((monitoring_dir / 'service-monitor.yaml').exists())
    
    @patch('scripts.deployment_manager.AdaptiveRateLimiter')
    def test_rate_limit_config_generation(self, mock_rate_limiter):
        """Test rate limit configuration generation"""
        # Mock rate limiter results
        mock_instance = MagicMock()
        mock_instance.run.return_value = {
            'configmaps': ['config1', 'config2'],
            'artifacts': ['artifact1', 'artifact2']
        }
        mock_rate_limiter.return_value = mock_instance
        
        with patch('scripts.deployment_manager.ConfigManager'):
            dm = DeploymentManager('local')
            result = dm._generate_rate_limit_configs()
            
            self.assertEqual(result['status'], 'success')
            self.assertIn('Generated 2 ConfigMaps', result['details'])
    
    @patch('subprocess.run')
    def test_kubernetes_apply_dry_run(self, mock_run):
        """Test Kubernetes apply in dry run mode"""
        # Create test YAML file
        test_yaml = self.test_dir / "output" / "test-config.yaml"
        test_yaml.write_text("apiVersion: v1\nkind: ConfigMap")
        
        with patch('scripts.deployment_manager.ConfigManager'):
            dm = DeploymentManager('local')
            result = dm._apply_kubernetes_resources(dry_run=True)
            
            self.assertEqual(result['status'], 'success')
            self.assertIn('Applied 1 resources', result['details'])
            
            # Should not have called kubectl
            mock_run.assert_not_called()
    
    @patch('subprocess.run')
    def test_kubernetes_apply_real(self, mock_run):
        """Test Kubernetes apply in real mode"""
        # Mock successful kubectl apply
        mock_run.return_value = MagicMock(returncode=0, stdout="configured")
        
        # Create test YAML file
        test_yaml = self.test_dir / "output" / "test-config.yaml"
        test_yaml.write_text("apiVersion: v1\nkind: ConfigMap")
        
        with patch('scripts.deployment_manager.ConfigManager'):
            dm = DeploymentManager('testing')  # Non-local environment
            result = dm._apply_kubernetes_resources(dry_run=False)
            
            self.assertEqual(result['status'], 'success')
            # Should have called kubectl
            mock_run.assert_called()
    
    def test_deployment_validation_local(self):
        """Test deployment validation for local environment"""
        # Create mock ConfigMap files
        (self.test_dir / "output" / "test-configmap.yaml").write_text("test")
        
        with patch('scripts.deployment_manager.ConfigManager'):
            dm = DeploymentManager('local')
            result = dm._validate_deployment()
            
            # Should pass validation for local environment
            self.assertIn(result['status'], ['success', 'warning'])
    
    @patch('subprocess.run')
    def test_deployment_validation_cluster(self, mock_run):
        """Test deployment validation for cluster environment"""
        # Mock successful kubectl get
        mock_run.return_value = MagicMock(returncode=0, stdout="ratelimit-config")
        
        with patch('scripts.deployment_manager.ConfigManager'):
            dm = DeploymentManager('testing')
            result = dm._validate_deployment()
            
            # Should attempt to check cluster
            self.assertIn(result['status'], ['success', 'warning', 'failed'])
    
    def test_monitoring_setup(self):
        """Test monitoring setup"""
        with patch('scripts.deployment_manager.ConfigManager'):
            dm = DeploymentManager('production')
            result = dm._setup_monitoring()
            
            self.assertEqual(result['status'], 'success')
            
            # Check if monitoring files were created
            dashboard_file = self.test_dir / "output" / "monitoring_dashboard_production.json"
            alerts_file = self.test_dir / "output" / "monitoring_alerts_production.yaml"
            
            self.assertTrue(dashboard_file.exists())
            self.assertTrue(alerts_file.exists())
    
    @patch('scripts.deployment_manager.AdaptiveRateLimiter')
    def test_full_local_deployment(self, mock_rate_limiter):
        """Test full local deployment workflow"""
        # Mock rate limiter
        mock_instance = MagicMock()
        mock_instance.run.return_value = {
            'configmaps': ['config1'],
            'artifacts': ['artifact1']
        }
        mock_rate_limiter.return_value = mock_instance
        
        with patch('scripts.deployment_manager.ConfigManager'):
            dm = DeploymentManager('local')
            result = dm.deploy()
            
            # Deployment should succeed
            self.assertTrue(result['success'])
            self.assertEqual(result['environment'], 'local')
            self.assertTrue(result['dry_run'])
            
            # Should have all expected steps
            expected_steps = ['prerequisites', 'simulation', 'configuration', 'kubernetes', 'validation']
            for step in expected_steps:
                self.assertIn(step, result['steps'])
    
    @patch('scripts.deployment_manager.AdaptiveRateLimiter')
    @patch('subprocess.run')
    def test_full_testing_deployment(self, mock_run, mock_rate_limiter):
        """Test full testing deployment workflow"""
        # Mock successful command executions
        mock_run.return_value = MagicMock(returncode=0, stdout="OK")
        
        # Mock rate limiter
        mock_instance = MagicMock()
        mock_instance.run.return_value = {
            'configmaps': ['config1'],
            'artifacts': ['artifact1']
        }
        mock_rate_limiter.return_value = mock_instance
        
        with patch('scripts.deployment_manager.ConfigManager'):
            dm = DeploymentManager('testing')
            result = dm.deploy()
            
            # Deployment should succeed (even if some checks fail)
            self.assertEqual(result['environment'], 'testing')
            self.assertTrue(result['dry_run'])  # Testing environment defaults to dry run
            
            # Should have expected steps (no simulation for testing)
            expected_steps = ['prerequisites', 'configuration', 'kubernetes', 'validation']
            for step in expected_steps:
                self.assertIn(step, result['steps'])
    
    def test_rollback_local(self):
        """Test rollback for local environment"""
        # Create multiple ConfigMap files to simulate versions
        (self.test_dir / "output" / "configmap_v1.yaml").write_text("v1")
        (self.test_dir / "output" / "configmap_v2.yaml").write_text("v2")
        
        with patch('scripts.deployment_manager.ConfigManager'):
            dm = DeploymentManager('local')
            result = dm.rollback()
            
            self.assertEqual(result['status'], 'success')
            self.assertIn('Rollback simulation completed', result['message'])
    
    @patch('subprocess.run')
    def test_rollback_cluster(self, mock_run):
        """Test rollback for cluster environment"""
        # Mock kubectl rollout commands
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="REVISION  CHANGE-CAUSE\n1  Initial\n2  Update"),
            MagicMock(returncode=0, stdout="deployment.apps/trendmaster-ai rolled back")
        ]
        
        with patch('scripts.deployment_manager.ConfigManager'):
            dm = DeploymentManager('production')
            result = dm.rollback()
            
            self.assertEqual(result['status'], 'success')
            # Should have called kubectl rollout commands
            self.assertEqual(mock_run.call_count, 2)


class TestDeploymentIntegration(unittest.TestCase):
    """Integration tests for deployment scenarios"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
    
    def tearDown(self):
        """Clean up integration test environment"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_environment_specific_configurations(self):
        """Test that each environment has correct configurations"""
        environments = ['local', 'testing', 'production']
        
        for env in environments:
            with patch('scripts.deployment_manager.ConfigManager'):
                dm = DeploymentManager(env)
                
                # Each environment should have different settings
                self.assertEqual(dm.environment, env)
                
                # Local should use mock data, others should not (except testing)
                if env == 'local':
                    self.assertTrue(dm.env_config.get('USE_MOCK_DATA', False))
                    self.assertTrue(dm.env_config.get('DRY_RUN', False))
                elif env == 'testing':
                    self.assertTrue(dm.env_config.get('DRY_RUN', False))
                elif env == 'production':
                    self.assertFalse(dm.env_config.get('DRY_RUN', True))
    
    def test_deployment_artifact_generation(self):
        """Test that deployments generate appropriate artifacts"""
        with patch('scripts.deployment_manager.ConfigManager'):
            dm = DeploymentManager('local')
            
            # Simulate EKS environment
            dm.simulate_eks_environment()
            
            # Check that simulation created the expected directory structure
            k8s_dir = self.test_dir / "k8s" / "simulated"
            self.assertTrue(k8s_dir.exists())
            
            # Check namespace directories
            for namespace in ['istio-system', 'monitoring', 'default']:
                ns_dir = k8s_dir / namespace
                self.assertTrue(ns_dir.exists())
    
    def test_deployment_safety_checks(self):
        """Test deployment safety mechanisms"""
        with patch('scripts.deployment_manager.ConfigManager'):
            # Local deployment should always be safe
            dm_local = DeploymentManager('local')
            self.assertTrue(dm_local.env_config.get('DRY_RUN', False))
            
            # Testing deployment should be safe by default
            dm_testing = DeploymentManager('testing')
            self.assertTrue(dm_testing.env_config.get('DRY_RUN', False))
            
            # Production deployment should require explicit configuration
            dm_prod = DeploymentManager('production')
            # Production can be non-dry-run, but should be carefully configured
            self.assertIsNotNone(dm_prod.env_config.get('DRY_RUN'))


if __name__ == '__main__':
    # Set up test environment
    test_suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"🧪 DEPLOYMENT TESTS SUMMARY")
    print(f"{'='*50}")
    print(f"✅ Tests run: {result.testsRun}")
    print(f"❌ Failures: {len(result.failures)}")
    print(f"💥 Errors: {len(result.errors)}")
    
    if result.failures:
        print(f"\n🔍 FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError: ')[-1].split('\\n')[0]}")
    
    if result.errors:
        print(f"\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('\\n')[-2]}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\n🚀 Overall Status: {'PASSED' if success else 'FAILED'}")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)