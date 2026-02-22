import os, dotenv, requests
from app.gmail_services import get_unread

dotenv.load_dotenv()

ACCESS_TOKEN = os.getenv("GMAIL_ACCESS_TOKEN")
GROQ_API_URL = os.getenv("GROQ_API_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def find_reply_match(unread_emails, match_recipient, match_description):
    """
    Finds the best matching email from the unread emails based on recipient and description.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}",
    }
    data = {
    "model": "llama-3.1-8b-instant",
    "messages": [
        {
            "role": "system",
            "content": (
                "Task: Map user intent to the correct Email ID for a reply.\n"
                "Constraints:\n"
                "1. Match based on Recipient Name/Email or Email Content description.\n"
                "2. If multiple emails exist from the same sender, pick the most relevant to the Description.\n"
                "3. If no clear match exists, you MUST output 'none'.\n"
                "4. Output ONLY the raw ID string or 'none'. No preamble, no quotes, no explanation."
            )
        },
        {
            "role": "user",
            "content": (
                f"--- UNREAD EMAILS ---\n{unread_emails}\n\n"
                f"--- USER INTENT ---\n"
                f"Recipient: {match_recipient}\n"
                f"Description: {match_description}\n\n"
                f"Match ID:"
            )
        }
    ],
    "temperature": 0.0,
}

    response = requests.post(GROQ_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content'].strip()
    else:
        return f"Error: {response.status_code}, {response.text}"

    
