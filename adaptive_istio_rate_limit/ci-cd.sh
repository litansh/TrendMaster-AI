#!/bin/bash

set -e 
set -o pipefail

# Constants
DOCKER_IMAGE="litanshamir/ratelimit_values:latest"
K8S_NAMESPACE="istio-system"
K8S_JOB_FILE="infra/istio_ratelimit_values_job.yaml"
POD_NAME_PREFIX="rate-limit"

log_info() {
  echo "[INFO] $1"
}

log_error() {
  echo "[ERROR] $1" >&2
}

retry() {
  local n=1
  local max=5
  local delay=3
  while true; do
    "$@" && break || {
      if [[ $n -lt $max ]]; then
        ((n++))
        log_info "Retrying in $delay seconds... (Attempt $n/$max)"
        sleep $delay
      else
        log_error "The command failed after $n attempts."
        return 1
      fi
    }
  done
}

log_info "Building Docker image: $DOCKER_IMAGE"
retry docker build -t "$DOCKER_IMAGE" -f Dockerfile .

log_info "Pushing Docker image: $DOCKER_IMAGE"
retry docker push "$DOCKER_IMAGE"

log_info "Deleting existing Kubernetes job"
kubectl delete -f "$K8S_JOB_FILE" --ignore-not-found

log_info "Applying the Kubernetes job"
retry kubectl apply -f "$K8S_JOB_FILE"

log_info "Waiting for the pod to start..."
sleep 5

pod=$(kubectl get pods -n "$K8S_NAMESPACE" | grep -e "$POD_NAME_PREFIX" | awk '{print $1}' | head -n 1)
if [[ -z "$pod" ]]; then
  log_error "No pod found matching the prefix: $POD_NAME_PREFIX"
  exit 1
fi

log_info "Checking pod status..."
if ! kubectl wait --for=condition=Ready pod/"$pod" -n "$K8S_NAMESPACE" --timeout=20s; then
  log_error "Pod failed to reach the 'Ready' state. Fetching logs for debugging..."
  kubectl logs -n "$K8S_NAMESPACE" "$pod"
  exit 1
fi

log_info "Tailing logs for pod: $pod"
kubectl logs -f "$pod" -n "$K8S_NAMESPACE"
