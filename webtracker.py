import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
CHECK_INTERVAL = 86400  # 24 hours in seconds
ALLTRAILS_URL = "https://www.alltrails.com/membership"
TARGET_PRICE = 29.99  # Set your target price here

# Email configuration (using environment variables)
EMAIL_SENDER = os.getenv('EMAIL_SENDER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
EMAIL_RECEIVER = os.getenv('EMAIL_RECEIVER')
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

def check_membership_price():
    """Check the current membership price on AllTrails"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(ALLTRAILS_URL, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # This selector might need adjustment based on AllTrails' HTML structure
        price_element = soup.find('div', {'class': 'price'})  # Update this selector
        
        if price_element:
            price_text = price_element.get_text()
            # Extract the numeric price from the text
            try:
                current_price = float(''.join(c for c in price_text if c.isdigit() or c == '.'))
                return current_price
            except (ValueError, AttributeError):
                print(f"Could not parse price from: {price_text}")
                return None
        else:
            print("Could not find price element on the page")
            return None
            
    except requests.RequestException as e:
        print(f"Error fetching AllTrails page: {e}")
        return None

def send_alert(price):
    """Send an email alert about the sale"""
    if not all([EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER]):
        print("Email configuration is incomplete. Please check your .env file.")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = f"🚨 AllTrails Membership Sale Alert! Now ${price}/year"
        
        body = f"""
        <h2>AllTrails Membership Sale Alert! 🎉</h2>
        <p>The AllTrails annual membership is now <strong>${price}/year</strong>!</p>
        <p>Hurry, this deal might not last long!</p>
        <p><a href="{ALLTRAILS_URL}">Click here to check it out</a></p>
        <p>This alert was sent at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
            
        print("Sale alert email sent successfully!")
        return True
        
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def main():
    print("Starting AllTrails membership price monitor...")
    print(f"Will check every {CHECK_INTERVAL//3600} hours for prices below ${TARGET_PRICE}")
    
    while True:
        try:
            print(f"\nChecking at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            current_price = check_membership_price()
            
            if current_price is not None:
                print(f"Current AllTrails membership price: ${current_price}")
                
                if current_price <= TARGET_PRICE:
                    print(f"Sale detected! Price is ${current_price} (target: ${TARGET_PRICE})")
                    send_alert(current_price)
                    print("Exiting after sending alert.")
                    break
                else:
                    print(f"No sale yet. Current price: ${current_price} (target: ${TARGET_PRICE})")
            
            # Wait for the next check (24 hours)
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user.")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            print("Waiting 5 minutes before retrying...")
            time.sleep(300)  # Wait 5 minutes before retrying on error

if __name__ == "__main__":
    main()