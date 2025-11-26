import os
import re
import smtplib
import time
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import schedule
from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta

# Facebook URL to scrape
FACEBOOK_URL = "https://www.facebook.com/alltrails"

def main():
    print("Starting Facebook scraper...")
    promotion_found, promotions, latest_post = scrape_facebook()
    
    if promotion_found:
        print("Promotions found! Sending email...")
        subject = "🎉 AllTrails Promotion Found!"
        body = "The following promotions were found:\n\n"
        for promo in promotions:
            body += f"Date: {promo['date']}\n"
            body += f"Match: {promo['match']}\n"
            body += f"Text: {promo['text']}\n\n"
        
        send_email(subject, body)
    else:
        print("No promotions found in the most recent posts.")

if __name__ == "__main__":
    main()

# Load environment variables from .env file
load_dotenv(override=True)

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = os.getenv("EMAIL_USERNAME") or os.getenv("EMAIL_SENDER")
SMTP_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Validate email configuration
if not SMTP_USERNAME or not SMTP_PASSWORD:
    print("Error: Email configuration is missing. Please check your .env file.")
    print(f"EMAIL_USERNAME: {'Set' if SMTP_USERNAME else 'Not set'}")
    print(f"EMAIL_PASSWORD: {'Set' if SMTP_PASSWORD else 'Not set'}")
    exit(1)

# Facebook page URL
FACEBOOK_URL = "https://www.facebook.com/AllTrails"

def setup_driver():
    """Set up and return a Chrome WebDriver."""
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Try to use system Chrome first, fallback to ChromeDriverManager
        try:
            driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            print("Using ChromeDriverManager as fallback...")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
        return driver
    except Exception as e:
        print(f"Error setting up Chrome WebDriver: {str(e)}")
        raise

def parse_facebook_time(time_str):
    """Parse Facebook's relative time strings into datetime objects."""
    if not time_str:
        return None
        
    now = datetime.now()
    time_str = time_str.lower()
    
    try:
        # Handle various time formats
        if 'hr' in time_str or 'hour' in time_str:
            hours = int(re.search(r'\d+', time_str).group())
            return now - timedelta(hours=hours)
        elif 'min' in time_str:
            minutes = int(re.search(r'\d+', time_str).group())
            return now - timedelta(minutes=minutes)
        elif 'yesterday' in time_str:
            return now - timedelta(days=1)
        elif 'day' in time_str:
            days = int(re.search(r'\d+', time_str).group())
            return now - timedelta(days=days)
        elif 'week' in time_str:
            weeks = int(re.search(r'\d+', time_str).group())
            return now - timedelta(weeks=weeks)
        elif 'month' in time_str:
            months = int(re.search(r'\d+', time_str).group())
            return now - relativedelta(months=months)
        elif 'year' in time_str:
            years = int(re.search(r'\d+', time_str).group())
            return now - relativedelta(years=years)
        else:
            # Try to parse as absolute date
            return parse_date(time_str, fuzzy=True)
    except Exception as e:
        print(f"Could not parse time: {time_str}, error: {str(e)}")
        return None

def get_latest_post(driver):
    """Get the most recent post's text and timestamp."""
    try:
        # Wait for the first post to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='article']"))
        )
        
        # Get the first post
        first_post = driver.find_element(By.CSS_SELECTOR, "div[role='article']")
        
        # Get post text
        post_text = first_post.text
        
        # Try to get the post time
        post_time = "Time not available"
        post_datetime = None
        try:
            time_element = first_post.find_element(By.CSS_SELECTOR, "a[href*='/posts/']")
            post_time = time_element.text
            post_datetime = parse_facebook_time(post_time)
        except Exception as e:
            print(f"Error getting post time: {str(e)}")
            
        return {
            'text': post_text[:500] + ('' if len(post_text) <= 500 else '...'),
            'time': post_time,
            'datetime': post_datetime,
            'full_text': post_text
        }
    except Exception as e:
        print(f"Error getting latest post: {str(e)}")
        return None

