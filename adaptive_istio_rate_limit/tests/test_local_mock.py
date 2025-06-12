#!/usr/bin/env python3
"""
Test script for local mode mock ConfigMap functionality
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

from scripts.main import AdaptiveRateLimiter
from scripts.core.config_manager import ConfigManager

def test_local_mock_configmap():
    """Test local mode with mock ConfigMap"""
    
    print("🧪 Testing Local Mode Mock ConfigMap Functionality")
    print("=" * 60)
    
    # Initialize with local mode
    orchestrator = AdaptiveRateLimiter('config/config.yaml')
    
    # Force local mode
    orchestrator.config_manager.deployment_mode = 'local'
    
    print(f"📍 Deployment Mode: {orchestrator.config_manager.deployment_mode}")
    print(f"📍 Is Local Mode: {orchestrator.config_manager.is_local_mode()}")
    
    # Test loading mock ConfigMap
    print("\n🔄 Loading Mock ConfigMap...")
    mock_configmap = orchestrator._load_mock_configmap()
    
    if mock_configmap:
        print("✅ Mock ConfigMap loaded successfully!")
        print(f"   Name: {mock_configmap['metadata']['name']}")
        print(f"   Namespace: {mock_configmap['metadata']['namespace']}")
        
        # Count existing combinations
        existing_combinations = []
        parsed_config = mock_configmap['parsed_config']
        
        for partner_desc in parsed_config.get('descriptors', []):
            partner = partner_desc.get('value', '')
            for path_desc in partner_desc.get('descriptors', []):
                path = path_desc.get('value', '')
                rate = path_desc.get('rate_limit', {}).get('requests_per_unit', 0)
                existing_combinations.append((partner, path, rate))
        
        print(f"   Found {len(existing_combinations)} existing partner/path combinations")
        
        # Show some examples
        print("\n📋 Existing Partner/Path Combinations (first 10):")
        for i, (partner, path, rate) in enumerate(existing_combinations[:10]):
            print(f"   {i+1:2d}. Partner {partner}: {path} (current: {rate} req/min)")
        
        if len(existing_combinations) > 10:
            print(f"   ... and {len(existing_combinations) - 10} more combinations")
        
        # Test selective update logic
        print(f"\n🔍 Testing Selective Update Logic...")
        print(f"   SELECTIVE_UPDATE setting: {orchestrator.config.get('SELECTIVE_UPDATE', False)}")
        
        # Test the _generate_configmap method in local mode
        print(f"\n🔄 Testing ConfigMap Generation in Local Mode...")
        
        # Mock some rate calculations for testing
        orchestrator.results = {
            'rate_calculations': {
                f"{existing_combinations[0][0]}_{existing_combinations[0][1]}": {
                    'partner': existing_combinations[0][0],
                    'path': existing_combinations[0][1],
                    'calculated_rate': 150,  # New calculated rate
                    'current_rate': existing_combinations[0][2],
                    'excluded': False
                },
                # Add a non-existing combination to test exclusion
                'new_partner_/api/new': {
                    'partner': 'new_partner',
                    'path': '/api/new',
                    'calculated_rate': 100,
                    'current_rate': 50,
                    'excluded': False
                }
            }
        }
        
        # Generate ConfigMap
        try:
            new_configmap = orchestrator._generate_configmap()
            if new_configmap:
                print("✅ ConfigMap generated successfully in local mode!")
                
                # Check if selective updates worked
                updated_config = new_configmap['data']['config.yaml']
                updated_combinations = []
                
                for partner_desc in updated_config.get('descriptors', []):
                    partner = partner_desc.get('value', '')
                    for path_desc in partner_desc.get('descriptors', []):
                        path = path_desc.get('value', '')
                        rate = path_desc.get('rate_limit', {}).get('requests_per_unit', 0)
                        updated_combinations.append((partner, path, rate))
                
                print(f"   Updated ConfigMap has {len(updated_combinations)} combinations")
                
                # Check if the first combination was updated
                first_combo = existing_combinations[0]
                found_updated = False
                for partner, path, rate in updated_combinations:
                    if partner == first_combo[0] and path == first_combo[1]:
                        print(f"   ✅ Found updated combination: Partner {partner}: {path}")
                        print(f"      Original rate: {first_combo[2]} req/min")
                        print(f"      Updated rate:  {rate} req/min")
                        found_updated = True
                        break
                
                if not found_updated:
                    print(f"   ❌ Could not find updated combination")
                
                # Check that new combinations were not added
                if len(updated_combinations) == len(existing_combinations):
                    print(f"   ✅ Selective update working: No new combinations added")
                else:
                    print(f"   ⚠️  Combination count changed: {len(existing_combinations)} -> {len(updated_combinations)}")
                
            else:
                print("❌ Failed to generate ConfigMap")
                
        except Exception as e:
            print(f"❌ Error generating ConfigMap: {e}")
            import traceback
            traceback.print_exc()
        
    else:
        print("❌ Failed to load mock ConfigMap")
    
    print(f"\n🏁 Local Mode Mock ConfigMap Test Complete!")

if __name__ == "__main__":
    test_local_mock_configmap()