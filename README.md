# Time Series DB Based Anomaly Detection using Prophet and LLM 

## Overview

This document is a comprehensive guide to implementing an advanced anomaly detection system designed for real-time monitoring of system metrics. Leveraging the capabilities of Prometheus for metric collection, Prophet for forecasting and anomaly detection, and Grafana for visualization, this system is further enhanced with AI-driven insights through ChatGPT integration. The goal is to provide a robust solution for proactively identifying and addressing system anomalies and improving system reliability and performance.

## System Architecture

The anomaly detection system integrates several key technologies:

- **Prometheus**: Collects and stores metrics as time series data, providing a reliable foundation for anomaly detection.
- **Prophet**: Utilized for its advanced forecasting capabilities, especially in handling seasonal data variations, to predict and detect anomalies.
- **Grafana**: Offers powerful visualization tools for the metrics collected by Prometheus, enabling easy identification of anomalies.
- **ChatGPT**: Enhances the analysis of detected anomalies by providing AI-driven insights, making the identification process more insightful and actionable.

### How-To Guide
WIP

## Running it locally

- Create a `config.yaml` file under the `config` directory
Fill it like so:
```
    PROMETHEUS_URL: '[Prometheus-End-Point]'
    OPENAI_API_KEY: '[CHAT-GPT-API-KEY]'
    GRAFANA_DASHBOARD_URL: '[Grafana-Dash]'
    DAYS_TO_INSPECT: [By-Default-7]
    DEVIATION_THRESHOLD: [By-Default-0.2]
    CSV_OUTPUT: [By-Default-False]
```

- Navigate to the `/scripts/` directory

- Run:
```
    python3 anomaly_detection.py
```

## What's it all about?

### System Setup and Configuration

Having Prometheus to ensure comprehensive metric collection across the system, And Grafana dashboards to visualize the metrics collected, facilitating easy monitoring and anomaly detection. A critical component of this phase was integrating Prophet and ChatGPT to process the data. This integration required establishing a server or cloud function that could access Prometheus data and interact with OpenAI's API, enabling the system to forecast anomalies and analyze them with AI insights.

### Adjusting Sensitivity

A vital aspect of the implementation was determining the optimal sensitivity levels for anomaly detection. Starting with Prophet's default settings, adjustments were made based on the specific characteristics of our data, such as volume and variability. The objective was to achieve a balance where the system could reliably detect anomalies without generating excessive false positives. This process involved extensive testing and validation using historical data, allowing for the refinement of sensitivity settings to improve detection accuracy.

### Deployment Environment

Choosing the right deployment environment was crucial, with options between on-premises and cloud-based solutions. Data security, scalability, and access to computational resources influenced this decision. Following the selection, the anomaly detection system was deployed, ensuring it had continuous access to Prometheus metrics and could communicate with Grafana and ChatGPT as needed.

### Output and Notification

The system was designed to output anomalies in a clear and actionable format, detailing the affected metric, the nature of the anomaly, and potential insights from ChatGPT. Integration with communication tools like Slack or Microsoft Teams was set up to facilitate timely responses, automating the notification process to alert relevant teams about detected anomalies.

### Towards Full Automation

The roadmap towards full automation included exploring tools and scripts capable of automatically responding to certain types of anomalies, such as resource scaling or service restarts. Additionally, the system was configured to potentially trigger other monitoring or diagnostic tools based on the anomaly detected, requiring clear rules and integrations for when and how these tools should be activated.

### Monitoring and Maintenance

Continuous monitoring of the anomaly detection system's performance and accuracy was instituted, including tracking false positives and negatives and response times. Regular updates and patches for all system components (Prometheus, Grafana, Prophet, and ChatGPT integration) were applied to ensure optimal performance and security.

## Conclusion

Implementing this anomaly detection system represents a significant advancement in our monitoring capabilities. By leveraging cutting-edge technologies and AI-driven insights, we have established a proactive approach to identifying and addressing system anomalies, thereby enhancing our operational reliability and performance.

