#!/usr/bin/env python3
"""
TrendMaster-AI Cache Metrics Collector
Production-Ready Cache Performance Analysis

This module provides comprehensive cache metrics collection and analysis
for accurate rate limiting calculations with cache awareness.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from .prometheus_client import PrometheusClient, PrometheusResult


@dataclass
class CacheMetrics:
    """Cache performance metrics"""
    partner: str
    path: str
    total_requests: int
    cache_hits: int
    cache_misses: int
    cache_bypasses: int
    cache_expired: int
    cache_stale: int
    hit_ratio: float
    miss_ratio: float
    bypass_ratio: float
    timestamp: datetime
    duration_hours: int


class CacheMetricsCollector:
    """
    Production-ready cache metrics collector with Prometheus integration
    """
    
    def __init__(self, prometheus_client: PrometheusClient, config: Dict[str, Any]):
        """
        Initialize cache metrics collector
        
        Args:
            prometheus_client: Prometheus client instance
            config: Configuration dictionary
        """
        self.prometheus_client = prometheus_client
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Cache configuration
        self.cache_config = config.get('COMMON', {}).get('CACHE_CONFIG', {})
        self.cache_statuses = self.cache_config.get('cache_statuses', ['HIT', 'MISS', 'BYPASS', 'EXPIRED', 'STALE'])
        self.default_hit_ratio = self.cache_config.get('default_hit_ratio', 0.15)
        self.timeout = self.cache_config.get('timeout', 30)
        
        self.logger.info("Cache metrics collector initialized")
    
    def get_cache_metrics(self, partner: str, path: str, hours: int = 24) -> Optional[CacheMetrics]:
        """
        Get comprehensive cache metrics for partner/path combination
        
        Args:
            partner: Partner ID
            path: API path
            hours: Number of hours to analyze
            
        Returns:
            CacheMetrics object or None if data unavailable
        """
        try:
            self.logger.debug(f"Collecting cache metrics for {partner}/{path}")
            
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            # Get cache status breakdown
            cache_breakdown = self._get_cache_status_breakdown(partner, path, start_time, end_time)
            
            if not cache_breakdown:
                self.logger.warning(f"No cache data available for {partner}/{path}")
                return self._get_default_cache_metrics(partner, path, hours)
            
            # Calculate metrics
            total_requests = sum(cache_breakdown.values())
            cache_hits = cache_breakdown.get('HIT', 0)
            cache_misses = cache_breakdown.get('MISS', 0)
            cache_bypasses = cache_breakdown.get('BYPASS', 0)
            cache_expired = cache_breakdown.get('EXPIRED', 0)
            cache_stale = cache_breakdown.get('STALE', 0)
            
            # Calculate ratios
            if total_requests > 0:
                hit_ratio = cache_hits / total_requests
                miss_ratio = cache_misses / total_requests
                bypass_ratio = cache_bypasses / total_requests
            else:
                hit_ratio = self.default_hit_ratio
                miss_ratio = 1.0 - hit_ratio
                bypass_ratio = 0.0
            
            cache_metrics = CacheMetrics(
                partner=partner,
                path=path,
                total_requests=total_requests,
                cache_hits=cache_hits,
                cache_misses=cache_misses,
                cache_bypasses=cache_bypasses,
                cache_expired=cache_expired,
                cache_stale=cache_stale,
                hit_ratio=hit_ratio,
                miss_ratio=miss_ratio,
                bypass_ratio=bypass_ratio,
                timestamp=end_time,
                duration_hours=hours
            )
            
            self.logger.info(
                f"Cache metrics for {partner}/{path}: "
                f"hit_ratio={hit_ratio:.2%}, total_requests={total_requests}"
            )
            
            return cache_metrics
        
        except Exception as e:
            self.logger.error(f"Failed to collect cache metrics for {partner}/{path}: {e}")
            return self._get_default_cache_metrics(partner, path, hours)
    
    def _get_cache_status_breakdown(self, partner: str, path: str, 
                                  start_time: datetime, end_time: datetime) -> Dict[str, int]:
        """
        Get cache status breakdown from Prometheus
        
        Args:
            partner: Partner ID
            path: API path
            start_time: Query start time
            end_time: Query end time
            
        Returns:
            Dictionary with cache status counts
        """
        try:
            # Construct PromQL query for cache metrics
            query = f'''
            sum(increase(
                service_nginx_request_time_s_count{{
                    path=~".*{path}.*",
                    partner="{partner}",
                    cache_status!=""
                }}[1m]
            )) by (cache_status)
            '''
            
            result = self.prometheus_client.query_range(
                query, start_time, end_time, "1m"
            )
            
            if not result.success:
                self.logger.warning(f"Cache metrics query failed: {result.error}")
                return {}
            
            # Process results
            cache_breakdown = {}
            
            for series in result.data.get('result', []):
                cache_status = series.get('metric', {}).get('cache_status', 'UNKNOWN')
                values = series.get('values', [])
                
                # Sum all values for this cache status
                total_count = 0
                for timestamp, value in values:
                    try:
                        total_count += float(value)
                    except (ValueError, TypeError):
                        continue
                
                cache_breakdown[cache_status] = int(total_count)
            
            return cache_breakdown
        
        except Exception as e:
            self.logger.error(f"Failed to get cache status breakdown: {e}")
            return {}
    
    def _get_default_cache_metrics(self, partner: str, path: str, hours: int) -> CacheMetrics:
        """
        Get default cache metrics when real data is unavailable
        
        Args:
            partner: Partner ID
            path: API path
            hours: Duration hours
            
        Returns:
            Default CacheMetrics object
        """
        return CacheMetrics(
            partner=partner,
            path=path,
            total_requests=0,
            cache_hits=0,
            cache_misses=0,
            cache_bypasses=0,
            cache_expired=0,
            cache_stale=0,
            hit_ratio=self.default_hit_ratio,
            miss_ratio=1.0 - self.default_hit_ratio,
            bypass_ratio=0.0,
            timestamp=datetime.now(),
            duration_hours=hours
        )
    
    def get_cache_efficiency_score(self, cache_metrics: CacheMetrics) -> float:
        """
        Calculate cache efficiency score (0.0 to 1.0)
        
        Args:
            cache_metrics: Cache metrics object
            
        Returns:
            Efficiency score between 0.0 and 1.0
        """
        try:
            # Base score from hit ratio
            base_score = cache_metrics.hit_ratio
            
            # Penalty for high bypass ratio (indicates cache configuration issues)
            bypass_penalty = cache_metrics.bypass_ratio * 0.3
            
            # Penalty for high expired/stale ratio (indicates cache TTL issues)
            if cache_metrics.total_requests > 0:
                expired_stale_ratio = (cache_metrics.cache_expired + cache_metrics.cache_stale) / cache_metrics.total_requests
                ttl_penalty = expired_stale_ratio * 0.2
            else:
                ttl_penalty = 0.0
            
            # Calculate final score
            efficiency_score = max(0.0, base_score - bypass_penalty - ttl_penalty)
            
            return min(1.0, efficiency_score)
        
        except Exception as e:
            self.logger.error(f"Failed to calculate cache efficiency score: {e}")
            return 0.5  # Default middle score
    
    def analyze_cache_patterns(self, partner: str, path: str, hours: int = 168) -> Dict[str, Any]:
        """
        Analyze cache patterns over time (default 1 week)
        
        Args:
            partner: Partner ID
            path: API path
            hours: Analysis period in hours
            
        Returns:
            Dictionary with cache pattern analysis
        """
        try:
            self.logger.debug(f"Analyzing cache patterns for {partner}/{path}")
            
            # Get cache metrics for different time periods
            periods = [1, 6, 24, 72, 168]  # 1h, 6h, 1d, 3d, 1w
            metrics_by_period = {}
            
            for period_hours in periods:
                if period_hours <= hours:
                    metrics = self.get_cache_metrics(partner, path, period_hours)
                    if metrics:
                        metrics_by_period[f"{period_hours}h"] = {
                            'hit_ratio': metrics.hit_ratio,
                            'total_requests': metrics.total_requests,
                            'efficiency_score': self.get_cache_efficiency_score(metrics)
                        }
            
            # Analyze trends
            hit_ratios = [data['hit_ratio'] for data in metrics_by_period.values()]
            efficiency_scores = [data['efficiency_score'] for data in metrics_by_period.values()]
            
            analysis = {
                'partner': partner,
                'path': path,
                'analysis_timestamp': datetime.now().isoformat(),
                'periods_analyzed': list(metrics_by_period.keys()),
                'metrics_by_period': metrics_by_period,
                'trends': {
                    'hit_ratio_trend': self._calculate_trend(hit_ratios),
                    'efficiency_trend': self._calculate_trend(efficiency_scores),
                    'average_hit_ratio': sum(hit_ratios) / len(hit_ratios) if hit_ratios else 0.0,
                    'average_efficiency': sum(efficiency_scores) / len(efficiency_scores) if efficiency_scores else 0.0
                },
                'recommendations': self._generate_cache_recommendations(metrics_by_period)
            }
            
            return analysis
        
        except Exception as e:
            self.logger.error(f"Failed to analyze cache patterns: {e}")
            return {
                'partner': partner,
                'path': path,
                'error': str(e),
                'analysis_timestamp': datetime.now().isoformat()
            }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """
        Calculate trend direction from a list of values
        
        Args:
            values: List of numeric values
            
        Returns:
            Trend direction: 'improving', 'declining', 'stable'
        """
        if len(values) < 2:
            return 'stable'
        
        # Simple linear trend calculation
        n = len(values)
        x_sum = sum(range(n))
        y_sum = sum(values)
        xy_sum = sum(i * values[i] for i in range(n))
        x2_sum = sum(i * i for i in range(n))
        
        try:
            slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)
            
            if slope > 0.01:
                return 'improving'
            elif slope < -0.01:
                return 'declining'
            else:
                return 'stable'
        except ZeroDivisionError:
            return 'stable'
    
    def _generate_cache_recommendations(self, metrics_by_period: Dict[str, Dict]) -> List[str]:
        """
        Generate cache optimization recommendations
        
        Args:
            metrics_by_period: Metrics data by time period
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        if not metrics_by_period:
            return ["Insufficient cache data for recommendations"]
        
        # Get latest metrics
        latest_period = max(metrics_by_period.keys())
        latest_metrics = metrics_by_period[latest_period]
        
        hit_ratio = latest_metrics.get('hit_ratio', 0.0)
        efficiency_score = latest_metrics.get('efficiency_score', 0.0)
        
        # Hit ratio recommendations
        if hit_ratio < 0.1:
            recommendations.append("Very low cache hit ratio - consider reviewing cache configuration")
        elif hit_ratio < 0.3:
            recommendations.append("Low cache hit ratio - optimize cache TTL and cache keys")
        elif hit_ratio > 0.8:
            recommendations.append("Excellent cache hit ratio - current configuration is optimal")
        
        # Efficiency recommendations
        if efficiency_score < 0.5:
            recommendations.append("Cache efficiency is below optimal - review bypass and expiration policies")
        elif efficiency_score > 0.8:
            recommendations.append("Cache efficiency is excellent - maintain current configuration")
        
        # Trend-based recommendations
        hit_ratios = [data['hit_ratio'] for data in metrics_by_period.values()]
        trend = self._calculate_trend(hit_ratios)
        
        if trend == 'declining':
            recommendations.append("Cache performance is declining - investigate recent changes")
        elif trend == 'improving':
            recommendations.append("Cache performance is improving - continue current optimizations")
        
        return recommendations if recommendations else ["Cache performance is within normal parameters"]
    
    def get_cache_impact_on_rate_limiting(self, cache_metrics: CacheMetrics) -> Dict[str, float]:
        """
        Calculate cache impact on rate limiting decisions
        
        Args:
            cache_metrics: Cache metrics object
            
        Returns:
            Dictionary with impact factors
        """
        try:
            # Calculate effective traffic multiplier
            # Higher cache hit ratio means fewer requests hit the backend
            effective_traffic_ratio = 1.0 - cache_metrics.hit_ratio
            
            # Cache adjustment factor for rate limiting
            # Good cache performance allows for more aggressive rate limits
            if cache_metrics.hit_ratio >= 0.5:
                cache_adjustment = 1.0 + (cache_metrics.hit_ratio * 0.3)  # Up to 30% increase
            else:
                cache_adjustment = 1.0 - ((0.5 - cache_metrics.hit_ratio) * 0.2)  # Up to 10% decrease
            
            # Confidence factor based on cache stability
            efficiency_score = self.get_cache_efficiency_score(cache_metrics)
            confidence_factor = 0.5 + (efficiency_score * 0.5)  # 0.5 to 1.0 range
            
            return {
                'effective_traffic_ratio': effective_traffic_ratio,
                'cache_adjustment_factor': cache_adjustment,
                'confidence_factor': confidence_factor,
                'hit_ratio': cache_metrics.hit_ratio,
                'efficiency_score': efficiency_score
            }
        
        except Exception as e:
            self.logger.error(f"Failed to calculate cache impact: {e}")
            return {
                'effective_traffic_ratio': 1.0,
                'cache_adjustment_factor': 1.0,
                'confidence_factor': 0.5,
                'hit_ratio': self.default_hit_ratio,
                'efficiency_score': 0.5
            }


