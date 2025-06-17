#!/usr/bin/env python3
"""
TrendMaster-AI Prometheus Client
Production-Ready Prometheus Integration

This module provides a robust Prometheus client for querying metrics
with environment awareness, error handling, and production optimizations.
"""

import os
import logging
import requests
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from urllib.parse import urljoin
import json


@dataclass
class PrometheusQuery:
    """Prometheus query configuration"""
    query: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    step: str = "1m"
    timeout: int = 30


@dataclass
class PrometheusResult:
    """Prometheus query result"""
    success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None
    query_time: float = 0.0
    result_count: int = 0


class PrometheusClient:
    """
    Production-ready Prometheus client with environment awareness
    """
    
    def __init__(self, base_url: str, timeout: int = 30, max_retries: int = 3):
        """
        Initialize Prometheus client
        
        Args:
            base_url: Prometheus server base URL
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)
        
        # Setup session with connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TrendMaster-AI-Prometheus-Client/3.0.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Connection pool settings
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=0  # We handle retries manually
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        self.logger.info(f"Prometheus client initialized: {self.base_url}")
    
    def query(self, query: str, time_param: Optional[datetime] = None) -> PrometheusResult:
        """
        Execute instant query
        
        Args:
            query: PromQL query string
            time_param: Optional evaluation time
            
        Returns:
            PrometheusResult with query results
        """
        start_time = time.time()
        
        try:
            url = urljoin(self.base_url, '/api/v1/query')
            params = {'query': query}
            
            if time_param:
                params['time'] = time_param.timestamp()
            
            self.logger.debug(f"Executing query: {query}")
            
            response = self._make_request('GET', url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                query_time = time.time() - start_time
                
                if data.get('status') == 'success':
                    result_data = data.get('data', {})
                    result_count = len(result_data.get('result', []))
                    
                    self.logger.debug(f"Query successful: {result_count} results in {query_time:.2f}s")
                    
                    return PrometheusResult(
                        success=True,
                        data=result_data,
                        query_time=query_time,
                        result_count=result_count
                    )
                else:
                    error_msg = data.get('error', 'Unknown Prometheus error')
                    self.logger.error(f"Prometheus query failed: {error_msg}")
                    return PrometheusResult(success=False, error=error_msg)
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.logger.error(f"Prometheus request failed: {error_msg}")
                return PrometheusResult(success=False, error=error_msg)
        
        except Exception as e:
            query_time = time.time() - start_time
            error_msg = f"Query execution failed: {e}"
            self.logger.error(error_msg)
            return PrometheusResult(success=False, error=error_msg, query_time=query_time)
    
    def query_range(self, query: str, start_time: datetime, end_time: datetime, 
                   step: str = "1m") -> PrometheusResult:
        """
        Execute range query
        
        Args:
            query: PromQL query string
            start_time: Query start time
            end_time: Query end time
            step: Query resolution step
            
        Returns:
            PrometheusResult with query results
        """
        start_exec_time = time.time()
        
        try:
            url = urljoin(self.base_url, '/api/v1/query_range')
            params = {
                'query': query,
                'start': start_time.timestamp(),
                'end': end_time.timestamp(),
                'step': step
            }
            
            self.logger.debug(f"Executing range query: {query} from {start_time} to {end_time}")
            
            response = self._make_request('GET', url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                query_time = time.time() - start_exec_time
                
                if data.get('status') == 'success':
                    result_data = data.get('data', {})
                    result_count = len(result_data.get('result', []))
                    
                    # Count total data points
                    total_points = sum(
                        len(series.get('values', [])) 
                        for series in result_data.get('result', [])
                    )
                    
                    self.logger.debug(
                        f"Range query successful: {result_count} series, "
                        f"{total_points} points in {query_time:.2f}s"
                    )
                    
                    return PrometheusResult(
                        success=True,
                        data=result_data,
                        query_time=query_time,
                        result_count=total_points
                    )
                else:
                    error_msg = data.get('error', 'Unknown Prometheus error')
                    self.logger.error(f"Prometheus range query failed: {error_msg}")
                    return PrometheusResult(success=False, error=error_msg)
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.logger.error(f"Prometheus range request failed: {error_msg}")
                return PrometheusResult(success=False, error=error_msg)
        
        except Exception as e:
            query_time = time.time() - start_exec_time
            error_msg = f"Range query execution failed: {e}"
            self.logger.error(error_msg)
            return PrometheusResult(success=False, error=error_msg, query_time=query_time)
    
    def get_traffic_metrics(self, partner: str, path: str, hours: int = 24) -> PrometheusResult:
        """
        Get traffic metrics for a specific partner and path
        
        Args:
            partner: Partner ID
            path: API path
            hours: Number of hours to look back
            
        Returns:
            PrometheusResult with traffic metrics
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # Construct PromQL query for traffic metrics
        query = f'''
        sum(increase(
            service_nginx_request_time_s_count{{
                path=~".*{path}.*",
                partner="{partner}"
            }}[1m]
        )) by (path, partner)
        '''
        
        return self.query_range(query, start_time, end_time, "1m")
    
    def get_cache_metrics(self, partner: str, path: str, hours: int = 24) -> PrometheusResult:
        """
        Get cache metrics for a specific partner and path
        
        Args:
            partner: Partner ID
            path: API path
            hours: Number of hours to look back
            
        Returns:
            PrometheusResult with cache metrics
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # Construct PromQL query for cache metrics
        query = f'''
        sum(increase(
            service_nginx_request_time_s_count{{
                path=~".*{path}.*",
                partner="{partner}",
                cache_status!=""
            }}[1m]
        )) by (path, partner, cache_status)
        '''
        
        return self.query_range(query, start_time, end_time, "1m")
    
    def test_connection(self) -> PrometheusResult:
        """
        Test connection to Prometheus server
        
        Returns:
            PrometheusResult indicating connection status
        """
        try:
            result = self.query('up', datetime.now())
            if result.success:
                self.logger.info("Prometheus connection test successful")
                return PrometheusResult(success=True, data={'status': 'connected'})
            else:
                self.logger.error(f"Prometheus connection test failed: {result.error}")
                return result
        
        except Exception as e:
            error_msg = f"Connection test failed: {e}"
            self.logger.error(error_msg)
            return PrometheusResult(success=False, error=error_msg)
    
    def get_server_info(self) -> PrometheusResult:
        """
        Get Prometheus server information
        
        Returns:
            PrometheusResult with server info
        """
        try:
            url = urljoin(self.base_url, '/api/v1/status/buildinfo')
            response = self._make_request('GET', url)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    build_info = data.get('data', {})
                    self.logger.info(f"Prometheus server info: {build_info.get('version', 'unknown')}")
                    return PrometheusResult(success=True, data=build_info)
                else:
                    error_msg = data.get('error', 'Failed to get server info')
                    return PrometheusResult(success=False, error=error_msg)
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                return PrometheusResult(success=False, error=error_msg)
        
        except Exception as e:
            error_msg = f"Failed to get server info: {e}"
            self.logger.error(error_msg)
            return PrometheusResult(success=False, error=error_msg)
    
    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Make HTTP request with retry logic
        
        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request arguments
            
        Returns:
            requests.Response object
        """
        kwargs.setdefault('timeout', self.timeout)
        
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(method, url, **kwargs)
                
                # Don't retry on client errors (4xx)
                if 400 <= response.status_code < 500:
                    return response
                
                # Return successful responses
                if response.status_code < 400:
                    return response
                
                # Retry on server errors (5xx) and other issues
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.warning(
                        f"Request failed (attempt {attempt + 1}/{self.max_retries + 1}), "
                        f"retrying in {wait_time}s: {response.status_code}"
                    )
                    time.sleep(wait_time)
                else:
                    return response
            
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    self.logger.warning(
                        f"Request exception (attempt {attempt + 1}/{self.max_retries + 1}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    raise
        
        # This should never be reached, but just in case
        raise Exception("Max retries exceeded")
    
    def close(self):
        """Close the HTTP session"""
        if hasattr(self, 'session'):
            self.session.close()
            self.logger.debug("Prometheus client session closed")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


class MockPrometheusClient:
    """
    Mock Prometheus client for testing and development
    """
    
    def __init__(self, base_url: str = "mock://prometheus", **kwargs):
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)
        self.logger.info("Mock Prometheus client initialized")
    
    def query(self, query: str, time_param: Optional[datetime] = None) -> PrometheusResult:
        """Mock instant query"""
        self.logger.debug(f"Mock query: {query}")
        
        # Return mock data
        mock_data = {
            'resultType': 'vector',
            'result': [
                {
                    'metric': {'__name__': 'up', 'instance': 'localhost:9090'},
                    'value': [time.time(), '1']
                }
            ]
        }
        
        return PrometheusResult(
            success=True,
            data=mock_data,
            query_time=0.1,
            result_count=1
        )
    
    def query_range(self, query: str, start_time: datetime, end_time: datetime, 
                   step: str = "1m") -> PrometheusResult:
        """Mock range query"""
        self.logger.debug(f"Mock range query: {query}")
        
        # Generate mock time series data
        import numpy as np
        
        duration = end_time - start_time
        points = int(duration.total_seconds() / 60)  # Assuming 1m step
        
        timestamps = []
        values = []
        
        base_value = 100
        for i in range(points):
            timestamp = start_time + timedelta(minutes=i)
            # Generate realistic traffic pattern with some randomness
            hour = timestamp.hour
            day_factor = 1.0 + 0.5 * np.sin(2 * np.pi * hour / 24)  # Daily pattern
            noise = np.random.normal(0, 0.1)  # Random noise
            value = max(0, base_value * day_factor * (1 + noise))
            
            timestamps.append(timestamp.timestamp())
            values.append([timestamp.timestamp(), str(value)])
        
        mock_data = {
            'resultType': 'matrix',
            'result': [
                {
                    'metric': {'path': '/api_v3/service/ENDPOINT_5', 'partner': 'CUSTOMER_ID_1'},
                    'values': values
                }
            ]
        }
        
        return PrometheusResult(
            success=True,
            data=mock_data,
            query_time=0.2,
            result_count=len(values)
        )
    
    def get_traffic_metrics(self, partner: str, path: str, hours: int = 24) -> PrometheusResult:
        """Mock traffic metrics"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        return self.query_range(f"mock_traffic_{partner}_{path}", start_time, end_time)
    
    def get_cache_metrics(self, partner: str, path: str, hours: int = 24) -> PrometheusResult:
        """Mock cache metrics"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # Mock cache hit/miss data
        mock_data = {
            'resultType': 'matrix',
            'result': [
                {
                    'metric': {'cache_status': 'HIT'},
                    'values': [[time.time(), '300']]
                },
                {
                    'metric': {'cache_status': 'MISS'},
                    'values': [[time.time(), '100']]
                }
            ]
        }
        
        return PrometheusResult(
            success=True,
            data=mock_data,
            query_time=0.1,
            result_count=2
        )
    
    def test_connection(self) -> PrometheusResult:
        """Mock connection test"""
        return PrometheusResult(success=True, data={'status': 'mock_connected'})
    
    def get_server_info(self) -> PrometheusResult:
        """Mock server info"""
        return PrometheusResult(
            success=True, 
            data={'version': 'mock-2.0.0', 'branch': 'mock', 'buildUser': 'mock'}
        )
    
    def close(self):
        """Mock close"""
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def create_prometheus_client(base_url: str, mock: bool = False, **kwargs) -> Union[PrometheusClient, MockPrometheusClient]:
    """
    Factory function to create Prometheus client
    
    Args:
        base_url: Prometheus server URL
        mock: Whether to create mock client
        **kwargs: Additional client arguments
        
    Returns:
        PrometheusClient or MockPrometheusClient instance
    """
    if mock or base_url.startswith('mock://'):
        return MockPrometheusClient(base_url, **kwargs)
    else:
        return PrometheusClient(base_url, **kwargs)


if __name__ == '__main__':
    # CLI for testing Prometheus connectivity
    import argparse
    
    parser = argparse.ArgumentParser(description='TrendMaster-AI Prometheus Client')
    parser.add_argument('--url', required=True, help='Prometheus server URL')
    parser.add_argument('--query', help='Test query to execute')
    parser.add_argument('--mock', action='store_true', help='Use mock client')
    parser.add_argument('--test-connection', action='store_true', help='Test connection only')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    try:
        client = create_prometheus_client(args.url, mock=args.mock)
        
        if args.test_connection:
            result = client.test_connection()
            if result.success:
                print("✅ Connection successful")
                
                # Get server info
                info_result = client.get_server_info()
                if info_result.success:
                    print(f"Server version: {info_result.data.get('version', 'unknown')}")
            else:
                print(f"❌ Connection failed: {result.error}")
        
        elif args.query:
            result = client.query(args.query)
            if result.success:
                print(f"✅ Query successful: {result.result_count} results in {result.query_time:.2f}s")
                print(json.dumps(result.data, indent=2))
            else:
                print(f"❌ Query failed: {result.error}")
        
        else:
            print("Please specify --test-connection or --query")
    
    except Exception as e:
        print(f"❌ Error: {e}")