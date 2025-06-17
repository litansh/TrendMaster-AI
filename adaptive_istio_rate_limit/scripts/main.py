#!/usr/bin/env python3
"""
TrendMaster-AI Adaptive Istio Rate Limiting System
Production-Ready Main Entry Point

This is the main entry point for the TrendMaster-AI adaptive rate limiting system.
It provides comprehensive rate limiting analysis with:

- Environment-aware configuration management
- Multi-environment support (local, testing, production)
- 2.5x average peaks formula with cache considerations
- Prophet-based ML analysis with anomaly detection
- Production-ready optimizations and monitoring
- Comprehensive logging and error handling
"""

import os
import sys
import logging
import argparse
import json
import yaml
import signal
import threading
import time
import multiprocessing
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import core modules
from scripts.utils.config_manager import ConfigManager, get_config_manager
from scripts.core.enhanced_rate_calculator import EnhancedRateCalculator
from scripts.core.data_fetcher import DataFetcher
from scripts.core.prophet_analyzer import ProphetAnalyzer
from scripts.core.prime_time_detector import PrimeTimeDetector
from scripts.core.cache_metrics_analyzer import CacheMetricsAnalyzer
from scripts.k8s_integration.configmap_manager import ConfigMapManager


class AdaptiveRateLimiter:
    """
    Main adaptive rate limiter orchestrator with environment awareness
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the adaptive rate limiter with environment-aware configuration"""
        # Initialize configuration manager
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.get_config()
        
        # Get environment information
        self.env_info = self.config_manager.get_environment_info()
        self.current_environment = self.env_info.name
        self.deployment_mode = self.env_info.deployment_mode
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Initialize core components
        self._initialize_components()
        
        # Log initialization
        self.logger.info("=" * 80)
        self.logger.info("TrendMaster-AI Adaptive Istio Rate Limiting System v3.0")
        self.logger.info("=" * 80)
        self.logger.info(f"Environment: {self.current_environment}")
        self.logger.info(f"Deployment Mode: {self.deployment_mode}")
        self.logger.info(f"Trickster Environment: {self.env_info.trickster_env}")
        self.logger.info(f"Partners: {len(self.env_info.partners)} configured")
        self.logger.info(f"APIs: {len(self.env_info.apis)} configured")
        self.logger.info(f"Dry Run: {self.env_info.dry_run}")
        self.logger.info("=" * 80)
    
    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive logging with environment awareness"""
        logger = logging.getLogger('trendmaster_ai')
        
        # Get log level from configuration
        log_level = self.config.get('COMMON', {}).get('LOG_LEVEL', 'INFO')
        logger.setLevel(getattr(logging, log_level))
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler (if not in local mode)
        if self.deployment_mode != 'local':
            log_dir = project_root / "logs"
            log_dir.mkdir(exist_ok=True)
            
            log_file = log_dir / f"adaptive_rate_limiter_{self.current_environment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            logger.info(f"Logging to file: {log_file}")
        
        return logger
    
    def _initialize_components(self) -> None:
        """Initialize all core components with environment awareness"""
        try:
            # Initialize Prometheus client
            from scripts.utils.prometheus_client import PrometheusClient
            prometheus_url = self.config_manager.get_prometheus_url()
            
            if prometheus_url and not self.env_info.dry_run:
                self.prometheus_client = PrometheusClient(prometheus_url)
                self.logger.info(f"Prometheus client initialized: {prometheus_url}")
            else:
                self.prometheus_client = None
                self.logger.info("Using mock data mode - Prometheus client not initialized")
            
            # Initialize core analyzers
            self.rate_calculator = EnhancedRateCalculator(self.config, self.prometheus_client, self.config_manager)
            self.data_fetcher = DataFetcher(self.config)
            self.prophet_analyzer = ProphetAnalyzer(self.config)
            self.prime_time_detector = PrimeTimeDetector(self.config)
            
            # Initialize cache analyzer with the new cache metrics collector
            if self.prometheus_client:
                from scripts.utils.cache_metrics import CacheMetricsCollector
                self.cache_analyzer = CacheMetricsCollector(self.prometheus_client, self.config)
            else:
                from scripts.utils.cache_metrics import MockCacheMetricsCollector
                self.cache_analyzer = MockCacheMetricsCollector()
            
            # Initialize Kubernetes integration
            k8s_config = self.config_manager.get_kubernetes_config()
            self.configmap_manager = ConfigMapManager(k8s_config=k8s_config)
            
            self.logger.info("All components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Component initialization failed: {e}", exc_info=True)
            raise
    
    def validate_environment(self) -> Dict[str, Any]:
        """Validate current environment configuration"""
        self.logger.info("Validating environment configuration...")
        
        validation_result = self.config_manager.validate_configuration()
        
        # Additional environment-specific validations
        partner_config = self.config_manager.get_partner_config()
        
        # Check if we have partners and APIs configured
        if not partner_config.get('partners'):
            validation_result['warnings'].append("No partners configured for current environment")
        
        if not partner_config.get('apis'):
            validation_result['warnings'].append("No APIs configured for current environment")
        
        # Check Prometheus connectivity (if not using mock data)
        if not self.env_info.dry_run and self.prometheus_client:
            try:
                # Test Prometheus connection
                test_query = 'up'
                result = self.prometheus_client.query(test_query)
                if not result:
                    validation_result['warnings'].append("Prometheus connectivity test failed")
            except Exception as e:
                validation_result['warnings'].append(f"Prometheus connectivity error: {e}")
        
        # Log validation results
        if validation_result['valid']:
            self.logger.info("✅ Environment validation passed")
        else:
            self.logger.error("❌ Environment validation failed")
        
        for warning in validation_result.get('warnings', []):
            self.logger.warning(f"⚠️  {warning}")
        
        for error in validation_result.get('errors', []):
            self.logger.error(f"❌ {error}")
        
        return validation_result
    
    def _get_partners_and_apis(self) -> tuple:
        """Get partners and APIs from appropriate source based on environment"""
        deployment_mode = self.config_manager.get_deployment_mode()
        
        if deployment_mode in ['production', 'testing']:
            # Get from existing ConfigMap
            return self._get_partners_apis_from_configmap()
        else:
            # Get from config.yaml (local development)
            return self._get_partners_apis_from_config()
    
    def _get_partners_apis_from_configmap(self) -> tuple:
        """Get partners and APIs from existing Istio ConfigMap"""
        try:
            # Fetch current ConfigMap from Kubernetes
            configmap_name = self.config.get('COMMON', {}).get('CONFIGMAP_NAME', 'ratelimit-config')
            current_configmap = self.configmap_manager.fetch_current_configmap(configmap_name)
            
            if current_configmap and 'parsed_config' in current_configmap:
                partners, apis = self._extract_partners_apis_from_configmap(current_configmap['parsed_config'])
                self.logger.info(f"Loaded from existing ConfigMap: {len(partners)} partners, {len(apis)} APIs")
                return partners, apis
            else:
                self.logger.warning("No existing ConfigMap found, falling back to config.yaml")
                return self._get_partners_apis_from_config()
                
        except Exception as e:
            self.logger.error(f"Failed to fetch ConfigMap: {e}")
            self.logger.warning("Falling back to config.yaml")
            return self._get_partners_apis_from_config()
    
    def _get_partners_apis_from_config(self) -> tuple:
        """Get partners and APIs from config.yaml"""
        partner_config = self.config_manager.get_partner_config()
        partners = partner_config.get('partners', [])
        apis = partner_config.get('apis', [])
        self.logger.info(f"Loaded from config.yaml: {len(partners)} partners, {len(apis)} APIs")
        return partners, apis
    
    def _extract_partners_apis_from_configmap(self, configmap_config: Dict) -> tuple:
        """Extract partners and APIs from ConfigMap structure"""
        partners = set()
        apis = set()
        
        descriptors = configmap_config.get('descriptors', [])
        for partner_desc in descriptors:
            partner = partner_desc.get('value', '')
            if partner:
                partners.add(partner)
                
                # Extract APIs from partner descriptors
                for path_desc in partner_desc.get('descriptors', []):
                    api_path = path_desc.get('value', '')
                    if api_path:
                        apis.add(api_path)
        
        return list(partners), list(apis)
    
    def run(self, partners: Optional[List[str]] = None, apis: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run the adaptive rate limiting analysis and configuration generation
        """
        start_time = datetime.now()
        self.logger.info("🚀 Starting adaptive rate limiting analysis")
        
        try:
            # Validate environment first
            validation_result = self.validate_environment()
            if not validation_result['valid']:
                raise RuntimeError("Environment validation failed")
            
            # Get partners and APIs from appropriate source
            if partners is None or apis is None:
                partners, apis = self._get_partners_and_apis()
            
            self.logger.info(f"Processing {len(partners)} partners and {len(apis)} APIs")
            
            # Initialize results structure
            results = {
                'environment': self.current_environment,
                'deployment_mode': self.deployment_mode,
                'timestamp': start_time.isoformat(),
                'partners_processed': [],
                'configmaps': [],
                'artifacts': [],
                'summary': {},
                'errors': []
            }
            
            # Process each partner/API combination
            all_rate_limits = {}
            
            for partner in partners:
                self.logger.info(f"📊 Processing partner: {partner}")
                partner_results = []
                
                for api in apis:
                    try:
                        # Validate partner/path combination
                        validation = self.rate_calculator.validate_partner_path(partner, api)
                        if not validation['valid']:
                            self.logger.warning(f"Skipping {partner}/{api}: {validation['reason']}")
                            continue
                        
                        # Process this partner/API combination
                        rate_limit_result = self._process_partner_api(partner, api)
                        if rate_limit_result:
                            partner_results.append(rate_limit_result)
                            
                            # Store for ConfigMap generation
                            if partner not in all_rate_limits:
                                all_rate_limits[partner] = {}
                            all_rate_limits[partner][api] = rate_limit_result
                    
                    except Exception as e:
                        error_msg = f"Error processing {partner}/{api}: {e}"
                        self.logger.error(error_msg)
                        results['errors'].append(error_msg)
                
                if partner_results:
                    results['partners_processed'].append({
                        'partner': partner,
                        'apis_processed': len(partner_results),
                        'results': partner_results
                    })
            
            # Generate ConfigMaps
            if all_rate_limits:
                configmaps = self._generate_configmaps(all_rate_limits)
                results['configmaps'] = configmaps
            
            # Generate analysis report
            report_path = self._generate_analysis_report(results)
            results['artifacts'].append(str(report_path))
            
            # Calculate summary statistics
            results['summary'] = self._calculate_summary(results)
            
            # Log completion
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"✅ Analysis completed in {duration:.2f} seconds")
            self.logger.info(f"📈 Generated {len(results['configmaps'])} ConfigMaps")
            self.logger.info(f"📄 Report saved to: {report_path}")
            
            return results
        
        except Exception as e:
            self.logger.error(f"❌ Analysis failed: {e}", exc_info=True)
            raise
    
    def _process_partner_api(self, partner: str, api: str) -> Optional[Dict[str, Any]]:
        """Process a single partner/API combination"""
        try:
            self.logger.info(f"Processing {partner}/{api}")
            
            # Fetch metrics data
            if self.env_info.dry_run or not self.prometheus_client:
                # Use mock data for local/dry-run mode
                clean_metrics, prime_time_data = self.data_fetcher.generate_mock_data(partner, api)
                self.logger.info(f"Using mock data for {partner}/{api}")
            else:
                # Fetch real data from Prometheus
                clean_metrics, prime_time_data = self.data_fetcher.fetch_and_clean_data(partner, api)
                self.logger.info(f"Fetched real data for {partner}/{api}: {len(clean_metrics)} points")
            
            if len(clean_metrics) == 0:
                self.logger.warning(f"No data available for {partner}/{api}")
                return None
            
            # Check if we should skip Prophet entirely for fastest processing
            skip_prophet = os.getenv('TRENDMASTER_SKIP_PROPHET', 'false').lower() == 'true'
            
            if skip_prophet:
                self.logger.info(f"Skipping Prophet analysis (TRENDMASTER_SKIP_PROPHET=true) for {partner}/{api}")
                prophet_analysis = self.prophet_analyzer._fallback_analysis(clean_metrics, partner, api)
            else:
                # Perform Prophet analysis with timeout protection
                prophet_analysis = self._analyze_with_timeout(clean_metrics, partner, api)
            
            # Detect prime time periods
            prime_time_periods = self.prime_time_detector.detect_prime_time_periods(
                clean_metrics, partner, api
            )
            
            # Get cache metrics if available
            cache_metrics = None
            if self.cache_analyzer and not self.env_info.dry_run:
                cache_metrics = self.cache_analyzer.get_cache_metrics(partner, api)
            
            # Calculate optimal rate limit
            rate_limit_result = self.rate_calculator.calculate_optimal_rate_limit(
                clean_metrics=clean_metrics,
                prime_time_data=prime_time_data,
                prophet_analysis=prophet_analysis,
                partner=partner,
                path=api,
                cache_metrics=cache_metrics
            )
            
            # Add additional metadata
            rate_limit_result.environment = self.current_environment
            
            self.logger.info(
                f"✅ {partner}/{api}: {rate_limit_result.recommended_rate_limit} req/min "
                f"(confidence: {rate_limit_result.confidence.get('confidence_level', 'unknown')})"
            )
            
            return {
                'partner': partner,
                'api': api,
                'rate_limit': rate_limit_result.recommended_rate_limit,
                'confidence': rate_limit_result.confidence,
                'rationale': rate_limit_result.rationale,
                'base_metrics': rate_limit_result.base_metrics,
                'calculation_method': rate_limit_result.calculation_method,
                'environment': rate_limit_result.environment
            }
        
        except Exception as e:
            self.logger.error(f"Failed to process {partner}/{api}: {e}")
            return None
    
    def _analyze_with_timeout(self, clean_metrics, partner: str, api: str, timeout_seconds: int = 60) -> Dict:
        """
        Perform Prophet analysis with aggressive timeout protection using multiprocessing
        """
        self.logger.info(f"Starting Prophet analysis with {timeout_seconds}s timeout for {partner}/{api}")
        
        def prophet_worker(queue, clean_metrics, partner, api):
            """Worker function that runs Prophet analysis in separate process"""
            try:
                # Set CI mode for faster processing
                os.environ['TRENDMASTER_CI_MODE'] = 'true'
                
                # Import here to avoid issues with multiprocessing
                from scripts.core.prophet_analyzer import ProphetAnalyzer
                analyzer = ProphetAnalyzer(self.config)
                
                self.logger.info(f"Worker process starting Prophet analysis for {partner}/{api}")
                result = analyzer.analyze_traffic_patterns(clean_metrics, partner, api)
                queue.put(('success', result))
                
            except Exception as e:
                self.logger.error(f"Prophet worker failed for {partner}/{api}: {e}")
                queue.put(('error', str(e)))
        
        # Try multiprocessing approach first
        try:
            # Create a queue for communication
            queue = multiprocessing.Queue()
            
            # Create and start process
            process = multiprocessing.Process(
                target=prophet_worker,
                args=(queue, clean_metrics, partner, api)
            )
            process.start()
            
            # Wait for completion with timeout
            process.join(timeout=timeout_seconds)
            
            if process.is_alive():
                # Timeout occurred - terminate the process
                self.logger.warning(f"Prophet analysis timed out after {timeout_seconds}s for {partner}/{api}, terminating process")
                process.terminate()
                process.join(timeout=5)  # Give it 5 seconds to terminate gracefully
                
                if process.is_alive():
                    # Force kill if it doesn't terminate
                    self.logger.warning(f"Force killing Prophet process for {partner}/{api}")
                    process.kill()
                    process.join()
                
                # Use fallback analysis
                self.logger.info(f"Using statistical fallback for {partner}/{api}")
                return self.prophet_analyzer._fallback_analysis(clean_metrics, partner, api)
            
            # Process completed - get result
            if not queue.empty():
                status, result = queue.get()
                if status == 'success':
                    self.logger.info(f"Prophet analysis completed successfully for {partner}/{api}")
                    return result
                else:
                    self.logger.warning(f"Prophet analysis failed for {partner}/{api}: {result}")
                    return self.prophet_analyzer._fallback_analysis(clean_metrics, partner, api)
            else:
                self.logger.warning(f"No result from Prophet process for {partner}/{api}")
                return self.prophet_analyzer._fallback_analysis(clean_metrics, partner, api)
                
        except Exception as e:
            self.logger.error(f"Multiprocessing Prophet analysis failed for {partner}/{api}: {e}")
        
        # Fallback to threading approach if multiprocessing fails
        self.logger.info(f"Falling back to threading approach for {partner}/{api}")
        return self._analyze_with_threading_timeout(clean_metrics, partner, api, timeout_seconds)
    
    def _analyze_with_threading_timeout(self, clean_metrics, partner: str, api: str, timeout_seconds: int = 30) -> Dict:
        """
        Fallback Prophet analysis with threading timeout
        """
        result = {}
        exception_occurred = None
        
        def target():
            nonlocal result, exception_occurred
            try:
                # Set CI mode temporarily for faster processing
                original_ci_mode = os.environ.get('TRENDMASTER_CI_MODE', '')
                os.environ['TRENDMASTER_CI_MODE'] = 'true'
                
                self.logger.info(f"Thread-based Prophet analysis starting for {partner}/{api}")
                
                try:
                    result = self.prophet_analyzer.analyze_traffic_patterns(
                        clean_metrics, partner, api
                    )
                finally:
                    # Restore original CI mode setting
                    if original_ci_mode:
                        os.environ['TRENDMASTER_CI_MODE'] = original_ci_mode
                    elif 'TRENDMASTER_CI_MODE' in os.environ:
                        del os.environ['TRENDMASTER_CI_MODE']
                        
            except Exception as e:
                exception_occurred = e
        
        # Create and start thread
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        
        # Wait for completion with timeout
        thread.join(timeout=timeout_seconds)
        
        if thread.is_alive():
            # Timeout occurred
            self.logger.warning(f"Threading Prophet analysis timed out after {timeout_seconds}s for {partner}/{api}")
            return self.prophet_analyzer._fallback_analysis(clean_metrics, partner, api)
        
        if exception_occurred:
            self.logger.warning(f"Threading Prophet analysis failed for {partner}/{api}: {exception_occurred}")
            return self.prophet_analyzer._fallback_analysis(clean_metrics, partner, api)
        
        return result
    
    def _generate_configmaps(self, rate_limits: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate Kubernetes ConfigMaps from rate limit results"""
        self.logger.info("📝 Generating Kubernetes ConfigMaps")
        
        try:
            configmaps = []
            
            # Convert rate_limits format to the expected format for ConfigMapManager
            # rate_limits is {partner: {api: result_dict}}
            # ConfigMapManager expects {(partner, api): result_dict}
            formatted_rate_limits = {}
            for partner, apis in rate_limits.items():
                for api, result in apis.items():
                    formatted_rate_limits[(partner, api)] = result
            
            # Generate ConfigMap for each partner or combined
            if self.config.get('COMMON', {}).get('SEPARATE_CONFIGMAPS_PER_PARTNER', False):
                # Separate ConfigMap per partner
                for partner, apis in rate_limits.items():
                    partner_formatted = {}
                    for api, result in apis.items():
                        partner_formatted[(partner, api)] = result
                    
                    configmap = self.configmap_manager.create_rate_limit_configmap(
                        rate_limits=partner_formatted,
                        configmap_name=f"ratelimit-config-{partner}",
                        env=self.current_environment
                    )
                    if configmap:
                        configmaps.append(configmap)
            else:
                # Single combined ConfigMap
                configmap = self.configmap_manager.create_rate_limit_configmap(
                    rate_limits=formatted_rate_limits,
                    configmap_name="ratelimit-config",
                    env=self.current_environment
                )
                if configmap:
                    configmaps.append(configmap)
            
            # Save ConfigMaps to output directory
            output_dir = project_root / "output"
            output_dir.mkdir(exist_ok=True)
            
            for i, configmap in enumerate(configmaps):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{self.deployment_mode}_configmap_{timestamp}"
                if len(configmaps) > 1:
                    filename += f"_{i+1}"
                filename += ".yaml"
                
                configmap_path = output_dir / filename
                with open(configmap_path, 'w') as f:
                    # Custom YAML formatting for proper ConfigMap structure
                    self._write_configmap_yaml(configmap, f)
                
                self.logger.info(f"💾 ConfigMap saved: {configmap_path}")
            
            return configmaps
        
        except Exception as e:
            self.logger.error(f"ConfigMap generation failed: {e}")
            return []
    
    def _write_configmap_yaml(self, configmap: Dict[str, Any], file_handle) -> None:
        """Write ConfigMap with proper YAML formatting for config.yaml field"""
        # Write the basic structure
        file_handle.write("apiVersion: v1\n")
        file_handle.write("kind: ConfigMap\n")
        file_handle.write("metadata:\n")
        
        # Write metadata
        metadata = configmap.get('metadata', {})
        if 'name' in metadata:
            file_handle.write(f"  name: {metadata['name']}\n")
        if 'namespace' in metadata:
            file_handle.write(f"  namespace: {metadata['namespace']}\n")
        
        # Write labels
        labels = metadata.get('labels', {})
        if labels:
            file_handle.write("  labels:\n")
            for key, value in labels.items():
                file_handle.write(f"    {key}: {value}\n")
        
        # Write data section with proper formatting for config.yaml
        file_handle.write("data:\n")
        data = configmap.get('data', {})
        
        for key, value in data.items():
            if key == 'config.yaml':
                # Use literal block scalar for config.yaml content
                file_handle.write(f"  {key}: |\n")
                
                # Parse the YAML content to reorder it properly
                import yaml
                try:
                    config_data = yaml.safe_load(value)
                    # Ensure domain comes first, then descriptors
                    ordered_content = f"    domain: {config_data.get('domain', 'global-ratelimit')}\n"
                    ordered_content += "    descriptors:\n"
                    
                    # Add descriptors
                    for desc in config_data.get('descriptors', []):
                        ordered_content += f"    - key: {desc.get('key', '')}\n"
                        ordered_content += f"      value: '{desc.get('value', '')}'\n"
                        ordered_content += "      descriptors:\n"
                        
                        for sub_desc in desc.get('descriptors', []):
                            ordered_content += f"      - key: {sub_desc.get('key', '')}\n"
                            ordered_content += f"        value: {sub_desc.get('value', '')}\n"
                            if 'rate_limit' in sub_desc:
                                rate_limit = sub_desc['rate_limit']
                                ordered_content += "        rate_limit:\n"
                                ordered_content += f"          unit: {rate_limit.get('unit', 'minute')}\n"
                                ordered_content += f"          requests_per_unit: {rate_limit.get('requests_per_unit', 1000)}\n"
                    
                    file_handle.write(ordered_content)
                    
                except Exception as e:
                    # Fallback to original method if parsing fails
                    for line in value.split('\n'):
                        if line.strip():
                            file_handle.write(f"    {line}\n")
                        else:
                            file_handle.write("\n")
            else:
                # Regular string value
                file_handle.write(f"  {key}: {value}\n")
    
    def _generate_analysis_report(self, results: Dict[str, Any]) -> Path:
        """Generate comprehensive analysis report"""
        output_dir = project_root / "output"
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = output_dir / f"analysis_report_{timestamp}.md"
        
        try:
            with open(report_path, 'w') as f:
                f.write(f"# TrendMaster-AI Rate Limiting Analysis Report\n\n")
                f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**Environment:** {self.current_environment}\n")
                f.write(f"**Deployment Mode:** {self.deployment_mode}\n")
                f.write(f"**Formula Version:** v3 (2.5x average peaks)\n\n")
                
                # Environment Information
                f.write("## Environment Configuration\n\n")
                f.write(f"- **Trickster Environment:** {self.env_info.trickster_env}\n")
                f.write(f"- **Prometheus URL:** {self.config_manager.get_prometheus_url()}\n")
                f.write(f"- **Dry Run Mode:** {self.env_info.dry_run}\n")
                f.write(f"- **Partners Configured:** {len(self.env_info.partners)}\n")
                f.write(f"- **APIs Configured:** {len(self.env_info.apis)}\n\n")
                
                # Summary Statistics
                summary = results.get('summary', {})
                f.write("## Summary Statistics\n\n")
                f.write(f"- **Total Partners Processed:** {summary.get('partners_processed', 0)}\n")
                f.write(f"- **Total API Endpoints:** {summary.get('apis_processed', 0)}\n")
                f.write(f"- **ConfigMaps Generated:** {len(results.get('configmaps', []))}\n")
                f.write(f"- **Average Rate Limit:** {summary.get('average_rate_limit', 0):.0f} req/min\n")
                f.write(f"- **High Confidence Results:** {summary.get('high_confidence_count', 0)}\n\n")
                
                # Detailed Results
                f.write("## Detailed Results\n\n")
                for partner_result in results.get('partners_processed', []):
                    partner = partner_result['partner']
                    f.write(f"### Partner: {partner}\n\n")
                    
                    for api_result in partner_result['results']:
                        api = api_result['api']
                        rate_limit = api_result['rate_limit']
                        confidence = api_result['confidence']
                        
                        f.write(f"#### API: `{api}`\n\n")
                        f.write(f"- **Rate Limit:** {rate_limit} requests/minute\n")
                        f.write(f"- **Confidence Level:** {confidence.get('confidence_level', 'unknown')}\n")
                        f.write(f"- **Confidence Score:** {confidence.get('overall_confidence', 0):.2f}\n")
                        f.write(f"- **Calculation Method:** {api_result['calculation_method']}\n")
                        f.write(f"- **Rationale:** {api_result['rationale']}\n\n")
                
                # Errors and Warnings
                if results.get('errors'):
                    f.write("## Errors and Warnings\n\n")
                    for error in results['errors']:
                        f.write(f"- ⚠️ {error}\n")
                    f.write("\n")
                
                # Configuration Details
                f.write("## Configuration Details\n\n")
                f.write("```yaml\n")
                f.write(yaml.dump({
                    'environment': self.current_environment,
                    'deployment_mode': self.deployment_mode,
                    'rate_calculation': self.config.get('COMMON', {}).get('RATE_CALCULATION', {}),
                    'partners': self.env_info.partners,
                    'apis_count': len(self.env_info.apis)
                }, default_flow_style=False))
                f.write("```\n")
            
            return report_path
        
        except Exception as e:
            self.logger.error(f"Report generation failed: {e}")
            return report_path
    
    def _calculate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate summary statistics from results"""
        summary = {
            'partners_processed': len(results.get('partners_processed', [])),
            'apis_processed': 0,
            'total_rate_limits': 0,
            'average_rate_limit': 0,
            'high_confidence_count': 0,
            'medium_confidence_count': 0,
            'low_confidence_count': 0
        }
        
        all_rate_limits = []
        
        for partner_result in results.get('partners_processed', []):
            summary['apis_processed'] += len(partner_result['results'])
            
            for api_result in partner_result['results']:
                rate_limit = api_result['rate_limit']
                confidence_level = api_result['confidence'].get('confidence_level', 'low')
                
                all_rate_limits.append(rate_limit)
                
                if confidence_level == 'high':
                    summary['high_confidence_count'] += 1
                elif confidence_level == 'medium':
                    summary['medium_confidence_count'] += 1
                else:
                    summary['low_confidence_count'] += 1
        
        if all_rate_limits:
            summary['total_rate_limits'] = len(all_rate_limits)
            summary['average_rate_limit'] = sum(all_rate_limits) / len(all_rate_limits)
            summary['min_rate_limit'] = min(all_rate_limits)
            summary['max_rate_limit'] = max(all_rate_limits)
        
        return summary


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='TrendMaster-AI Adaptive Istio Rate Limiting System v3.0',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default configuration (environment from env vars)
  python main.py
  
  # Run for specific environment
  ENVIRONMENT=production python main.py
  
  # Run with custom configuration file
  python main.py --config /path/to/config.yaml
  
  # Run with specific partners and APIs
  python main.py --partners CUSTOMER_ID_1,CUSTOMER_ID_3 --apis /api_v3/service/ENDPOINT_5
  
  # Validate configuration only
  python main.py --validate-only
  
  # Show environment information
  python main.py --show-env
        """
    )
    
    parser.add_argument('--config', '-c', help='Path to configuration file')
    parser.add_argument('--partners', help='Comma-separated list of partner IDs')
    parser.add_argument('--apis', help='Comma-separated list of API paths')
    parser.add_argument('--validate-only', action='store_true', help='Only validate configuration')
    parser.add_argument('--show-env', action='store_true', help='Show environment information')
    parser.add_argument('--output-format', choices=['json', 'yaml'], default='json', help='Output format')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--mode', choices=['fixed', 'adaptive'], default=None,
                       help='Calculation mode: fixed (simple 2.5x prime peak) or adaptive (full analysis)')
    
    args = parser.parse_args()
    
    try:
        # Initialize the adaptive rate limiter
        rate_limiter = AdaptiveRateLimiter(args.config)
        
        # Override calculation mode if specified via command line
        if args.mode:
            rate_limiter.rate_calculator.calculation_mode = args.mode
            rate_limiter.logger.info(f"Calculation mode overridden to: {args.mode}")
        
        # Handle special modes
        if args.show_env:
            env_info = rate_limiter.config_manager.get_environment_info()
            print("Environment Information:")
            print(f"  Name: {env_info.name}")
            print(f"  Deployment Mode: {env_info.deployment_mode}")
            print(f"  Trickster Environment: {env_info.trickster_env}")
            print(f"  Prometheus URL: {env_info.prometheus_url}")
            print(f"  Dry Run: {env_info.dry_run}")
            print(f"  Partners: {len(env_info.partners)} ({', '.join(env_info.partners)})")
            print(f"  APIs: {len(env_info.apis)}")
            return
        
        if args.validate_only:
            validation_result = rate_limiter.validate_environment()
            if args.output_format == 'yaml':
                print(yaml.dump(validation_result, default_flow_style=False))
            else:
                print(json.dumps(validation_result, indent=2))
            sys.exit(0 if validation_result['valid'] else 1)
        
        # Parse partners and APIs if provided
        partners = None
        if args.partners:
            partners = [p.strip() for p in args.partners.split(',')]
        
        apis = None
        if args.apis:
            apis = [a.strip() for a in args.apis.split(',')]
        
        # Run the analysis
        results = rate_limiter.run(partners=partners, apis=apis)
        
        # Output results
        if args.output_format == 'yaml':
            print(yaml.dump(results, default_flow_style=False, default=str))
        else:
            print(json.dumps(results, indent=2, default=str))
        
        # Exit with success
        sys.exit(0)
    
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()