class MockCacheMetricsCollector:
    """
    Mock cache metrics collector for testing and development
    """
    
    def __init__(self, prometheus_client=None, config=None):
        self.logger = logging.getLogger(__name__)
        self.default_hit_ratio = 0.15
        self.logger.info("Mock cache metrics collector initialized")
    
    def get_cache_metrics(self, partner: str, path: str, hours: int = 24) -> CacheMetrics:
        """Generate mock cache metrics"""
        import random
        
        # Generate realistic mock data
        total_requests = random.randint(1000, 10000)
        hit_ratio = random.uniform(0.1, 0.6)  # 10% to 60% hit ratio
        
        cache_hits = int(total_requests * hit_ratio)
        cache_misses = int(total_requests * (1 - hit_ratio) * 0.8)
        cache_bypasses = int(total_requests * 0.1)
        cache_expired = int(total_requests * 0.05)
        cache_stale = int(total_requests * 0.02)
        
        return CacheMetrics(
            partner=partner,
            path=path,
            total_requests=total_requests,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            cache_bypasses=cache_bypasses,
            cache_expired=cache_expired,
            cache_stale=cache_stale,
            hit_ratio=hit_ratio,
            miss_ratio=1.0 - hit_ratio,
            bypass_ratio=cache_bypasses / total_requests,
            timestamp=datetime.now(),
            duration_hours=hours
        )
    
    def get_cache_efficiency_score(self, cache_metrics: CacheMetrics) -> float:
        """Mock efficiency score"""
        return cache_metrics.hit_ratio * 0.9  # Slightly lower than hit ratio
    
    def analyze_cache_patterns(self, partner: str, path: str, hours: int = 168) -> Dict[str, Any]:
        """Mock cache pattern analysis"""
        return {
            'partner': partner,
            'path': path,
            'analysis_timestamp': datetime.now().isoformat(),
            'trends': {
                'hit_ratio_trend': 'stable',
                'efficiency_trend': 'stable',
                'average_hit_ratio': 0.25,
                'average_efficiency': 0.22
            },
            'recommendations': ["Mock cache analysis - data is simulated"]
        }
    
    def get_cache_impact_on_rate_limiting(self, cache_metrics: CacheMetrics) -> Dict[str, float]:
        """Mock cache impact calculation"""
        return {
            'effective_traffic_ratio': 1.0 - cache_metrics.hit_ratio,
            'cache_adjustment_factor': 1.0 + (cache_metrics.hit_ratio * 0.2),
            'confidence_factor': 0.7,
            'hit_ratio': cache_metrics.hit_ratio,
            'efficiency_score': cache_metrics.hit_ratio * 0.9
        }


