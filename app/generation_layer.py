import os, dotenv, requests
import logging
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import random 

dotenv.load_dotenv()

ACCESS_TOKEN = os.getenv("GMAIL_ACCESS_TOKEN")
GROQ_API_URL = os.getenv("GROQ_API_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GENERATION_MODEL = os.getenv("GENERATION_MODEL")
VALIDATION_MODEL = os.getenv("VALIDATION_MODEL")

logger = logging.getLogger(__name__)


def prioritized_insights(emails: dict) -> str:
    """
    Analyzes a batch of emails and delivers a voice-optimized briefing
    of only the items that genuinely need the user's attention.

    Unlike summarize_emails(), this function triages before it speaks —
    skipping automated, mass, and purely informational emails entirely,
    and surfacing only deadlines, personal requests, and schedule changes
    in a directive EA-style format rather than a narrative summary.

    Args:
        emails: The raw emails dict from get_unread(), keyed by Gmail message ID.
                Each value contains: from, from-email, subject, body, rfc-id.

    Returns:
        A voice-ready string of 1-3 sentences covering only what needs attention,
        or a graceful fallback if nothing in the inbox requires action.
    """
    if not emails:
        logger.info("No emails passed to prioritized_insights")
        return "Nothing in your inbox needs attention right now."

    # Format emails with subject lines included — subject carries critical triage signal
    # (e.g., "ACTION REQUIRED", "URGENT", "Re:") that the body-only format loses.
    # Pre-compute email age so the model doesn't need to do date arithmetic itself.
    formatted_emails = ""
    for i, email_data in enumerate(emails.values(), 1):
        try:
            sent_dt = parsedate_to_datetime(email_data['date'])
            days_ago = (datetime.now(timezone.utc) - sent_dt).days
            age_label = "SENT TODAY" if days_ago == 0 else f"SENT {days_ago} DAY(S) AGO"
            if days_ago > 0:
                sent_date_str = sent_dt.strftime("%A, %B %d")
                temporal_warning = (
                    f"[TEMPORAL WARNING: This email was sent {days_ago} day(s) ago on {sent_date_str}. "
                    f"Words like 'today', 'tonight', 'tomorrow', and 'this [weekday]' in the body referred to {sent_date_str}, NOT to today. "
                    f"Any event described as happening 'today' or 'tonight' in this email has ALREADY PASSED. Do not present it as current or upcoming.]\n"
                )
            else:
                temporal_warning = ""
        except Exception:
            age_label = "SENT DATE UNKNOWN"
            temporal_warning = ""

        formatted_emails += (
            f"[Email {i}] [{age_label}]\n"
            f"{temporal_warning}"
            f"Sent_Date: {email_data['date']}\n"
            f"From: {email_data['from']}\n"
            f"Subject: {email_data['subject']}\n"
            f"Body: {email_data['body']}\n"
            f"---\n"
        )


    # Inject today's date so the model can contextualize deadline urgency.
    # "Due March 1st" means something very different depending on when it's read.
    today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")

    logger.info(f"Calling GROQ API for prioritized insights across {len(emails)} emails")
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": GENERATION_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a spoken inbox assistant. Summarize the emails below and deliver a voice briefing of the main points in a single paragraph that can be easily read by Alexa. Be friendly and well-spoken. \n\n"
                    "Keep it brief and concise and professional. Keep it under 80 words. Don't get into the details too much."
                    "Don't tell the user what to do. "
                ),
            },
            {
                "role": "user",
                "content": f"{formatted_emails}"
            }
        ],
        "temperature": 0.0,
    }


    preamble = [
        "Here's what I found:",           # neutral, direct
        "Here's a quick update:", # warm, conversational
    ]
    epilogue = [
        "That's all for now. Have a great day!",  # warm, friendly
        "That's everything worth noting. Have a good one!",         # clean, no forced cheerfulness
        "That covers it from your inbox. Enjoy your day!",         # clear, definitive
    ]


    response = requests.post(GROQ_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        result = response.json()['choices'][0]['message']['content'].strip()

        #full_result = preamble[random.randint(0, len(preamble)-1)] + " " + result.strip() + " " + epilogue[random.randint(0, len(epilogue)-1)]
        #logger.info("Prioritized insights generated successfully")
        return result
    else:
        logger.error(f"GROQ API error: {response.status_code} - {response.text}")
        return "Sorry, I had trouble checking your inbox."

def summarize_emails(email_content):
    if not email_content or "no unread emails" in email_content:
        logger.info("No unread emails to summarize")
        return "You have no new emails. Enjoy your day!"

    logger.info("Calling GROQ API to summarize emails")
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": GENERATION_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a minimalist voice assistant. "
                    "START IMMEDIATELY with the first piece of news. "
                    "CRITICAL: Do not include ANY introductory phrases, greetings, or meta-talk (e.g., 'Here is your summary', 'You have...', 'Regarding your emails'). "
                    "Provide a single, fluid paragraph under 80 words. "
                    "Use conjunctions like 'while', 'and', or 'also' to link updates into a natural spoken flow. "
                    "Avoid short, choppy sentences and run-on sentences. "
                    "STRICT RULES: No lists, no special characters, no transaction IDs, and no links. "
                    "ONLY output the final spoken text. No preambles, no headers, no announcements."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Emails:\n{email_content}\n\n"
                    "Task: Summarize into one smooth spoken paragraph. "
                    "DO NOT use a preamble. START IMMEDIATELY with the information."
                )
            }
        ],
        "temperature": 0.2, # Slightly lower to reduce the chance of 'creative' intros
    }



    response = requests.post(GROQ_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        result = response.json()['choices'][0]['message']['content']
        logger.info("Email summary generated successfully")
        return result
    else:
        logger.error(f"GROQ API error: {response.status_code} - {response.text}")
        return "Sorry, I had trouble summarizing your emails."


def generate_draft(recipient_name: str, email_description: str) -> str:
    """
    Generates a draft email based on the recipient and description provided.
    """
    logger.info(f"Generating draft email for {recipient_name}: {email_description}")
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": GENERATION_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a professional student writing assistant. "
                    "Output ONLY the text of the email. "
                    "STRICT RULES:\n"
                    "1. NO PREAMBLE: Start directly with 'Hi [Name],' or 'Dear [Name],'.\n"
                    "2. NO SUBJECT LINE: Do not include a subject line or 'Subject:' header.\n"
                    "3. NO PLACEHOLDERS: Never use brackets like '[Your Name]' or '[Date]'. \n"
                    "4. SIGN-OFF: End the email with a professional sign-off like 'Best,' or 'Thanks,' but DO NOT include a name after it.\n"
                    "5. FORMATTING: Use clear paragraph breaks (\\n\\n).\n"
                    "6. TONE: Maintain a polite, student-to-professor or student-to-peer balance."
                )
            },
            {
                "role": "user",
                "content": f"Recipient: {recipient_name}\nMessage: {email_description}"
            }
        ],
        "temperature": 0.5, # Lowered slightly for more consistent professional tone
        "max_tokens": 500
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=data)

        if response.status_code == 200:
            result = response.json()
            draft = result["choices"][0]["message"]["content"].strip()
            logger.info(f"Draft generated successfully (length: {len(draft)} chars)")
            return draft
        else:
            error_msg = f"GROQ API error: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return error_msg
    except Exception as e:
        logger.error(f"Exception while generating draft: {e}", exc_info=True)
        return f"Error generating draft: {str(e)}"
    

