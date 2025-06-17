#!/usr/bin/env python3
"""
TrendMaster-AI Enhanced Rate Calculator v3.0
Production-Optimized Rate Limiting with 2.5x Average Peaks Formula

This module implements the new v3 rate limiting formula:
recommended_rate = effective_peak * 2.5 * cache_adjustment * trend_adjustment

Key Features:
- 2.5x average peaks formula (excluding anomalies)
- Cache-aware calculations with real cache hit ratio integration
- Production-ready optimizations using numpy for performance
- Structured data classes and enums for better type safety
- Environment-specific partner and API configurations
- Enhanced confidence calculations and comprehensive logging
- Environment variable-based configuration
"""

import os
import sys
import logging
import numpy as np
import pandas as pd
import math
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime, timedelta
import yaml

# Add the project root to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from scripts.utils.prometheus_client import PrometheusClient
    from scripts.utils.cache_metrics import CacheMetricsCollector
except ImportError:
    # Fallback for standalone usage
    PrometheusClient = None
    CacheMetricsCollector = None


class TrafficPattern(Enum):
    """Traffic pattern classifications for production optimization"""
    STABLE = "stable"
    VARIABLE = "variable"
    MODERATELY_SPIKY = "moderately_spiky"
    VERY_SPIKY = "very_spiky"


