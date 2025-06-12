import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

class PrimeTimeDetector:
    """
    Dynamic prime time detection for identifying high-traffic periods
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.prime_time_config = config.get('PRIME_TIME_CONFIG', {})
        self.logger = logging.getLogger(__name__)
        
        # Configuration parameters
        self.detection_method = self.prime_time_config.get('detection_method', 'dynamic')
        self.percentile_threshold = self.prime_time_config.get('percentile_threshold', 75)
        self.min_duration = self.prime_time_config.get('min_duration', 60)  # minutes
        self.consistency_check = self.prime_time_config.get('consistency_check', True)
        self.min_traffic_threshold = self.prime_time_config.get('min_traffic_threshold', 100)
    
    def detect_prime_hours(self, metrics_df: pd.DataFrame, partner: str, path: str) -> Dict:
        """
        Detect prime time hours for a specific partner/path combination
        """
        try:
            if len(metrics_df) == 0:
                self.logger.warning(f"No data available for prime time detection: {partner}/{path}")
                return self._get_default_prime_time()
            
            # Prepare data for analysis
            analysis_df = self._prepare_data_for_analysis(metrics_df)
            
            if len(analysis_df) == 0:
                self.logger.warning(f"No valid data after preparation: {partner}/{path}")
                return self._get_default_prime_time()
            
            # Detect prime time periods
            if self.detection_method == 'dynamic':
                prime_periods = self._detect_dynamic_prime_time(analysis_df, partner, path)
            else:
                prime_periods = self._get_fixed_prime_time()
            
            # Validate and refine prime time periods
            if self.consistency_check:
                prime_periods = self._validate_prime_time_consistency(analysis_df, prime_periods)
            
            # Calculate statistics for prime time periods
            prime_time_stats = self._calculate_prime_time_stats(analysis_df, prime_periods)
            
            return {
                'partner': partner,
                'path': path,
                'prime_periods': prime_periods,
                'detection_method': self.detection_method,
                'stats': prime_time_stats,
                'total_prime_hours': sum([period['duration'] for period in prime_periods])
            }
            
        except Exception as e:
            self.logger.error(f"Prime time detection failed for {partner}/{path}: {e}")
            return self._get_default_prime_time()
    
    def _prepare_data_for_analysis(self, metrics_df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare data for prime time analysis
        """
        # Ensure timestamp is datetime
        df = metrics_df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        
        # Remove NaN values
        df = df.dropna()
        
        # Add time-based features
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['date'] = df['timestamp'].dt.date
        
        # Filter out very low traffic (likely maintenance periods)
        df = df[df['value'] >= self.min_traffic_threshold]
        
        return df
    
    def _detect_dynamic_prime_time(self, analysis_df: pd.DataFrame, partner: str, path: str) -> List[Dict]:
        """
        Dynamically detect prime time periods based on traffic patterns
        """
        prime_periods = []
        
        # Group by hour and calculate statistics
        hourly_stats = analysis_df.groupby('hour')['value'].agg([
            'count', 'mean', 'median', 'std', 'min', 'max'
        ]).reset_index()
        
        # Calculate percentile threshold
        threshold_value = hourly_stats['mean'].quantile(self.percentile_threshold / 100.0)
        
        # Find hours above threshold
        high_traffic_hours = hourly_stats[hourly_stats['mean'] >= threshold_value]['hour'].tolist()
        
        if not high_traffic_hours:
            self.logger.warning(f"No high-traffic hours found for {partner}/{path}")
            return self._get_default_prime_time()['prime_periods']
        
        # Group consecutive hours into periods
        prime_periods = self._group_consecutive_hours(high_traffic_hours)
        
        # Filter periods by minimum duration
        prime_periods = [
            period for period in prime_periods 
            if period['duration'] >= (self.min_duration / 60.0)  # Convert minutes to hours
        ]
        
        # Add statistical information to each period
        for period in prime_periods:
            period_hours = list(range(period['start_hour'], period['end_hour'] + 1))
            period_stats = hourly_stats[hourly_stats['hour'].isin(period_hours)]
            
            period.update({
                'avg_traffic': period_stats['mean'].mean(),
                'peak_traffic': period_stats['max'].max(),
                'consistency': 1.0 - (period_stats['std'].mean() / period_stats['mean'].mean()) if period_stats['mean'].mean() > 0 else 0,
                'data_points': period_stats['count'].sum()
            })
        
        # Sort by average traffic (highest first)
        prime_periods.sort(key=lambda x: x['avg_traffic'], reverse=True)
        
        self.logger.info(f"Detected {len(prime_periods)} prime time periods for {partner}/{path}")
        
        return prime_periods
    
    def _group_consecutive_hours(self, hours: List[int]) -> List[Dict]:
        """
        Group consecutive hours into periods
        """
        if not hours:
            return []
        
        hours = sorted(hours)
        periods = []
        current_start = hours[0]
        current_end = hours[0]
        
        for i in range(1, len(hours)):
            if hours[i] == current_end + 1:
                # Consecutive hour
                current_end = hours[i]
            else:
                # Gap found, save current period and start new one
                periods.append({
                    'start_hour': current_start,
                    'end_hour': current_end,
                    'duration': current_end - current_start + 1
                })
                current_start = hours[i]
                current_end = hours[i]
        
        # Add the last period
        periods.append({
            'start_hour': current_start,
            'end_hour': current_end,
            'duration': current_end - current_start + 1
        })
        
        return periods
    
    def _validate_prime_time_consistency(self, analysis_df: pd.DataFrame, prime_periods: List[Dict]) -> List[Dict]:
        """
        Validate prime time periods for consistency across different days
        """
        validated_periods = []
        
        for period in prime_periods:
            period_hours = list(range(period['start_hour'], period['end_hour'] + 1))
            
            # Check consistency across different days
            daily_consistency = self._check_daily_consistency(analysis_df, period_hours)
            
            if daily_consistency['consistency_score'] >= 0.6:  # 60% consistency threshold
                period['consistency_score'] = daily_consistency['consistency_score']
                period['consistent_days'] = daily_consistency['consistent_days']
                validated_periods.append(period)
            else:
                self.logger.debug(f"Period {period['start_hour']}-{period['end_hour']} failed consistency check")
        
        return validated_periods
    
    def _check_daily_consistency(self, analysis_df: pd.DataFrame, period_hours: List[int]) -> Dict:
        """
        Check how consistently a time period is high-traffic across different days
        """
        # Get unique dates
        unique_dates = analysis_df['date'].unique()
        
        if len(unique_dates) < 2:
            return {'consistency_score': 1.0, 'consistent_days': len(unique_dates)}
        
        consistent_days = 0
        total_days = len(unique_dates)
        
        # Calculate average traffic for the period across all days
        period_data = analysis_df[analysis_df['hour'].isin(period_hours)]
        overall_period_avg = period_data['value'].mean()
        
        for date in unique_dates:
            day_data = analysis_df[analysis_df['date'] == date]
            
            if len(day_data) == 0:
                continue
            
            # Calculate average for this period on this day
            day_period_data = day_data[day_data['hour'].isin(period_hours)]
            
            if len(day_period_data) == 0:
                continue
            
            day_period_avg = day_period_data['value'].mean()
            day_overall_avg = day_data['value'].mean()
            
            # Check if this period is above average for this day
            if day_overall_avg > 0 and day_period_avg >= day_overall_avg:
                consistent_days += 1
        
        consistency_score = consistent_days / total_days if total_days > 0 else 0
        
        return {
            'consistency_score': consistency_score,
            'consistent_days': consistent_days,
            'total_days': total_days
        }
    
    def _calculate_prime_time_stats(self, analysis_df: pd.DataFrame, prime_periods: List[Dict]) -> Dict:
        """
        Calculate statistics for prime time periods
        """
        if not prime_periods:
            return {}
        
        # Get all prime time hours
        all_prime_hours = []
        for period in prime_periods:
            all_prime_hours.extend(list(range(period['start_hour'], period['end_hour'] + 1)))
        
        # Filter data for prime time hours
        prime_time_data = analysis_df[analysis_df['hour'].isin(all_prime_hours)]
        non_prime_time_data = analysis_df[~analysis_df['hour'].isin(all_prime_hours)]
        
        stats = {}
        
        if len(prime_time_data) > 0:
            stats['prime_time'] = {
                'mean': prime_time_data['value'].mean(),
                'median': prime_time_data['value'].median(),
                'std': prime_time_data['value'].std(),
                'min': prime_time_data['value'].min(),
                'max': prime_time_data['value'].max(),
                'count': len(prime_time_data)
            }
        
        if len(non_prime_time_data) > 0:
            stats['non_prime_time'] = {
                'mean': non_prime_time_data['value'].mean(),
                'median': non_prime_time_data['value'].median(),
                'std': non_prime_time_data['value'].std(),
                'min': non_prime_time_data['value'].min(),
                'max': non_prime_time_data['value'].max(),
                'count': len(non_prime_time_data)
            }
        
        # Calculate prime time vs non-prime time ratio
        if len(prime_time_data) > 0 and len(non_prime_time_data) > 0:
            stats['prime_time_ratio'] = stats['prime_time']['mean'] / stats['non_prime_time']['mean']
        else:
            stats['prime_time_ratio'] = 1.0
        
        return stats
    
    def _get_fixed_prime_time(self) -> List[Dict]:
        """
        Get fixed prime time periods (fallback method)
        """
        # Default business hours: 9 AM to 6 PM
        return [{
            'start_hour': 9,
            'end_hour': 18,
            'duration': 10,
            'type': 'fixed_business_hours'
        }]
    
    def _get_default_prime_time(self) -> Dict:
        """
        Get default prime time configuration
        """
        return {
            'partner': 'unknown',
            'path': 'unknown',
            'prime_periods': self._get_fixed_prime_time(),
            'detection_method': 'default',
            'stats': {},
            'total_prime_hours': 10
        }
    
    def get_prime_time_data(self, metrics_df: pd.DataFrame, prime_time_result: Dict) -> pd.DataFrame:
        """
        Filter metrics data to only include prime time periods
        """
        if not prime_time_result.get('prime_periods'):
            return metrics_df
        
        # Get all prime time hours
        prime_hours = []
        for period in prime_time_result['prime_periods']:
            prime_hours.extend(list(range(period['start_hour'], period['end_hour'] + 1)))
        
        # Filter data
        df = metrics_df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        
        prime_time_df = df[df['hour'].isin(prime_hours)].copy()
        prime_time_df = prime_time_df.drop('hour', axis=1)
        
        self.logger.info(f"Filtered to {len(prime_time_df)} prime time data points out of {len(metrics_df)}")
        
        return prime_time_df
    
    def get_prime_time_summary(self, prime_time_result: Dict) -> str:
        """
        Get a human-readable summary of prime time detection results
        """
        if not prime_time_result.get('prime_periods'):
            return "No prime time periods detected"
        
        summary_parts = []
        summary_parts.append(f"Partner: {prime_time_result.get('partner', 'unknown')}")
        summary_parts.append(f"Path: {prime_time_result.get('path', 'unknown')}")
        summary_parts.append(f"Detection Method: {prime_time_result.get('detection_method', 'unknown')}")
        summary_parts.append(f"Total Prime Hours: {prime_time_result.get('total_prime_hours', 0)}")
        
        summary_parts.append("\nPrime Time Periods:")
        for i, period in enumerate(prime_time_result['prime_periods'], 1):
            period_summary = f"  {i}. {period['start_hour']:02d}:00 - {period['end_hour']:02d}:59"
            period_summary += f" (Duration: {period['duration']} hours)"
            
            if 'avg_traffic' in period:
                period_summary += f" (Avg Traffic: {period['avg_traffic']:.1f})"
            
            summary_parts.append(period_summary)
        
        return "\n".join(summary_parts)
    
    def detect_prime_time_periods(self, metrics_df: pd.DataFrame, partner: str, path: str) -> Dict:
        """
        Alias for detect_prime_hours method for backward compatibility
        """
        return self.detect_prime_hours(metrics_df, partner, path)