def generate_reply(thread_body: str, recipient_name: str, reply_description: str) -> str:
    """
    Generates a reply email based on the thread body and description provided.
    """
    logger.info(f"Generating reply email to {recipient_name}: {reply_description}")
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": GENERATION_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a professional student writing assistant specialized in email replies. "
                    "Output ONLY the text of the reply email. "
                    "STRICT RULES:\n"
                    "1. NO PREAMBLE: Start immediately with the greeting (e.g., 'Hi [Name],' or 'Dear [Name],').\n"
                    "2. NO SUBJECT: Do not include a subject line or 'Re:' header.\n"
                    "3. NO PLACEHOLDERS: Never use brackets like '[Your Name]'. \n"
                    "4. SIGN-OFF: End with 'Best,' 'Thanks,' or a similar polite closing, but leave the name blank.\n"
                    "5. CONTEXT AWARENESS: Use the 'Previous Thread' only to determine the appropriate formality (Professor vs. Peer). \n"
                    "6. FOCUS: Your primary goal is to execute the 'REPLY INTENT' accurately. Do not repeat what was already said in the thread."
                )
            },
            {
                "role": "user",
                "content": (
                    f"--- PREVIOUS THREAD ---\n{thread_body}\n\n" # Truncated to save tokens
                    f"--- REPLY INTENT ---\n"
                    f"Recipient: {recipient_name}\n"
                    f"What I want to say: {reply_description}\n\n"
                    "Write the reply email now:"
                )
            }
        ],
        "temperature": 0.4, # Lowered for more precise instruction following
        "max_tokens": 600
    }
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=data)

        if response.status_code == 200:
            result = response.json()
            reply = result["choices"][0]["message"]["content"].strip()
            logger.info(f"Reply generated successfully (length: {len(reply)} chars)")
            return reply
        else:
            error_msg = f"GROQ API error: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return error_msg
    except Exception as e:
        logger.error(f"Exception while generating reply: {e}", exc_info=True)
        return f"Error generating reply: {str(e)}"


