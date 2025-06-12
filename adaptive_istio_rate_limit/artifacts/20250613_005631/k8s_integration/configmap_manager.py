import yaml
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException

class ConfigMapManager:
    """
    Kubernetes ConfigMap manager for handling Istio rate limit configurations
    """
    
    def __init__(self, k8s_config: Dict):
        self.k8s_config = k8s_config
        self.namespace = k8s_config.get('namespace', 'istio-system')
        self.context = k8s_config.get('context')
        self.config_file = k8s_config.get('config_file')
        self.logger = logging.getLogger(__name__)
        
        # Initialize Kubernetes client
        self.v1_client = self._setup_kubernetes_client()
        
    def _setup_kubernetes_client(self) -> Optional[client.CoreV1Api]:
        """
        Setup Kubernetes client with proper configuration
        """
        try:
            if self.config_file and os.path.exists(os.path.expanduser(self.config_file)):
                k8s_config.load_kube_config(
                    config_file=os.path.expanduser(self.config_file),
                    context=self.context
                )
            else:
                # Try in-cluster config if file doesn't exist
                k8s_config.load_incluster_config()
            
            v1_client = client.CoreV1Api()
            
            # Test the connection
            try:
                v1_client.list_namespace(limit=1)
                self.logger.info(f"Successfully connected to Kubernetes cluster (context: {self.context})")
                return v1_client
            except ApiException as e:
                self.logger.error(f"Failed to connect to Kubernetes: {e}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to setup Kubernetes client: {e}")
            return None
    
    def fetch_current_configmap(self, configmap_name: str) -> Optional[Dict]:
        """
        Fetch current ConfigMap from Kubernetes cluster
        """
        if not self.v1_client:
            self.logger.error("Kubernetes client not available")
            return None
        
        try:
            self.logger.info(f"Fetching ConfigMap '{configmap_name}' from namespace '{self.namespace}'")
            
            configmap = self.v1_client.read_namespaced_config_map(
                name=configmap_name,
                namespace=self.namespace
            )
            
            # Parse the ConfigMap data
            parsed_data = self._parse_configmap_data(configmap)
            
            self.logger.info(f"Successfully fetched ConfigMap '{configmap_name}'")
            return parsed_data
            
        except ApiException as e:
            if e.status == 404:
                self.logger.warning(f"ConfigMap '{configmap_name}' not found in namespace '{self.namespace}'")
            else:
                self.logger.error(f"Failed to fetch ConfigMap '{configmap_name}': {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error fetching ConfigMap '{configmap_name}': {e}")
            return None
    
    def _parse_configmap_data(self, configmap) -> Dict:
        """
        Parse ConfigMap data into a structured format
        """
        parsed_data = {
            'metadata': {
                'name': configmap.metadata.name,
                'namespace': configmap.metadata.namespace,
                'labels': configmap.metadata.labels or {},
                'creation_timestamp': configmap.metadata.creation_timestamp.isoformat() if configmap.metadata.creation_timestamp else None,
                'resource_version': configmap.metadata.resource_version
            },
            'data': {}
        }
        
        if configmap.data:
            for key, value in configmap.data.items():
                if key == 'config.yaml':
                    try:
                        # Parse the YAML content
                        parsed_data['data'][key] = yaml.safe_load(value)
                        parsed_data['parsed_config'] = yaml.safe_load(value)
                    except yaml.YAMLError as e:
                        self.logger.error(f"Failed to parse YAML in ConfigMap data: {e}")
                        parsed_data['data'][key] = value
                else:
                    parsed_data['data'][key] = value
        
        return parsed_data
    
    def generate_configmap(self, rate_limits: Dict[str, Dict],
                          template_configmap: Optional[Dict] = None,
                          env: str = "orp2",
                          selective_update: bool = True) -> Dict:
        """
        Generate new ConfigMap with updated rate limits
        
        Args:
            rate_limits: Calculated rate limits from analysis
            template_configmap: Existing ConfigMap to use as template
            env: Environment name
            selective_update: If True, only update existing partner/path combinations
        """
        # Use template if provided, otherwise create from scratch
        if template_configmap:
            new_configmap = template_configmap.copy()
        else:
            new_configmap = self._create_default_configmap_structure(env)
        
        # Build the rate limit configuration
        if selective_update and template_configmap:
            rate_limit_config = self._build_selective_rate_limit_config(
                rate_limits, template_configmap.get('parsed_config', {})
            )
        else:
            rate_limit_config = self._build_rate_limit_config(rate_limits)
        
        # Update the ConfigMap data
        config_yaml = yaml.dump(rate_limit_config, default_flow_style=False, indent=2)
        new_configmap['data']['config.yaml'] = config_yaml
        new_configmap['parsed_config'] = rate_limit_config
        
        # Update metadata
        new_configmap['metadata']['labels']['updated_by'] = 'adaptive-rate-limiter'
        new_configmap['metadata']['labels']['updated_at'] = datetime.now().strftime('%Y%m%d-%H%M%S')
        
        return new_configmap
    
    def _create_default_configmap_structure(self, env: str) -> Dict:
        """
        Create default ConfigMap structure
        """
        return {
            'apiVersion': 'v1',
            'kind': 'ConfigMap',
            'metadata': {
                'name': 'ratelimit-config',
                'namespace': self.namespace,
                'labels': {
                    'app.kubernetes.io/instance': f'{env}-istio-ratelimit',
                    'managed_by': 'adaptive-rate-limiter'
                }
            },
            'data': {}
        }
    
    def _build_rate_limit_config(self, rate_limits: Dict[str, Dict]) -> Dict:
        """
        Build rate limit configuration structure
        """
        config = {
            'domain': 'global-ratelimit',
            'descriptors': []
        }
        
        # Group rate limits by partner
        partners_data = {}
        for key, rate_data in rate_limits.items():
            if isinstance(key, tuple) and len(key) == 2:
                partner, path = key
            else:
                continue
            
            if partner not in partners_data:
                partners_data[partner] = []
            
            partners_data[partner].append({
                'path': path,
                'rate_limit': rate_data.get('recommended_rate_limit', 1000),
                'unit': 'minute'
            })
        
        # Build descriptors structure
        for partner, paths_data in partners_data.items():
            partner_descriptor = {
                'key': 'PARTNER',
                'value': partner,
                'descriptors': []
            }
            
            for path_data in paths_data:
                path_descriptor = {
                    'key': 'PATH',
                    'value': path_data['path'],
                    'rate_limit': {
                        'unit': path_data['unit'],
                        'requests_per_unit': path_data['rate_limit']
                    }
                }
                partner_descriptor['descriptors'].append(path_descriptor)
            
            config['descriptors'].append(partner_descriptor)
        
        return config
    
    def _build_selective_rate_limit_config(self, rate_limits: Dict[str, Dict],
                                         existing_config: Dict) -> Dict:
        """
        Build rate limit configuration that only updates existing partner/path combinations
        
        Args:
            rate_limits: New calculated rate limits
            existing_config: Current ConfigMap configuration
        
        Returns:
            Updated configuration with only existing combinations modified
        """
        # Start with existing configuration
        config = existing_config.copy() if existing_config else {
            'domain': 'global-ratelimit',
            'descriptors': []
        }
        
        # Extract existing partner/path combinations
        existing_combinations = set()
        for partner_desc in config.get('descriptors', []):
            partner = partner_desc.get('value', '')
            for path_desc in partner_desc.get('descriptors', []):
                path = path_desc.get('value', '')
                existing_combinations.add((partner, path))
        
        # Only update rate limits for existing combinations
        updated_count = 0
        for key, rate_data in rate_limits.items():
            if isinstance(key, tuple) and len(key) == 2:
                partner, path = key
                
                # Only process if this partner/path combination already exists
                if (partner, path) in existing_combinations:
                    new_rate = rate_data.get('recommended_rate_limit', 1000)
                    
                    # Find and update the specific rate limit
                    for partner_desc in config['descriptors']:
                        if partner_desc.get('value') == partner:
                            for path_desc in partner_desc.get('descriptors', []):
                                if path_desc.get('value') == path:
                                    # Update the rate limit
                                    if 'rate_limit' not in path_desc:
                                        path_desc['rate_limit'] = {}
                                    path_desc['rate_limit']['requests_per_unit'] = new_rate
                                    path_desc['rate_limit']['unit'] = 'minute'
                                    updated_count += 1
                                    break
                            break
        
        self.logger.info(f"Selective update: Modified {updated_count} existing rate limits, "
                        f"skipped {len(rate_limits) - updated_count} new combinations")
        
        return config
    
    def update_configmap(self, configmap_name: str, new_configmap_data: Dict, 
                        dry_run: bool = False) -> Optional[Dict]:
        """
        Update ConfigMap in Kubernetes cluster
        """
        if not self.v1_client:
            self.logger.error("Kubernetes client not available")
            return None
        
        try:
            # Prepare the ConfigMap body for Kubernetes API
            configmap_body = self._prepare_configmap_body(new_configmap_data)
            
            if dry_run:
                self.logger.info(f"DRY RUN: Would update ConfigMap '{configmap_name}'")
                return self._validate_configmap(configmap_body)
            
            # Backup current ConfigMap
            current_configmap = self.fetch_current_configmap(configmap_name)
            if current_configmap:
                self._backup_configmap(current_configmap, configmap_name)
            
            # Apply the update
            self.logger.info(f"Updating ConfigMap '{configmap_name}' in namespace '{self.namespace}'")
            
            if current_configmap:
                # Update existing ConfigMap
                response = self.v1_client.patch_namespaced_config_map(
                    name=configmap_name,
                    namespace=self.namespace,
                    body=configmap_body
                )
            else:
                # Create new ConfigMap
                response = self.v1_client.create_namespaced_config_map(
                    namespace=self.namespace,
                    body=configmap_body
                )
            
            self.logger.info(f"Successfully updated ConfigMap '{configmap_name}'")
            return self._parse_configmap_data(response)
            
        except ApiException as e:
            self.logger.error(f"Failed to update ConfigMap '{configmap_name}': {e}")
            if e.status == 422:
                self.logger.error("ConfigMap validation failed - check the configuration format")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error updating ConfigMap '{configmap_name}': {e}")
            return None
    
    def _prepare_configmap_body(self, configmap_data: Dict) -> client.V1ConfigMap:
        """
        Prepare ConfigMap body for Kubernetes API
        """
        # Extract metadata
        metadata = configmap_data.get('metadata', {})
        
        # Prepare V1ObjectMeta
        k8s_metadata = client.V1ObjectMeta(
            name=metadata.get('name', 'ratelimit-config'),
            namespace=metadata.get('namespace', self.namespace),
            labels=metadata.get('labels', {})
        )
        
        # Prepare data - convert parsed config back to YAML string
        data = {}
        for key, value in configmap_data.get('data', {}).items():
            if key == 'config.yaml' and isinstance(value, dict):
                data[key] = yaml.dump(value, default_flow_style=False, indent=2)
            else:
                data[key] = str(value)
        
        return client.V1ConfigMap(
            api_version='v1',
            kind='ConfigMap',
            metadata=k8s_metadata,
            data=data
        )
    
    def _validate_configmap(self, configmap_body: client.V1ConfigMap) -> Dict:
        """
        Validate ConfigMap structure and content
        """
        validation_result = {
            'valid': True,
            'issues': [],
            'warnings': []
        }
        
        # Check required fields
        if not configmap_body.metadata or not configmap_body.metadata.name:
            validation_result['valid'] = False
            validation_result['issues'].append('ConfigMap name is required')
        
        if not configmap_body.data or 'config.yaml' not in configmap_body.data:
            validation_result['valid'] = False
            validation_result['issues'].append('config.yaml data is required')
        
        # Validate YAML content
        if configmap_body.data and 'config.yaml' in configmap_body.data:
            try:
                config_data = yaml.safe_load(configmap_body.data['config.yaml'])
                
                # Check required structure
                if not isinstance(config_data, dict):
                    validation_result['valid'] = False
                    validation_result['issues'].append('config.yaml must be a valid YAML object')
                
                elif 'domain' not in config_data or 'descriptors' not in config_data:
                    validation_result['valid'] = False
                    validation_result['issues'].append('config.yaml must contain domain and descriptors')
                
                # Check descriptors structure
                elif not isinstance(config_data.get('descriptors'), list):
                    validation_result['valid'] = False
                    validation_result['issues'].append('descriptors must be a list')
                
                else:
                    # Validate each descriptor
                    for i, descriptor in enumerate(config_data['descriptors']):
                        if not isinstance(descriptor, dict):
                            validation_result['issues'].append(f'Descriptor {i} must be an object')
                            continue
                        
                        if 'key' not in descriptor or 'value' not in descriptor:
                            validation_result['issues'].append(f'Descriptor {i} missing key or value')
                        
                        if 'descriptors' in descriptor:
                            for j, sub_desc in enumerate(descriptor['descriptors']):
                                if 'rate_limit' in sub_desc:
                                    rate_limit = sub_desc['rate_limit']
                                    if 'requests_per_unit' not in rate_limit:
                                        validation_result['warnings'].append(
                                            f'Descriptor {i}.{j} missing requests_per_unit'
                                        )
            
            except yaml.YAMLError as e:
                validation_result['valid'] = False
                validation_result['issues'].append(f'Invalid YAML in config.yaml: {e}')
        
        return validation_result
    
    def _backup_configmap(self, configmap_data: Dict, configmap_name: str):
        """
        Backup ConfigMap before updates
        """
        try:
            backup_dir = 'backups'
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f'{configmap_name}_backup_{timestamp}.yaml'
            backup_path = os.path.join(backup_dir, backup_filename)
            
            with open(backup_path, 'w') as f:
                yaml.dump(configmap_data, f, default_flow_style=False, indent=2)
            
            self.logger.info(f"ConfigMap backed up to: {backup_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to backup ConfigMap: {e}")
    
    def generate_diff_report(self, current_configmap: Dict, proposed_configmap: Dict) -> Dict:
        """
        Generate detailed diff report between current and proposed ConfigMaps
        """
        import difflib
        
        # Convert to YAML strings for comparison
        current_yaml = yaml.dump(
            current_configmap.get('parsed_config', {}), 
            default_flow_style=False, 
            indent=2
        )
        proposed_yaml = yaml.dump(
            proposed_configmap.get('parsed_config', {}), 
            default_flow_style=False, 
            indent=2
        )
        
        # Generate unified diff
        diff_lines = list(difflib.unified_diff(
            current_yaml.splitlines(keepends=True),
            proposed_yaml.splitlines(keepends=True),
            fromfile='current_configmap.yaml',
            tofile='proposed_configmap.yaml',
            lineterm=''
        ))
        
        # Analyze changes
        changes_summary = self._analyze_rate_limit_changes(
            current_configmap.get('parsed_config', {}),
            proposed_configmap.get('parsed_config', {})
        )
        
        return {
            'diff_lines': diff_lines,
            'changes_summary': changes_summary,
            'has_changes': len(diff_lines) > 0
        }
    
    def _analyze_rate_limit_changes(self, current_config: Dict, proposed_config: Dict) -> Dict:
        """
        Analyze specific rate limit changes
        """
        changes = {
            'added': [],
            'removed': [],
            'modified': [],
            'unchanged': []
        }
        
        # Extract rate limits from both configs
        current_rates = self._extract_rate_limits(current_config)
        proposed_rates = self._extract_rate_limits(proposed_config)
        
        # Find changes
        all_keys = set(current_rates.keys()) | set(proposed_rates.keys())
        
        for key in all_keys:
            if key not in current_rates:
                changes['added'].append({
                    'partner': key[0] if isinstance(key, tuple) else key,
                    'path': key[1] if isinstance(key, tuple) else '',
                    'new_rate': proposed_rates[key]
                })
            elif key not in proposed_rates:
                changes['removed'].append({
                    'partner': key[0] if isinstance(key, tuple) else key,
                    'path': key[1] if isinstance(key, tuple) else '',
                    'old_rate': current_rates[key]
                })
            elif current_rates[key] != proposed_rates[key]:
                changes['modified'].append({
                    'partner': key[0] if isinstance(key, tuple) else key,
                    'path': key[1] if isinstance(key, tuple) else '',
                    'old_rate': current_rates[key],
                    'new_rate': proposed_rates[key],
                    'change_percent': ((proposed_rates[key] - current_rates[key]) / current_rates[key]) * 100
                })
            else:
                changes['unchanged'].append({
                    'partner': key[0] if isinstance(key, tuple) else key,
                    'path': key[1] if isinstance(key, tuple) else '',
                    'rate': current_rates[key]
                })
        
        return changes
    
    def _extract_rate_limits(self, config: Dict) -> Dict:
        """
        Extract rate limits from configuration into a flat dictionary
        """
        rate_limits = {}
        
        descriptors = config.get('descriptors', [])
        for partner_desc in descriptors:
            partner = partner_desc.get('value', '')
            
            for path_desc in partner_desc.get('descriptors', []):
                path = path_desc.get('value', '')
                rate_limit_info = path_desc.get('rate_limit', {})
                rate = rate_limit_info.get('requests_per_unit', 0)
                
                rate_limits[(partner, path)] = rate
        
        return rate_limits
    
    def list_configmaps(self, label_selector: Optional[str] = None) -> List[Dict]:
        """
        List ConfigMaps in the namespace
        """
        if not self.v1_client:
            self.logger.error("Kubernetes client not available")
            return []
        
        try:
            configmaps = self.v1_client.list_namespaced_config_map(
                namespace=self.namespace,
                label_selector=label_selector
            )
            
            result = []
            for cm in configmaps.items:
                result.append({
                    'name': cm.metadata.name,
                    'namespace': cm.metadata.namespace,
                    'labels': cm.metadata.labels or {},
                    'creation_timestamp': cm.metadata.creation_timestamp.isoformat() if cm.metadata.creation_timestamp else None,
                    'data_keys': list(cm.data.keys()) if cm.data else []
                })
            
            return result
            
        except ApiException as e:
            self.logger.error(f"Failed to list ConfigMaps: {e}")
            return []
    
    def create_rate_limit_configmap(self, rate_limits: Dict[str, Dict],
                                  configmap_name: str = "ratelimit-config",
                                  env: str = "orp2") -> Optional[Dict]:
        """
        Create a new rate limit ConfigMap with calculated rate limits
        
        Args:
            rate_limits: Dictionary of calculated rate limits
            configmap_name: Name for the ConfigMap
            env: Environment name
            
        Returns:
            Generated ConfigMap data or None if failed
        """
        try:
            # Generate the ConfigMap
            new_configmap = self.generate_configmap(
                rate_limits=rate_limits,
                template_configmap=None,
                env=env,
                selective_update=False
            )
            
            # Set the ConfigMap name
            new_configmap['metadata']['name'] = configmap_name
            
            self.logger.info(f"Created ConfigMap '{configmap_name}' with {len(rate_limits)} rate limits")
            
            return new_configmap
            
        except Exception as e:
            self.logger.error(f"Failed to create rate limit ConfigMap: {e}")
            return None