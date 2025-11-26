#!/bin/bash

# AllTrails Scraper Deployment Script - EXAMPLE
# Copy this file to deploy.sh and configure with your values
# Do not use this file directly - it contains placeholder values

set -e  # Exit on any error

# Configuration - UPDATE THESE VALUES
PROJECT_ID="your-project-id"                    # Your Google Cloud project ID
REGION="your-region"                             # e.g., us-central1
SERVICE_NAME="your-service-name"                 # e.g., alltrails-scraper
REPO_NAME="your-repo-name"                       # e.g., alltrails-scraper
IMAGE_NAME="your-image-name"                     # e.g., app

echo "🚀 Starting deployment of AllTrails scraper..."
echo "⚠️  This is an example file - copy to deploy.sh and configure first!"

# Exit if using example values
if [[ "$PROJECT_ID" == "your-project-id" ]]; then
    echo "❌ Please copy this file to deploy.sh and update the configuration values"
    exit 1
fi

# Set project
gcloud config set project $PROJECT_ID

# Build and push container
echo "📦 Building and pushing container..."
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}

# Deploy to Cloud Run
echo "🌐 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME} \
  --platform managed \
  --region $REGION \
  --memory=1Gi \
  --no-allow-unauthenticated

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)')
echo "✅ Service deployed at: $SERVICE_URL"

# Create service account if it doesn't exist
echo "🔐 Setting up service account..."
if ! gcloud iam service-accounts describe scheduler@$PROJECT_ID.iam.gserviceaccount.com --project=$PROJECT_ID >/dev/null 2>&1; then
    gcloud iam service-accounts create scheduler \
      --display-name="Cloud Scheduler Service Account" \
      --project=$PROJECT_ID
fi

# Grant permissions
gcloud run services add-iam-policy-binding $SERVICE_NAME \
  --region=$REGION \
  --member="serviceAccount:scheduler@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# Create/update scheduler job
echo "⏰ Setting up Cloud Scheduler..."
gcloud scheduler jobs delete run-alltrails-check --location=$REGION 2>/dev/null || true
gcloud scheduler jobs create http run-alltrails-check \
  --location=$REGION \
  --schedule="0 12 * * *" \
  --time-zone="America/New_York" \
  --uri=$SERVICE_URL \
  --http-method=GET \
  --oidc-service-account-email="scheduler@$PROJECT_ID.iam.gserviceaccount.com"

echo "🎉 Deployment complete!"
echo "📧 Don't forget to set EMAIL_USERNAME and EMAIL_PASSWORD environment variables:"
echo "   gcloud run services update $SERVICE_NAME \\"
echo "     --region=$REGION \\"
echo "     --set-env-vars EMAIL_USERNAME=your-email@gmail.com,EMAIL_PASSWORD=your-app-password"
echo ""
echo "🔧 Test the deployment:"
echo "   gcloud scheduler jobs run run-alltrails-check --location=$REGION"
