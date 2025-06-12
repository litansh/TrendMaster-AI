#!/bin/bash

set -e

K8S_NAMESPACE="istio-system"

echo "🔧 Fixing Kubernetes namespace issue..."

# Clean up existing resources that might be in a bad state
echo "Cleaning up existing resources..."
kubectl delete clusterrole adaptive-rate-limiter --ignore-not-found
kubectl delete clusterrolebinding adaptive-rate-limiter --ignore-not-found
kubectl delete serviceaccount adaptive-rate-limiter -n "$K8S_NAMESPACE" --ignore-not-found 2>/dev/null || true

# Create the namespace if it doesn't exist
echo "Creating namespace '$K8S_NAMESPACE'..."
kubectl create namespace "$K8S_NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# Apply RBAC resources
echo "Applying RBAC configuration..."
kubectl apply -f infra/rbac.yaml

# Apply ConfigMap
echo "Applying ConfigMap..."
kubectl apply -f config/istio_ratelimit_configmap.yaml

echo "✅ Namespace and prerequisites fixed successfully!"
echo "You can now run: ./ci-cd.sh"