def scrape_facebook():
    """Scrape AllTrails Facebook page for discount promotions from the last 7 days."""
    driver = None
    try:
        print(f"[{datetime.now()}] Starting Facebook scrape...")
        driver = setup_driver()
        driver.get(FACEBOOK_URL)
        
        # Get the latest post first
        latest_post = get_latest_post(driver)
        
        # Wait for posts to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='article']"))
        )
        
        # Calculate the cutoff date (7 days ago)
        cutoff_date = datetime.now() - timedelta(days=7)
        print(f"Looking for posts since: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Look for discount patterns (e.g., 50%, 20% off, etc.)
        discount_pattern = re.compile(r'\b\d+%\b|\b\d+%\s*discount\b', re.IGNORECASE)
        promotion_found = False
        promotion_details = []
        processed_posts = 0
        max_posts_to_check = 5  # Only check the first 5 most recent posts
        
        # Keep loading more posts until we find one older than 7 days or reach max posts
        while processed_posts <= max_posts_to_check:
            # Get all visible posts
            posts = driver.find_elements(By.CSS_SELECTOR, "div[role='article']")
            
            # Process new posts
            for i in range(processed_posts, len(posts)):
                if processed_posts >= max_posts_to_check:
                    break
                    
                try:
                    post = posts[i]
                    processed_posts += 1
                    
                    # Get post time
                    try:
                        time_elements = post.find_elements(By.CSS_SELECTOR, "a[href*='/posts/']")
                        if not time_elements:
                            continue
                            
                        post_time_text = time_elements[0].text
                        post_datetime = parse_facebook_time(post_time_text)
                        
                        # If we can't parse the date, assume it's recent
                        if not post_datetime:
                            print(f"Could not parse time for post {processed_posts}, assuming recent")
                            post_datetime = datetime.now()
                            # We're only checking the first 5 most recent posts
                            # regardless of date since Facebook shows most recent first
                            pass
                        
                        # Print post text for debugging
                        print(f"\n--- Post {processed_posts + 1} ---")
                        print(f"Time: {post_time_text}")
                        print("Content:")
                        print(post.text)
                        print("-" * 40)
                        
                        # Check for promotions
                        post_text = post.text.lower()
                        if match := discount_pattern.search(post_text):
                            promotion_found = True
                            promotion_text = post.text[:200] + ('' if len(post.text) <= 200 else '...')
                            promotion_details.append({
                                'date': post_time_text,
                                'datetime': post_datetime,
                                'text': promotion_text,
                                'match': match.group()
                            })
                            print(f"✅ Found promotion: {match.group()}")
                        else:
                            print("No promotion found in this post")
                            
                    except Exception as e:
                        print(f"Error processing post {processed_posts}: {str(e)}")
                        continue
                        
                except Exception as e:
                    print(f"Error getting post {processed_posts}: {str(e)}")
                    continue
            
            # Only process the initially loaded posts
            if processed_posts >= max_posts_to_check or processed_posts >= len(posts):
                break  # Stop if we've processed the maximum number of posts or all visible posts
            
        print(f"Checked {processed_posts} posts (max limit reached)")
        return promotion_found, promotion_details, latest_post
        
    except Exception as e:
        print(f"Error during scraping: {str(e)}")
        return False, []
    finally:
        if driver:
            driver.quit()

def send_email(subject, body=None, is_html=False):
    """Send an email notification."""
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print("Email credentials not found in environment variables.")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = SMTP_USERNAME  # Send to the same email address
        msg['Subject'] = subject
        
        if body:
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"Email sent: {subject}")
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False

