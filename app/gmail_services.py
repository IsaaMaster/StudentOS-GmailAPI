import os, dotenv
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from app.gmail_helpers import get_email_body, clean_emails
import base64
from email.message import EmailMessage
import email.utils
import logging

dotenv.load_dotenv()

logger = logging.getLogger(__name__)

ACCESS_TOKEN = os.getenv("GMAIL_ACCESS_TOKEN")
GROQ_API_URL = os.getenv("GROQ_API_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

import requests

def get_user_first_name(access_token: str) -> str:
    response = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    response.raise_for_status()
    return response.json().get("given_name")


def get_emails(hours_back=24, max_results=15, body_max_length=2000, access_token=ACCESS_TOKEN) -> dict:
    logger.info(f"Fetching unread emails from last {hours_back} hours (max {max_results} results)")
    try:
        creds = Credentials(access_token)

        service = build('gmail', 'v1', credentials=creds)

        after_ts = int((datetime.now() - timedelta(hours=hours_back)).timestamp())
        query = f"label:INBOX category:primary after:{after_ts}"

        results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages = results.get('messages', [])

        if not messages:
            logger.info(f"No unread emails found from last {hours_back} hours")
            return {}

        logger.info(f"Found {len(messages)} unread messages, fetching full details")
        emails = {}
        for msg in messages:
            m = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            payload = m.get('payload', {})
            headers = m.get('payload', {}).get('headers', [])

            body = get_email_body(payload)
            body = clean_emails(body, max_length=body_max_length)
            from_header = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown Sender")
            from_email = email.utils.parseaddr(from_header)[1]
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
            rfc_id = next((h['value'] for h in headers if h['name'] == 'Message-ID'), None)
            date = next((h['value'] for h in headers if h['name'] == 'Date'), None)
            emails[msg['id']] = {'from': from_header, 'from-email': from_email, 'date': date, 'subject': subject, 'body': body, 'rfc-id': rfc_id}

        logger.info(f"Successfully retrieved {len(emails)} email details")
        return emails
    except Exception as e:
        logger.error(f"Error fetching unread emails: {e}", exc_info=True)
        raise



def get_unread(hours_back=24, max_results=3, access_token = ACCESS_TOKEN) -> str:
    logger.info(f"Fetching unread emails from last {hours_back} hours (max {max_results} results)")
    try:
        creds = Credentials(access_token)

        service = build('gmail', 'v1', credentials=creds)

        after_ts = int((datetime.now() - timedelta(hours=hours_back)).timestamp())
        query = f"label:INBOX category:primary is:unread after:{after_ts}"

        results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages = results.get('messages', [])

        if not messages:
            logger.info(f"No unread emails found from last {hours_back} hours")
            return {}

        logger.info(f"Found {len(messages)} unread messages, fetching full details")
        emails = {}
        for msg in messages:
            m = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            payload = m.get('payload', {})
            headers = m.get('payload', {}).get('headers', [])

            # Clean and Truncate logic applied here
            body = get_email_body(payload)
            body = clean_emails(body)
            from_header = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown Sender")
            from_email = email.utils.parseaddr(from_header)[1]
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
            rfc_id = next((h['value'] for h in headers if h['name'] == 'Message-ID'), None)
            emails[msg['id']] = {'from': from_header, 'from-email': from_email, 'subject': subject, 'body': body, 'rfc-id': rfc_id}

        logger.info(f"Successfully retrieved {len(emails)} email details")
        return emails
    except Exception as e:
        logger.error(f"Error fetching unread emails: {e}", exc_info=True)
        raise





def get_recent_all_emails(minutes_back=10, max_results=10, access_token=ACCESS_TOKEN) -> dict:
    """
    Fetches all emails (across all categories, not just Primary) received in the
    last `minutes_back` minutes. Used for verification code lookup where the
    email may land in Updates, Promotions, or Spam rather than Primary.

    Body is capped at 500 chars — OTP emails are short and codes always appear
    near the top, so a tighter limit avoids wasting tokens on boilerplate footers.
    """
    logger.info(f"Fetching all emails from last {minutes_back} minutes (max {max_results} results)")
    try:
        creds = Credentials(access_token)
        service = build('gmail', 'v1', credentials=creds)

        after_ts = int((datetime.now() - timedelta(minutes=minutes_back)).timestamp())
        query = f"after:{after_ts}"

        results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages = results.get('messages', [])

        if not messages:
            logger.info(f"No emails found from last {minutes_back} minutes")
            return {}

        logger.info(f"Found {len(messages)} messages, fetching full details")
        emails = {}
        for msg in messages:
            m = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            payload = m.get('payload', {})
            headers = m.get('payload', {}).get('headers', [])

            body = get_email_body(payload)
            body = clean_emails(body, max_length=500)
            from_header = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown Sender")
            from_email = email.utils.parseaddr(from_header)[1]
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
            date = next((h['value'] for h in headers if h['name'] == 'Date'), None)
            emails[msg['id']] = {'from': from_header, 'from-email': from_email, 'date': date, 'subject': subject, 'body': body}

        logger.info(f"Successfully retrieved {len(emails)} recent emails")
        return emails
    except Exception as e:
        logger.error(f"Error fetching recent emails: {e}", exc_info=True)
        raise


def upsert_draft(body: str, access_token: str = ACCESS_TOKEN) -> tuple:
    logger.info(f"Creating draft (body length: {len(body)} chars)")
    try:
        creds = Credentials(access_token)
        service = build('gmail', 'v1', credentials=creds)

        message = EmailMessage()
        message.set_content(body)

        # Gmail API requires base64url encoded string
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_message = {'message': {'raw': encoded_message}}
        draft = service.users().drafts().create(userId='me', body=create_message).execute()

        logger.info(f"Draft created successfully with ID: {draft['id']}")
        return (True, f"Draft created successfully. ID: {draft['id']}")
    except Exception as e:
        logger.error(f"Error creating draft: {e}", exc_info=True)
        return (False, f"Error creating draft: {str(e)}")



def upsert_reply(body: str, thread_id: str, rfc_id: str, subject: str, to_email: str, access_token: str = ACCESS_TOKEN) -> tuple:
    """
    Creates a Gmail draft that is correctly threaded as a reply.
    """
    logger.info(f"Creating reply to {to_email} in thread {thread_id} (body length: {len(body)} chars)")
    try:
        creds = Credentials(access_token)
        service = build('gmail', 'v1', credentials=creds)

        # 1. Create the MIME message
        message = EmailMessage()
        message.set_content(body)

        # 2. Add the "Stitch" Headers
        # Ensure subject starts with Re:
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        message['Subject'] = subject
        message['To'] = to_email
        message['In-Reply-To'] = rfc_id
        message['References'] = rfc_id  # For a simple reply, these are usually the same

        # 3. Encode to base64url
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        # 4. Create the Draft object
        create_message = {
            'message': {
                'raw': encoded_message,
                'threadId': thread_id  # This tells Gmail's DB where to put it
            }
        }

        draft = service.users().drafts().create(userId='me', body=create_message).execute()

        logger.info(f"Reply draft created successfully with ID: {draft['id']}")
        return (True, f"Reply draft created successfully. ID: {draft['id']}")
    except Exception as e:
        logger.error(f"Error creating reply: {e}", exc_info=True)
        return (False, f"Error creating reply: {str(e)}")