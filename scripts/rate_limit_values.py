import requests
import pandas as pd
from datetime import datetime, timedelta
import logging
import yaml

with open("../config/rate_limit_values_config.yaml", "r") as yamlfile:
    cfg = yaml.safe_load(yamlfile)

PROMETHEUS_URL = cfg['PROMETHEUS_URL']
QUERY = 'sum by (path, partner) (increase(service_nginx_request_time_s_count{path!="", partner!=""}[1m]))'
DAYS_TO_INSPECT = cfg.get('DAYS_TO_INSPECT', 7)
LOG_LEVEL = cfg.get('LOG_LEVEL', 'INFO').upper()

logging.basicConfig(level=LOG_LEVEL)

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
        response = requests.get(f'{PROMETHEUS_URL}/api/v1/query_range', params=params)
        response.raise_for_status()
        results = response.json().get('data', {}).get('result', [])
        return results
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch metrics due to: {e}")
        return []

def process_metrics(results):
    data = []
    for result in results:
        try:
            df = pd.DataFrame(result['values'], columns=['timestamp', 'value'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df['value'] = pd.to_numeric(df['value'])
            df['path'] = result['metric']['path']
            df['partner'] = result['metric']['partner']
            data.append(df)
        except Exception as e:
            logging.error(f"Error processing metrics: {e}")
    return pd.concat(data, ignore_index=True) if data else pd.DataFrame()

def calculate_statistics(df):
    grouped = df.groupby(['partner', 'path'])
    stats = grouped['value'].agg(['min', 'max', 'mean']).reset_index()
    stats['rate_limit'] = stats.apply(lambda row: row['max'] * 1.5 if row['max'] > 3 * row['mean'] else row['max'] * 2.5, axis=1)
    return stats

def main():
    results = fetch_prometheus_metrics(QUERY, DAYS_TO_INSPECT)
    if results:
        metrics_df = process_metrics(results)
        if not metrics_df.empty:
            stats = calculate_statistics(metrics_df)
            for _, row in stats.iterrows():
                logging.info(f"Partner: {row['partner']}, API Path: {row['path']}, "
                             f"Min: {row['min']:.2f}, Max: {row['max']:.2f}, "
                             f"Average: {row['mean']:.2f}, Rate Limit: {row['rate_limit']:.2f}")
        else:
            logging.info("No data available to process.")
    else:
        logging.info("No results returned from Prometheus query.")

if __name__ == "__main__":
    main()



# Get config from the configmap
# Add to it API that are being ratelimited and the ones that are not
# Deviation between current state and the recommendedion
