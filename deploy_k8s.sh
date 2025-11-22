#!/bin/bash
set -e # Stop the script immediately if any command fails

# --- 1. CONFIGURATION ---
AWS_REGION="eu-central-1" # Change if using a different region
GIT_SHA=$(git rev-parse --short HEAD) # Uses the latest commit hash as the version tag

# Dynamically fetch your AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URL="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

echo "==============================================="
echo "🚀 STARTING DEPLOYMENT"
echo "   Version: $GIT_SHA"
echo "   Account: $ACCOUNT_ID"
echo "==============================================="

# --- 2. LOGIN TO ECR ---
echo "🔑 Logging into AWS ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URL

# --- 3. BACKEND PHASE ---
echo ""
echo "📦 [1/4] Building & Pushing Backend Image..."
cd app/backend
docker build -t innovatech-backend:$GIT_SHA .
docker tag innovatech-backend:$GIT_SHA $ECR_URL/innovatech-backend:$GIT_SHA
docker push $ECR_URL/innovatech-backend:$GIT_SHA
cd ../..

echo ""
echo "🏗️ [2/4] Deploying Backend Infrastructure..."
cd infrastructure/apps
terraform init
# We target specific backend resources first to generate the LoadBalancer URL
terraform apply \
  -target=kubernetes_service.backend_svc \
  -target=kubernetes_deployment.backend \
  -target=kubernetes_config_map.backend_config \
  -target=kubernetes_secret.backend_secrets \
  -var="image_tag=$GIT_SHA" \
  -auto-approve

echo ""
echo "📦 [3/4] Building & Pushing Frontend Image..."

cd ../../app/frontend
# Build Arg is CRITICAL here: passing the backend URL to Vite
docker build -t innovatech-frontend:$GIT_SHA .
docker tag innovatech-frontend:$GIT_SHA $ECR_URL/innovatech-frontend:$GIT_SHA
docker push $ECR_URL/innovatech-frontend:$GIT_SHA
cd ../..

echo ""
echo "🏗️ [4/4] Deploying Frontend Infrastructure..."
cd infrastructure/apps
# Now we apply everything (including the Frontend)
terraform apply -var="image_tag=$GIT_SHA" -auto-approve

# --- 5. SUMMARY ---
FRONTEND_URL=$(terraform output -raw frontend_url)
echo ""
echo "==============================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "   Frontend Access: http://$FRONTEND_URL"
echo "==============================================="