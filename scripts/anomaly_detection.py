import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from prophet import Prophet
from datetime import datetime, timedelta
import yaml
import os
import shutil
import openai
import logging

# Load configuration
with open("../config/config.yaml", "r") as yamlfile:
    cfg = yaml.safe_load(yamlfile)

# Configuration variables
PROMETHEUS_URL = cfg['PROMETHEUS_URL']
OPENAI_API_KEY = cfg['OPENAI_API_KEY']
GRAFANA_DASHBOARD_URL = cfg['GRAFANA_DASHBOARD_URL']
DAYS_TO_INSPECT = cfg.get('DAYS_TO_INSPECT', 7)
DEVIATION_THRESHOLD = cfg.get('DEVIATION_THRESHOLD', 0.2)
EXCESS_DEVIATION_THRESHOLD = cfg.get('EXCESS_DEVIATION_THRESHOLD', 0.1)
CSV_OUTPUT = cfg.get('CSV_OUTPUT', False)
IMG_OUTPUT = cfg.get('IMG_OUTPUT', False)
GPT_ON = cfg.get('GPT_ON', False)
DOCKER = cfg.get('DOCKER', False)

current_date = datetime.now()
date_str = current_date.strftime('%Y-%m-%d')
csv_directory_name = f"outputs/csv_outputs/{date_str}"
img_directory_name = f"outputs/img_outputs/{date_str}"

openai.api_key = OPENAI_API_KEY


def fetch_prometheus_metrics(query, days):
    """Fetch metrics from Prometheus for the given number of days."""
    end = datetime.now()
    start = end - timedelta(days=days)
    params = {
        'query': query,
        'start': start.timestamp(),
        'end': end.timestamp(),
        'step': '1h'
    }
    response = requests.get(f'{PROMETHEUS_URL}/api/v1/query_range', params=params)
    if response.status_code == 200:
        results = response.json().get('data', {}).get('result', [])
        logging.debug("Fetched data from Prometheus: %s", results)
        dataframes = []
        for result in results:
            if 'values' in result and 'metric' in result and 'path' in result['metric']:
                df = pd.DataFrame(result['values'], columns=['ds', 'y'])
                df['ds'] = pd.to_datetime(df['ds'], unit='s')
                df['y'] = pd.to_numeric(df['y'], errors='coerce')
                df['partner'] = result['metric'].get('partner', 'unknown')
                df['path'] = result['metric']['path']  # Extracting path
                dataframes.append(df)
                logging.debug("DataFrame created: %s", df.head())
            else:
                logging.warning("Missing 'values' or 'path' in result.")
        return dataframes
    else:
        logging.error("Failed to fetch metrics: %s %s", response.status_code, response.text)
        return []


def detect_anomalies_with_prophet(dfs, sensitivity, deviation_threshold, excess_deviation_threshold):
    """Detect anomalies using Prophet with specified sensitivity and deviation thresholds."""
    anomalies_list = []
    for df in dfs:
        df = df[df['y'] >= 0]
        if len(df) < 2:
            logging.info("Insufficient data to fit model.")
            continue
        m = Prophet(changepoint_prior_scale=sensitivity)
        m.fit(df[['ds', 'y']])
        future = m.make_future_dataframe(periods=24, freq='h')
        forecast = m.predict(future)
        forecast['fact'] = df['y'].reset_index(drop=True)
        forecast['partner'] = df['partner'].iloc[0]
        forecast['lower_bound'] = forecast['yhat'] - (forecast['yhat'] * deviation_threshold)
        forecast['upper_bound'] = forecast['yhat'] + (forecast['yhat'] * deviation_threshold)
        forecast['excessive_deviation'] = forecast['fact'] > (forecast['upper_bound'] + (forecast['upper_bound'] * excess_deviation_threshold))
        forecast['anomaly'] = (forecast['fact'] < forecast['lower_bound']) | (forecast['fact'] > forecast['upper_bound'])
        anomalies = forecast[forecast['anomaly'] | forecast['excessive_deviation']]
        if not anomalies.empty:
            anomalies_list.append(anomalies)
            logging.debug("Anomalies detected: %s", anomalies)
    return anomalies_list


def visualize_trends(anomalies_list, img_directory_name):
    """Visualize trends and anomalies and save the plots to the specified image directory."""
    for anomalies in anomalies_list:
        plt.figure(figsize=(10, 6))
        partner = anomalies['partner'].iloc[0]
        plt.title(f"Trend and Anomalies for Partner: {partner}")
        
        # Dynamic palette adjustment based on unique conditions
        conditions = anomalies['excessive_deviation'].apply(lambda x: 'Excessive' if x else 'Normal')
        unique_conditions = conditions.unique()
        palette = {cond: ('red' if cond == 'Excessive' else 'grey') for cond in unique_conditions}
        
        sns.lineplot(x=anomalies['ds'], y=anomalies['yhat'], label='Trend', color='blue')
        plt.fill_between(anomalies['ds'], anomalies['lower_bound'], anomalies['upper_bound'], color='green', alpha=0.3, label='Expected Range')
        sns.scatterplot(x=anomalies['ds'], y=anomalies['fact'], 
                        hue=conditions, 
                        palette=palette, 
                        legend='full', marker='o')
        plt.xlabel('Date')
        plt.ylabel('Request Count')
        plt.legend(title='Point Type')
        filename = f"{img_directory_name}/trend_{partner.replace(' ', '_')}.png"
        plt.savefig(filename)
        plt.close()


def main():
    logging.basicConfig(level=logging.INFO)
    
    if CSV_OUTPUT and not os.path.isdir(csv_directory_name):
        os.makedirs(csv_directory_name, exist_ok=True)
    
    if IMG_OUTPUT and not os.path.isdir(img_directory_name):
        os.makedirs(img_directory_name, exist_ok=True)

    queries = {
        'Nginx Requests Per Minute - 2xx/3xx': 'sum by (path, partner) (increase(service_nginx_request_time_s_count{path!="", partner!=""}[1m]))'
    }

    for metric_name, query in queries.items():
        logging.info("Processing query: %s", metric_name)
        dfs = fetch_prometheus_metrics(query, DAYS_TO_INSPECT)
        if not dfs:
            logging.info("No data frames returned for the query.")
            continue

        anomalies_list = detect_anomalies_with_prophet(dfs, 0.1, DEVIATION_THRESHOLD, EXCESS_DEVIATION_THRESHOLD)
        if anomalies_list:
            if IMG_OUTPUT:
                visualize_trends(anomalies_list, img_directory_name)  # Pass the image directory name for saving files
            if CSV_OUTPUT:
                for anomalies in anomalies_list:
                    filename = f"{csv_directory_name}/anomalies_{metric_name.replace('/', '_').replace(' ', '_')}_partner_{anomalies['partner'].iloc[0]}.csv"
                    anomalies.to_csv(filename, index=False)
        else:
            logging.info("No anomalies detected.")

if __name__ == "__main__":
    main()