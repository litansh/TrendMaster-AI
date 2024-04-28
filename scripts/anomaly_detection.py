import requests
import openai
import pandas as pd
import holidays
from prophet import Prophet
from datetime import datetime, timedelta
import yaml
from datetime import datetime
import os
import shutil

current_date = datetime.now()
date_str = current_date.strftime('%Y-%m-%d')
directory_name = f"script_csv_outputs/{date_str}"

with open("../config/config.yaml", "r") as yamlfile:
    cfg = yaml.safe_load(yamlfile)

PROMETHEUS_URL = cfg['PROMETHEUS_URL']
OPENAI_API_KEY = cfg['OPENAI_API_KEY']
GRAFANA_DASHBOARD_URL = cfg['GRAFANA_DASHBOARD_URL']
DAYS_TO_INSPECT = cfg.get('DAYS_TO_INSPECT', 7)
DEVIATION_THRESHOLD = cfg.get('DEVIATION_THRESHOLD', 0.2)
EXCESS_DEVIATION_THRESHOLD = cfg.get('EXCESS_DEVIATION_THRESHOLD', 0.1)
CSV_OUTPUT = cfg.get('CSV_OUTPUT', False)
GPT_ON = cfg.get('GPT_ON', False)
DOCKER = cfg.get('DOCKER', False)

openai.api_key = OPENAI_API_KEY

def print_hyperlink_with_fallback(url, text):
    return f'\033]8;;{url}\033\\{text}\033]8;;\033\\ \n(Fallback URL: {url})'

def fetch_prometheus_metrics(query, days=7):
    end = datetime.now()
    start = end - timedelta(days=days)
    step = '1h'
    params = {
        'query': query,
        'start': start.timestamp(),
        'end': end.timestamp(),
        'step': step
    }
    try:
        response = requests.get(f'{PROMETHEUS_URL}/api/v1/query_range', params=params)
        response.raise_for_status()
        results = response.json()['data']['result']
        dfs = []
        for result in results:
            values = result['values']
            partner = result['metric'].get('partner', 'unknown')
            df = pd.DataFrame(values, columns=['ds', 'y'])
            df['ds'] = pd.to_datetime(df['ds'], unit='s')
            df['y'] = pd.to_numeric(df['y'])
            df['partner'] = partner
            dfs.append(df)
        return dfs
    except requests.exceptions.RequestException as e:
        print(f"Error fetching metrics from Prometheus: {e}")
        return []

def detect_anomalies_with_prophet(dfs, sensitivity=0.05, deviation_threshold=0.2, excess_deviation_threshold=0.1):
    anomalies_list = []
    for df in dfs:
        df = df[df['y'] >= 0]  # Ensure non-negative 'y' values
        m = Prophet(changepoint_prior_scale=sensitivity)
        if df.dropna().shape[0] < 2:
            print(f"{current_date} ERROR: Prophet fit equals {df.dropna().shape[0]}. Insufficient data to fit model.")
            continue  # Skip to the next DataFrame
        m.fit(df[['ds', 'y']])
        future = m.make_future_dataframe(periods=24, freq='h')
        forecast = m.predict(future)
        forecast['fact'] = df['y'].reset_index(drop=True)
        forecast['partner'] = df['partner'].iloc[0]
        
        forecast['lower_bound'] = forecast['yhat'] * (1 - deviation_threshold)
        forecast['upper_bound'] = forecast['yhat'] * (1 + deviation_threshold)
        forecast['excessive_deviation'] = forecast['fact'] > forecast['upper_bound'] * (1 + excess_deviation_threshold)
        forecast['anomaly'] = ((forecast['fact'] < forecast['lower_bound']) | (forecast['fact'] > forecast['upper_bound'])) & (forecast['fact'] >= 0)
        
        anomalies = forecast[forecast['anomaly'] | forecast['excessive_deviation']]
        if not anomalies.empty:
            anomalies_list.append(anomalies[['ds', 'fact', 'yhat', 'lower_bound', 'upper_bound', 'partner', 'excessive_deviation']])
    
    return anomalies_list


def generate_grafana_link(metric_name, partner):
    dashboard_ids = {
        'Nginx Requests Per Minute - 2xx/3xx': 'DkA689pGh/nginx?orgId=1&viewPanel=225&var-env=orp2&var-partner=All&var-api=All&var-tvpapi=All&var-clientTag=All'
    }
    dashboard_id = dashboard_ids.get(metric_name, 'default')
    grafana_link = print_hyperlink_with_fallback(f"{GRAFANA_DASHBOARD_URL}/{dashboard_id}&var-partner={partner}", f"Click here to visit '{metric_name}' for partner {partner}")
    return grafana_link

def analyze_metrics_with_chatgpt(anomalies, metric_name):
    try:
        prompt_messages = [
            {"role": "system", "content": f"Analyze the following anomalies for {metric_name} and provide insights."},
            {"role": "user", "content": anomalies.to_string()}
        ]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=prompt_messages
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error analyzing anomalies with ChatGPT for {metric_name}: {e}")
        return None

def main():
    metrics_queries = {
        'Nginx Requests Per Minute - 2xx/3xx': 'sum by (partner) (increase(service_nginx_request_time_s_count{path!="", partner!=""}[1m]))'
    }

    if CSV_OUTPUT:
        if os.path.isdir(date_str):
            shutil.rmtree(date_str)
        os.makedirs(directory_name, exist_ok=True)
        
    for metric_name, query in metrics_queries.items():
        print(f"Analyzing {metric_name}...")
        dfs = fetch_prometheus_metrics(query, days=DAYS_TO_INSPECT)
        
        if dfs:
            anomalies_list = detect_anomalies_with_prophet(dfs, sensitivity=0.1, deviation_threshold=DEVIATION_THRESHOLD, excess_deviation_threshold=EXCESS_DEVIATION_THRESHOLD)
            for anomalies in anomalies_list:
                if not anomalies.empty:
                    # Filter out rows where 'yhat', 'lower_bound', or 'upper_bound' are below 0
                    anomalies = anomalies[(anomalies['yhat'] >= 0) & (anomalies['lower_bound'] >= 0) & (anomalies['upper_bound'] >= 0)]
                    
                    partner = anomalies['partner'].iloc[0]
                    print(f"Anomalies detected by Prophet for {metric_name} (Partner: {partner}):", anomalies)
                    grafana_link = generate_grafana_link(metric_name, partner)
                    print(grafana_link)

                    if GPT_ON:
                        analysis_result = analyze_metrics_with_chatgpt(anomalies, metric_name)
                        if analysis_result:
                            print(f"Analysis result from ChatGPT for {metric_name} (Partner: {partner}):", analysis_result)
                        else:
                            print(f"Failed to analyze anomalies with ChatGPT for {metric_name} (Partner: {partner}).")
                    
                    safe_metric_name = metric_name.replace("/", "_").replace(" ", "_")

                    if DOCKER:
                        filename = f"/data/{date_str}/anomalies_{safe_metric_name}_partner_{partner}.csv"
                    else:
                        filename = f"script_csv_outputs/{date_str}/anomalies_{safe_metric_name}_partner_{partner}.csv"

                    if not anomalies.empty:
                        if CSV_OUTPUT:
                            anomalies.to_csv(filename, index=False)
                        print(f"Anomalies for {metric_name} (Partner: {partner})")
                    else:
                        print(f"No non-negative anomalies detected by Prophet for {metric_name} (Partner: {partner}).")
                else:
                    print(f"No anomalies detected by Prophet for {metric_name}.")
        else:
            print(f"Failed to fetch metrics or no data available for {metric_name}.")

if __name__ == "__main__":
    main()
