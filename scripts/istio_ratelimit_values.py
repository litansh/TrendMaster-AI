import requests
import pandas as pd
from datetime import datetime, timedelta
import logging
import yaml
import os
import math

print("Starting script...")

CONFIG_FILE_PATH = os.getenv('CONFIG_FILE_PATH', '/etc/config/config.yaml')
RATE_LIMIT_CONFIG_FILE_PATH = "/etc/config/example_istio_cm.yaml"
OUTPUT_CONFIG_FILE_PATH = "/etc/config/output_istio_cm.yaml"
DEVIATIONS_FILE_PATH = "/etc/config/deviations.yaml"

if os.path.exists(CONFIG_FILE_PATH):
    print(f"Found config file at {CONFIG_FILE_PATH}")
    with open(CONFIG_FILE_PATH, "r") as yamlfile:
        cfg = yaml.safe_load(yamlfile)
else:
    print(f"Configuration file not found at {CONFIG_FILE_PATH}")
    raise FileNotFoundError(f"Configuration file not found at {CONFIG_FILE_PATH}.")

if os.path.exists(RATE_LIMIT_CONFIG_FILE_PATH):
    print(f"Found rate limit config file at {RATE_LIMIT_CONFIG_FILE_PATH}")
    with open(RATE_LIMIT_CONFIG_FILE_PATH, "r") as yamlfile:
        configmap = yaml.safe_load(yamlfile)
        if 'data' in configmap and 'config.yaml' in configmap['data']:
            rate_limit_cfg = yaml.safe_load(configmap['data']['config.yaml'])
        else:
            raise KeyError(f"Key 'data' or 'config.yaml' not found in the loaded config map: {configmap}")
else:
    print(f"Rate limit configuration file not found at {RATE_LIMIT_CONFIG_FILE_PATH}")
    raise FileNotFoundError(f"Rate limit configuration file not found at {RATE_LIMIT_CONFIG_FILE_PATH}.")

PROMETHEUS_URL = cfg['PROMETHEUS_URL']
QUERY = 'sum by (path, partner) (increase(service_nginx_request_time_s_count{path!="", partner!=""}[1m]))'
DAYS_TO_INSPECT = cfg.get('DAYS_TO_INSPECT', 7)
LOG_LEVEL = cfg.get('LOG_LEVEL', 'DEBUG').upper()
SHOW_ONLY_CONFIGURED = cfg.get('SHOW_ONLY_CONFIGURED', False)

logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.info("Logging setup complete")

def fetch_prometheus_metrics(query, days):
    end = datetime.now()
    start = end - timedelta(days=days)
    params = {
        'query': query,
        'start': start.timestamp(),
        'end': end.timestamp(),
        'step': '1m'
    }
    try:
        logging.debug(f"Fetching Prometheus metrics with params: {params}")
        response = requests.get(f'{PROMETHEUS_URL}/api/v1/query_range', params=params)
        response.raise_for_status()
        results = response.json().get('data', {}).get('result', [])
        logging.debug(f"Metrics fetched: {results}")
        return results
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch metrics due to: {e}")
        return []