if __name__ == '__main__':
    # CLI for testing cache metrics collection
    import argparse
    
    parser = argparse.ArgumentParser(description='TrendMaster-AI Cache Metrics Collector')
    parser.add_argument('--prometheus-url', required=True, help='Prometheus server URL')
    parser.add_argument('--partner', required=True, help='Partner ID')
    parser.add_argument('--path', required=True, help='API path')
    parser.add_argument('--hours', type=int, default=24, help='Analysis period in hours')
    parser.add_argument('--mock', action='store_true', help='Use mock data')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    try:
        if args.mock:
            collector = MockCacheMetricsCollector()
        else:
            from .prometheus_client import PrometheusClient
            prometheus_client = PrometheusClient(args.prometheus_url)
            collector = CacheMetricsCollector(prometheus_client, {})
        
        # Get cache metrics
        metrics = collector.get_cache_metrics(args.partner, args.path, args.hours)
        
        if metrics:
            print(f"Cache Metrics for {args.partner}/{args.path}:")
            print(f"  Total Requests: {metrics.total_requests}")
            print(f"  Cache Hit Ratio: {metrics.hit_ratio:.2%}")
            print(f"  Cache Miss Ratio: {metrics.miss_ratio:.2%}")
            print(f"  Cache Bypass Ratio: {metrics.bypass_ratio:.2%}")
            
            # Get efficiency score
            efficiency = collector.get_cache_efficiency_score(metrics)
            print(f"  Efficiency Score: {efficiency:.2f}")
            
            # Get impact on rate limiting
            impact = collector.get_cache_impact_on_rate_limiting(metrics)
            print(f"  Rate Limiting Impact:")
            print(f"    Effective Traffic Ratio: {impact['effective_traffic_ratio']:.2f}")
            print(f"    Cache Adjustment Factor: {impact['cache_adjustment_factor']:.2f}")
            print(f"    Confidence Factor: {impact['confidence_factor']:.2f}")
        else:
            print("No cache metrics available")
    
    except Exception as e:
        print(f"Error: {e}")