# AllTrails Promotion Scraper

A Python script that scrapes the AllTrails Facebook page for discount promotions and sends email notifications when found. Deployed on Google Cloud Run with daily scheduling.

## Features

- 🤖 Automated Facebook scraping using Selenium
- 📧 Email notifications for promotions (50% off, etc.)
- 🔄 Daily execution via Google Cloud Scheduler
- ☁️ Serverless deployment on Google Cloud Run
- 🔍 Expands collapsed Facebook posts ("See more")

## Project Structure

```
.
├── facebook_scraper.py    # Main scraping logic
├── main.py               # Flask web server entry point
├── dockerfile           # Container configuration
├── requirements.txt     # Python dependencies
├── deploy.example.sh    # Example deployment script
├── deploy.sh           # Your actual deployment script (don't commit)
└── README.md           # This file
```

## Local Development

### Prerequisites

- Python 3.8+
- Google Chrome
- Gmail account with app password for email sending

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/alltrails-bot.git
cd alltrails-bot
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your email credentials:
```bash
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-gmail-app-password
```

### Running Locally

#### Option 1: Direct execution
```bash
python facebook_scraper.py
```

#### Option 2: Web server (for testing Cloud Run behavior)
```bash
python main.py
# Then visit http://localhost:8080
```

## Deployment

### Quick Deploy

1. Copy the example deployment script:
```bash
cp deploy.example.sh deploy.sh
```

2. Edit `deploy.sh` with your configuration:
```bash
# Update these values
PROJECT_ID="your-gcp-project-id"
REGION="us-central1"
SERVICE_NAME="alltrails-scraper"
```

3. Run the deployment:
```bash
chmod +x deploy.sh
./deploy.sh
```

4. Set email environment variables:
```bash
gcloud run services update alltrails-scraper \
  --region=us-central1 \
  --set-env-vars EMAIL_USERNAME=your-email@gmail.com,EMAIL_PASSWORD="your-app-password"
```

### Manual Deployment

If you prefer manual deployment:

1. Build and push the container:
```bash
gcloud builds submit --tag us-central1-docker.pkg.dev/PROJECT-ID/alltrails-scraper/app
```

2. Deploy to Cloud Run:
```bash
gcloud run deploy alltrails-scraper \
  --image us-central1-docker.pkg.dev/PROJECT-ID/alltrails-scraper/app \
  --platform managed \
  --region us-central1 \
  --memory=1Gi \
  --no-allow-unauthenticated
```

3. Set up the scheduler:
```bash
# Create service account
gcloud iam service-accounts create scheduler \
  --display-name="Cloud Scheduler Service Account" \
  --project=PROJECT-ID

# Grant permissions
gcloud run services add-iam-policy-binding alltrails-scraper \
  --region=us-central1 \
  --member="serviceAccount:scheduler@PROJECT-ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# Create scheduler job
gcloud scheduler jobs create http run-alltrails-check \
  --location=us-central1 \
  --schedule="0 12 * * *" \
  --time-zone="America/New_York" \
  --uri="https://alltrails-scraper-PROJECT-ID.us-central1.run.app" \
  --http-method=GET \
  --oidc-service-account-email="scheduler@PROJECT-ID.iam.gserviceaccount.com"
```

## Configuration

### Email Setup

1. Enable 2-factor authentication on your Gmail account
2. Generate an app password: https://myaccount.google.com/apppasswords
3. Use the app password in the `EMAIL_PASSWORD` environment variable

### Scheduling

The scheduler runs daily at 12:00 PM Eastern Time by default. To change this:

```bash
# Update the schedule (cron format)
gcloud scheduler jobs update run-alltrails-check \
  --location=us-central1 \
  --schedule="0 9 * * *"  # 9 AM Eastern
```

### Memory Configuration

The scraper requires 1GiB of memory for Selenium/Chrome. To adjust:

```bash
gcloud run services update alltrails-scraper \
  --region=us-central1 \
  --memory=2Gi  # Increase to 2GiB if needed
```

## Monitoring

### Check Logs

```bash
# Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=alltrails-scraper" \
  --limit 20 \
  --project=PROJECT-ID

# Scheduler job logs
gcloud scheduler jobs describe run-alltrails-check \
  --location=us-central1
```

### Test Execution

Manually trigger a job:
```bash
gcloud scheduler jobs run run-alltrails-check --location=us-central1
```

## Troubleshooting

### Common Issues

1. **Memory errors**: Increase memory allocation to 2GiB
2. **Email not sending**: Verify Gmail app password and environment variables
3. **Facebook scraping fails**: Check if Facebook changed their page structure
4. **Scheduler not running**: Verify service account permissions

### Debug Mode

For debugging, you can temporarily disable headless mode in `facebook_scraper.py`:
```python
# chrome_options.add_argument("--headless")  # Comment out this line
```

## Security Notes

- Never commit `.env` files or deployment scripts with credentials
- Use Gmail app passwords instead of your main password
- Keep your Google Cloud project ID private
- The service runs with `--no-allow-unauthenticated` by default

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool scrapes Facebook content. Use responsibly and in accordance with Facebook's terms of service. The author is not responsible for any misuse of this software.
