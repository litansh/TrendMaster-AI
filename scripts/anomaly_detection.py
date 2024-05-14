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
import hashlib

with open("../config/config.yaml", "r") as yamlfile:
    cfg = yaml.safe_load(yamlfile)

PROMETHEUS_URL = cfg['PROMETHEUS_URL']
OPENAI_API_KEY = cfg['OPENAI_API_KEY']
GRAFANA_DASHBOARD_URL = cfg['GRAFANA_DASHBOARD_URL']
DAYS_TO_INSPECT = cfg.get('DAYS_TO_INSPECT', 7)
DEVIATION_THRESHOLD = cfg.get('DEVIATION_THRESHOLD', 0.2)
K8S_SPIKE_THRESHOLD = cfg.get('K8S_SPIKE_THRESHOLD', 0.5)
EXCESS_DEVIATION_THRESHOLD = cfg.get('EXCESS_DEVIATION_THRESHOLD', 0.1)
CSV_OUTPUT = cfg.get('CSV_OUTPUT', False)
IMG_OUTPUT = cfg.get('IMG_OUTPUT', False)
GPT_ON = cfg.get('GPT_ON', False)
DOCKER = cfg.get('DOCKER', False)

current_date = datetime.now()
date_str = current_date.strftime('%Y-%m-%d')
base_directory_name = f"outputs/{date_str}"


def sanitize_filename(s):
    """Sanitize a string to create a safe filename by hashing it."""
    s = str(s)
    hash_suffix = hashlib.md5(s.encode('utf-8')).hexdigest()[:8]
    s = s.replace('/', '_').replace('\\', '_').replace(':', '_').replace('\n', '_').replace(' ', '_')
    return s[:50] + '_' + hash_suffix


def setup_directories(metric_name):
    csv_dir = f"{base_directory_name}/csv_outputs/{sanitize_filename(metric_name)}"
    img_dir = f"{base_directory_name}/img_outputs/{sanitize_filename(metric_name)}"
    os.makedirs(csv_dir, exist_ok=True)
    os.makedirs(img_dir, exist_ok=True)
    return csv_dir, img_dir

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
        dataframes = []
        for result in results:
            df = pd.DataFrame(result['values'], columns=['ds', 'y'])
            df['ds'] = pd.to_datetime(df['ds'], unit='s')
            df['y'] = pd.to_numeric(df['y'], errors='coerce')
            if 'metric' in result:
                for key in ['partner', 'path', 'pod']:
                    df[key] = result['metric'].get(key, 'unknown')
            dataframes.append(df)
        return dataframes
    else:
        logging.error("Failed to fetch metrics: %s %s", response.status_code, response.text)
        return []


def detect_anomalies_with_prophet(dfs, sensitivity, deviation_threshold, excess_deviation_threshold, is_k8s=False):
    anomalies_list = []
    for df in dfs:
        df = df[df['y'] >= 0]
        if len(df) < 2:
            logging.info("Insufficient data to fit model.")
            continue
        m = Prophet(changepoint_prior_scale=sensitivity, yearly_seasonality=False, weekly_seasonality=True, daily_seasonality=is_k8s)
        m.fit(df[['ds', 'y']])
        future = m.make_future_dataframe(periods=24, freq='h')
        forecast = m.predict(future)
        forecast['fact'] = df['y'].reset_index(drop=True)

        if 'partner' not in df.columns and not is_k8s:
            df['partner'] = 'unknown'

        forecast = forecast.join(df[['partner', 'path']] if 'partner' in df.columns else df[['path']], how='left')

        if 'partner' in df.columns:
            grouped = forecast.groupby(['partner', 'path'])
        else:
            grouped = forecast.groupby(['path'])

        for name, group in grouped:
            group['lower_bound'] = group['yhat'] - (group['yhat'] * deviation_threshold)
            group['upper_bound'] = group['yhat'] + (group['yhat'] * deviation_threshold)
            group['excessive_deviation'] = group['fact'] > (group['upper_bound'] + (group['upper_bound'] * excess_deviation_threshold))
            if is_k8s:
                group['spike_deviation'] = group['fact'] > (group['yhat'] + (group['yhat'] * K8S_SPIKE_THRESHOLD))
                group['anomaly'] = (group['spike_deviation'] | group['excessive_deviation'])
            else:
                group['anomaly'] = (group['fact'] < group['lower_bound']) | (group['fact'] > group['upper_bound'])

            anomalies = group[group['anomaly']]
            if not anomalies.empty:
                anomalies_list.append((anomalies, name))

    return anomalies_list


