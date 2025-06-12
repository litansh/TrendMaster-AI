#!/usr/bin/env python3
"""
Test script to demonstrate selective ConfigMap updates
"""

import sys
import os
import yaml
from datetime import datetime

# Add the scripts directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts'))

from core.config_manager import ConfigManager
from k8s_integration.configmap_manager import ConfigMapManager

def main():
    """Test selective update functionality"""
    
    print("=== Testing Selective ConfigMap Update ===\n")
    
    # Initialize configuration
    config_manager = ConfigManager()
    config = config_manager.get_config()
    
    # Initialize ConfigMap manager
    k8s_config = config_manager.get_kubernetes_config()
    configmap_manager = ConfigMapManager(k8s_config)
    
    # Fetch current ConfigMap
    configmap_name = config.get('OPERATOR_CONFIG', {}).get('configmap_name', 'ratelimit-config')
    print(f"Fetching current ConfigMap: {configmap_name}")
    
    current_configmap = configmap_manager.fetch_current_configmap(configmap_name)
    if not current_configmap:
        print("❌ No existing ConfigMap found")
        return
    
    print(f"✅ Found existing ConfigMap with {len(current_configmap.get('parsed_config', {}).get('descriptors', []))} partner descriptors")
    
    # Extract existing combinations
    existing_combinations = set()
    for partner_desc in current_configmap.get('parsed_config', {}).get('descriptors', []):
        partner = partner_desc.get('value', '')
        for path_desc in partner_desc.get('descriptors', []):
            path = path_desc.get('value', '')
            existing_combinations.add((partner, path))
    
    print(f"📋 Found {len(existing_combinations)} existing partner/path combinations:")
    for i, (partner, path) in enumerate(sorted(list(existing_combinations)[:5])):  # Show first 5
        print(f"   {i+1}. Partner {partner}: {path}")
    if len(existing_combinations) > 5:
        print(f"   ... and {len(existing_combinations) - 5} more")
    
    # Create mock rate limits (some existing, some new)
    mock_rate_limits = {}
    
    # Add updates for existing combinations (first 3)
    existing_list = list(existing_combinations)
    for i, combo in enumerate(existing_list[:3]):
        mock_rate_limits[combo] = {
            'recommended_rate_limit': 500 + (i * 100),  # 500, 600, 700
            'confidence': {'confidence_level': 'high'}
        }
    
    # Add some new combinations that shouldn't be added in selective mode
    mock_rate_limits[('999', '/api_v3/service/test/action/new')] = {
        'recommended_rate_limit': 1000,
        'confidence': {'confidence_level': 'medium'}
    }
    mock_rate_limits[('888', '/api_v3/service/another/action/new')] = {
        'recommended_rate_limit': 2000,
        'confidence': {'confidence_level': 'low'}
    }
    
    print(f"\n🔄 Testing selective update with {len(mock_rate_limits)} rate limits:")
    print(f"   - {len([k for k in mock_rate_limits.keys() if k in existing_combinations])} existing combinations to update")
    print(f"   - {len([k for k in mock_rate_limits.keys() if k not in existing_combinations])} new combinations (should be skipped)")
    
    # Test selective update
    print("\n🧪 Generating ConfigMap with selective_update=True...")
    selective_configmap = configmap_manager.generate_configmap(
        mock_rate_limits,
        current_configmap,
        config.get('ENV', 'orp2'),
        selective_update=True
    )
    
    # Test full update
    print("🧪 Generating ConfigMap with selective_update=False...")
    full_configmap = configmap_manager.generate_configmap(
        mock_rate_limits,
        current_configmap,
        config.get('ENV', 'orp2'),
        selective_update=False
    )
    
    # Compare results
    selective_combinations = set()
    for partner_desc in selective_configmap.get('parsed_config', {}).get('descriptors', []):
        partner = partner_desc.get('value', '')
        for path_desc in partner_desc.get('descriptors', []):
            path = path_desc.get('value', '')
            selective_combinations.add((partner, path))
    
    full_combinations = set()
    for partner_desc in full_configmap.get('parsed_config', {}).get('descriptors', []):
        partner = partner_desc.get('value', '')
        for path_desc in partner_desc.get('descriptors', []):
            path = path_desc.get('value', '')
            full_combinations.add((partner, path))
    
    print(f"\n📊 Results Comparison:")
    print(f"   Original ConfigMap: {len(existing_combinations)} combinations")
    print(f"   Selective Update:   {len(selective_combinations)} combinations")
    print(f"   Full Update:        {len(full_combinations)} combinations")
    
    # Show what would be added in full update
    new_in_full = full_combinations - existing_combinations
    if new_in_full:
        print(f"\n➕ Full update would add {len(new_in_full)} new combinations:")
        for partner, path in sorted(list(new_in_full)):
            print(f"   - Partner {partner}: {path}")
    
    # Show what was preserved in selective update
    preserved_in_selective = selective_combinations & existing_combinations
    print(f"\n✅ Selective update preserved {len(preserved_in_selective)} existing combinations")
    
    # Generate diff report
    print("\n📝 Generating diff report...")
    diff_report = configmap_manager.generate_diff_report(current_configmap, selective_configmap)
    
    if diff_report['has_changes']:
        changes = diff_report['changes_summary']
        print(f"   - Modified: {len(changes['modified'])} rate limits")
        print(f"   - Added: {len(changes['added'])} rate limits")
        print(f"   - Removed: {len(changes['removed'])} rate limits")
        
        if changes['modified']:
            print("\n🔄 Modified rate limits:")
            for change in changes['modified'][:3]:  # Show first 3
                print(f"   - {change['partner']}/{change['path']}: {change['old_rate']} → {change['new_rate']} ({change['change_percent']:+.1f}%)")
    else:
        print("   - No changes detected")
    
    print(f"\n✅ Selective update test completed!")
    print(f"💡 In production, set SELECTIVE_UPDATE: true to only modify existing partner/path combinations")

if __name__ == "__main__":
    main()