def check_for_promotions():
    """Check for promotions and send email notifications."""
    print(f"\n[{datetime.now()}] Checking for AllTrails promotions...")
    
    try:
        promotion_found, promotions, latest_post = scrape_facebook()
        
        # Create base HTML content with latest post info
        if latest_post:
            latest_post_section = f"""
            <div style="margin: 20px 0; padding: 15px; border: 1px solid #e0e0e0; border-radius: 8px; background-color: #f9f9f9;">
                <h3>Latest Post from AllTrails</h3>
                <p><strong>Posted:</strong> {latest_post['time']}</p>
                <div style="white-space: pre-line; background-color: white; padding: 12px; border-radius: 6px; border: 1px solid #e0e0e0; margin: 10px 0;">
                    {latest_post['text']}
                </div>
                <p><a href="{FACEBOOK_URL}" style="color: #1a73e8; text-decoration: none;">View on Facebook →</a></p>
            </div>
            """
        else:
            latest_post_section = "<p>Could not retrieve the latest post. Please check the Facebook page directly.</p>"
        
        if promotion_found:
            # Create HTML email content
            subject = f"🎉 AllTrails Promotion Found! - {datetime.now().strftime('%Y-%m-%d')}"
            
            # Build HTML content
            html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #1a73e8;">🎉 AllTrails Promotion Found!</h2>
                    <p>We found the following promotions on the AllTrails Facebook page:</p>
                    {latest_post_section}
                    <h3>🎯 Promotions Found:</h3>
            """
            
            for i, promo in enumerate(promotions, 1):
                html_content += f"""
                <div style="margin-bottom: 20px; padding: 15px; border: 1px solid #e0e0e0; border-radius: 8px; background-color: #fff8e1;">
                    <h3 style="color: #e65100;">🎁 Promotion {i} - {promo['match'].upper()}</h3>
                    <p><strong>Posted:</strong> {promo['date']}</p>
                    <div style="white-space: pre-line; background-color: white; padding: 12px; border-radius: 6px; border: 1px solid #e0e0e0;">
                        {promo['text']}
                    </div>
                    <p><a href="{FACEBOOK_URL}" style="color: #1a73e8; text-decoration: none; font-weight: bold;">View on Facebook →</a></p>
                </div>
                """
            
            html_content += """
                    <div style="margin-top: 30px; padding: 15px; background-color: #f5f5f5; border-radius: 8px; text-align: center;">
                        <p>Check the <a href="https://www.facebook.com/AllTrails" style="color: #1a73e8; text-decoration: none; font-weight: bold;">AllTrails Facebook page</a> for more details.</p>
                        <p style="color: #666; font-size: 0.9em;">Happy trails! 🚶‍♂️🌲</p>
                    </div>
                </body>
            </html>
            """
            
            send_email(subject, html_content, is_html=True)
        else:
            subject = f"AllTrails Update - No Promotions Found - {datetime.now().strftime('%Y-%m-%d')}"
            
            # Create HTML content for no promotions found
            html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #1a73e8;">🔍 AllTrails Update</h2>
                    <p>No promotions were found on the AllTrails Facebook page today. Here's their latest post:</p>
                    {latest_post_section}
                    <div style="margin-top: 30px; padding: 15px; background-color: #f5f5f5; border-radius: 8px; text-align: center;">
                        <p>Check the <a href="https://www.facebook.com/AllTrails" style="color: #1a73e8; text-decoration: none; font-weight: bold;">AllTrails Facebook page</a> for updates.</p>
                        <p style="color: #666; font-size: 0.9em;">We'll keep checking for you! 🚶‍♂️🌲</p>
                    </div>
                </body>
            </html>
            """
            
            send_email(subject, html_content, is_html=True)
            print("No promotions found.")
            
    except Exception as e:
        error_subject = "Error Checking AllTrails Promotions"
        error_body = f"An error occurred while checking for AllTrails promotions:\n\n{str(e)}"
        if 'latest_post' in locals() and latest_post:
            error_body += f"\n\nLatest post info that was retrieved before the error:\nTime: {latest_post.get('time', 'N/A')}\n\n{latest_post.get('text', 'No post text')}"
        send_email(error_subject, error_body)
        print(f"Error: {str(e)}")

from flask import Flask, jsonify
import threading
import os

app = Flask(__name__)

@app.route('/')
def health_check():
    return jsonify({"status": "healthy"})

def run_scheduler():
    while True:
        print("Running scheduled promotion check...")
        check_for_promotions()
        time.sleep(3600)  # Run every hour

def main():
    print("Starting AllTrails Promotion Checker Service")
    print("------------------------------------------")
    
    # Start the scheduler in a background thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # Start the web server
    port = int(os.environ.get('PORT', 8080))
    print(f"Starting web server on port {port}...")
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    main()
