import os, dotenv
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from app.gmail_helpers import get_email_body, clean_emails
import base64
from email.message import EmailMessage
import email.utils


dotenv.load_dotenv()

ACCESS_TOKEN = os.getenv("GMAIL_ACCESS_TOKEN")
GROQ_API_URL = os.getenv("GROQ_API_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")



def get_unread(hours_back=24, max_results=3) -> str:
    creds = Credentials(ACCESS_TOKEN)
      
    service = build('gmail', 'v1', credentials=creds)
    
    after_ts = int((datetime.now() - timedelta(hours=hours_back)).timestamp())
    query = f"label:INBOX category:primary is:unread after:{after_ts}"
    
    results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
    messages = results.get('messages', [])
    
    if not messages:
        return f"You have no unread emails from the last {hours_back} hours."

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
    
    return emails



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



def upsert_reply(body: str, thread_id: str, rfc_id: str, subject: str, to_email: str) -> str:
    """
    Creates a Gmail draft that is correctly threaded as a reply.
    """
    creds = Credentials(ACCESS_TOKEN)
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
    
    return f"Reply draft created successfully. ID: {draft['id']}"