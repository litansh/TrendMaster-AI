#!/bin/bash
# TrendMaster-AI No-Hang Execution Script
# Multiple options to prevent Prophet analysis from hanging

echo "🚀 TrendMaster-AI No-Hang Execution Options"
echo "=============================================="

# Option 1: Skip Prophet entirely (fastest, guaranteed no hang)
echo ""
echo "Option 1: Skip Prophet Analysis (Fastest - 0.24s)"
echo "Command: TRENDMASTER_SKIP_PROPHET=true python scripts/main.py"
echo "Use this when you want guaranteed fast execution with statistical analysis only"
echo ""

# Option 2: Use timeout protection (balanced approach)
echo "Option 2: Prophet with Timeout Protection (Balanced - ~0.35s)"
echo "Command: python scripts/main.py"
echo "Use this for normal operation with automatic timeout protection"
echo ""

# Option 3: CI mode (fast Prophet settings)
echo "Option 3: Fast Prophet Mode (CI settings)"
echo "Command: TRENDMASTER_CI_MODE=true python scripts/main.py"
echo "Use this for faster Prophet analysis with reduced accuracy"
echo ""

# Option 4: Combination for maximum safety
echo "Option 4: Maximum Safety (Skip Prophet + Timeout)"
echo "Command: TRENDMASTER_SKIP_PROPHET=true timeout 60 python scripts/main.py"
echo "Use this for absolute guarantee against hanging"
echo ""

echo "=============================================="
echo "Recommended for your case:"
echo "TRENDMASTER_SKIP_PROPHET=true python scripts/main.py"
echo ""

# Ask user which option they want to run
read -p "Which option would you like to run? (1-4 or 'q' to quit): " choice

case $choice in
    1)
        echo "Running Option 1: Skip Prophet Analysis..."
        TRENDMASTER_SKIP_PROPHET=true python scripts/main.py
        ;;
    2)
        echo "Running Option 2: Prophet with Timeout Protection..."
        python scripts/main.py
        ;;
    3)
        echo "Running Option 3: Fast Prophet Mode..."
        TRENDMASTER_CI_MODE=true python scripts/main.py
        ;;
    4)
        echo "Running Option 4: Maximum Safety..."
        TRENDMASTER_SKIP_PROPHET=true timeout 60 python scripts/main.py
        ;;
    q|Q)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid option. Running recommended Option 1..."
        TRENDMASTER_SKIP_PROPHET=true python scripts/main.py
        ;;
esac