class ConfidenceLevel(Enum):
    """Confidence level classifications for production reliability"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class RateCalculationResult:
    """Structured result for rate limit calculations with comprehensive metadata"""
    partner: str
    path: str
    recommended_rate_limit: int
    base_metrics: Dict
    calculation_method: str
    confidence: Dict
    cache_ratio_applied: float
    safety_margin_applied: float
    rationale: str
    environment: str = ""
    excluded: bool = False
    error: Optional[str] = None


class EnhancedRateCalculator:
    """
    Production-optimized rate calculator implementing v3 formula with 2.5x average peaks.
    
    This calculator provides:
    - Environment-aware partner and API configurations
    - Cache-aware rate limiting with real cache hit ratios
    - Production-ready performance optimizations
    - Comprehensive confidence scoring and logging
    - Environment variable-based configuration
    """
    
    def __init__(self, config: Dict[str, Any], prometheus_client: Optional[Any] = None, config_manager: Optional[Any] = None):
        """Initialize the enhanced rate calculator with production optimizations."""
        self.config = config
        self.prometheus_client = prometheus_client
        self.config_manager = config_manager
        
        # Initialize logger first
        self.logger = logging.getLogger(__name__)
        
        # Initialize cache collector if available
        if CacheMetricsCollector and prometheus_client:
            self.cache_collector = CacheMetricsCollector(prometheus_client, config)
        else:
            self.cache_collector = None
        
        # Get environment from environment variables or config manager
        if self.config_manager:
            self.current_environment = self.config_manager.get_current_environment()
            self.deployment_mode = self.config_manager.get_deployment_mode()
            self.partner_config = self.config_manager.get_partner_config()
        else:
            # Fallback to original method if no config manager provided
            self.current_environment = self._get_environment_from_env_vars()
            self.deployment_mode = self._determine_deployment_mode()
            self.partner_config = self._load_partner_config()
        
        # Load rate calculation configuration
        self.rate_config = config.get('COMMON', {}).get('RATE_CALCULATION', {})
        self.formula_version = self.rate_config.get('formula_version', 'v3')
        self.peak_multiplier = self.rate_config.get('peak_multiplier', 2.5)
        self.cache_adjustment_factor = self.rate_config.get('cache_adjustment_factor', 1.2)
        self.safety_margin = self.rate_config.get('safety_margin', 1.2)
        self.min_rate_limit = self.rate_config.get('min_rate_limit', 100)
        self.max_rate_limit = self.rate_config.get('max_rate_limit', 50000)
        self.rounding_method = self.rate_config.get('rounding_method', 'nearest_hundred')
        
        # Load environment-specific configurations
        self.env_config = config.get('ENVIRONMENTS', {}).get(self.deployment_mode, {})
        
        # Apply deployment-specific overrides
        self._apply_deployment_overrides()
        
        # Load path multipliers and exclusions
        self.path_multipliers = config.get('COMMON', {}).get('PATH_MULTIPLIERS', {})
        self.exclusions = config.get('COMMON', {}).get('EXCLUSIONS', {})
        
        # Traffic pattern thresholds
        self.spike_threshold_high = self.rate_config.get('spike_threshold_high', 8.0)
        self.spike_threshold_medium = self.rate_config.get('spike_threshold_medium', 4.0)
        self.variability_threshold_high = self.rate_config.get('variability_threshold_high', 1.0)
        self.variability_threshold_medium = self.rate_config.get('variability_threshold_medium', 0.6)
        
        # Cache integration settings
        self.enable_cache_adjustment = self.rate_config.get('enable_cache_adjustment', True)
        self.cache_hit_threshold = self.rate_config.get('cache_hit_threshold', 0.1)
        
        # Setup logging
        log_level = config.get('COMMON', {}).get('LOG_LEVEL', 'INFO')
        self.logger.setLevel(getattr(logging, log_level))
        
        self.logger.info(f"Enhanced Rate Calculator v3.0 initialized")
        self.logger.info(f"Formula: {self.formula_version}, Peak Multiplier: {self.peak_multiplier}")
        self.logger.info(f"Current Environment: {self.current_environment}")
        self.logger.info(f"Deployment Mode: {self.deployment_mode}")
        self.logger.info(f"Trickster Environment: {self.env_config.get('TRICKSTER_ENV', 'unknown')}")
        self.logger.info(f"Partner Config: {len(self.partner_config.get('partners', []))} partners, {len(self.partner_config.get('apis', []))} APIs")

    def _get_environment_from_env_vars(self) -> str:
        """Get current environment from environment variables."""
        # Check multiple possible environment variable names
        env_vars_to_check = [
            'ENVIRONMENT',
            'ENV',
            'DEPLOYMENT_ENV',
            'KALTURA_ENV',
            'TRICKSTER_ENV',
            'APP_ENV',
            'NODE_ENV'
        ]
        
        for env_var in env_vars_to_check:
            env_value = os.environ.get(env_var)
            if env_value:
                self.logger.info(f"Environment detected from {env_var}: {env_value}")
                return env_value.lower()
        
        # Default fallback
        default_env = 'orp2'
        self.logger.warning(f"No environment variable found, defaulting to: {default_env}")
        return default_env
    
    def _determine_deployment_mode(self) -> str:
        """Determine deployment mode based on environment."""
        # Check for explicit deployment mode in environment variables
        deployment_mode = os.environ.get('DEPLOYMENT_MODE')
        if deployment_mode:
            return deployment_mode.lower()
        
        # Map environment to deployment mode
        env_to_mode_mapping = {
            'orp2': 'local',
            'local': 'local',
            'development': 'local',
            'dev': 'local',
            'testing': 'testing',
            'test': 'testing',
            'staging': 'testing',
            'production': 'production',
            'prod': 'production'
        }
        
        deployment_mode = env_to_mode_mapping.get(self.current_environment, 'local')
        self.logger.info(f"Deployment mode determined: {deployment_mode} (from environment: {self.current_environment})")
        return deployment_mode
    
    def _apply_deployment_overrides(self) -> None:
        """Apply deployment-specific configuration overrides."""
        overrides = self.config.get('DEPLOYMENT_OVERRIDES', {}).get(self.deployment_mode, {})
        
        if overrides:
            self.logger.info(f"Applying deployment overrides for {self.deployment_mode}")
            
            # Apply common overrides
            common_overrides = overrides.get('COMMON', {})
            if common_overrides:
                # Update rate calculation config
                rate_calc_overrides = common_overrides.get('RATE_CALCULATION', {})
                self.rate_config.update(rate_calc_overrides)
                
                # Update safety margin if overridden
                if 'safety_margin' in rate_calc_overrides:
                    self.safety_margin = rate_calc_overrides['safety_margin']
                    self.logger.info(f"Safety margin overridden to: {self.safety_margin}")
    
    def _load_partner_config(self) -> Dict[str, Any]:
        """Load environment-specific partner configuration."""
        # Determine which partner config to use based on current environment
        partner_configs = self.config.get('PARTNER_CONFIGS', {})
        
        # Prioritize direct match for current_environment in PARTNER_CONFIGS
        if self.current_environment in partner_configs:
            config_key = self.current_environment
        # Fallback logic for specific environment categories if direct match failed
        elif self.current_environment in ['orp2', 'local', 'development'] and 'orp2' in partner_configs:
            config_key = 'orp2'
            self.logger.info(f"Using 'orp2' partner config as fallback for environment '{self.current_environment}'")
        elif self.current_environment in ['orp2', 'local', 'development'] and 'local' in partner_configs:
            config_key = 'local'
            self.logger.info(f"Using 'local' partner config as fallback for environment '{self.current_environment}'")
        # If current_environment is 'testing' or 'staging', it should have been caught by the first 'if'
        # if a 'testing' or 'staging' section exists in PARTNER_CONFIGS.
        # If not, we proceed to a more general fallback.
        elif 'production' in partner_configs: # General fallback to 'production' if it exists
            config_key = 'production'
            self.logger.info(f"Using 'production' partner config as general fallback for environment '{self.current_environment}'")
        else:
            # Absolute fallback if no suitable key found in PARTNER_CONFIGS
            self.logger.warning(f"No specific or standard fallback partner config found for '{self.current_environment}' in PARTNER_CONFIGS. Using hardcoded default.")
            return {
                'partners': ['CUSTOMER_ID_1', 'CUSTOMER_ID_3'],
                'apis': ['/api_v3/service/ENDPOINT_5'],
                'partner_multipliers': {'CUSTOMER_ID_1': 1.0, 'CUSTOMER_ID_3': 1.0}
            }
        
        # Check if the determined config_key (which should now be more accurate) exists
        if config_key not in partner_configs:
            self.logger.warning(f"No partner config found for '{config_key}', using default")
            # Return default configuration
            return {
                'partners': ['CUSTOMER_ID_1', 'CUSTOMER_ID_3'],
                'apis': ['/api_v3/service/ENDPOINT_5'],
                'partner_multipliers': {'CUSTOMER_ID_1': 1.0, 'CUSTOMER_ID_3': 1.0}
            }
        
        selected_config = partner_configs[config_key]
        self.logger.info(f"Loaded partner config for '{config_key}': {len(selected_config.get('partners', []))} partners, {len(selected_config.get('apis', []))} APIs")
        return selected_config

    def calculate_optimal_rate_limit(self, 
                                   clean_metrics: pd.DataFrame, 
                                   prime_time_data: pd.DataFrame,
                                   prophet_analysis: Dict,
                                   partner: str, 
                                   path: str,
                                   cache_metrics: Optional[Dict] = None) -> RateCalculationResult:
        """
        Calculate optimal rate limit using production-ready v3 formula:
        2.5x average peaks (excluding anomalies) with cache considerations
        """
        try:
            # Check exclusions first
            if self._should_exclude(partner, path):
                return self._get_exclusion_result(partner, path)
            
            # Validate input data
            if len(clean_metrics) == 0:
                self.logger.warning(f"No clean metrics data for {partner}/{path}")
                return self._get_default_result(partner, path)
            
            # Calculate base metrics from anomaly-free data
            base_metrics = self._calculate_base_metrics(clean_metrics, prime_time_data)
            
            # Apply v3 formula (2.5x average peaks)
            recommended_rate = self._calculate_v3_formula(
                base_metrics, prophet_analysis, partner, path, cache_metrics
            )
            
            # Apply partner and path-specific adjustments
            recommended_rate = self._apply_partner_path_adjustments(
                recommended_rate, partner, path, base_metrics
            )
            
            # Apply safety margins and bounds
            final_rate = self._apply_safety_and_bounds(recommended_rate, base_metrics)
            
            # Round according to configuration
            final_rate = self._round_rate_limit(final_rate)
            
            # Calculate confidence metrics
            confidence_info = self._calculate_confidence(base_metrics, prophet_analysis, clean_metrics)
            
            return RateCalculationResult(
                partner=partner,
                path=path,
                recommended_rate_limit=final_rate,
                base_metrics=base_metrics,
                calculation_method=f'enhanced_formula_{self.formula_version}',
                confidence=confidence_info,
                cache_ratio_applied=self.cache_adjustment_factor,
                safety_margin_applied=self.safety_margin,
                rationale=self._generate_rationale(base_metrics, recommended_rate, final_rate, cache_metrics),
                environment=self.current_environment
            )
            
        except Exception as e:
            self.logger.error(f"Rate calculation failed for {partner}/{path}: {e}", exc_info=True)
            return self._get_error_result(partner, path, str(e))
    
    def _calculate_base_metrics(self, clean_metrics: pd.DataFrame, prime_time_data: pd.DataFrame) -> Dict:
        """
        Calculate comprehensive base metrics from anomaly-free data
        Optimized for production performance using numpy
        """
        # Convert to numpy arrays for faster computation
        overall_values = clean_metrics['value'].astype(float).values
        prime_values = prime_time_data['value'].astype(float).values if len(prime_time_data) > 0 else overall_values
        
        # Calculate percentiles efficiently
        overall_percentiles = np.percentile(overall_values, [50, 75, 90, 95, 99])
        prime_percentiles = np.percentile(prime_values, [50, 75, 90, 95, 99])
        
        # Calculate key statistics
        overall_mean = np.mean(overall_values)
        overall_std = np.std(overall_values)
        prime_mean = np.mean(prime_values)
        prime_std = np.std(prime_values)
        
        # Calculate average peaks (excluding anomalies) - KEY METRIC for v3 formula
        # Use 90th percentile as representative of "peaks" to avoid extreme outliers
        average_peak_overall = overall_percentiles[2]  # 90th percentile
        average_peak_prime = prime_percentiles[2]      # 90th percentile
        
        base_metrics = {
            # Core metrics for v3 formula
            'average_peak_overall': average_peak_overall,
            'average_peak_prime': average_peak_prime,
            'effective_peak': max(average_peak_overall, average_peak_prime),  # Use higher of the two
            
            # Overall metrics (optimized)
            'overall_mean': overall_mean,
            'overall_median': overall_percentiles[0],
            'overall_std': overall_std,
            'overall_min': np.min(overall_values),
            'overall_max': np.max(overall_values),
            'overall_count': len(overall_values),
            'overall_p95': overall_percentiles[3],
            'overall_p99': overall_percentiles[4],
            
            # Prime time metrics (optimized)
            'prime_mean': prime_mean,
            'prime_median': prime_percentiles[0],
            'prime_std': prime_std,
            'prime_min': np.min(prime_values),
            'prime_max': np.max(prime_values),
            'prime_count': len(prime_values),
            'prime_p95': prime_percentiles[3],
            'prime_p99': prime_percentiles[4],
            
            # Pattern analysis metrics
            'coefficient_of_variation': overall_std / overall_mean if overall_mean > 0 else 0,
            'peak_to_mean_ratio': np.max(overall_values) / overall_mean if overall_mean > 0 else 1.0,
            'prime_to_overall_ratio': prime_mean / overall_mean if overall_mean > 0 else 1.0,
            'traffic_pattern': self._classify_traffic_pattern(overall_values, prime_values)
        }
        
        return base_metrics
    
    def _calculate_v3_formula(self, base_metrics: Dict, prophet_analysis: Dict, 
                             partner: str, path: str, cache_metrics: Optional[Dict] = None) -> float:
        """
        NEW v3 Formula: 2.5x average peaks (excluding anomalies) with cache considerations
        
        Core Formula: recommended_rate = effective_peak * 2.5 * cache_adjustment * trend_adjustment
        """
        # Get the effective peak (90th percentile representing average peaks)
        effective_peak = base_metrics['effective_peak']
        traffic_pattern = base_metrics['traffic_pattern']
        
        # Apply core 2.5x multiplier to average peaks
        base_rate = effective_peak * self.peak_multiplier
        
        # Apply cache adjustment if enabled and cache metrics available
        cache_multiplier = 1.0
        if self.enable_cache_adjustment and cache_metrics:
            cache_multiplier = self._calculate_cache_multiplier(cache_metrics)
        else:
            # Default cache adjustment factor for production safety
            cache_multiplier = self.cache_adjustment_factor
        
        # Apply cache adjustment
        cache_adjusted_rate = base_rate * cache_multiplier
        
        # Apply traffic pattern adjustments for production stability
        pattern_multiplier = self._get_pattern_multiplier(traffic_pattern, base_metrics)
        pattern_adjusted_rate = cache_adjusted_rate * pattern_multiplier
        
        # Apply trend adjustments from Prophet analysis
        trend_multiplier = self._calculate_trend_multiplier(prophet_analysis, base_metrics)
        final_rate = pattern_adjusted_rate * trend_multiplier
        
        self.logger.debug(
            f"V3 Formula for {partner}/{path}: "
            f"EffectivePeak={effective_peak:.1f}, "
            f"BaseRate={base_rate:.1f}, "
            f"CacheMultiplier={cache_multiplier:.2f}, "
            f"PatternMultiplier={pattern_multiplier:.2f}, "
            f"TrendMultiplier={trend_multiplier:.2f}, "
            f"FinalRate={final_rate:.1f}"
        )
        
        return final_rate
    
    def _classify_traffic_pattern(self, overall_values: np.ndarray, prime_values: np.ndarray) -> TrafficPattern:
        """
        Classify traffic pattern for optimized rate limiting
        """
        overall_mean = np.mean(overall_values)
        overall_std = np.std(overall_values)
        overall_max = np.max(overall_values)
        
        if overall_mean == 0:
            return TrafficPattern.STABLE
        
        peak_to_mean = overall_max / overall_mean
        coefficient_of_variation = overall_std / overall_mean
        
        if peak_to_mean > self.spike_threshold_high and coefficient_of_variation > self.variability_threshold_high:
            return TrafficPattern.VERY_SPIKY
        elif peak_to_mean > self.spike_threshold_medium and coefficient_of_variation > self.variability_threshold_medium:
            return TrafficPattern.MODERATELY_SPIKY
        elif peak_to_mean > 2.0 or coefficient_of_variation > 0.3:
            return TrafficPattern.VARIABLE
        else:
            return TrafficPattern.STABLE
    
    def _get_pattern_multiplier(self, pattern: TrafficPattern, base_metrics: Dict) -> float:
        """
        Get multiplier based on traffic pattern for production stability
        """
        multipliers = {
            TrafficPattern.VERY_SPIKY: 0.9,      # Conservative for very spiky traffic
            TrafficPattern.MODERATELY_SPIKY: 1.0, # Standard multiplier
            TrafficPattern.VARIABLE: 1.1,        # Slightly higher for variable traffic
            TrafficPattern.STABLE: 1.2           # Higher confidence for stable traffic
        }
        return multipliers.get(pattern, 1.0)
    
    def _calculate_cache_multiplier(self, cache_metrics: Dict) -> float:
        """
        Calculate cache-aware multiplier based on actual cache performance
        Formula: Adjust based on cache hit ratio to account for requests not hitting Istio
        """
        if not cache_metrics:
            return self.cache_adjustment_factor
        
        try:
            cache_hit_ratio = cache_metrics.get('cache_hit_ratio', 0.0)
            
            # Ensure we have valid ratios
            if cache_hit_ratio < 0 or cache_hit_ratio > 1:
                cache_hit_ratio = 0.0
            
            # Calculate effective traffic multiplier
            # Higher cache hit ratio means fewer requests hit Istio, so we can be more aggressive
            # Lower cache hit ratio means more requests hit Istio, so we need to be more conservative
            if cache_hit_ratio >= self.cache_hit_threshold:
                # Good cache performance - requests hitting Istio are reduced
                cache_multiplier = 1.0 + (cache_hit_ratio * 0.3)  # Up to 30% increase
            else:
                # Poor cache performance - most requests hit Istio
                cache_multiplier = self.cache_adjustment_factor
            
            self.logger.debug(f"Cache multiplier: {cache_multiplier:.2f} (hit_ratio: {cache_hit_ratio:.2f})")
            return cache_multiplier
            
        except Exception as e:
            self.logger.warning(f"Error calculating cache multiplier: {e}")
            return self.cache_adjustment_factor
    
    def _calculate_trend_multiplier(self, prophet_analysis: Dict, base_metrics: Dict) -> float:
        """
        Calculate trend-based multiplier from Prophet analysis
        """
        if not prophet_analysis or not prophet_analysis.get('trend_info'):
            return 1.0
        
        try:
            trend_info = prophet_analysis['trend_info']
            direction = trend_info.get('direction', 'stable')
            slope = trend_info.get('slope', 0)
            
            if direction == 'increasing' and slope > 0:
                # Growing traffic - apply conservative growth multiplier
                prime_mean = base_metrics.get('prime_mean', 1)
                if prime_mean > 0:
                    # Limit trend adjustment to reasonable bounds (1.0 to 1.3)
                    trend_multiplier = min(1.3, 1.0 + (slope / prime_mean) * 0.2)
                else:
                    trend_multiplier = 1.1
                    
                self.logger.debug(f"Applied increasing trend multiplier: {trend_multiplier:.2f}")
                return trend_multiplier
                
            elif direction == 'decreasing' and slope < 0:
                # Declining traffic - can be slightly more aggressive
                return 0.95
            
            return 1.0
            
        except Exception as e:
            self.logger.warning(f"Error calculating trend multiplier: {e}")
            return 1.0
    
    def _apply_partner_path_adjustments(self, base_rate: float, partner: str, path: str, base_metrics: Dict) -> float:
        """
        Apply production-ready partner and path-specific adjustments using environment-aware configuration
        """
        adjusted_rate = base_rate
        
        # Apply partner multiplier from environment-specific configuration
        partner_multipliers = self.partner_config.get('partner_multipliers', {})
        partner_multiplier = partner_multipliers.get(partner, 1.0)
        adjusted_rate *= partner_multiplier
        
        if partner_multiplier != 1.0:
            self.logger.debug(f"Applied partner multiplier {partner_multiplier} for partner {partner} (env: {self.current_environment})")
        
        # Apply path-specific multiplier
        path_multiplier = 1.0
        for path_pattern, multiplier in self.path_multipliers.items():
            if path_pattern in path:
                path_multiplier = multiplier
                break
        
        adjusted_rate *= path_multiplier
        
        if path_multiplier != 1.0:
            self.logger.debug(f"Applied path multiplier {path_multiplier} for path {path}")
        
        return adjusted_rate
    
    def _apply_safety_and_bounds(self, recommended_rate: float, base_metrics: Dict) -> float:
        """
        Apply safety margins and bounds checking with production safeguards
        """
        # Apply safety margin
        safe_rate = recommended_rate * self.safety_margin
        
        # Apply bounds
        bounded_rate = max(self.min_rate_limit, min(safe_rate, self.max_rate_limit))
        
        # Production safeguard: ensure rate is reasonable compared to observed traffic
        observed_peak = base_metrics.get('effective_peak', 0)
        if bounded_rate < observed_peak:
            self.logger.warning(
                f"Calculated rate {bounded_rate} is less than observed peak {observed_peak}. "
                f"Adjusting to safe minimum."
            )
            bounded_rate = max(bounded_rate, observed_peak * 1.2)
        
        return bounded_rate
    
    def _round_rate_limit(self, rate: float) -> int:
        """
        Round rate limit according to configuration for production consistency
        """
        if self.rounding_method == 'nearest_hundred':
            return max(100, int(round(rate / 100.0)) * 100)
        elif self.rounding_method == 'nearest_fifty':
            return max(50, int(round(rate / 50.0)) * 50)
        elif self.rounding_method == 'nearest_ten':
            return max(10, int(round(rate / 10.0)) * 10)
        else:
            return max(1, int(round(rate)))
    
    def _calculate_confidence(self, base_metrics: Dict, prophet_analysis: Dict, clean_metrics: pd.DataFrame) -> Dict:
        """
        Calculate production-ready confidence metrics
        """
        confidence_factors = {}
        
        # Data quantity confidence
        data_points = len(clean_metrics)
        if data_points >= 2000:
            data_confidence = 0.95
        elif data_points >= 1000:
            data_confidence = 0.85
        elif data_points >= 500:
            data_confidence = 0.75
        elif data_points >= 100:
            data_confidence = 0.65
        else:
            data_confidence = 0.45
        
        confidence_factors['data_quantity'] = data_confidence
        
        # Traffic stability confidence
        cv = base_metrics.get('coefficient_of_variation', 1.0)
        if cv < 0.2:
            stability_confidence = 0.95
        elif cv < 0.4:
            stability_confidence = 0.85
        elif cv < 0.8:
            stability_confidence = 0.70
        else:
            stability_confidence = 0.50
        
        confidence_factors['traffic_stability'] = stability_confidence
        
        # Analysis method confidence
        if prophet_analysis and prophet_analysis.get('analysis_method') == 'prophet':
            method_confidence = 0.90
        elif prophet_analysis:
            method_confidence = 0.75
        else:
            method_confidence = 0.60
        
        confidence_factors['analysis_method'] = method_confidence
        
        # Prime time data confidence
        prime_count = base_metrics.get('prime_count', 0)
        total_count = base_metrics.get('overall_count', 1)
        prime_ratio = prime_count / total_count if total_count > 0 else 0
        
        if prime_ratio >= 0.3:
            prime_confidence = 0.90
        elif prime_ratio >= 0.15:
            prime_confidence = 0.75
        else:
            prime_confidence = 0.60
        
        confidence_factors['prime_time_coverage'] = prime_confidence
        
        # Calculate weighted overall confidence
        weights = [0.25, 0.30, 0.25, 0.20]  # data, stability, method, prime_time
        overall_confidence = sum(
            conf * weight for conf, weight in zip(confidence_factors.values(), weights)
        )
        
        return {
            'overall_confidence': overall_confidence,
            'confidence_factors': confidence_factors,
            'confidence_level': self._get_confidence_level(overall_confidence).value
        }
    
    def _get_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Get confidence level classification"""
        if confidence >= 0.80:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.65:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def _generate_rationale(self, base_metrics: Dict, recommended_rate: float, 
                          final_rate: int, cache_metrics: Optional[Dict] = None) -> str:
        """
        Generate comprehensive rationale for production transparency
        """
        rationale_parts = []
        
        # Core formula explanation
        effective_peak = base_metrics.get('effective_peak', 0)
        traffic_pattern = base_metrics.get('traffic_pattern', TrafficPattern.STABLE)
        
        rationale_parts.append(
            f"Applied v{self.formula_version} formula: {self.peak_multiplier}x average peak "
            f"({effective_peak:.1f}) with {traffic_pattern.value} traffic pattern in {self.current_environment} environment"
        )
        
        # Cache consideration
        if cache_metrics:
            cache_hit_ratio = cache_metrics.get('cache_hit_ratio', 0)
            rationale_parts.append(f"Cache hit ratio: {cache_hit_ratio:.1%} considered in calculations")
        else:
            rationale_parts.append(f"Default cache adjustment factor {self.cache_adjustment_factor}x applied")
        
        # Safety margin
        if abs(final_rate - recommended_rate) > 1:
            rationale_parts.append(
                f"Safety margin {self.safety_margin}x applied "
                f"(from {recommended_rate:.0f} to {final_rate})"
            )
        
        return ". ".join(rationale_parts)
    
    def _should_exclude(self, partner: str, path: str) -> bool:
        """Check if partner/path should be excluded using environment-aware exclusions"""
        exclusions = self.exclusions
        
        # Global exclusions
        if partner in exclusions.get('global_partners', []):
            return True
        if path in exclusions.get('global_paths', []):
            return True
        
        # Environment-specific partner-path exclusions
        conditional_exclusions = exclusions.get('conditional_exclusions', {})
        partner_paths = conditional_exclusions.get('partner_paths', {})
        
        # Check environment-specific exclusions
        env_exclusions = partner_paths.get(self.current_environment, {})
        if partner in env_exclusions and path in env_exclusions[partner]:
            return True
        
        # Check if partner is in configured partners list
        configured_partners = self.partner_config.get('partners', [])
        if configured_partners and partner not in configured_partners:
            self.logger.debug(f"Partner {partner} not in configured partners for {self.current_environment}")
            return True
        
        # Check if path is in configured APIs list
        configured_apis = self.partner_config.get('apis', [])
        if configured_apis:
            # Check if any configured API pattern matches the path
            path_matches = any(api_pattern in path for api_pattern in configured_apis)
            if not path_matches:
                self.logger.debug(f"Path {path} not in configured APIs for {self.current_environment}")
                return True
        
        return False
    
    def _get_exclusion_result(self, partner: str, path: str) -> RateCalculationResult:
        """Get result for excluded partner/path"""
        return RateCalculationResult(
            partner=partner,
            path=path,
            recommended_rate_limit=0,
            base_metrics={},
            calculation_method='excluded',
            confidence={},
            cache_ratio_applied=0.0,
            safety_margin_applied=0.0,
            rationale=f'Configured exclusion for {self.current_environment} environment',
            environment=self.current_environment,
            excluded=True
        )
    
    def _get_default_result(self, partner: str, path: str) -> RateCalculationResult:
        """Get default result when calculation cannot be performed"""
        return RateCalculationResult(
            partner=partner,
            path=path,
            recommended_rate_limit=self.min_rate_limit,
            base_metrics={},
            calculation_method='default_fallback',
            confidence={'overall_confidence': 0.3, 'confidence_level': 'low'},
            cache_ratio_applied=self.cache_adjustment_factor,
            safety_margin_applied=self.safety_margin,
            rationale=f'Insufficient data - using minimum rate limit of {self.min_rate_limit} for {self.current_environment}',
            environment=self.current_environment
        )
    
    def _get_error_result(self, partner: str, path: str, error_message: str) -> RateCalculationResult:
        """Get result for calculation errors"""
        return RateCalculationResult(
            partner=partner,
            path=path,
            recommended_rate_limit=self.min_rate_limit,
            base_metrics={},
            calculation_method='error_fallback',
            confidence={'overall_confidence': 0.2, 'confidence_level': 'low'},
            cache_ratio_applied=self.cache_adjustment_factor,
            safety_margin_applied=self.safety_margin,
            rationale=f'Calculation error - using minimum rate limit of {self.min_rate_limit} for {self.current_environment}',
            environment=self.current_environment,
            error=error_message
        )

    def get_environment_info(self) -> Dict[str, Any]:
        """Get current environment configuration information"""
        return {
            'current_environment': self.current_environment,
            'deployment_mode': self.deployment_mode,
            'trickster_env': self.env_config.get('TRICKSTER_ENV', 'unknown'),
            'prometheus_url': self.env_config.get('PROMETHEUS_URL', ''),
            'partners_count': len(self.partner_config.get('partners', [])),
            'apis_count': len(self.partner_config.get('apis', [])),
            'formula_version': self.formula_version,
            'peak_multiplier': self.peak_multiplier,
            'safety_margin': self.safety_margin
        }

    def validate_partner_path(self, partner: str, path: str) -> Dict[str, Any]:
        """Validate if partner/path combination is supported in current environment"""
        result = {
            'valid': True,
            'partner_supported': partner in self.partner_config.get('partners', []),
            'path_supported': False,
            'environment': self.current_environment,
            'reason': ''
        }
        
        # Check if path matches any configured API
        configured_apis = self.partner_config.get('apis', [])
        if configured_apis:
            result['path_supported'] = any(api_pattern in path for api_pattern in configured_apis)
        else:
            result['path_supported'] = True  # If no APIs configured, allow all paths
        
        # Check exclusions
        if self._should_exclude(partner, path):
            result['valid'] = False
            result['reason'] = 'Excluded by configuration'
        elif not result['partner_supported']:
            result['valid'] = False
            result['reason'] = f'Partner {partner} not configured for {self.current_environment} environment'
        elif not result['path_supported']:
            result['valid'] = False
            result['reason'] = f'Path {path} not in configured APIs for {self.current_environment} environment'
        
        return result