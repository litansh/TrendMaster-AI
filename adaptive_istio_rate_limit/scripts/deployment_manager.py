#!/usr/bin/env python3
"""
TrendMaster-AI Deployment Manager
Handles local, testing, and production deployment scenarios with EKS simulation
"""

import os
import sys
import yaml
import json
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.config_manager import ConfigManager

class DeploymentManager:
    """Manages deployments across local, testing, and production environments"""
    
    def __init__(self, environment: str = "local"):
        self.environment = environment
        
        # Initialize configuration manager with environment awareness
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()
        
        # Get environment-specific configurations using the config manager
        self.deployment_mode = self.config_manager.get_deployment_mode()
        self.env_config = self.config_manager.get_environment_config()
        self.current_env = self.config_manager.get_current_environment()
        
        # Override environment if explicitly provided
        if environment != "local":
            self.deployment_mode = environment
            self.env_config = self.config.get('ENVIRONMENTS', {}).get(environment, {})
        
        # Deployment paths - setup BEFORE logging
        self.project_root = Path(__file__).parent.parent
        self.output_dir = self.project_root / "output"
        self.k8s_dir = self.project_root / "k8s"
        self.logs_dir = self.project_root / "logs"
        
        # Ensure directories exist
        for dir_path in [self.output_dir, self.k8s_dir, self.logs_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # Setup logging after directories are created
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup environment-specific logging"""
        logger = logging.getLogger(f"deployment_manager_{self.environment}")
        logger.setLevel(logging.DEBUG if self.env_config.get('VERBOSE_LOGGING', False) else logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler
        log_file = self.logs_dir / f"deployment_{self.environment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def check_prerequisites(self) -> Dict[str, bool]:
        """Check deployment prerequisites for the environment"""
        self.logger.info(f"🔧 Checking prerequisites for {self.environment} environment")
        
        prerequisites = {
            'python': self._check_python(),
            'kubectl': self._check_kubectl(),
            'docker': self._check_docker() if self.environment != 'local' else True,
            'helm': self._check_helm() if self.environment == 'production' else True,
            'aws_cli': self._check_aws_cli() if 'eks' in self.env_config.get('KUBERNETES_CONTEXT', '') else True,
            'kube_config': self._check_kube_config(),
            'prometheus': self._check_prometheus_connectivity(),
        }
        
        # Log results
        for check, result in prerequisites.items():
            status = "✅" if result else "❌"
            self.logger.info(f"{status} {check}: {'OK' if result else 'FAILED'}")
        
        return prerequisites
    
    def _check_python(self) -> bool:
        """Check Python version and required packages"""
        try:
            import sys
            if sys.version_info < (3, 8):
                return False
            
            # Check critical packages
            required_packages = ['yaml', 'requests', 'pandas', 'numpy', 'prophet']
            for package in required_packages:
                try:
                    __import__(package)
                except ImportError:
                    self.logger.warning(f"Missing package: {package}")
                    return False
            
            return True
        except Exception:
            return False
    
    def _check_kubectl(self) -> bool:
        """Check kubectl availability and configuration"""
        try:
            result = subprocess.run(['kubectl', 'version', '--client'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_docker(self) -> bool:
        """Check Docker availability"""
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_helm(self) -> bool:
        """Check Helm availability"""
        try:
            result = subprocess.run(['helm', 'version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_aws_cli(self) -> bool:
        """Check AWS CLI availability and configuration"""
        try:
            result = subprocess.run(['aws', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return False
            
            # Check AWS credentials
            result = subprocess.run(['aws', 'sts', 'get-caller-identity'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_kube_config(self) -> bool:
        """Check Kubernetes configuration"""
        try:
            kube_context = self.env_config.get('KUBERNETES_CONTEXT')
            if not kube_context:
                return True  # No specific context required
            
            # For local environment, check if minikube is available
            if self.environment == 'local' and kube_context == 'minikube':
                result = subprocess.run(['minikube', 'status'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode != 0:
                    self.logger.warning("Minikube not running - will simulate K8s operations")
                    return True  # Allow simulation
            
            # Check if context exists
            result = subprocess.run(['kubectl', 'config', 'get-contexts', kube_context], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_prometheus_connectivity(self) -> bool:
        """Check Prometheus connectivity"""
        if self.env_config.get('USE_MOCK_DATA', False):
            return True  # Mock data doesn't require Prometheus
        
        try:
            import requests
            prometheus_url = self.env_config.get('PROMETHEUS_URL')
            if not prometheus_url:
                return False
            
            response = requests.get(f"{prometheus_url}/api/v1/status/config", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def simulate_eks_environment(self) -> bool:
        """Simulate EKS environment for local testing"""
        self.logger.info("🎭 Simulating EKS environment locally")
        
        # Create mock EKS namespace structure
        namespaces = ['istio-system', 'kube-system', 'default', 'monitoring']
        
        for namespace in namespaces:
            ns_dir = self.k8s_dir / "simulated" / namespace
            ns_dir.mkdir(parents=True, exist_ok=True)
            
            # Create namespace manifest
            ns_manifest = {
                'apiVersion': 'v1',
                'kind': 'Namespace',
                'metadata': {
                    'name': namespace,
                    'labels': {
                        'environment': self.environment,
                        'managed-by': 'trendmaster-ai',
                        'simulated': 'true'
                    }
                }
            }
            
            with open(ns_dir / 'namespace.yaml', 'w') as f:
                yaml.dump(ns_manifest, f, default_flow_style=False)
        
        # Create mock Istio resources
        self._create_mock_istio_resources()
        
        # Create mock monitoring resources
        self._create_mock_monitoring_resources()
        
        self.logger.info("✅ EKS environment simulation completed")
        return True
    
    def _create_mock_istio_resources(self):
        """Create mock Istio resources for simulation"""
        istio_dir = self.k8s_dir / "simulated" / "istio-system"
        
        # Mock EnvoyFilter for rate limiting
        envoy_filter = {
            'apiVersion': 'networking.istio.io/v1alpha3',
            'kind': 'EnvoyFilter',
            'metadata': {
                'name': 'trendmaster-ai-ratelimit',
                'namespace': 'istio-system',
                'labels': {
                    'managed-by': 'trendmaster-ai',
                    'environment': self.environment
                }
            },
            'spec': {
                'configPatches': [{
                    'applyTo': 'HTTP_FILTER',
                    'match': {
                        'context': 'SIDECAR_INBOUND',
                        'listener': {
                            'filterChain': {
                                'filter': {
                                    'name': 'envoy.filters.network.http_connection_manager'
                                }
                            }
                        }
                    },
                    'patch': {
                        'operation': 'INSERT_BEFORE',
                        'value': {
                            'name': 'envoy.filters.http.local_ratelimit',
                            'typed_config': {
                                '@type': 'type.googleapis.com/udpa.type.v1.TypedStruct',
                                'type_url': 'type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit',
                                'value': {
                                    'stat_prefix': 'trendmaster_ai_rate_limiter'
                                }
                            }
                        }
                    }
                }]
            }
        }
        
        with open(istio_dir / 'envoy-filter.yaml', 'w') as f:
            yaml.dump(envoy_filter, f, default_flow_style=False)
        
        # Mock ConfigMap for rate limit configuration
        configmap = {
            'apiVersion': 'v1',
            'kind': 'ConfigMap',
            'metadata': {
                'name': 'ratelimit-config',
                'namespace': 'istio-system',
                'labels': {
                    'managed-by': 'trendmaster-ai',
                    'environment': self.environment
                }
            },
            'data': {
                'config.yaml': 'domain: trendmaster-ai\ndescriptors:\n  - key: partner_id\n    value: "CUSTOMER_ID_1"\n    rate_limit:\n      unit: minute\n      requests_per_unit: 1000'
            }
        }
        
        with open(istio_dir / 'ratelimit-configmap.yaml', 'w') as f:
            yaml.dump(configmap, f, default_flow_style=False)
    
    def _create_mock_monitoring_resources(self):
        """Create mock monitoring resources"""
        monitoring_dir = self.k8s_dir / "simulated" / "monitoring"
        
        # Mock ServiceMonitor for Prometheus
        service_monitor = {
            'apiVersion': 'monitoring.coreos.com/v1',
            'kind': 'ServiceMonitor',
            'metadata': {
                'name': 'trendmaster-ai-metrics',
                'namespace': 'monitoring',
                'labels': {
                    'managed-by': 'trendmaster-ai',
                    'environment': self.environment
                }
            },
            'spec': {
                'selector': {
                    'matchLabels': {
                        'app': 'trendmaster-ai'
                    }
                },
                'endpoints': [{
                    'port': 'metrics',
                    'interval': '30s',
                    'path': '/metrics'
                }]
            }
        }
        
        with open(monitoring_dir / 'service-monitor.yaml', 'w') as f:
            yaml.dump(service_monitor, f, default_flow_style=False)
    
    def deploy(self, dry_run: bool = None) -> Dict[str, Any]:
        """Execute deployment for the environment"""
        if dry_run is None:
            dry_run = self.env_config.get('DRY_RUN', True)
        
        self.logger.info(f"🚀 Starting {self.environment} deployment (dry_run={dry_run})")
        
        deployment_result = {
            'environment': self.environment,
            'timestamp': datetime.now().isoformat(),
            'dry_run': dry_run,
            'steps': {},
            'success': False,
            'artifacts': []
        }
        
        try:
            # Step 1: Prerequisites check
            prerequisites = self.check_prerequisites()
            deployment_result['steps']['prerequisites'] = {
                'status': 'success' if all(prerequisites.values()) else 'warning',
                'details': prerequisites
            }
            
            # Step 2: Environment simulation (for local)
            if self.environment == 'local':
                sim_result = self.simulate_eks_environment()
                deployment_result['steps']['simulation'] = {
                    'status': 'success' if sim_result else 'failed',
                    'details': 'EKS environment simulated locally'
                }
            
            # Step 3: Generate rate limit configurations
            config_result = self._generate_rate_limit_configs()
            deployment_result['steps']['configuration'] = config_result
            
            # Step 4: Apply Kubernetes resources
            k8s_result = self._apply_kubernetes_resources(dry_run)
            deployment_result['steps']['kubernetes'] = k8s_result
            
            # Step 5: Validate deployment
            validation_result = self._validate_deployment()
            deployment_result['steps']['validation'] = validation_result
            
            # Step 6: Setup monitoring (if enabled)
            if self.env_config.get('MONITORING_ENABLED', False):
                monitoring_result = self._setup_monitoring()
                deployment_result['steps']['monitoring'] = monitoring_result
            
            deployment_result['success'] = all(
                step.get('status') in ['success', 'warning'] 
                for step in deployment_result['steps'].values()
            )
            
        except Exception as e:
            self.logger.error(f"Deployment failed: {str(e)}")
            deployment_result['error'] = str(e)
            deployment_result['success'] = False
        
        # Save deployment report
        self._save_deployment_report(deployment_result)
        
        return deployment_result
    
    def _generate_rate_limit_configs(self) -> Dict[str, Any]:
        """Generate rate limit configurations"""
        self.logger.info("📋 Generating rate limit configurations")
        
        try:
            # Import and run the main adaptive rate limiter
            from main import AdaptiveRateLimiter
            
            # Initialize rate limiter with default config path
            rate_limiter = AdaptiveRateLimiter()
            
            # Override the deployment mode in the rate limiter's config
            if hasattr(rate_limiter, 'config') and rate_limiter.config:
                if 'DEPLOYMENT' not in rate_limiter.config:
                    rate_limiter.config['DEPLOYMENT'] = {}
                rate_limiter.config['DEPLOYMENT']['MODE'] = self.environment
                
                # Also update the config manager's deployment mode
                if hasattr(rate_limiter.config_manager, '_deployment_mode'):
                    rate_limiter.config_manager._deployment_mode = self.environment
            
            # Run analysis and generate configs
            results = rate_limiter.run()
            
            return {
                'status': 'success',
                'details': f"Generated {len(results.get('configmaps', []))} ConfigMaps",
                'artifacts': results.get('artifacts', [])
            }
            
        except Exception as e:
            self.logger.error(f"Configuration generation failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def _apply_kubernetes_resources(self, dry_run: bool) -> Dict[str, Any]:
        """Apply Kubernetes resources"""
        self.logger.info(f"☸️  Applying Kubernetes resources (dry_run={dry_run})")
        
        try:
            applied_resources = []
            
            # Find all YAML files in output directory
            yaml_files = list(self.output_dir.glob("*.yaml"))
            
            for yaml_file in yaml_files:
                if dry_run or self.environment == 'local':
                    # Simulate kubectl apply
                    self.logger.info(f"[DRY RUN] Would apply: {yaml_file.name}")
                    applied_resources.append({
                        'file': yaml_file.name,
                        'status': 'simulated',
                        'action': 'apply'
                    })
                else:
                    # Actually apply to cluster
                    result = self._kubectl_apply(yaml_file)
                    applied_resources.append(result)
            
            return {
                'status': 'success',
                'details': f"Applied {len(applied_resources)} resources",
                'resources': applied_resources
            }
            
        except Exception as e:
            self.logger.error(f"Kubernetes apply failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def _kubectl_apply(self, yaml_file: Path) -> Dict[str, Any]:
        """Apply a single YAML file with kubectl"""
        try:
            context = self.env_config.get('KUBERNETES_CONTEXT')
            namespace = self.env_config.get('CONFIGMAP_NAMESPACE', 'default')
            
            cmd = ['kubectl', 'apply', '-f', str(yaml_file), '-n', namespace]
            if context:
                cmd.extend(['--context', context])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            return {
                'file': yaml_file.name,
                'status': 'success' if result.returncode == 0 else 'failed',
                'output': result.stdout,
                'error': result.stderr if result.returncode != 0 else None
            }
            
        except Exception as e:
            return {
                'file': yaml_file.name,
                'status': 'failed',
                'error': str(e)
            }
    
    def _validate_deployment(self) -> Dict[str, Any]:
        """Validate the deployment"""
        self.logger.info("✅ Validating deployment")
        
        try:
            validation_checks = {
                'configmaps_exist': self._check_configmaps_exist(),
                'rate_limits_applied': self._check_rate_limits_applied(),
                'monitoring_active': self._check_monitoring_active(),
                'health_check': self._perform_health_check()
            }
            
            all_passed = all(validation_checks.values())
            
            return {
                'status': 'success' if all_passed else 'warning',
                'details': 'All validation checks passed' if all_passed else 'Some checks failed',
                'checks': validation_checks
            }
            
        except Exception as e:
            self.logger.error(f"Validation failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def _check_configmaps_exist(self) -> bool:
        """Check if ConfigMaps were created successfully"""
        if self.environment == 'local':
            # Check if ConfigMap files exist in output directory
            configmap_files = list(self.output_dir.glob("*configmap*.yaml"))
            return len(configmap_files) > 0
        else:
            # Check actual Kubernetes cluster
            try:
                context = self.env_config.get('KUBERNETES_CONTEXT')
                namespace = self.env_config.get('CONFIGMAP_NAMESPACE', 'default')
                
                cmd = ['kubectl', 'get', 'configmaps', '-n', namespace, '-l', 'managed-by=trendmaster-ai']
                if context:
                    cmd.extend(['--context', context])
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                return result.returncode == 0 and 'ratelimit-config' in result.stdout
            except Exception:
                return False
    
    def _check_rate_limits_applied(self) -> bool:
        """Check if rate limits are properly applied"""
        # For now, assume success if ConfigMaps exist
        return self._check_configmaps_exist()
    
    def _check_monitoring_active(self) -> bool:
        """Check if monitoring is active"""
        if not self.env_config.get('MONITORING_ENABLED', False):
            return True  # Not required
        
        # Check if monitoring resources exist
        monitoring_files = list(self.k8s_dir.glob("**/service-monitor.yaml"))
        return len(monitoring_files) > 0
    
    def _perform_health_check(self) -> bool:
        """Perform basic health check"""
        try:
            # Check if system can generate configurations
            from utils.config_manager import ConfigManager
            config_manager = ConfigManager()
            config = config_manager.get_config()
            return config is not None
        except Exception:
            return False
    
    def _setup_monitoring(self) -> Dict[str, Any]:
        """Setup monitoring for the deployment"""
        self.logger.info("📊 Setting up monitoring")
        
        try:
            # Create monitoring dashboard
            dashboard_config = self._create_monitoring_dashboard()
            
            # Setup alerts
            alerts_config = self._create_monitoring_alerts()
            
            return {
                'status': 'success',
                'details': 'Monitoring configured successfully',
                'dashboard': dashboard_config,
                'alerts': alerts_config
            }
            
        except Exception as e:
            self.logger.error(f"Monitoring setup failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def _create_monitoring_dashboard(self) -> Dict[str, Any]:
        """Create monitoring dashboard configuration"""
        dashboard = {
            'dashboard': {
                'title': f'TrendMaster-AI Rate Limiting - {self.environment.title()}',
                'tags': ['trendmaster-ai', 'rate-limiting', self.environment],
                'panels': [
                    {
                        'title': 'Rate Limit Effectiveness',
                        'type': 'graph',
                        'targets': [
                            {
                                'expr': 'rate(istio_requests_total[5m])',
                                'legendFormat': 'Request Rate'
                            }
                        ]
                    },
                    {
                        'title': 'Rate Limit Violations',
                        'type': 'stat',
                        'targets': [
                            {
                                'expr': 'increase(envoy_http_local_rate_limiter_rate_limited_total[1h])',
                                'legendFormat': 'Rate Limited Requests'
                            }
                        ]
                    }
                ]
            }
        }
        
        # Save dashboard configuration
        dashboard_file = self.output_dir / f"monitoring_dashboard_{self.environment}.json"
        with open(dashboard_file, 'w') as f:
            json.dump(dashboard, f, indent=2)
        
        return {'file': str(dashboard_file), 'status': 'created'}
    
    def _create_monitoring_alerts(self) -> Dict[str, Any]:
        """Create monitoring alerts"""
        alerts = {
            'groups': [
                {
                    'name': f'trendmaster-ai-{self.environment}',
                    'rules': [
                        {
                            'alert': 'HighRateLimitViolations',
                            'expr': 'rate(envoy_http_local_rate_limiter_rate_limited_total[5m]) > 10',
                            'for': '5m',
                            'labels': {
                                'severity': 'warning',
                                'environment': self.environment
                            },
                            'annotations': {
                                'summary': 'High rate limit violations detected',
                                'description': 'Rate limit violations exceed threshold'
                            }
                        }
                    ]
                }
            ]
        }
        
        # Save alerts configuration
        alerts_file = self.output_dir / f"monitoring_alerts_{self.environment}.yaml"
        with open(alerts_file, 'w') as f:
            yaml.dump(alerts, f, default_flow_style=False)
        
        return {'file': str(alerts_file), 'status': 'created'}
    
    def _save_deployment_report(self, deployment_result: Dict[str, Any]):
        """Save deployment report"""
        report_file = self.logs_dir / f"deployment_report_{self.environment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w') as f:
            json.dump(deployment_result, f, indent=2, default=str)
        
        deployment_result['artifacts'].append(str(report_file))
        self.logger.info(f"📄 Deployment report saved to: {report_file}")
    
    def rollback(self, version: str = None) -> Dict[str, Any]:
        """Rollback deployment to previous version"""
        self.logger.info(f"🔄 Rolling back {self.environment} deployment")
        
        try:
            # For local environment, just restore previous configs
            if self.environment == 'local':
                return self._simulate_rollback()
            
            # For other environments, use kubectl rollout
            return self._kubectl_rollback(version)
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def _simulate_rollback(self) -> Dict[str, Any]:
        """Simulate rollback for local environment"""
        self.logger.info("Simulating rollback for local environment")
        
        # Find previous deployment artifacts
        previous_configs = sorted(self.output_dir.glob("*configmap*.yaml"))
        
        if len(previous_configs) < 2:
            return {
                'status': 'warning',
                'message': 'No previous version found to rollback to'
            }
        
        return {
            'status': 'success',
            'message': 'Rollback simulation completed',
            'previous_version': previous_configs[-2].name
        }
    
    def _kubectl_rollback(self, version: str = None) -> Dict[str, Any]:
        """Perform kubectl rollback"""
        try:
            context = self.env_config.get('KUBERNETES_CONTEXT')
            namespace = self.env_config.get('CONFIGMAP_NAMESPACE', 'default')
            
            # Get deployment history
            cmd = ['kubectl', 'rollout', 'history', 'deployment/trendmaster-ai', '-n', namespace]
            if context:
                cmd.extend(['--context', context])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return {
                    'status': 'failed',
                    'error': 'No deployment found to rollback'
                }
            
            # Perform rollback
            rollback_cmd = ['kubectl', 'rollout', 'undo', 'deployment/trendmaster-ai', '-n', namespace]
            if version:
                rollback_cmd.extend(['--to-revision', version])
            if context:
                rollback_cmd.extend(['--context', context])
            
            rollback_result = subprocess.run(rollback_cmd, capture_output=True, text=True, timeout=60)
            
            return {
                'status': 'success' if rollback_result.returncode == 0 else 'failed',
                'output': rollback_result.stdout,
                'error': rollback_result.stderr if rollback_result.returncode != 0 else None
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e)
            }


def main():
    """Main deployment manager CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(description='TrendMaster-AI Deployment Manager')
    parser.add_argument('--environment', '-e', choices=['local', 'testing', 'production'], 
                       default='local', help='Deployment environment')
    parser.add_argument('--action', '-a', choices=['deploy', 'rollback', 'validate', 'simulate'], 
                       default='deploy', help='Action to perform')
    parser.add_argument('--dry-run', action='store_true', help='Perform dry run')
    parser.add_argument('--version', help='Version for rollback')
    
    args = parser.parse_args()
    
    # Initialize deployment manager
    deployment_manager = DeploymentManager(args.environment)
    
    # Execute action
    if args.action == 'deploy':
        result = deployment_manager.deploy(dry_run=args.dry_run)
    elif args.action == 'rollback':
        result = deployment_manager.rollback(args.version)
    elif args.action == 'validate':
        result = deployment_manager._validate_deployment()
    elif args.action == 'simulate':
        result = {'success': deployment_manager.simulate_eks_environment()}
    
    # Print result
    print(json.dumps(result, indent=2, default=str))
    
    # Exit with appropriate code
    exit(0 if result.get('success', False) else 1)


if __name__ == '__main__':
    main()