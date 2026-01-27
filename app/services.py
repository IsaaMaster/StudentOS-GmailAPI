import os, dotenv, requests
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from app.gmail_helpers import get_email_body, clean_emails

dotenv.load_dotenv()

ACCESS_TOKEN = os.getenv("GMAIL_ACCESS_TOKEN")
GROQ_API_URL = os.getenv("GROQ_API_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")



def summarize_emails(email_content):
    if not email_content or "no unread emails" in email_content.lower():
        return email_content

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}   
    data = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": (
                    "You are a minimalist voice assistant briefing a student. "
                    "Provide a single, fluid paragraph containing all updates (Less than 100 words). "
                    "CRITICAL: Use conjunctions like 'while', 'and', or 'also' to link different emails into a natural spoken flow. "
                    "Avoid choppy, short sentences. Get straight to the news without a preamble. "
                    "STRICT RULES: No lists, no special characters, no transaction IDs, no links, and NO announcement of the summary. "
                    "Use only words meant to be spoken aloud. "
                    "Avoid run-on sentences."
                    "Example: 'The Dean invited you to a social this Friday, and your Amazon package has arrived.'"
                ),
            }, 
            {
                "role": "user", 
                "content": f"Summarize these emails into one smooth spoken update:\n\n{email_content}"
            }
        ],
        "temperature": 0.3, # Slight increase from 0.0 helps the model find better "flow" words
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        print(f"DEBUG: Tokens used: {response.json()['usage']['total_tokens']}")
        return response.json()['choices'][0]['message']['content'] if response.status_code == 200 else f"Error: {response.text}"
    else:
        return f"Error: {response.status_code}, {response.text}"



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

with open(f"tests/mock_data/email_batch_1.txt", "r") as f:
    email_content = f.read()
    summary = summarize_emails(email_content)
    print(summary)

