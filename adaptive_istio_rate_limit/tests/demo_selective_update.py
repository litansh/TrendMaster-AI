#!/usr/bin/env python3
"""
Demo script to show how selective ConfigMap updates work
"""

import yaml

def demo_selective_update():
    """Demonstrate selective vs full ConfigMap updates"""
    
    print("=== Selective ConfigMap Update Demo ===\n")
    
    # Simulate existing ConfigMap
    existing_configmap = {
        'domain': 'global-ratelimit',
        'descriptors': [
            {
                'key': 'PARTNER',
                'value': 'CUSTOMER_ID_1',
                'descriptors': [
                    {
                        'key': 'PATH',
                        'value': '/api_v3/service/ENDPOINT_2',
                        'rate_limit': {
                            'unit': 'minute',
                            'requests_per_unit': 1000
                        }
                    },
                    {
                        'key': 'PATH',
                        'value': '/api_v3/service/ENDPOINT_7',
                        'rate_limit': {
                            'unit': 'minute',
                            'requests_per_unit': 500
                        }
                    }
                ]
            },
            {
                'key': 'PARTNER',
                'value': 'CUSTOMER_ID_3',
                'descriptors': [
                    {
                        'key': 'PATH',
                        'value': '/api_v3/service/ENDPOINT_8',
                        'rate_limit': {
                            'unit': 'minute',
                            'requests_per_unit': 800
                        }
                    }
                ]
            }
        ]
    }
    
    # New rate limits from analysis (some existing, some new)
    new_rate_limits = {
        ('CUSTOMER_ID_1', '/api_v3/service/ENDPOINT_2'): {'recommended_rate_limit': 1500},  # Existing - UPDATE
        ('CUSTOMER_ID_1', '/api_v3/service/ENDPOINT_7'): {'recommended_rate_limit': 700},   # Existing - UPDATE
        ('CUSTOMER_ID_3', '/api_v3/service/ENDPOINT_8'): {'recommended_rate_limit': 1200},   # Existing - UPDATE
        ('CUSTOMER_ID_1', '/api_v3/service/ENDPOINT_9'): {'recommended_rate_limit': 300},   # New - SKIP in selective
        ('999', '/api_v3/service/TEST_ENDPOINT/action/run'): {'recommended_rate_limit': 600},     # New - SKIP in selective
    }
    
    print("📋 EXISTING ConfigMap:")
    print("   Partner CUSTOMER_ID_1:")
    print("     - /api_v3/service/ENDPOINT_2: 1000 req/min")
    print("     - /api_v3/service/ENDPOINT_7: 500 req/min")
    print("   Partner CUSTOMER_ID_3:")
    print("     - /api_v3/service/ENDPOINT_8: 800 req/min")
    
    print(f"\n🔄 NEW RATE LIMITS from analysis ({len(new_rate_limits)} total):")
    for (partner, path), data in new_rate_limits.items():
        rate = data['recommended_rate_limit']
        is_existing = any(
            partner_desc.get('value') == partner and 
            any(path_desc.get('value') == path for path_desc in partner_desc.get('descriptors', []))
            for partner_desc in existing_configmap['descriptors']
        )
        status = "✅ EXISTING" if is_existing else "🆕 NEW"
        print(f"   {status} - Partner {partner}: {path} → {rate} req/min")
    
    # Simulate selective update
    print(f"\n🎯 SELECTIVE UPDATE (SELECTIVE_UPDATE: true):")
    print("   ✅ Updates ONLY existing partner/path combinations")
    print("   ❌ Skips new combinations to avoid adding unwanted entries")
    print("\n   Result:")
    print("   Partner CUSTOMER_ID_1:")
    print("     - /api_v3/service/ENDPOINT_2: 1000 → 1500 req/min ✅ UPDATED")
    print("     - /api_v3/service/ENDPOINT_7: 500 → 700 req/min ✅ UPDATED")
    print("   Partner CUSTOMER_ID_3:")
    print("     - /api_v3/service/ENDPOINT_8: 800 → 1200 req/min ✅ UPDATED")
    print("   📊 Total: 3 existing combinations updated, 2 new combinations skipped")
    
    # Simulate full update
    print(f"\n🌐 FULL UPDATE (SELECTIVE_UPDATE: false):")
    print("   ✅ Updates existing partner/path combinations")
    print("   ➕ Adds ALL new combinations found in Prometheus data")
    print("\n   Result:")
    print("   Partner CUSTOMER_ID_1:")
    print("     - /api_v3/service/ENDPOINT_2: 1000 → 1500 req/min ✅ UPDATED")
    print("     - /api_v3/service/ENDPOINT_7: 500 → 700 req/min ✅ UPDATED")
    print("     - /api_v3/service/ENDPOINT_9: 300 req/min ➕ ADDED")
    print("   Partner CUSTOMER_ID_3:")
    print("     - /api_v3/service/ENDPOINT_8: 800 → 1200 req/min ✅ UPDATED")
    print("   Partner 999:")
    print("     - /api_v3/service/TEST_ENDPOINT/action/run: 600 req/min ➕ ADDED")
    print("   📊 Total: 3 existing combinations updated, 2 new combinations added")
    
    print(f"\n💡 PRODUCTION RECOMMENDATION:")
    print("   🎯 Use SELECTIVE_UPDATE: true for production")
    print("   📝 This ensures only monitored APIs get updated rate limits")
    print("   🛡️  Prevents adding rate limits for APIs that shouldn't be limited")
    print("   ⚡ Maintains control over which endpoints are rate-limited")
    
    print(f"\n🔧 CONFIGURATION:")
    print("   Add to config/config.yaml:")
    print("   ```yaml")
    print("   COMMON:")
    print("     SELECTIVE_UPDATE: true  # Only update existing combinations")
    print("   ```")

if __name__ == "__main__":
    demo_selective_update()