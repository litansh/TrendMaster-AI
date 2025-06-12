#!/usr/bin/env python3
"""
Cache Metrics Analyzer for TrendMaster-AI
Analyzes cache hit/miss/bypass rates and adjusts traffic metrics accordingly
"""

import logging
import requests
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np


class CacheMetricsAnalyzer:
    """Analyzes cache metrics to adjust traffic calculations for Istio rate limiting"""
    
    def __init__(self, prometheus_url: str, logger: Optional[logging.Logger] = None):
        self.prometheus_url = prometheus_url.rstrip('/')
        self.logger = logger or logging.getLogger(__name__)
        
        # Cache status types
        self.cache_statuses = ['HIT', 'MISS', 'BYPASS', 'EXPIRED', 'STALE']
        
        # Cache metrics queries
        self.cache_queries = {
            'request_count': 'round(sum(increase(service_nginx_request_time_s_count{{path=~"{path}", partner=~"{partner}", cache_status!=""}}[{timerange}])) by (path, cache_status))',
            'cache_ratio': 'sum(increase(service_nginx_request_time_s_count{{path=~"{path}", partner=~"{partner}", cache_status=~"HIT|EXPIRED|STALE"}}[{timerange}])) / sum(increase(service_nginx_request_time_s_count{{path=~"{path}", partner=~"{partner}", cache_status!=""}}[{timerange}]))',
            'total_requests': 'sum(increase(service_nginx_request_time_s_count{{path=~"{path}", partner=~"{partner}"}}[{timerange}]))'
        }
    
    def fetch_cache_metrics(self, partner: str, path: str, timerange: str = "1h") -> Dict[str, any]:
        """
        Fetch cache metrics for a specific partner and API path
        
        Args:
            partner: Partner ID
            path: API path pattern
            timerange: Time range for metrics (e.g., "1h", "1d")
            
        Returns:
            Dictionary containing cache metrics
        """
        self.logger.debug(f"Fetching cache metrics for partner {partner}, path {path}")
        
        cache_metrics = {
            'partner': partner,
            'path': path,
            'timerange': timerange,
            'cache_breakdown': {},
            'cache_ratio': 0.0,
            'total_requests': 0,
            'istio_requests': 0,
            'cache_efficiency': 0.0
        }
        
        try:
            # Fetch cache breakdown by status
            cache_breakdown = self._fetch_cache_breakdown(partner, path, timerange)
            cache_metrics['cache_breakdown'] = cache_breakdown
            
            # Calculate cache ratio (HIT + EXPIRED + STALE / Total)
            cache_ratio = self._calculate_cache_ratio(partner, path, timerange)
            cache_metrics['cache_ratio'] = cache_ratio
            
            # Fetch total requests
            total_requests = self._fetch_total_requests(partner, path, timerange)
            cache_metrics['total_requests'] = total_requests
            
            # Calculate actual Istio traffic (requests that bypass cache)
            istio_requests = self._calculate_istio_requests(cache_breakdown, total_requests)
            cache_metrics['istio_requests'] = istio_requests
            
            # Calculate cache efficiency
            cache_efficiency = self._calculate_cache_efficiency(cache_breakdown)
            cache_metrics['cache_efficiency'] = cache_efficiency
            
            self.logger.info(f"Cache metrics for {partner}/{path}: "
                           f"Total={total_requests}, Istio={istio_requests}, "
                           f"Cache Ratio={cache_ratio:.2%}, Efficiency={cache_efficiency:.2%}")
            
        except Exception as e:
            self.logger.error(f"Failed to fetch cache metrics for {partner}/{path}: {str(e)}")
            # Return safe defaults
            cache_metrics['istio_requests'] = cache_metrics['total_requests']
        
        return cache_metrics
    
    def _fetch_cache_breakdown(self, partner: str, path: str, timerange: str) -> Dict[str, int]:
        """Fetch detailed cache breakdown by status"""
        query = self.cache_queries['request_count'].format(
            partner=partner,
            path=path,
            timerange=timerange
        )
        
        try:
            response = self._query_prometheus(query)
            cache_breakdown = {}
            
            if response and 'data' in response and 'result' in response['data']:
                for result in response['data']['result']:
                    cache_status = result['metric'].get('cache_status', 'UNKNOWN')
                    value = float(result['value'][1]) if result['value'][1] != 'NaN' else 0
                    cache_breakdown[cache_status] = int(value)
            
            # Ensure all cache statuses are represented
            for status in self.cache_statuses:
                if status not in cache_breakdown:
                    cache_breakdown[status] = 0
            
            return cache_breakdown
            
        except Exception as e:
            self.logger.warning(f"Failed to fetch cache breakdown: {str(e)}")
            return {status: 0 for status in self.cache_statuses}
    
    def _calculate_cache_ratio(self, partner: str, path: str, timerange: str) -> float:
        """Calculate overall cache hit ratio"""
        query = self.cache_queries['cache_ratio'].format(
            partner=partner,
            path=path,
            timerange=timerange
        )
        
        try:
            response = self._query_prometheus(query)
            
            if (response and 'data' in response and 'result' in response['data'] 
                and len(response['data']['result']) > 0):
                value = response['data']['result'][0]['value'][1]
                if value != 'NaN':
                    return float(value)
            
            return 0.0
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate cache ratio: {str(e)}")
            return 0.0
    
    def _fetch_total_requests(self, partner: str, path: str, timerange: str) -> int:
        """Fetch total request count"""
        query = self.cache_queries['total_requests'].format(
            partner=partner,
            path=path,
            timerange=timerange
        )
        
        try:
            response = self._query_prometheus(query)
            
            if (response and 'data' in response and 'result' in response['data'] 
                and len(response['data']['result']) > 0):
                value = response['data']['result'][0]['value'][1]
                if value != 'NaN':
                    return int(float(value))
            
            return 0
            
        except Exception as e:
            self.logger.warning(f"Failed to fetch total requests: {str(e)}")
            return 0
    
    def _calculate_istio_requests(self, cache_breakdown: Dict[str, int], total_requests: int) -> int:
        """
        Calculate actual requests that go through Istio (non-cached requests)
        
        Logic:
        - HIT: Request served from cache, doesn't go through Istio
        - MISS: Request not in cache, goes through Istio
        - BYPASS: Cache bypassed, goes through Istio
        - EXPIRED/STALE: May go through Istio for revalidation
        """
        if not cache_breakdown or total_requests == 0:
            return total_requests
        
        # Requests that definitely don't go through Istio
        cached_requests = cache_breakdown.get('HIT', 0)
        
        # Requests that go through Istio
        istio_requests = (
            cache_breakdown.get('MISS', 0) +
            cache_breakdown.get('BYPASS', 0) +
            cache_breakdown.get('EXPIRED', 0) +
            cache_breakdown.get('STALE', 0)
        )
        
        # If we have cache breakdown data, use it
        if sum(cache_breakdown.values()) > 0:
            calculated_total = cached_requests + istio_requests
            
            # If calculated total doesn't match, adjust proportionally
            if calculated_total != total_requests and calculated_total > 0:
                adjustment_ratio = total_requests / calculated_total
                istio_requests = int(istio_requests * adjustment_ratio)
        else:
            # No cache data available, assume all requests go through Istio
            istio_requests = total_requests
        
        # Ensure we don't exceed total requests
        istio_requests = min(istio_requests, total_requests)
        
        self.logger.debug(f"Cache breakdown: {cache_breakdown}")
        self.logger.debug(f"Total requests: {total_requests}, Istio requests: {istio_requests}")
        
        return istio_requests
    
    def _calculate_cache_efficiency(self, cache_breakdown: Dict[str, int]) -> float:
        """Calculate cache efficiency percentage"""
        if not cache_breakdown:
            return 0.0
        
        total_cache_requests = sum(cache_breakdown.values())
        if total_cache_requests == 0:
            return 0.0
        
        # Efficient cache responses (HIT + STALE)
        efficient_responses = cache_breakdown.get('HIT', 0) + cache_breakdown.get('STALE', 0)
        
        return efficient_responses / total_cache_requests
    
    def _query_prometheus(self, query: str) -> Optional[Dict]:
        """Execute Prometheus query"""
        try:
            url = f"{self.prometheus_url}/api/v1/query"
            params = {
                'query': query,
                'time': datetime.now().isoformat()
            }
            
            self.logger.debug(f"Prometheus query: {query}")
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('status') != 'success':
                self.logger.warning(f"Prometheus query failed: {result.get('error', 'Unknown error')}")
                return None
            
            return result
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Prometheus request failed: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Prometheus query error: {str(e)}")
            return None
    
    def adjust_metrics_for_cache(self, raw_metrics: pd.DataFrame, partner: str, path: str) -> pd.DataFrame:
        """
        Adjust raw traffic metrics by removing cached requests
        
        Args:
            raw_metrics: DataFrame with raw traffic metrics
            partner: Partner ID
            path: API path
            
        Returns:
            Adjusted DataFrame with cache-corrected metrics
        """
        self.logger.info(f"Adjusting metrics for cache impact: {partner}/{path}")
        
        if raw_metrics.empty:
            return raw_metrics
        
        try:
            # Fetch cache metrics for the same time period
            cache_metrics = self.fetch_cache_metrics(partner, path, "1h")
            
            if cache_metrics['cache_ratio'] == 0:
                self.logger.info(f"No cache data found for {partner}/{path}, using raw metrics")
                return raw_metrics
            
            # Create adjusted metrics DataFrame
            adjusted_metrics = raw_metrics.copy()
            
            # Apply cache adjustment to request counts
            cache_ratio = cache_metrics['cache_ratio']
            adjustment_factor = 1 - cache_ratio
            
            # Adjust the value column (assuming it contains request counts)
            if 'value' in adjusted_metrics.columns:
                original_sum = adjusted_metrics['value'].sum()
                adjusted_metrics['value'] = adjusted_metrics['value'] * adjustment_factor
                adjusted_sum = adjusted_metrics['value'].sum()
                
                self.logger.info(f"Cache adjustment applied: {cache_ratio:.2%} cache ratio, "
                               f"reduced from {original_sum:.0f} to {adjusted_sum:.0f} requests")
            
            # Add cache metadata
            adjusted_metrics.attrs = {
                'cache_ratio': cache_ratio,
                'cache_efficiency': cache_metrics['cache_efficiency'],
                'adjustment_factor': adjustment_factor,
                'original_total': raw_metrics['value'].sum() if 'value' in raw_metrics.columns else 0,
                'adjusted_total': adjusted_metrics['value'].sum() if 'value' in adjusted_metrics.columns else 0
            }
            
            return adjusted_metrics
            
        except Exception as e:
            self.logger.error(f"Failed to adjust metrics for cache: {str(e)}")
            return raw_metrics
    
    def get_cache_summary(self, partners: List[str], paths: List[str]) -> Dict[str, Dict]:
        """Get cache summary for multiple partner/path combinations"""
        self.logger.info(f"Generating cache summary for {len(partners)} partners and {len(paths)} paths")
        
        cache_summary = {}
        
        for partner in partners:
            cache_summary[partner] = {}
            
            for path in paths:
                try:
                    cache_metrics = self.fetch_cache_metrics(partner, path)
                    cache_summary[partner][path] = {
                        'cache_ratio': cache_metrics['cache_ratio'],
                        'cache_efficiency': cache_metrics['cache_efficiency'],
                        'total_requests': cache_metrics['total_requests'],
                        'istio_requests': cache_metrics['istio_requests'],
                        'cache_breakdown': cache_metrics['cache_breakdown']
                    }
                except Exception as e:
                    self.logger.warning(f"Failed to get cache metrics for {partner}/{path}: {str(e)}")
                    cache_summary[partner][path] = {
                        'cache_ratio': 0.0,
                        'cache_efficiency': 0.0,
                        'total_requests': 0,
                        'istio_requests': 0,
                        'cache_breakdown': {}
                    }
        
        return cache_summary
    
    def generate_cache_report(self, cache_summary: Dict[str, Dict]) -> str:
        """Generate a human-readable cache report"""
        report_lines = [
            "# Cache Metrics Analysis Report",
            f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Cache Performance Summary",
            ""
        ]
        
        total_partners = len(cache_summary)
        total_paths = sum(len(paths) for paths in cache_summary.values())
        
        # Overall statistics
        all_ratios = []
        all_efficiencies = []
        total_requests = 0
        total_istio_requests = 0
        
        for partner_data in cache_summary.values():
            for path_data in partner_data.values():
                if path_data['total_requests'] > 0:
                    all_ratios.append(path_data['cache_ratio'])
                    all_efficiencies.append(path_data['cache_efficiency'])
                    total_requests += path_data['total_requests']
                    total_istio_requests += path_data['istio_requests']
        
        if all_ratios:
            avg_cache_ratio = np.mean(all_ratios)
            avg_cache_efficiency = np.mean(all_efficiencies)
            overall_istio_ratio = total_istio_requests / total_requests if total_requests > 0 else 0
            
            report_lines.extend([
                f"- **Total Partners**: {total_partners}",
                f"- **Total API Paths**: {total_paths}",
                f"- **Average Cache Ratio**: {avg_cache_ratio:.2%}",
                f"- **Average Cache Efficiency**: {avg_cache_efficiency:.2%}",
                f"- **Total Requests**: {total_requests:,}",
                f"- **Istio Requests**: {total_istio_requests:,}",
                f"- **Istio Traffic Ratio**: {overall_istio_ratio:.2%}",
                "",
                "## Per-Partner Analysis",
                ""
            ])
        
        # Per-partner details
        for partner, partner_data in cache_summary.items():
            report_lines.append(f"### Partner {partner}")
            report_lines.append("")
            
            for path, path_data in partner_data.items():
                cache_ratio = path_data['cache_ratio']
                efficiency = path_data['cache_efficiency']
                total_reqs = path_data['total_requests']
                istio_reqs = path_data['istio_requests']
                
                report_lines.extend([
                    f"**{path}**",
                    f"- Cache Ratio: {cache_ratio:.2%}",
                    f"- Cache Efficiency: {efficiency:.2%}",
                    f"- Total Requests: {total_reqs:,}",
                    f"- Istio Requests: {istio_reqs:,}",
                    f"- Cache Breakdown: {path_data['cache_breakdown']}",
                    ""
                ])
        
        return "\n".join(report_lines)


def main():
    """Main function for testing cache metrics analyzer"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Cache Metrics Analyzer')
    parser.add_argument('--prometheus-url', required=True, help='Prometheus URL')
    parser.add_argument('--partner', required=True, help='Partner ID')
    parser.add_argument('--path', required=True, help='API path pattern')
    parser.add_argument('--timerange', default='1h', help='Time range for metrics')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Initialize analyzer
    analyzer = CacheMetricsAnalyzer(args.prometheus_url, logger)
    
    # Fetch and display cache metrics
    cache_metrics = analyzer.fetch_cache_metrics(args.partner, args.path, args.timerange)
    
    print(f"\nCache Metrics for Partner {args.partner}, Path {args.path}:")
    print(f"Cache Ratio: {cache_metrics['cache_ratio']:.2%}")
    print(f"Cache Efficiency: {cache_metrics['cache_efficiency']:.2%}")
    print(f"Total Requests: {cache_metrics['total_requests']:,}")
    print(f"Istio Requests: {cache_metrics['istio_requests']:,}")
    print(f"Cache Breakdown: {cache_metrics['cache_breakdown']}")


if __name__ == '__main__':
    main()