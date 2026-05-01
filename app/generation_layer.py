import os, dotenv, requests
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import random 

dotenv.load_dotenv()

ACCESS_TOKEN = os.getenv("GMAIL_ACCESS_TOKEN")
GROQ_API_URL = os.getenv("GROQ_API_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GENERATION_MODEL = os.getenv("GENERATION_MODEL")
VALIDATION_MODEL = os.getenv("VALIDATION_MODEL")
SUMMARY_MODEL = os.getenv("SUMMARY_MODEL")
REASONING_MODEL = os.getenv("REASONING_MODEL")

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
    temporal_notes = []
    for i, email_data in enumerate(emails.values(), 1):
        try:
            sent_dt = parsedate_to_datetime(email_data['date'])
            days_ago = (datetime.now(timezone.utc) - sent_dt).days
            age_label = "SENT TODAY" if days_ago == 0 else f"SENT {days_ago} DAY(S) AGO"
            if days_ago > 0:
                sent_date_str = sent_dt.strftime("%A, %B %d")
                temporal_notes.append(
                    f"- Email {i} (sent {sent_date_str}): 'today', 'tonight', and 'tomorrow' in the body "
                    f"referred to {sent_date_str} — those events have already passed."
                )
        except Exception:
            age_label = "SENT DATE UNKNOWN"

        formatted_emails += (
            f"[Email {i}] [{age_label}]\n"
            f"Sent_Date: {email_data['date']}\n"
            f"From: {email_data['from']}\n"
            f"Subject: {email_data['subject']}\n"
            f"Body: {email_data['body']}\n"
            f"---\n"
        )

    temporal_preamble = ""
    if temporal_notes:
        temporal_preamble = (
            "TEMPORAL NOTES (read before summarizing):\n"
            + "\n".join(temporal_notes)
            + "\n\n"
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
        "model": SUMMARY_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a voice inbox assistant delivering a spoken summary of the user's most important emails.\n\n"
                    "IMPORTANCE HIERARCHY — use this to decide what to include:\n"
                    "  HIGH: Personal, direct emails from real people (colleagues, friends, contacts)\n"
                    "  MEDIUM: Emails from organizations specific to the user (a direct response, a status update, a confirmation)\n"
                    "  SKIP: Newsletters, marketing, automated notifications, mass emails, digests\n\n"
                    "OUTPUT RULES:\n"
                    "  - Cover at most 3-4 emails, most important first\n"
                    "  - If the inbox is mostly low-importance emails, say so briefly\n"
                    "  - One continuous paragraph, under 80 words\n"
                    "  - No lists, bullets, special characters, or links\n"
                    "  - Do not open with a preamble like 'Here is your summary' or 'You have X emails'\n"
                    "  - Do not instruct the user to take action\n"
                    "  - Write naturally — this will be read aloud by a voice assistant. Use transitional words/phrases to connect ideas smoothly.\n"
                    "  - TEMPORAL: Each email is labeled with its age. If a TEMPORAL NOTES section is present, "
                    "read it first — never describe a past event as upcoming or current"
                ),
            },
            {
                "role": "user",
                "content": f"Today is {today}.\n\n{temporal_preamble}{formatted_emails}"
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

def summarize_sender_emails(emails: dict, sender_name: str) -> str:
    """
    Given a batch of recent emails and a loosely-specified sender name,
    uses the LLM to fuzzy-match the sender and summarize what they said.

    The LLM handles cases where the user's phrasing ("my advisor", "mom",
    "Professor Kim") doesn't exactly match the From header ("Kimberly Johnson
    <k.johnson@ucsb.edu>"). If no emails match, it returns a graceful fallback.

    Args:
        emails: Recent emails dict from get_emails(), keyed by Gmail message ID.
        sender_name: The sender as described by the user (may be informal or partial).

    Returns:
        A voice-ready string summarizing what the sender wrote, or a fallback
        if no matching emails are found.
    """
    if not emails:
        logger.info("No emails passed to summarize_sender_emails")
        return f"I didn't find any recent emails from {sender_name}."

    formatted_emails = ""
    for i, email_data in enumerate(emails.values(), 1):
        formatted_emails += (
            f"[Email {i}]\n"
            f"From: {email_data['from']}\n"
            f"Subject: {email_data['subject']}\n"
            f"Body: {email_data['body']}\n"
            f"---\n"
        )

    logger.info(f"Calling GROQ API to find emails from '{sender_name}' across {len(emails)} emails")
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
                    "You are a voice assistant that checks a user's inbox for emails from a specific person or organization. "
                    "The user will give you a sender name that may be informal, partial, or a nickname "
                    "(e.g. 'mom', 'Professor Kim', 'the financial aid office', 'my advisor'). "
                    "Use common sense to match it against the actual From headers in the emails.\n\n"
                    "RULES:\n"
                    "1. MATCHING: Match loosely — 'Professor Kim' can match 'Kimberly Johnson', "
                    "'mom' can match a personal name, 'the registrar' can match a university email address.\n"
                    "2. IF MATCH FOUND: Respond with a single spoken sentence or two summarizing what they said. "
                    "Example: 'Yes, Professor Johnson emailed you yesterday about the midterm. She said the exam has been moved to Friday.'\n"
                    "3. IF NO MATCH: Respond with exactly: " f"'I didn't find any recent emails from {sender_name}.'\n"
                    "4. Keep it under 50 words. Output ONLY the spoken response, no preamble.",
                    "5.Write naturally — this will be read aloud by a voice assistant. Do not include anything expect easily spoken text.\n"

                ),
            },
            {
                "role": "user",
                "content": (
                    f"Who I'm looking for: '{sender_name}'\n\n"
                    f"Recent emails:\n{formatted_emails}"
                )
            }
        ],
        "temperature": 0.0,
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        result = response.json()['choices'][0]['message']['content'].strip()
        logger.info(f"Sender email summary generated successfully for '{sender_name}'")
        return result
    else:
        logger.error(f"GROQ API error: {response.status_code} - {response.text}")
        return f"Sorry, I had trouble checking your emails for messages from {sender_name}."


