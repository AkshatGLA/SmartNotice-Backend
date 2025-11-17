import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
import os # Import os to get credentials from environment variables

# --- CONFIGURATION ---
# It's better to load sensitive data from environment variables
EMAIL_SENDER_ADDRESS = os.environ.get("EMAIL_SENDER_ADDRESS", "team.smart.notice@gmail.com")
EMAIL_SENDER_PASSWORD = os.environ.get("EMAIL_SENDER_PASSWORD", "sqbpaqxlstzrxabk") # Your App Password
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

def send_bulk_email(recipient_emails: List[str], subject: str, body: str) -> bool:
    if not all([EMAIL_SENDER_ADDRESS, EMAIL_SENDER_PASSWORD, recipient_emails]):
        print("ERROR: Email credentials are not configured or recipient list is empty.")
        return False

    message = MIMEMultipart()
    message["From"] = EMAIL_SENDER_ADDRESS
    # Use Bcc to hide recipient emails from each other
    message["Bcc"] = ", ".join(recipient_emails)
    message["Subject"] = subject
    
    # Attach the body as HTML to preserve formatting from the RTE
    message.attach(MIMEText(body, "html"))

    try:
        print(f"Connecting to email server {SMTP_SERVER}...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER_ADDRESS, EMAIL_SENDER_PASSWORD)
        print(f"Sending email to {len(recipient_emails)} recipients...")
        # Send to recipient_emails list directly
        server.sendmail(EMAIL_SENDER_ADDRESS, recipient_emails, message.as_string())
        print("✅ Email sent successfully!")
        return True
    except smtplib.SMTPAuthenticationError:
        print("❌ Authentication failed. Check your credentials.")
        return False
    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        return False
    finally:
        if 'server' in locals() and server:
            server.quit()