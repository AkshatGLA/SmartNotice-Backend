from flask import Blueprint, request, jsonify
import csv
import datetime
import logging
from threading import Thread, Lock
from mongoengine import Document, StringField, IntField
import time
import smtplib
from email.mime.text import MIMEText

# Configure logger to show debug logs too
logging.basicConfig(level=logging.DEBUG)    
logger = logging.getLogger(__name__)

DEFAULT_NOTICE_DAYS = 7

# MongoEngine Model
class Holiday(Document):
    name = StringField(required=True)
    start_date = StringField(required=True)  # "MM-DD-YYYY"
    end_date = StringField(required=True)
    type = StringField(default="Public Holiday")
    notice_days = IntField(default=DEFAULT_NOTICE_DAYS)
    message = StringField(default="")
    meta = {"collection": "holidays"}

# Thread-safe Holiday Manager
class HolidayManager:
    def __init__(self):
        self.lock = Lock()
        self.holidays = []
        self.initialized = False

    def load_from_csv_data(self, csv_data, save_to_db=True):
        logger.debug("Starting CSV parsing...")
        with self.lock:
            try:
                reader = csv.DictReader(csv_data)
                new_holidays = []
                for row in reader:
                    logger.debug(f"Processing row: {row}")
                    try:
                        start_date = datetime.datetime.strptime(row['start_date'], "%m/%d/%Y").date()
                        end_date = datetime.datetime.strptime(row['end_date'], "%m/%d/%Y").date()

                        holiday_entry = {
                            "name": row['name'],
                            "start_date": start_date.strftime("%m-%d-%Y"),
                            "end_date": end_date.strftime("%m-%d-%Y"),
                            "type": row.get('type', 'Public Holiday'),
                            "notice_days": int(row.get('notice_days', DEFAULT_NOTICE_DAYS)),
                            "message": row.get('message', '')
                        }
                        new_holidays.append(holiday_entry)
                        logger.debug(f"Added holiday: {holiday_entry}")
                    except (ValueError, KeyError) as e:
                        logger.error(f"Error processing row {row}: {e}")

                self.holidays = new_holidays
                self.initialized = True
                logger.debug(f"Total holidays loaded: {len(self.holidays)}")

                if save_to_db:
                    logger.debug("Saving holidays to MongoDB...")
                    Holiday.objects.insert([Holiday(**h) for h in new_holidays])
                    logger.info("Holidays saved to MongoDB")

                return True
            except Exception as e:
                logger.exception("CSV loading failed")
                return False

    def load_from_db(self):
        logger.debug("Loading holidays from MongoDB...")
        with self.lock:
            try:
                holidays = list(Holiday.objects)
                logger.debug(f"Found {len(holidays)} holidays in DB")
                if holidays:
                    # Keep the same dict structure as CSV loader
                    self.holidays = [
                        {
                            "name": h.name,
                            "start_date": h.start_date,
                            "end_date": h.end_date,
                            "type": h.type,
                            "notice_days": h.notice_days,
                            "message": h.message
                        }
                        for h in holidays
                    ]
                    self.initialized = True
                    logger.info("Holidays loaded from MongoDB")
                    return True
                return False
            except Exception as e:
                logger.exception("Failed to load holidays from MongoDB")
                return False

    def check_holidays(self):
        logger.debug("Running holiday check...")
        with self.lock:
            if not self.initialized:
                logger.warning("Holiday data not initialized")
                return []

            today = datetime.date.today()
            notices = []
            for holiday in self.holidays:
                logger.debug(f"Checking holiday: {holiday}")
                try:
                    holiday_date = datetime.datetime.strptime(holiday["start_date"], "%m-%d-%Y").date()
                    days_until = (holiday_date - today).days
                    logger.debug(f"Days until holiday: {days_until}")
                    if days_until == holiday["notice_days"]:
                        notice = {
                            "subject": f"Upcoming Holiday: {holiday['name']}",
                            "message": (
                                f"{holiday['name']} is from {holiday_date.strftime('%A, %B %d')} "
                                f"to {datetime.datetime.strptime(holiday['end_date'], '%m-%d-%Y').date().strftime('%B %d')}.\n"
                                f"{holiday['message']}"
                            )
                        }
                        notices.append(notice)
                        logger.info(f"Notice triggered: {notice}")
                except Exception as e:
                    logger.exception(f"Error processing holiday {holiday}")
            return notices