def visualize_trends(anomalies_list, img_directory_name):
    for anomaly_info in anomalies_list:
        if isinstance(anomaly_info, tuple) and isinstance(anomaly_info[0], pd.DataFrame):
            anomalies, group_keys = anomaly_info
            plt.figure(figsize=(10, 6))

            if isinstance(group_keys, tuple):
                partner, path = group_keys
                sanitized_partner = sanitize_filename(partner)
                sanitized_path = sanitize_filename(path)
                title = f"Trend and Anomalies for {sanitized_partner} Path: {sanitized_path}"
                filename = f"{img_directory_name}/trend_{sanitized_partner}_{sanitized_path}.png"
            else:
                path = group_keys
                sanitized_path = sanitize_filename(path)
                title = f"Trend and Anomalies for Path: {sanitized_path}"
                filename = f"{img_directory_name}/trend_{sanitized_path}.png"

            plt.title(title)

            conditions = anomalies['excessive_deviation'].apply(lambda x: 'Excessive' if x else 'Normal')
            palette = {cond: ('red' if cond == 'Excessive' else 'grey') for cond in conditions.unique()}

            sns.lineplot(x=anomalies['ds'], y=anomalies['yhat'], label='Trend', color='blue')
            plt.fill_between(anomalies['ds'], anomalies['lower_bound'], anomalies['upper_bound'], color='green', alpha=0.3, label='Expected Range')
            sns.scatterplot(x=anomalies['ds'], y=anomalies['fact'], hue=conditions, palette=palette, legend='full', marker='o')

            plt.xlabel('Date')
            plt.ylabel('Metric Value')
            plt.legend(title='Point Type')

            plt.savefig(filename)
            plt.close()
        else:
            logging.error("Expected a tuple with a DataFrame, but got a different type. Check data handling.")


def main():
    logging.basicConfig(level=logging.INFO)
    queries = {
        'Nginx Requests Per Minute - 2xx/3xx': 'sum by (path, partner) (increase(service_nginx_request_time_s_count{path!="", partner!=""}[1m]))',
        'Kubernetes Running Pods': 'sum by (phase, kubernetes_node, pod) (increase(kube_pod_status_phase{phase="Running", kubernetes_node!="", pod=~"kphoenix.*"}[1m]))'
    }
    for metric_name, query in queries.items():
        csv_dir, img_dir = setup_directories(metric_name)
        dfs = fetch_prometheus_metrics(query, DAYS_TO_INSPECT)
        if not dfs:
            logging.info("No data frames returned for query: %s", metric_name)
            continue
        is_k8s = "Kubernetes" in metric_name
        anomalies_list = detect_anomalies_with_prophet(dfs, 0.1, DEVIATION_THRESHOLD, EXCESS_DEVIATION_THRESHOLD, is_k8s=is_k8s)
        if anomalies_list:
            visualize_trends(anomalies_list, img_dir)
            if CSV_OUTPUT:
                for anomalies, _, _ in anomalies_list:
                    filename = f"{csv_dir}/anomalies_{sanitize_filename(metric_name)}.csv"
                    anomalies.to_csv(filename, index=False)
        else:
            logging.info("No anomalies detected for %s", metric_name)


if __name__ == "__main__":
    main()