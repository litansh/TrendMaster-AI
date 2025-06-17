#!/usr/bin/env python3
"""
Script to systematically replace all sensitive information with variables
This script will:
1. Replace all customer IDs (313, 9020, 439, etc.) with variables
2. Replace all API endpoints with variables  
3. Replace all company references with variables
4. Update all documentation and README files
"""

import os
import re
import sys
from pathlib import Path

# Sensitive data patterns to replace
REPLACEMENTS = {
    # Customer IDs
    r'\b313\b': 'CUSTOMER_ID_1',
    r'\b9020\b': 'CUSTOMER_ID_2', 
    r'\b439\b': 'CUSTOMER_ID_3',
    r'\b3079\b': 'CUSTOMER_ID_4',
    r'partner_313': 'PARTNER_ID_1',
    r'partner_439': 'PARTNER_ID_2',
    r'partner_9020': 'PARTNER_ID_3',
    r'partner_alpha': 'PARTNER_ALPHA',
    r'partner_beta': 'PARTNER_BETA',
    
    # API Endpoints
    r'/api/v3/service/configurations/action/servebydevice': '/api/v3/service/ENDPOINT_1',
    r'/api/v3/service/asset/action/list': '/api/v3/service/ENDPOINT_2',
    r'/api/v3/service/ottuser/action/login': '/api/v3/service/ENDPOINT_3',
    r'/api/v3/service/session/action/get': '/api/v3/service/ENDPOINT_4',
    r'/api/v3/service/multirequest': '/api/v3/service/ENDPOINT_5',
    r'/api/v3/service/assethistory/action/list': '/api/v3/service/ENDPOINT_6',
    r'/api_v3/service/multirequest': '/api_v3/service/ENDPOINT_5',
    r'/api_v3/service/test': '/api_v3/service/TEST_ENDPOINT',
    r'/api_v3/service/asset/action/list': '/api_v3/service/ENDPOINT_2',
    r'/api_v3/service/ottuser/action/get': '/api_v3/service/ENDPOINT_7',
    r'/api_v3/service/asset/action/get': '/api_v3/service/ENDPOINT_8',
    r'/api_v3/service/new/action/create': '/api_v3/service/ENDPOINT_9',
    
    # Company references
    r'kaltura\.com': 'YOUR_COMPANY.com',
    r'Kaltura': 'YOUR_COMPANY',
    r'kaltura': 'your_company',
    r'trickster\.orp2\.ott\.kaltura\.com': 'trickster.staging.YOUR_DOMAIN.com',
    r'trickster\.prd1\.ott\.kaltura\.com': 'trickster.production.YOUR_DOMAIN.com',
    
    # ECR Registry
    r'066597193667\.dkr\.ecr\.us-east-1\.amazonaws\.com': 'YOUR_ECR_REGISTRY.dkr.ecr.YOUR_REGION.amazonaws.com',
    
    # Slack channels
    r'#kprod-ops': '#alerts',
    r'#alerts-production': '#alerts',
    r'#platform-team': '#platform-team',
}

# Files to exclude from processing
EXCLUDE_FILES = {
    '.git',
    '__pycache__',
    '.pytest_cache',
    'node_modules',
    '.venv',
    'venv',
    'logs',
    'output',
    'artifacts',
    '.local.config.yaml',
    '.test.config.yaml',
    '.sensitive.config.yaml',
    'variabilize_sensitive_data.py'  # Don't modify this script itself
}

# File extensions to process
INCLUDE_EXTENSIONS = {
    '.py', '.yaml', '.yml', '.md', '.txt', '.json', '.sh', '.cfg', '.ini'
}

def should_process_file(file_path):
    """Check if file should be processed"""
    # Skip if in exclude list
    for exclude in EXCLUDE_FILES:
        if exclude in str(file_path):
            return False
    
    # Only process certain extensions
    if file_path.suffix not in INCLUDE_EXTENSIONS:
        return False
        
    # Skip binary files
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            f.read(100)  # Try to read first 100 chars
        return True
    except (UnicodeDecodeError, PermissionError):
        return False

def process_file(file_path):
    """Process a single file and replace sensitive data"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = 0
        
        # Apply all replacements
        for pattern, replacement in REPLACEMENTS.items():
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                changes_made += content.count(re.search(pattern, content).group() if re.search(pattern, content) else '')
                content = new_content
        
        # Write back if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return changes_made
        
        return 0
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return 0

def main():
    """Main function to process all files"""
    base_dir = Path(__file__).parent.parent
    total_files = 0
    total_changes = 0
    
    print("🔒 Starting sensitive data variabilization...")
    print(f"📁 Processing directory: {base_dir}")
    
    # Walk through all files
    for file_path in base_dir.rglob('*'):
        if file_path.is_file() and should_process_file(file_path):
            changes = process_file(file_path)
            if changes > 0:
                total_files += 1
                total_changes += changes
                print(f"✅ {file_path.relative_to(base_dir)}: {changes} changes")
    
    print(f"\n🎉 Completed!")
    print(f"📊 Files modified: {total_files}")
    print(f"🔄 Total replacements: {total_changes}")
    
    # Create summary of what was replaced
    print(f"\n📋 Replacement Summary:")
    for pattern, replacement in REPLACEMENTS.items():
        print(f"   {pattern} → {replacement}")
    
    print(f"\n⚠️  Next Steps:")
    print(f"   1. Review changes with: git diff")
    print(f"   2. Update .local.config.yaml with actual values")
    print(f"   3. Test the system to ensure everything works")
    print(f"   4. Update documentation if needed")

if __name__ == "__main__":
    main()