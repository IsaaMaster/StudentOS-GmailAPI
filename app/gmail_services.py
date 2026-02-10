import os, dotenv
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from app.gmail_helpers import get_email_body, clean_emails
import base64
from email.message import EmailMessage

dotenv.load_dotenv()

ACCESS_TOKEN = os.getenv("GMAIL_ACCESS_TOKEN")
GROQ_API_URL = os.getenv("GROQ_API_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")



def get_unread(hours_back=24):
    creds = Credentials(ACCESS_TOKEN)
      
    service = build('gmail', 'v1', credentials=creds)
    
    after_ts = int((datetime.now() - timedelta(hours=hours_back)).timestamp())
    query = f"label:INBOX category:primary is:unread after:{after_ts}"
    
    results = service.users().messages().list(userId='me', q=query, maxResults=3).execute()
    messages = results.get('messages', [])
    
    if not messages:
        return f"You have no unread emails from the last {hours_back} hours."

    formatted_output = ""
    for msg in messages:
        m = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        payload = m.get('payload', {})
        
        # Clean and Truncate logic applied here
        body = get_email_body(payload)
        body = clean_emails(body)

        formatted_output += f"{body}\n---\n"
    
    return formatted_output



def upsert_draft(body: str) -> str:
    creds = Credentials(ACCESS_TOKEN)
    service = build('gmail', 'v1', credentials=creds)

    message = EmailMessage()
    message.set_content(body)

    # Gmail API requires base64url encoded string
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    create_message = {'message': {'raw': encoded_message}}
    draft = service.users().drafts().create(userId='me', body=create_message).execute()
    
    return f"Draft created successfully. ID: {draft['id']}"

