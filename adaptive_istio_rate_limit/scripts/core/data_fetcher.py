import requests
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Import cache metrics analyzer
try:
    from .cache_metrics_analyzer import CacheMetricsAnalyzer
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from cache_metrics_analyzer import CacheMetricsAnalyzer

class DataFetcher:
    """
    Data fetcher for Prometheus metrics with support for mock data in local mode
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.prometheus_url = config.get('PROMETHEUS_URL')
        self.use_mock_data = config.get('USE_MOCK_DATA', False)
        self.deployment_mode = config.get('DEPLOYMENT_MODE', 'local')
        self.logger = logging.getLogger(__name__)
        
        # Default query for rate limiting metrics
        self.default_query = 'sum by (path, partner) (increase(service_nginx_request_time_s_count{path!="", partner!=""}[1m]))'
        
        # Initialize cache metrics analyzer
        self.cache_analyzer = None
        if not self.use_mock_data and self.prometheus_url:
            try:
                self.cache_analyzer = CacheMetricsAnalyzer(self.prometheus_url, self.logger)
                self.logger.info("Cache metrics analyzer initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize cache metrics analyzer: {e}")
        
        self.logger.info(f"Data Fetcher initialized - Mode: {self.deployment_mode}, Mock Data: {self.use_mock_data}")
    
    def fetch_prometheus_metrics(self, query: Optional[str] = None, days: int = 7) -> List[Dict]:
        """
        Fetch Prometheus metrics data
        """
        if self.use_mock_data:
            self.logger.info("Using mock data for local development")
            return self.generate_mock_prometheus_data(days)
        else:
            return self.fetch_real_prometheus_data(query or self.default_query, days)
    
    def fetch_real_prometheus_data(self, query: str, days: int) -> List[Dict]:
        """
        Fetch real Prometheus data from the configured endpoint
        """
        if not self.prometheus_url:
            self.logger.error("Prometheus URL not configured")
            return []
        
        end = datetime.now()
        start = end - timedelta(days=days)
        
        params = {
            'query': query,
            'start': start.timestamp(),
            'end': end.timestamp(),
            'step': '1m'
        }
        
        try:
            self.logger.info(f"Fetching Prometheus metrics from {self.prometheus_url}")
            self.logger.debug(f"Query: {query}")
            self.logger.debug(f"Time range: {start} to {end}")
            
            response = requests.get(f'{self.prometheus_url}/api/v1/query_range', params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get('status') != 'success':
                self.logger.error(f"Prometheus query failed: {data.get('error', 'Unknown error')}")
                return []
            
            results = data.get('data', {}).get('result', [])
            self.logger.info(f"Fetched {len(results)} metric series from Prometheus")
            
            return results
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch Prometheus metrics: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error fetching Prometheus metrics: {e}")
            return []
    
    def generate_mock_prometheus_data(self, days: int = 7) -> List[Dict]:
        """
        Generate realistic mock Prometheus data for local development and testing
        """
        self.logger.info(f"Generating mock Prometheus data for {days} days")
        
        # Define realistic partners and paths based on the example config
        partners = ['313', '439', '3079', '9020']
        paths = [
            '/api_v3/service/configurations/action/servebydevice',
            '/api_v3/service/asset/action/getplaybackcontext',
            '/api_v3/service/userassetrule/action/list',
            '/api_v3/service/licensedurl/action/get',
            '/api_v3/service/assethistory/action/list',
            '/api_v3/service/multirequest',
            '/api_v3/service/asset/action/list',
            '/api_v3/service/ottuser/action/get',
            '/api_v3/service/householdquota/action/get'
        ]
        
        # Partner-specific traffic patterns
        partner_patterns = {
            '313': {'base_traffic': 100, 'peak_multiplier': 3, 'variability': 0.3},
            '439': {'base_traffic': 200, 'peak_multiplier': 4, 'variability': 0.4},
            '3079': {'base_traffic': 80, 'peak_multiplier': 2, 'variability': 0.2},
            '9020': {'base_traffic': 150, 'peak_multiplier': 3.5, 'variability': 0.35}
        }
        
        # Path-specific traffic patterns
        path_patterns = {
            '/api_v3/service/asset/action/getplaybackcontext': {'multiplier': 2.0, 'prime_hours': [19, 20, 21, 22]},
            '/api_v3/service/multirequest': {'multiplier': 1.5, 'prime_hours': [9, 10, 11, 14, 15, 16]},
            '/api_v3/service/configurations/action/servebydevice': {'multiplier': 0.8, 'prime_hours': [8, 9, 18, 19]},
            '/api_v3/service/userassetrule/action/list': {'multiplier': 1.2, 'prime_hours': [10, 11, 15, 16, 20, 21]},
            '/api_v3/service/licensedurl/action/get': {'multiplier': 1.8, 'prime_hours': [19, 20, 21, 22, 23]},
            '/api_v3/service/assethistory/action/list': {'multiplier': 1.0, 'prime_hours': [14, 15, 16, 17]},
            '/api_v3/service/asset/action/list': {'multiplier': 1.3, 'prime_hours': [10, 11, 15, 16, 20, 21]},
            '/api_v3/service/ottuser/action/get': {'multiplier': 0.9, 'prime_hours': [18, 19, 20, 21]},
            '/api_v3/service/householdquota/action/get': {'multiplier': 0.7, 'prime_hours': [9, 10, 18, 19]}
        }
        
        mock_results = []
        
        for partner in partners:
            for path in paths:
                # Skip some combinations to make it more realistic
                if partner == '9020' and path not in ['/api_v3/service/assethistory/action/list']:
                    continue
                if partner == '3079' and path in ['/api_v3/service/multirequest']:
                    continue
                
                # Generate time series data
                timestamps = pd.date_range(
                    start=datetime.now() - timedelta(days=days),
                    end=datetime.now(),
                    freq='1min'
                )
                
                # Get patterns for this partner/path combination
                partner_pattern = partner_patterns.get(partner, partner_patterns['313'])
                path_pattern = path_patterns.get(path, {'multiplier': 1.0, 'prime_hours': [10, 11, 15, 16, 20, 21]})
                
                # Generate realistic traffic patterns
                values = self._generate_realistic_traffic(
                    timestamps, 
                    partner_pattern, 
                    path_pattern
                )
                
                # Convert to Prometheus format
                prometheus_values = [
                    [int(ts.timestamp()), str(max(0, int(val)))]
                    for ts, val in zip(timestamps, values)
                ]
                
                mock_results.append({
                    'metric': {
                        'partner': partner,
                        'path': path
                    },
                    'values': prometheus_values
                })
        
        self.logger.info(f"Generated {len(mock_results)} mock metric series")
        return mock_results
    
    def _generate_realistic_traffic(self, timestamps: pd.DatetimeIndex, 
                                  partner_pattern: Dict, path_pattern: Dict) -> np.ndarray:
        """
        Generate realistic traffic patterns with daily/weekly seasonality and anomalies
        """
        base_traffic = partner_pattern['base_traffic'] * path_pattern['multiplier']
        peak_multiplier = partner_pattern['peak_multiplier']
        variability = partner_pattern['variability']
        prime_hours = path_pattern['prime_hours']
        
        # Base Poisson-distributed traffic
        base_values = np.random.poisson(base_traffic, len(timestamps))
        
        # Add daily seasonality
        hours = timestamps.hour
        daily_pattern = np.ones(len(timestamps))
        
        # Prime time boost
        for hour in prime_hours:
            hour_mask = (hours == hour)
            daily_pattern[hour_mask] *= peak_multiplier
        
        # General daily pattern (lower at night, higher during day)
        daily_multiplier = 0.3 + 0.7 * np.sin(2 * np.pi * (hours - 6) / 24)
        daily_multiplier = np.maximum(daily_multiplier, 0.1)  # Minimum 10% traffic
        daily_pattern *= daily_multiplier
        
        # Add weekly seasonality (lower on weekends)
        weekdays = timestamps.dayofweek
        weekend_mask = (weekdays >= 5)  # Saturday and Sunday
        weekly_pattern = np.ones(len(timestamps))
        weekly_pattern[weekend_mask] *= 0.7  # 30% reduction on weekends
        
        # Add noise and variability
        noise = np.random.normal(0, base_traffic * variability, len(timestamps))
        
        # Add occasional spikes (anomalies)
        spike_probability = 0.001  # 0.1% chance of spike per minute
        spike_mask = np.random.random(len(timestamps)) < spike_probability
        spikes = np.zeros(len(timestamps))
        spikes[spike_mask] = np.random.exponential(base_traffic * 3, np.sum(spike_mask))
        
        # Add occasional drops (maintenance, issues)
        drop_probability = 0.0005  # 0.05% chance of drop per minute
        drop_mask = np.random.random(len(timestamps)) < drop_probability
        drops = np.zeros(len(timestamps))
        drops[drop_mask] = -base_values[drop_mask] * 0.8  # 80% reduction
        
        # Combine all patterns
        final_values = (base_values * daily_pattern * weekly_pattern + 
                       noise + spikes + drops)
        
        # Ensure non-negative values
        final_values = np.maximum(final_values, 0)
        
        return final_values
    
    def process_prometheus_results(self, results: List[Dict]) -> pd.DataFrame:
        """
        Process Prometheus results into a pandas DataFrame with cache adjustment
        """
        if not results:
            self.logger.warning("No Prometheus results to process")
            return pd.DataFrame()
        
        data = []
        
        for result in results:
            try:
                metric = result.get('metric', {})
                values = result.get('values', [])
                
                if not values:
                    continue
                
                # Create DataFrame for this metric
                df = pd.DataFrame(values, columns=['timestamp', 'value'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                df['value'] = pd.to_numeric(df['value'], errors='coerce')
                
                # Add metric labels
                df['path'] = metric.get('path', '').strip()
                df['partner'] = str(metric.get('partner', '')).strip()
                
                # Filter out invalid data
                df = df.dropna()
                df = df[df['value'] >= 0]  # Remove negative values
                
                if len(df) > 0:
                    # Apply cache adjustment if cache analyzer is available
                    if self.cache_analyzer and not self.use_mock_data:
                        try:
                            adjusted_df = self.cache_analyzer.adjust_metrics_for_cache(
                                df, df['partner'].iloc[0], df['path'].iloc[0]
                            )
                            data.append(adjusted_df)
                            
                            # Log cache adjustment details
                            if hasattr(adjusted_df, 'attrs') and adjusted_df.attrs:
                                cache_ratio = adjusted_df.attrs.get('cache_ratio', 0)
                                original_total = adjusted_df.attrs.get('original_total', 0)
                                adjusted_total = adjusted_df.attrs.get('adjusted_total', 0)
                                self.logger.info(f"Cache-adjusted metrics for {df['partner'].iloc[0]}/{df['path'].iloc[0]}: "
                                               f"{cache_ratio:.2%} cache ratio, {original_total:.0f}→{adjusted_total:.0f} requests")
                            else:
                                self.logger.debug(f"No cache adjustment applied for {df['partner'].iloc[0]}/{df['path'].iloc[0]}")
                        except Exception as e:
                            self.logger.warning(f"Cache adjustment failed for {df['partner'].iloc[0]}/{df['path'].iloc[0]}: {e}")
                            data.append(df)  # Use original data if cache adjustment fails
                    else:
                        data.append(df)
                    
                    self.logger.debug(f"Processed {len(df)} data points for partner {df['partner'].iloc[0]}, path {df['path'].iloc[0]}")
                
            except Exception as e:
                self.logger.error(f"Error processing Prometheus result: {e}")
                continue
        
        if data:
            combined_df = pd.concat(data, ignore_index=True)
            self.logger.info(f"Processed {len(combined_df)} total data points from {len(data)} metric series")
            return combined_df
        else:
            self.logger.warning("No valid data processed from Prometheus results")
            return pd.DataFrame()
    
    def get_metrics_summary(self, df: pd.DataFrame) -> Dict:
        """
        Get summary statistics of the fetched metrics
        """
        if df.empty:
            return {'error': 'No data available'}
        
        # Overall statistics
        summary = {
            'total_data_points': len(df),
            'time_range': {
                'start': df['timestamp'].min().isoformat() if not df.empty else None,
                'end': df['timestamp'].max().isoformat() if not df.empty else None,
                'duration_hours': (df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 3600 if len(df) > 1 else 0
            },
            'partners': df['partner'].nunique(),
            'paths': df['path'].nunique(),
            'partner_list': sorted(df['partner'].unique().tolist()),
            'path_list': sorted(df['path'].unique().tolist())
        }
        
        # Per-partner statistics
        partner_stats = df.groupby('partner')['value'].agg([
            'count', 'mean', 'median', 'std', 'min', 'max'
        ]).round(2).to_dict('index')
        
        summary['partner_statistics'] = partner_stats
        
        # Traffic distribution
        summary['traffic_distribution'] = {
            'total_requests': df['value'].sum(),
            'average_rps': df['value'].mean(),
            'peak_rps': df['value'].max(),
            'percentiles': {
                'p50': df['value'].quantile(0.5),
                'p75': df['value'].quantile(0.75),
                'p90': df['value'].quantile(0.9),
                'p95': df['value'].quantile(0.95),
                'p99': df['value'].quantile(0.99)
            }
        }
        
        return summary
    
    def validate_data_quality(self, df: pd.DataFrame) -> Dict:
        """
        Validate the quality of fetched data
        """
        if df.empty:
            return {
                'valid': False,
                'issues': ['No data available'],
                'recommendations': ['Check Prometheus connectivity and query']
            }
        
        issues = []
        recommendations = []
        
        # Check for sufficient data points
        min_data_points = 100
        if len(df) < min_data_points:
            issues.append(f'Insufficient data points: {len(df)} < {min_data_points}')
            recommendations.append('Increase time range or check data availability')
        
        # Check for data gaps
        time_diff = df['timestamp'].diff().dt.total_seconds()
        expected_interval = 60  # 1 minute
        large_gaps = time_diff > expected_interval * 5  # More than 5 minutes
        
        if large_gaps.sum() > 0:
            issues.append(f'Found {large_gaps.sum()} large time gaps in data')
            recommendations.append('Check for data collection issues during identified gaps')
        
        # Check for zero values
        zero_values = (df['value'] == 0).sum()
        if zero_values > len(df) * 0.1:  # More than 10% zeros
            issues.append(f'High number of zero values: {zero_values} ({zero_values/len(df)*100:.1f}%)')
            recommendations.append('Investigate periods of zero traffic')
        
        # Check for extremely high values (potential data quality issues)
        q99 = df['value'].quantile(0.99)
        q95 = df['value'].quantile(0.95)
        if q99 > q95 * 10:  # 99th percentile is 10x higher than 95th
            issues.append('Detected potential data quality issues with extreme values')
            recommendations.append('Review and potentially filter extreme outliers')
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'recommendations': recommendations,
            'data_quality_score': max(0, 1.0 - len(issues) * 0.2)  # Reduce score by 0.2 per issue
        }
    
    def fetch_and_clean_data(self, partner: str, path: str, days: int = 7) -> tuple:
        """
        Fetch and clean data for a specific partner/path combination
        
        Args:
            partner: Partner ID
            path: API path
            days: Number of days to fetch
            
        Returns:
            Tuple of (clean_metrics, prime_time_data) as DataFrames
        """
        try:
            # Construct query for specific partner/path
            query = f'sum by (path, partner) (increase(service_nginx_request_time_s_count{{path=~".*{path}.*", partner="{partner}"}}[1m]))'
            
            # Fetch data
            results = self.fetch_prometheus_metrics(query, days)
            df = self.process_prometheus_results(results)
            
            if df.empty:
                self.logger.warning(f"No data found for {partner}/{path}")
                return pd.DataFrame(), pd.DataFrame()
            
            # Filter for specific partner/path
            filtered_df = df[
                (df['partner'] == partner) &
                (df['path'].str.contains(path, na=False))
            ].copy()
            
            if filtered_df.empty:
                self.logger.warning(f"No matching data for {partner}/{path}")
                return pd.DataFrame(), pd.DataFrame()
            
            # Basic data cleaning
            clean_df = self._clean_data(filtered_df)
            
            # Extract prime time data (simple heuristic: 7-11 PM)
            prime_time_df = clean_df[
                clean_df['timestamp'].dt.hour.isin([19, 20, 21, 22, 23])
            ].copy()
            
            self.logger.info(f"Fetched {len(clean_df)} clean data points, {len(prime_time_df)} prime time points for {partner}/{path}")
            
            return clean_df, prime_time_df
            
        except Exception as e:
            self.logger.error(f"Failed to fetch and clean data for {partner}/{path}: {e}")
            return pd.DataFrame(), pd.DataFrame()
    
    def generate_mock_data(self, partner: str, path: str, days: int = 7) -> tuple:
        """
        Generate mock data for a specific partner/path combination
        
        Args:
            partner: Partner ID
            path: API path
            days: Number of days to generate
            
        Returns:
            Tuple of (clean_metrics, prime_time_data) as DataFrames
        """
        try:
            # Generate timestamps
            timestamps = pd.date_range(
                start=datetime.now() - timedelta(days=days),
                end=datetime.now(),
                freq='1min'
            )
            
            # Generate realistic traffic pattern
            base_traffic = 50 + hash(partner + path) % 100  # Deterministic but varied base traffic
            
            values = []
            for ts in timestamps:
                # Daily pattern
                hour = ts.hour
                daily_multiplier = 0.3 + 0.7 * np.sin(2 * np.pi * (hour - 6) / 24)
                daily_multiplier = max(daily_multiplier, 0.1)
                
                # Prime time boost
                if hour in [19, 20, 21, 22]:
                    daily_multiplier *= 2.5
                
                # Weekend reduction
                if ts.weekday() >= 5:
                    daily_multiplier *= 0.7
                
                # Add noise
                noise = np.random.normal(0, base_traffic * 0.2)
                value = max(0, base_traffic * daily_multiplier + noise)
                values.append(value)
            
            # Create DataFrame
            df = pd.DataFrame({
                'timestamp': timestamps,
                'value': values,
                'partner': partner,
                'path': path
            })
            
            # Extract prime time data
            prime_time_df = df[df['timestamp'].dt.hour.isin([19, 20, 21, 22])].copy()
            
            self.logger.debug(f"Generated {len(df)} mock data points, {len(prime_time_df)} prime time points for {partner}/{path}")
            
            return df, prime_time_df
            
        except Exception as e:
            self.logger.error(f"Failed to generate mock data for {partner}/{path}: {e}")
            return pd.DataFrame(), pd.DataFrame()
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean data by removing obvious outliers and invalid values
        
        Args:
            df: Raw DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        if df.empty:
            return df
        
        cleaned_df = df.copy()
        
        # Remove negative values
        cleaned_df = cleaned_df[cleaned_df['value'] >= 0]
        
        # Remove extreme outliers (values > 99.9th percentile)
        if len(cleaned_df) > 100:  # Only if we have enough data
            q999 = cleaned_df['value'].quantile(0.999)
            cleaned_df = cleaned_df[cleaned_df['value'] <= q999]
        
        # Remove NaN values
        cleaned_df = cleaned_df.dropna()
        
        # Sort by timestamp
        cleaned_df = cleaned_df.sort_values('timestamp')
        
        return cleaned_df