# Create Blueprint
holiday_api = Blueprint("holiday_api", __name__, url_prefix="/api")

holiday_manager = HolidayManager()

@holiday_api.route('/upload-csv', methods=['POST'])
def upload_csv():
    logger.debug("Received CSV upload request")
    if 'file' not in request.files:
        logger.warning("No file part in request")
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if not file.filename:
        logger.warning("Empty filename in upload")
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        csv_content = file.read().decode('utf-8').splitlines()
        logger.debug(f"CSV content lines: {len(csv_content)}")
        if holiday_manager.load_from_csv_data(csv_content, save_to_db=True):
            logger.info("CSV processed and holidays stored successfully")
            return jsonify({"holidays": holiday_manager.holidays}), 200
        else:
            logger.error("Failed to process CSV")
            return jsonify({'error': 'Failed to process CSV'}), 500
    except Exception as e:
        logger.exception("Upload failed")
        return jsonify({'error': str(e)}), 500

@holiday_api.route('/get-holidays', methods=['GET'])
def get_holidays():
    logger.debug("Received request to get holidays")
    try:
        holidays = [
            {
                "name": h.name,
                "start_date": h.start_date,
                "end_date": h.end_date,
                "type": h.type,
                "notice_days": h.notice_days,
                "message": h.message
            }
            for h in Holiday.objects
        ]
        logger.debug(f"Returning {len(holidays)} holidays")
        return jsonify({"holidays": holidays}), 200
    except Exception as e:
        logger.exception("Failed to get holidays")
        return jsonify({"error": str(e)}), 500

@holiday_api.route('/delete-holidays', methods=['DELETE'])
def delete_holidays():
    logger.debug("Received request to delete all holidays")
    try:
        Holiday.drop_collection()
        holiday_manager.holidays = []
        holiday_manager.initialized = False
        logger.info("All holidays deleted")
        return jsonify({"message": "All holidays deleted"}), 200
    except Exception as e:
        logger.exception("Failed to delete holidays")
        return jsonify({"error": str(e)}), 500

# # Email configuration
# SMTP_SERVER = "smtp.gmail.com"       # Or your SMTP server
# SMTP_PORT = 587
# SMTP_USERNAME = "your_email@example.com"
# SMTP_PASSWORD = "your_password"
# FROM_EMAIL = "your_email@example.com"
# TO_EMAILS = ["recipient1@example.com", "recipient2@example.com"]

# def send_email(subject, message):
#     try:
#         msg = MIMEText(message, "plain")
#         msg["Subject"] = subject
#         msg["From"] = FROM_EMAIL
#         msg["To"] = ", ".join(TO_EMAILS)

#         with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
#             server.starttls()  # Secure connection
#             server.login(SMTP_USERNAME, SMTP_PASSWORD)
#             server.sendmail(FROM_EMAIL, TO_EMAILS, msg.as_string())

#         logger.info(f"Email sent: {subject}")
#     except Exception as e:
#         logger.exception("Failed to send email")


def start_holiday_checker():
    logger.debug("Starting holiday background checker...")
    if not holiday_manager.load_from_db():
        logger.warning("No holiday data found in DB. Upload a CSV.")
    def automated_daily_check():
        logger.info("Holiday automation started")
        while True:
            notices = holiday_manager.check_holidays()
            if notices:
                for notice in notices:
                    logger.info(f"NOTICE: {notice['subject']}\n{notice['message']}")
                    # send_email(notice['subject'], notice['message'])
            else:
                logger.debug(f"{datetime.date.today()} - No notices today")
                print(f"{datetime.date.today()} - No notices today")
            time.sleep(5*60*60)
    Thread(target=automated_daily_check, daemon=True).start()
