#!/bin/bash

# Docker Build and Push Script for TrendMaster-AI
# Integrates with YOUR_COMPANY's ECR infrastructure

set -e

# Parse arguments
DRY_RUN=false
VERSION="latest"

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            VERSION="$1"
            shift
            ;;
    esac
done

# Configuration
REGION="us-east-1"
ECR_REGISTRY="YOUR_ECR_REGISTRY.dkr.ecr.YOUR_REGION.amazonaws.com"
IMAGE_NAME="trendmaster-ai"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Building and pushing TrendMaster-AI Docker image${NC}"
echo -e "${YELLOW}Registry: ${ECR_REGISTRY}${NC}"
echo -e "${YELLOW}Image: ${IMAGE_NAME}:${VERSION}${NC}"
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}🔍 DRY RUN MODE - No actual build/push will occur${NC}"
fi

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Navigate to the project directory
cd "$(dirname "$0")/../.."

if [ "$DRY_RUN" = true ]; then
    echo -e "${GREEN}📦 [DRY RUN] Would build Docker image: ${IMAGE_NAME}:${VERSION}${NC}"
    echo -e "${GREEN}🔐 [DRY RUN] Would login to ECR: ${ECR_REGISTRY}${NC}"
    echo -e "${GREEN}🔍 [DRY RUN] Would check/create ECR repository: ${IMAGE_NAME}${NC}"
    echo -e "${GREEN}⬆️  [DRY RUN] Would push image: ${ECR_REGISTRY}/${IMAGE_NAME}:${VERSION}${NC}"
    
    if [ "${VERSION}" != "latest" ]; then
        echo -e "${GREEN}⬆️  [DRY RUN] Would also push as latest: ${ECR_REGISTRY}/${IMAGE_NAME}:latest${NC}"
    fi
    
    echo -e "${GREEN}🎉 [DRY RUN] Build and push simulation completed!${NC}"
else
    echo -e "${GREEN}📦 Building Docker image...${NC}"
    docker build -t ${IMAGE_NAME}:${VERSION} .

    # Tag for ECR
    FULL_IMAGE_NAME="${ECR_REGISTRY}/${IMAGE_NAME}:${VERSION}"
    docker tag ${IMAGE_NAME}:${VERSION} ${FULL_IMAGE_NAME}

    echo -e "${GREEN}🔐 Logging into ECR...${NC}"
    aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}

    # Check if repository exists, create if not
    echo -e "${GREEN}🔍 Checking ECR repository...${NC}"
    if ! aws ecr describe-repositories --repository-names ${IMAGE_NAME} --region ${REGION} &> /dev/null; then
        echo -e "${YELLOW}📝 Creating ECR repository: ${IMAGE_NAME}${NC}"
        aws ecr create-repository --repository-name ${IMAGE_NAME} --region ${REGION}
    fi

    echo -e "${GREEN}⬆️  Pushing image to ECR...${NC}"
    docker push ${FULL_IMAGE_NAME}

    echo -e "${GREEN}✅ Successfully pushed ${FULL_IMAGE_NAME}${NC}"

    # Also tag as latest if version is not latest
    if [ "${VERSION}" != "latest" ]; then
        LATEST_IMAGE_NAME="${ECR_REGISTRY}/${IMAGE_NAME}:latest"
        docker tag ${IMAGE_NAME}:${VERSION} ${LATEST_IMAGE_NAME}
        docker push ${LATEST_IMAGE_NAME}
        echo -e "${GREEN}✅ Also pushed as latest: ${LATEST_IMAGE_NAME}${NC}"
    fi

    echo -e "${GREEN}🎉 Build and push completed successfully!${NC}"
fi

echo -e "${YELLOW}📋 Update your Helm values files with:${NC}"
echo -e "   image:"
echo -e "     repository: ${ECR_REGISTRY}/${IMAGE_NAME}"
echo -e "     tag: ${VERSION}"