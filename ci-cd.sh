#!/bin/bash

docker build -t litanshamir/ratelimit_values:latest -f Dockerfile-istio-ratelimit-values .
sleep 3
docker push litanshamir/ratelimit_values:latest
sleep 3
kubectl delete -f infra/istio_ratelimit_values_job.yaml 
sleep 3
kubectl apply -f infra/istio_ratelimit_values_job.yaml
