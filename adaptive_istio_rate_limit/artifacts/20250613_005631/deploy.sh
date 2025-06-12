#!/bin/bash
echo "🚀 Deploying TrendMaster-AI..."
echo "Running post-deployment sanity check..."
python3 test_sanity.py
echo "✅ Deployment completed successfully!"