def extract_verification_code(emails: dict) -> str:
    """
    Scans a batch of recent emails and extracts the most recent verification
    code, OTP, or one-time password for Alexa to read aloud.

    Args:
        emails: Dict of recent emails from get_recent_all_emails(), keyed by
                Gmail message ID. Each value contains: from, subject, body.

    Returns:
        A voice-ready string with the code (e.g. "Your verification code from
        Google is 4 8 3 2 1 9."), or a graceful fallback if none is found.
    """
    if not emails:
        logger.info("No emails passed to extract_verification_code")
        return "I couldn't find any recent emails with a verification code."

    formatted_emails = ""
    for i, email_data in enumerate(emails.values(), 1):
        formatted_emails += (
            f"[Email {i}]\n"
            f"From: {email_data['from']}\n"
            f"Subject: {email_data['subject']}\n"
            f"Body: {email_data['body']}\n"
            f"---\n"
        )

    logger.info(f"Calling GROQ API to extract verification code from {len(emails)} emails")
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
                    "You are a voice assistant that finds verification codes in emails. "
                    "Search the provided emails for a verification code, OTP, one-time password, "
                    "confirmation code, or security code.\n\n"
                    "RULES:\n"
                    "1. Find the most relevant code (typically 4-8 digits, but may be alphanumeric).\n"
                    "2. Respond with a single spoken sentence like: "
                    "'Your verification code from [Sender] is [digits spoken with spaces between each digit].'\n"
                    "   Example: 'Your verification code from Google is 4 8 3 2 1 9.'\n"
                    "3. Insert a space between every digit/character so Alexa reads them individually.\n"
                    "4. If multiple codes are found, use the one from the most recent or most relevant email.\n"
                    "5. If no verification code is found in any email, respond with exactly: "
                    "'I couldn't find a verification code in your recent emails.'\n"
                    "6. Output ONLY the spoken sentence. No preamble, no extra text."
                ),
            },
            {
                "role": "user",
                "content": formatted_emails
            }
        ],
        "temperature": 0.0,
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        result = response.json()['choices'][0]['message']['content'].strip()
        logger.info("Verification code extracted successfully")
        return result
    else:
        logger.error(f"GROQ API error: {response.status_code} - {response.text}")
        return "Sorry, I had trouble checking your emails for a verification code."


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


