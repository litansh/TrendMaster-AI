#!/usr/bin/env python3
"""
Test script for the Adaptive Istio Rate Limiting System

This script tests the system in local mode with mock data to ensure
all components are working correctly.
"""

import sys
import os
import logging

# Add project root directory to path so we can import scripts and core modules
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)

def test_configuration():
    """Test configuration loading"""
    print("Testing configuration loading...")
    
    try:
        from scripts.core.config_manager import ConfigManager
        
        config_manager = ConfigManager('config/config.yaml')
        config = config_manager.get_config()
        
        print(f"✅ Configuration loaded successfully")
        print(f"   - Mode: {config_manager.deployment_mode}")
        print(f"   - Environment: {config.get('ENVIRONMENT')}")
        print(f"   - Prophet enabled: {config.get('PROPHET_CONFIG', {}).get('enabled', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_data_fetcher():
    """Test data fetching with mock data"""
    print("\nTesting data fetcher with mock data...")
    
    try:
        from scripts.core.config_manager import ConfigManager
        from scripts.core.data_fetcher import DataFetcher
        
        config_manager = ConfigManager('config/config.yaml')
        config = config_manager.get_config()
        
        # Ensure we use mock data
        config['USE_MOCK_DATA'] = True
        
        data_fetcher = DataFetcher(config)
        
        # Fetch mock data
        raw_results = data_fetcher.fetch_prometheus_metrics(days=3)
        print(f"✅ Fetched {len(raw_results)} mock metric series")
        
        # Process data
        metrics_df = data_fetcher.process_prometheus_results(raw_results)
        print(f"✅ Processed {len(metrics_df)} data points")
        
        # Get summary
        summary = data_fetcher.get_metrics_summary(metrics_df)
        print(f"   - Partners: {summary['partners']}")
        print(f"   - Paths: {summary['paths']}")
        print(f"   - Time range: {summary['time_range']['duration_hours']:.1f} hours")
        
        return True
        
    except Exception as e:
        print(f"❌ Data fetcher test failed: {e}")
        return False

def test_prophet_analyzer():
    """Test Prophet analyzer"""
    print("\nTesting Prophet analyzer...")
    
    try:
        from scripts.core.config_manager import ConfigManager
        from scripts.core.data_fetcher import DataFetcher
        from scripts.core.prophet_analyzer import ProphetAnalyzer
        
        config_manager = ConfigManager('config/config.yaml')
        config = config_manager.get_config()
        config['USE_MOCK_DATA'] = True
        
        # Get some mock data
        data_fetcher = DataFetcher(config)
        raw_results = data_fetcher.fetch_prometheus_metrics(days=2)
        metrics_df = data_fetcher.process_prometheus_results(raw_results)
        
        # Test Prophet analyzer
        prophet_analyzer = ProphetAnalyzer(config)
        
        # Get first partner/path combination
        first_combo = metrics_df[['partner', 'path']].drop_duplicates().iloc[0]
        partner = str(first_combo['partner'])
        path = first_combo['path']
        
        combo_data = metrics_df[
            (metrics_df['partner'] == partner) & 
            (metrics_df['path'] == path)
        ]
        
        # Analyze
        analysis_result = prophet_analyzer.analyze_traffic_patterns(combo_data, partner, path)
        
        print(f"✅ Prophet analysis completed for {partner}/{path}")
        print(f"   - Method: {analysis_result.get('analysis_method', 'unknown')}")
        print(f"   - Anomalies detected: {len(analysis_result.get('anomalies', []))}")
        print(f"   - Trend: {analysis_result.get('trend_info', {}).get('direction', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Prophet analyzer test failed: {e}")
        return False

def test_full_system():
    """Test the full system"""
    print("\nTesting full system...")
    
    try:
        from scripts.main import AdaptiveRateLimiter
        
        # Initialize with local config
        rate_limiter = AdaptiveRateLimiter('config/config.yaml')
        
        # Override config to use mock data for testing
        rate_limiter.config['USE_MOCK_DATA'] = True
        rate_limiter.data_fetcher.config['USE_MOCK_DATA'] = True
        rate_limiter.data_fetcher.use_mock_data = True
        
        # Run with limited days for faster testing
        results = rate_limiter.run(days_to_inspect=2)
        
        if results.get('success'):
            print(f"✅ Full system test completed successfully")
            print(f"   - Execution time: {results['execution_time']:.2f} seconds")
            print(f"   - Mode: {results['deployment_mode']}")
            print(f"   - Combinations analyzed: {results['summary']['total_combinations_analyzed']}")
            print(f"   - Rate calculations: {results['summary']['rate_calculations']}")
            
            return True
        else:
            print(f"❌ Full system test failed: {results.get('error', 'Unknown error')}")
            return False
        
    except Exception as e:
        print(f"❌ Full system test failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Adaptive Istio Rate Limiting System")
    print("=" * 50)
    
    # Setup basic logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during testing
    
    tests = [
        ("Configuration", test_configuration),
        ("Data Fetcher", test_data_fetcher),
        ("Prophet Analyzer", test_prophet_analyzer),
        ("Full System", test_full_system)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        if test_func():
            passed += 1
        else:
            print(f"   ⚠️  {test_name} test failed - check the logs above")
    
    print("\n" + "=" * 50)
    print(f"🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The system is ready to use.")
        print("\n📖 Next steps:")
        print("   1. Update config/config.yaml with your Prometheus URL for testing/production")
        print("   2. Run: python3 scripts/main.py")
        print("   3. Check the output/ directory for generated ConfigMaps")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()