def process_metrics(results):
    logging.debug("Processing metrics...")
    data = []
    for result in results:
        try:
            df = pd.DataFrame(result['values'], columns=['timestamp', 'value'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df['value'] = pd.to_numeric(df['value'])
            df['path'] = result['metric']['path']
            df['partner'] = result['metric']['partner']
            data.append(df)
            logging.debug(f"Processed DataFrame: {df.head()}")
        except Exception as e:
            logging.error(f"Error processing metrics: {e}")
    if data:
        combined_df = pd.concat(data, ignore_index=True)
        logging.debug(f"Combined DataFrame: {combined_df.head()}")
        return combined_df
    else:
        logging.warning("No data processed from metrics results")
        return pd.DataFrame()

def calculate_statistics(df):
    logging.debug("Calculating statistics...")
    grouped = df.groupby(['partner', 'path'])
    stats = grouped['value'].agg(['min', 'max', 'mean']).reset_index()
    stats['max_count'] = grouped['value'].apply(lambda x: (x == x.max()).sum()).reset_index()['value']
    stats['total_count'] = grouped['value'].count().reset_index()['value']
    stats['max_dates'] = grouped['timestamp'].apply(lambda x: x[x == x.max()].tolist()).reset_index()['timestamp']
    logging.debug(f"Stats before rate limit calculation: {stats.head()}")
    stats['rate_limit'] = stats.apply(lambda row: calculate_rate_limit(row), axis=1)
    logging.debug(f"Calculated stats with rate limits: {stats.head()}")
    return stats

def calculate_rate_limit(row):
    if 3 < row['max'] < 10 * row['mean']:
        recommended_rate = math.ceil(row['max'] * 2)
    elif row['max'] > 10 * row['mean']:
        recommended_rate = math.ceil(row['max'] * 1.1)
    else:
        recommended_rate = math.ceil(row['max'] * 2.5)
    
    logging.debug(f"Calculated rate limit: {recommended_rate} for Partner: {row['partner']}, Path: {row['path']}, Max: {row['max']}, Mean: {row['mean']}")
    
    return recommended_rate

def load_rate_limit_config():
    rate_limits = {}
    if 'descriptors' not in rate_limit_cfg:
        logging.error("Key 'descriptors' not found in rate_limit_cfg")
        return rate_limits
    
    for descriptor in rate_limit_cfg['descriptors']:
        partner = descriptor['value']
        for path_descriptor in descriptor['descriptors']:
            path = path_descriptor['value']
            rate_limit = path_descriptor['rate_limit']['requests_per_unit']
            rate_limits[(str(partner), path)] = rate_limit
            logging.debug(f"Loaded config: Partner {partner}, Path {path}, Rate Limit {rate_limit}")
    return rate_limits

def compare_with_config(stats, rate_limits, filter_partners_paths):
    results = []
    for _, row in stats.iterrows():
        partner = str(row['partner'])
        path = row['path']
        if (partner, path) not in filter_partners_paths:
            continue
        recommended_rate_limit = row['rate_limit']
        current_rate_limit = rate_limits.get((partner, path))
        logging.debug(f"Processing comparison for Partner {partner}, Path {path}, Recommended Rate Limit {recommended_rate_limit}, Current Rate Limit {current_rate_limit}")
        if current_rate_limit is not None:
            deviation = ((recommended_rate_limit - current_rate_limit) / current_rate_limit) * 100
        else:
            deviation = None
        in_config = current_rate_limit is not None
        excessive_deviation = deviation is not None and (deviation > 10 or deviation < -10)
        max_count = row['max_count']
        total_count = row['total_count']
        anomaly_for_max = max_count < total_count / 2
        if anomaly_for_max:
            recommended_rate_limit = math.ceil(row['max'] * 1.2)
        recommended_rate_limit = round(recommended_rate_limit, -2)

        results.append({
            'partner': partner,
            'path': path,
            'current_rate_limit': current_rate_limit,
            'recommended_rate_limit': recommended_rate_limit,
            'deviation': deviation,
            'in_config': in_config,
            'excessive_deviation': excessive_deviation,
            'anomaly_for_max': anomaly_for_max,
            'max_dates': row['max_dates']
        })
        logging.debug(f"Comparison result: Partner {partner}, Path {path}, Current Rate Limit {current_rate_limit}, "
                      f"Recommended Rate Limit {recommended_rate_limit}, Deviation {deviation}%, In Config {in_config}, "
                      f"Excessive Deviation {excessive_deviation}, Anomaly for Max {anomaly_for_max} (Dates: {row['max_dates']})")
    return results

def update_config_map(comparison_results):
    deviations = []
    for descriptor in rate_limit_cfg['descriptors']:
        logging.info(f"rate_limit_cfgggggg: {rate_limit_cfg['descriptors']}")
        partner = descriptor['value']
        logging.info(f"partnerrrrrrrr: {partner}")
        for path_descriptor in descriptor['descriptors']:
            logging.info(f"path_descriptorrrrrrr: {path_descriptor}")
            path = path_descriptor['value']
            match = next((result for result in comparison_results if result['partner'] == partner and result['path'] == path), None)
            logging.info(f"matchhhhhhhh: {match}")
            if match:
                logging.debug(f"Updating rate limit for Partner {partner}, Path {path} from {path_descriptor['rate_limit']['requests_per_unit']} to {match['recommended_rate_limit']}")
                path_descriptor['rate_limit']['requests_per_unit'] = match['recommended_rate_limit']
                deviation_info = {
                    'partner': partner,
                    'path': path,
                    'current_rate_limit': match['current_rate_limit'],
                    'recommended_rate_limit': match['recommended_rate_limit'],
                    'deviation': match['deviation'],
                    'max_dates': [date.strftime('%Y-%m-%d %H:%M:%S') for date in match['max_dates']]
                }
                deviations.append(deviation_info)
                logging.debug(f"Appended deviation info: {deviation_info}")

    try:
        with open(OUTPUT_CONFIG_FILE_PATH, 'w') as outfile:
            yaml.dump({'domain': 'global-ratelimit', 'descriptors': rate_limit_cfg['descriptors']}, outfile, default_flow_style=False)
        logging.info(f"Updated ConfigMap written to {OUTPUT_CONFIG_FILE_PATH}")

        with open(DEVIATIONS_FILE_PATH, 'w') as devfile:
            yaml.dump({'deviations': deviations}, devfile, default_flow_style=False)
        logging.info(f"Deviations file written to {DEVIATIONS_FILE_PATH}")

    except Exception as e:
        logging.error(f"Failed to write updated ConfigMap or deviations file: {e}")

def main():
    logging.info("Starting to fetch metrics...")
    results = fetch_prometheus_metrics(QUERY, DAYS_TO_INSPECT)
    logging.debug(f"Fetched results: {results}")
    if results:
        metrics_df = process_metrics(results)
        if not metrics_df.empty:
            stats = calculate_statistics(metrics_df)
            rate_limits = load_rate_limit_config()
            
            # Define the partners and paths to filter based on the example config
            filter_partners_paths = set()
            for descriptor in rate_limit_cfg['descriptors']:
                partner = descriptor['value']
                for path_descriptor in descriptor['descriptors']:
                    path = path_descriptor['value']
                    filter_partners_paths.add((str(partner), path))
            
            comparison_results = compare_with_config(stats, rate_limits, filter_partners_paths)
            for result in comparison_results:
                logging.debug(f"Comparison result for Partner {result['partner']} and Path {result['path']}")
                if SHOW_ONLY_CONFIGURED and result['current_rate_limit'] is None:
                    continue
                deviation_display = f"{result['deviation']:.2f}%" if result['deviation'] is not None else "N/A"
                anomaly_dates_display = ', '.join([date.strftime('%Y-%m-%d %H:%M:%S') for date in result['max_dates']])
                logging.info(f"Partner: {result['partner']}, API Path: {result['path']}, "
                             f"Current Rate Limit: {result['current_rate_limit']}, "
                             f"Recommended Rate Limit: {result['recommended_rate_limit']}, "
                             f"Deviation: {deviation_display}, "
                             f"In Config: {result['in_config']}, "
                             f"Excessive Deviation: {result['excessive_deviation']}, "
                             f"Anomaly for Max: {result['anomaly_for_max']} (Dates: {anomaly_dates_display})")
            update_config_map(comparison_results)
        else:
            logging.info("No data available to process.")
    else:
        logging.info("No results returned from Prometheus query.")

if __name__ == "__main__":
    print("Executing main function...")
    main()
    print("Main function execution complete.")

def print_file_contents(file_path):
    try:
        with open(file_path, 'r') as file:
            content = file.read()
            logging.info(f"Contents of {file_path}:\n{content}")
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {e}")

file_path = "/etc/config/output_istio_cm.yaml"
print_file_contents(file_path)

file_path = "/etc/config/deviations.yaml"
print_file_contents(file_path)

#
# Check that the script is parsing as it should - see all partners and apis
# Get the configmap from the env
# Check the formula
# Add cache ratio to the formula
# Fix dates of max
# Think of exclusions api/partner
# Arrange the code
# Update the CM
# Deploy it as an operator
#