def _generate_single_draft(recipient_name: str, email_description: str, system_prompt: str, temperature: float) -> str | None:
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": GENERATION_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Recipient: {recipient_name}\nMessage: {email_description}"}
        ],
        "temperature": temperature,
        "max_tokens": 500
    }
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
        logger.error(f"Draft generation API error: {response.status_code} - {response.text}")
        return None
    except Exception as e:
        logger.error(f"Exception in _generate_single_draft: {e}", exc_info=True)
        return None


def _select_best_draft(drafts: list, recipient_name: str, email_description: str) -> str:
    for draft in drafts:
        print(f"Draft option:\n{draft}\n{'-'*40}")
    
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    drafts_block = "\n\n---\n\n".join(f"Draft {i + 1}:\n{d}" for i, d in enumerate(drafts))
    data = {
        "model": REASONING_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are evaluating email drafts. Select the single best one using this rubric:\n"
                    "1. INTENT MATCH: Fully and accurately addresses the user's request\n"
                    "2. TONE: Appropriate for the recipient and context\n"
                    "3. QUALITY: Natural, polished, no awkward phrasing\n"
                    "4. NO ARTIFACTS: No placeholders like [Name] or [Date], no subject line, no preamble\n\n"
                    "Output ONLY the draft number (e.g. '1', '2', or '3'). No explanation."
                )
            },
            {
                "role": "user",
                "content": (
                    f"User's request: email to '{recipient_name}' — '{email_description}'\n\n"
                    f"{drafts_block}\n\n"
                    "Best draft number:"
                )
            }
        ],
        "temperature": 0.0,
    }
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=data)
        if response.status_code == 200:
            raw = response.json()["choices"][0]["message"]["content"].strip()
            for char in raw:
                if char.isdigit():
                    idx = int(char) - 1
                    if 0 <= idx < len(drafts):
                        logger.info(f"Selected draft {char} of {len(drafts)}")
                        return drafts[idx]
        logger.error(f"Draft selection failed: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Exception in _select_best_draft: {e}", exc_info=True)
    return drafts[0]


def generate_draft(recipient_name: str, email_description: str) -> str:
    """
    Generates three draft variants in parallel (balanced, concise, warm) then
    uses the reasoning model to select the best one against a quality rubric.
    """
    logger.info(f"Generating draft email for {recipient_name}: {email_description}")

    base_rules = (
        "Output ONLY the text of the email. "
        "STRICT RULES:\n"
        "1. NO PREAMBLE: Start directly with 'Hi [Name],' or 'Dear [Name],'.\n"
        "2. NO SUBJECT LINE: Do not include a subject line or 'Subject:' header.\n"
        "3. NO PLACEHOLDERS: Never use brackets like '[Your Name]' or '[Date]'.\n"
        "4. SIGN-OFF: End with a professional closing like 'Best,' or 'Thanks,' but DO NOT include a name after it.\n"
        "5. FORMATTING: Use clear paragraph breaks (\\n\\n)."
    )

    draft_configs = [
        # Variant 1: balanced, professional
        (
            "You are a professional email writing assistant. " + base_rules,
            0.4
        ),
        # Variant 2: concise and direct
        (
            "You are a professional email writing assistant who prizes being clear and concise. "
            "Write the most concise version that still fully conveys the message while still adding necessary context. " + base_rules,
            0.4
        ),
        # Variant 3: warm and natural
        (
            "You are a professional email writing assistant. "
            "Write in a warm, natural tone that sounds like a real person rather than a formal template. " + base_rules,
            0.7
        ),
    ]

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(_generate_single_draft, recipient_name, email_description, prompt, temp)
            for prompt, temp in draft_configs
        ]
        results = [f.result() for f in futures]

    valid_drafts = [d for d in results if d is not None]

    if not valid_drafts:
        logger.error("All parallel draft generation attempts failed")
        return "Error generating draft: all generation attempts failed"

    if len(valid_drafts) == 1:
        logger.info("Only one draft generated successfully, skipping selection")
        return valid_drafts[0]

    logger.info(f"Generated {len(valid_drafts)} drafts, selecting best via reasoning model")
    return _select_best_draft(valid_drafts, recipient_name, email_description)
    

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


