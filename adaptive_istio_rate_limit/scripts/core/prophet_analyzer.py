import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings

# Suppress Prophet warnings for cleaner output
warnings.filterwarnings("ignore", category=FutureWarning)

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logging.warning("Prophet not available. Install with: pip install prophet")

class ProphetAnalyzer:
    """
    Prophet-based time series analysis for rate limiting optimization
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.prophet_config = config.get('PROPHET_CONFIG', {})
        self.anomaly_config = config.get('ANOMALY_CONFIG', {})
        self.logger = logging.getLogger(__name__)
        
        if not PROPHET_AVAILABLE:
            self.logger.warning("Prophet not available - falling back to statistical methods")
    
    def analyze_traffic_patterns(self, metrics_df: pd.DataFrame, partner: str, path: str) -> Dict:
        """
        Analyze traffic patterns for a specific partner/path combination
        """
        if not PROPHET_AVAILABLE:
            return self._fallback_analysis(metrics_df, partner, path)
        
        # Check if running in CI/CD mode for timeout handling
        import os
        ci_mode = os.getenv('TRENDMASTER_CI_MODE', 'false').lower() == 'true'
        
        try:
            # Prepare data for Prophet
            prophet_df = self._prepare_prophet_data(metrics_df)
            
            if len(prophet_df) < 10:  # Need minimum data points
                self.logger.warning(f"Insufficient data for Prophet analysis: {partner}/{path}")
                return self._fallback_analysis(metrics_df, partner, path)
            
            # In CI mode, use a timeout for Prophet operations
            if ci_mode:
                import signal
                
                def timeout_handler(signum, frame):
                    raise TimeoutError("Prophet analysis timed out")
                
                # Set timeout for Prophet operations (30 seconds in CI mode)
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(30)
                
                try:
                    # Create and fit Prophet model
                    model = self._create_prophet_model()
                    self.logger.info(f"Fitting Prophet model for {partner}/{path} (CI mode)")
                    model.fit(prophet_df)
                    
                    # Generate forecast
                    future = model.make_future_dataframe(periods=0)  # No future prediction, just analysis
                    forecast = model.predict(future)
                    
                    signal.alarm(0)  # Cancel timeout
                    
                except TimeoutError:
                    signal.alarm(0)  # Cancel timeout
                    self.logger.warning(f"Prophet analysis timed out for {partner}/{path}, falling back to statistical analysis")
                    return self._fallback_analysis(metrics_df, partner, path)
            else:
                # Normal mode without timeout
                model = self._create_prophet_model()
                model.fit(prophet_df)
                
                # Generate forecast
                future = model.make_future_dataframe(periods=0)  # No future prediction, just analysis
                forecast = model.predict(future)
            
            # Detect anomalies
            anomalies = self._detect_prophet_anomalies(prophet_df, forecast)
            
            # Extract seasonal components
            seasonal_components = self._extract_seasonal_components(model, forecast)
            
            # Calculate trend information
            trend_info = self._calculate_trend_info(forecast)
            
            return {
                'partner': partner,
                'path': path,
                'model': model,
                'forecast': forecast,
                'anomalies': anomalies,
                'seasonal_components': seasonal_components,
                'trend_info': trend_info,
                'analysis_method': 'prophet'
            }
            
        except Exception as e:
            self.logger.error(f"Prophet analysis failed for {partner}/{path}: {e}")
            return self._fallback_analysis(metrics_df, partner, path)
    
    def _prepare_prophet_data(self, metrics_df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare data in Prophet format (ds, y columns)
        """
        prophet_df = pd.DataFrame()
        prophet_df['ds'] = pd.to_datetime(metrics_df['timestamp'])
        prophet_df['y'] = metrics_df['value'].astype(float)
        
        # Remove any NaN or infinite values
        prophet_df = prophet_df.dropna()
        prophet_df = prophet_df[np.isfinite(prophet_df['y'])]
        
        # Sort by timestamp
        prophet_df = prophet_df.sort_values('ds').reset_index(drop=True)
        
        return prophet_df
    
    def _create_prophet_model(self) -> Prophet:
        """
        Create Prophet model with configuration
        """
        # Check if running in CI/CD mode for faster execution
        import os
        ci_mode = os.getenv('TRENDMASTER_CI_MODE', 'false').lower() == 'true'
        
        if ci_mode:
            # Use faster settings for CI/CD
            model_params = {
                'seasonality_mode': 'additive',  # Faster than multiplicative
                'yearly_seasonality': False,
                'weekly_seasonality': False,     # Disable for speed
                'daily_seasonality': False,      # Disable for speed
                'changepoint_prior_scale': 0.1,  # Less sensitive for speed
                'uncertainty_samples': 100,      # Much faster than 1000
                'interval_width': 0.8           # Smaller interval for speed
            }
            self.logger.info("Using fast Prophet settings for CI/CD mode")
        else:
            # Use normal settings for production
            model_params = {
                'seasonality_mode': self.prophet_config.get('seasonality_mode', 'multiplicative'),
                'yearly_seasonality': self.prophet_config.get('yearly_seasonality', False),
                'weekly_seasonality': self.prophet_config.get('weekly_seasonality', True),
                'daily_seasonality': self.prophet_config.get('daily_seasonality', True),
                'changepoint_prior_scale': self.prophet_config.get('changepoint_prior_scale', 0.05),
                'uncertainty_samples': self.prophet_config.get('uncertainty_samples', 1000),
                'interval_width': self.prophet_config.get('interval_width', 0.95)
            }
        
        # Note: verbosity parameter removed in newer Prophet versions
        # Prophet output is already minimal by default
        
        return Prophet(**model_params)
    
    def _detect_prophet_anomalies(self, actual_df: pd.DataFrame, forecast_df: pd.DataFrame) -> List[Dict]:
        """
        Detect anomalies using Prophet's uncertainty intervals
        """
        anomalies = []
        
        # Merge actual and forecast data
        merged_df = actual_df.merge(forecast_df[['ds', 'yhat', 'yhat_lower', 'yhat_upper']], on='ds')
        
        # Find points outside uncertainty intervals
        anomaly_mask = (merged_df['y'] < merged_df['yhat_lower']) | (merged_df['y'] > merged_df['yhat_upper'])
        anomaly_points = merged_df[anomaly_mask]
        
        for _, row in anomaly_points.iterrows():
            severity = self._calculate_anomaly_severity(row['y'], row['yhat'], row['yhat_lower'], row['yhat_upper'])
            
            anomalies.append({
                'timestamp': row['ds'],
                'actual_value': row['y'],
                'predicted_value': row['yhat'],
                'lower_bound': row['yhat_lower'],
                'upper_bound': row['yhat_upper'],
                'severity': severity,
                'type': 'prophet_uncertainty'
            })
        
        return anomalies
    
    def _calculate_anomaly_severity(self, actual: float, predicted: float, lower: float, upper: float) -> str:
        """
        Calculate anomaly severity based on how far outside bounds the value is
        """
        if actual > upper:
            deviation = (actual - upper) / (upper - predicted) if upper != predicted else 1
        else:
            deviation = (lower - actual) / (predicted - lower) if predicted != lower else 1
        
        if deviation > 3:
            return 'high'
        elif deviation > 1.5:
            return 'medium'
        else:
            return 'low'
    
    def _extract_seasonal_components(self, model: Prophet, forecast: pd.DataFrame) -> Dict:
        """
        Extract seasonal components from Prophet model
        """
        components = {}
        
        if 'weekly' in forecast.columns:
            components['weekly'] = {
                'mean': forecast['weekly'].mean(),
                'std': forecast['weekly'].std(),
                'min': forecast['weekly'].min(),
                'max': forecast['weekly'].max()
            }
        
        if 'daily' in forecast.columns:
            components['daily'] = {
                'mean': forecast['daily'].mean(),
                'std': forecast['daily'].std(),
                'min': forecast['daily'].min(),
                'max': forecast['daily'].max()
            }
        
        return components
    
    def _calculate_trend_info(self, forecast: pd.DataFrame) -> Dict:
        """
        Calculate trend information from forecast
        """
        trend_values = forecast['trend'].values
        
        # Calculate trend direction and strength
        if len(trend_values) > 1:
            trend_slope = np.polyfit(range(len(trend_values)), trend_values, 1)[0]
            trend_direction = 'increasing' if trend_slope > 0 else 'decreasing' if trend_slope < 0 else 'stable'
        else:
            trend_slope = 0
            trend_direction = 'stable'
        
        return {
            'slope': trend_slope,
            'direction': trend_direction,
            'mean': trend_values.mean(),
            'std': trend_values.std(),
            'start_value': trend_values[0] if len(trend_values) > 0 else 0,
            'end_value': trend_values[-1] if len(trend_values) > 0 else 0
        }
    
    def _fallback_analysis(self, metrics_df: pd.DataFrame, partner: str, path: str) -> Dict:
        """
        Fallback analysis when Prophet is not available
        """
        self.logger.info(f"Using statistical fallback analysis for {partner}/{path}")
        
        # Basic statistical analysis
        values = metrics_df['value'].astype(float)
        
        # Detect statistical anomalies
        anomalies = self._detect_statistical_anomalies(metrics_df)
        
        # Simple trend calculation
        if len(values) > 1:
            trend_slope = np.polyfit(range(len(values)), values, 1)[0]
            trend_direction = 'increasing' if trend_slope > 0 else 'decreasing' if trend_slope < 0 else 'stable'
        else:
            trend_slope = 0
            trend_direction = 'stable'
        
        return {
            'partner': partner,
            'path': path,
            'anomalies': anomalies,
            'trend_info': {
                'slope': trend_slope,
                'direction': trend_direction,
                'mean': values.mean(),
                'std': values.std()
            },
            'seasonal_components': {},
            'analysis_method': 'statistical_fallback'
        }
    
    def _detect_statistical_anomalies(self, metrics_df: pd.DataFrame) -> List[Dict]:
        """
        Detect anomalies using statistical methods (IQR and Z-score)
        """
        anomalies = []
        values = metrics_df['value'].astype(float)
        
        # IQR method
        Q1 = values.quantile(0.25)
        Q3 = values.quantile(0.75)
        IQR = Q3 - Q1
        iqr_multiplier = self.anomaly_config.get('iqr_multiplier', 1.5)
        
        lower_bound = Q1 - iqr_multiplier * IQR
        upper_bound = Q3 + iqr_multiplier * IQR
        
        # Z-score method
        mean_val = values.mean()
        std_val = values.std()
        zscore_threshold = self.anomaly_config.get('zscore_threshold', 3.0)
        
        for idx, row in metrics_df.iterrows():
            value = float(row['value'])
            timestamp = row['timestamp']
            
            # Check IQR bounds
            iqr_anomaly = value < lower_bound or value > upper_bound
            
            # Check Z-score
            if std_val > 0:
                zscore = abs(value - mean_val) / std_val
                zscore_anomaly = zscore > zscore_threshold
            else:
                zscore_anomaly = False
            
            if iqr_anomaly or zscore_anomaly:
                severity = 'high' if (iqr_anomaly and zscore_anomaly) else 'medium'
                
                anomalies.append({
                    'timestamp': timestamp,
                    'actual_value': value,
                    'predicted_value': mean_val,
                    'lower_bound': lower_bound,
                    'upper_bound': upper_bound,
                    'severity': severity,
                    'type': 'statistical'
                })
        
        return anomalies
    
    def filter_anomalous_data(self, metrics_df: pd.DataFrame, analysis_result: Dict) -> pd.DataFrame:
        """
        Filter out anomalous data points from metrics DataFrame
        """
        if not analysis_result.get('anomalies'):
            return metrics_df
        
        # Get anomalous timestamps
        anomaly_timestamps = [anomaly['timestamp'] for anomaly in analysis_result['anomalies']]
        
        # Filter out anomalies based on severity
        severity_filter = self.anomaly_config.get('severity_filter', ['high'])
        filtered_timestamps = [
            anomaly['timestamp'] for anomaly in analysis_result['anomalies']
            if anomaly['severity'] in severity_filter
        ]
        
        # Remove anomalous data points
        clean_df = metrics_df[~metrics_df['timestamp'].isin(filtered_timestamps)].copy()
        
        self.logger.info(f"Filtered {len(filtered_timestamps)} anomalous data points out of {len(metrics_df)}")
        
        return clean_df
    
    def get_analysis_summary(self, analysis_result: Dict) -> Dict:
        """
        Get summary of analysis results
        """
        summary = {
            'partner': analysis_result.get('partner'),
            'path': analysis_result.get('path'),
            'analysis_method': analysis_result.get('analysis_method'),
            'anomaly_count': len(analysis_result.get('anomalies', [])),
            'trend_direction': analysis_result.get('trend_info', {}).get('direction', 'unknown'),
            'trend_slope': analysis_result.get('trend_info', {}).get('slope', 0)
        }
        
        # Add anomaly breakdown by severity
        anomalies = analysis_result.get('anomalies', [])
        summary['anomaly_breakdown'] = {
            'high': len([a for a in anomalies if a['severity'] == 'high']),
            'medium': len([a for a in anomalies if a['severity'] == 'medium']),
            'low': len([a for a in anomalies if a['severity'] == 'low'])
        }
        
        return summary