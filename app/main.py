from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from matplotlib.patheffects import Normal
from app.intent_reasoning import mapIntent, parseArguments
from app.gmail_services import get_unread, get_user_first_name, upsert_draft, upsert_reply, get_emails, get_recent_all_emails
from app.generation_layer import summarize_emails, generate_draft, generate_reply, prioritized_insights, extract_verification_code, summarize_sender_emails
from app.gmail_reasoning import find_reply_match
from app.demo_data import MOCK_EMAILS
from app.utils import calculate_seconds
from collections import defaultdict
from contextlib import asynccontextmanager
from posthog import Posthog, new_context, identify_context
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import atexit
import hashlib
import os
import time
from dotenv import load_dotenv
import logging


load_dotenv()

ACCESS_TOKEN = os.getenv("GMAIL_ACCESS_TOKEN")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

posthog_client = Posthog(
    api_key=os.getenv("POSTHOG_API_KEY"),
    host=os.getenv("POSTHOG_HOST", "https://us.i.posthog.com"),
    enable_exception_autocapture=True,
)
atexit.register(posthog_client.shutdown)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    posthog_client.flush()


app = FastAPI(title="StudentOS API", lifespan=lifespan)

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


intent_arguments = {
    "gmail_summarize": ["lookback_period_units", "lookback_period_value"],
    "gmail_draft": ["recipient_name", "email_description"],
    "gmail_reply": ["reply_recipient_name", "email_description"],
    "gmail_verification_code": [],
    "gmail_check_sender": ["sender_name"]}


@app.get("/gmail/{command}")
def read_root(command: str, authorization: str = Header(None)):
    logger.info(f"Received command: {command}")

    if not authorization:
        logger.warning("Missing or invalid authorization header")
        return "Please link your Gmail account in the Alexa app."

    access_token = authorization.split(" ")[1]
    user_id = hashlib.sha256(access_token.encode()).hexdigest()[:16]

    with new_context():
        identify_context(user_id)
        posthog_client.capture("command received", properties={"command_length": len(command)})

        try:
            intent = mapIntent(command)
            logger.info(f"Mapped intent: {intent}")
        except Exception as e:
            logger.error(f"Error mapping intent: {e}", exc_info=True)
            return "Sorry, I'm having trouble reaching the server. Please try again later."

        if intent == "none":
            logger.info("Intent classified as 'none'")
            posthog_client.capture("intent mapping failed", properties={"command_length": len(command)})
            return "Sorry, I couldn't understand your command."

        posthog_client.capture("intent mapped", properties={"intent": intent})

        arguments = {}
        if intent in intent_arguments:
            try:
                arguments = parseArguments(command, intent)
                logger.info(f"Parsed arguments: {arguments}")
            except Exception as e:
                logger.error(f"Error parsing arguments for {intent}: {e}", exc_info=True)
                return "There's a problem with the server. Please try again later."

        try:
            result = executeCommand(intent, arguments, access_token)
            logger.info(f"Command executed successfully for intent: {intent}")
            return result
        except Exception as e:
            logger.error(f"Unhandled error in executeCommand for intent {intent}: {e}", exc_info=True)
            return "Sorry, I'm having trouble reaching the server. Please try again later."


def executeCommand(intent: str, arguments: dict, access_token = ACCESS_TOKEN) -> str:
    if intent == "gmail_summarize":
        logger.info("Executing gmail_summarize")
        try:
            hours_back = calculate_seconds(arguments["lookback_period_value"], arguments["lookback_period_units"])/3600 if "lookback_period_units" in arguments and "lookback_period_value" in arguments else 12
            emails = get_emails(hours_back=hours_back, access_token=access_token)
            logger.info(f"Retrieved {len(emails)} emails")
            if len(emails) == 0:
                logger.info("No unread emails found")
                return f"Sorry, I couldn't find any emails from the last {arguments['lookback_period_value']} {arguments['lookback_period_units']}." 
        
        except Exception as e:
            logger.error(f"Error retrieving unread emails: {e}", exc_info=True)
            return f"There's a problem with the Gmail server. I couldn't retrieve your emails. Please try again later."

        try:
            summary = prioritized_insights(emails)
            logger.info("Email summary generated successfully")
            posthog_client.capture("email summarized", properties={"email_count": len(emails), "hours_back": hours_back})
            return summary
        except Exception as e:
            logger.error(f"Error summarizing emails: {e}", exc_info=True)
            return "Sorry, I'm having trouble reaching the server. Please try again later."

    elif intent == "gmail_draft":
        logger.info(f"Executing gmail_draft with arguments: {arguments}")
        try:
            draft = generate_draft(arguments['recipient_name'], arguments['email_description'])
            logger.debug(f"Generated draft for {arguments['recipient_name']}")

            success, result = upsert_draft(draft, access_token=access_token)
            if success:
                logger.info(f"Draft created successfully: {result}")
                posthog_client.capture("draft created")
                return "Draft created successfully."
            else:
                logger.error(f"Failed to upsert draft: {result}")
                return "Sorry, I was unable to create the draft. Please try again later."
        except Exception as e:
            logger.error(f"Error in gmail_draft: {e}", exc_info=True)
            return "Sorry, I was unable to create the draft. Please try again later."

    elif intent == "gmail_check_sender":
        logger.info(f"Executing gmail_check_sender with arguments: {arguments}")
        sender_name = arguments.get("sender_name", "")
        if not sender_name:
            return "I didn't catch who you're looking for. Please try again."
        try:
            emails = get_emails(hours_back=72, max_results=15, body_max_length=800, access_token=access_token)
            logger.info(f"Retrieved {len(emails)} emails for sender check")
        except Exception as e:
            logger.error(f"Error retrieving emails for sender check: {e}", exc_info=True)
            return "There's a problem with the Gmail server. I couldn't retrieve your emails. Please try again later."

        try:
            result = summarize_sender_emails(emails, sender_name)
            logger.info(f"Sender check completed for '{sender_name}'")
            posthog_client.capture("sender checked")
            return result
        except Exception as e:
            logger.error(f"Error summarizing sender emails: {e}", exc_info=True)
            return f"Sorry, I had trouble checking your emails. Please try again."

    elif intent == "gmail_verification_code":
        logger.info("Executing gmail_verification_code")
        try:
            emails = get_recent_all_emails(minutes_back=10, access_token=access_token)
            logger.info(f"Retrieved {len(emails)} recent emails for verification code search")
        except Exception as e:
            logger.error(f"Error retrieving recent emails: {e}", exc_info=True)
            return "There's a problem with the Gmail server. I couldn't retrieve your emails. Please try again later."

        try:
            result = extract_verification_code(emails)
            logger.info("Verification code extraction completed")
            posthog_client.capture("verification code found")
            return result
        except Exception as e:
            logger.error(f"Error extracting verification code: {e}", exc_info=True)
            return "Sorry, I had trouble finding your verification code. Please try again."

    elif intent == "gmail_reply":
        logger.info(f"Executing gmail_reply with arguments: {arguments}")
        try:
            emails = get_unread(hours_back=72, max_results=8, access_token=access_token)
            logger.info(f"Retrieved {len(emails)} recent emails for reply matching")
        except Exception as e:
            logger.error(f"Error retrieving emails for reply: {e}", exc_info=True)
            return f"There's a problem with the Gmail server. I couldn't retrieve your emails. Please try again later."

        try:
            # Pass a compact version to find_reply_match — full bodies aren't needed to identify
            # the right thread. A short snippet covers the disambiguation case where the same
            # sender has multiple emails with similar subjects.
            compact_emails = {
                msg_id: {'from': data['from'], 'subject': data['subject'], 'snippet': data['body'][:200]}
                for msg_id, data in emails.items()
            }
            best_match_id = find_reply_match(compact_emails, arguments['reply_recipient_name'], arguments['email_description'])
            logger.debug(f"Found best match email ID: {best_match_id}")

            if best_match_id == 'none':
                logger.info("No suitable email found for reply")
                return "I couldn't find a matching email to reply to. Please try again."

            reply = generate_reply(emails[best_match_id]['body'], arguments['reply_recipient_name'], arguments['email_description'])
            logger.debug(f"Generated reply to {arguments['reply_recipient_name']}: {reply}")

            success, result = upsert_reply(reply, best_match_id, rfc_id=emails[best_match_id]['rfc-id'], subject=emails[best_match_id]['subject'], to_email=emails[best_match_id]['from-email'], access_token=access_token)
            if success:
                logger.info(f"Reply created successfully: {result}")
                posthog_client.capture("reply created")
                return "Reply created successfully."
            else:
                logger.error(f"Failed to upsert reply: {result}")
                return "Sorry, I was unable to create the reply. Please try again later."
        except Exception as e:
            logger.error(f"Error in gmail_reply: {e}", exc_info=True)
            return "Sorry, I was unable to create the reply. Please try again later."



# ── Demo endpoints ───────────────────────────────────────────────────────────
# Public, no auth. Uses MOCK_EMAILS instead of Gmail API so every
# generation function works unchanged — only the data source differs.

_demo_rate: dict[str, list[float]] = defaultdict(list)
_DEMO_LIMIT = 10  # requests per IP per hour


class DemoChatRequest(BaseModel):
    command: str


@app.get("/demo/seed")
def demo_seed():
    """Returns frontend-safe mock inbox (strips internal rfc-id field)."""
    return {
        "emails": [
            {
                "id":         eid,
                "from":       data["from"],
                "from_email": data["from-email"],
                "date":       data["date"],
                "subject":    data["subject"],
                "body":       data["body"],
                "snippet":    data["snippet"],
            }
            for eid, data in MOCK_EMAILS.items()
        ]
    }


@app.post("/demo/chat")
def demo_chat(req: DemoChatRequest, request: Request):
    ip  = request.client.host
    now = time.time()
    _demo_rate[ip] = [t for t in _demo_rate[ip] if now - t < 3600]
    if len(_demo_rate[ip]) >= _DEMO_LIMIT:
        with new_context():
            identify_context(ip)
            posthog_client.capture("demo rate limit hit")
        return {"response": "Demo limit reached — please try again in an hour.", "mutation": None}
    _demo_rate[ip].append(now)

    command = req.command.strip()
    if not command:
        return {"response": "Please type a command to try.", "mutation": None}

    with new_context():
        identify_context(ip)

        try:
            intent = mapIntent(command)
            logger.info(f"Demo intent: {intent}")
        except Exception as e:
            logger.error(f"Demo intent mapping failed: {e}", exc_info=True)
            return {"response": "Sorry, I'm having trouble right now. Please try again.", "mutation": None}

        posthog_client.capture("demo command used", properties={"intent": intent, "command_length": len(command)})

        if intent == "none":
            return {
                "response": (
                    "Sorry, I couldn't understand that. "
                    "Try: 'Summarize my emails', 'Draft an email to Professor Chen', or 'What's my verification code?'"
                ),
                "mutation": None,
            }

        try:
            args = parseArguments(command, intent) if intent in intent_arguments else {}
            logger.info(f"Demo args: {args}")
        except Exception as e:
            logger.error(f"Demo argument parsing failed: {e}", exc_info=True)
            return {"response": "I had trouble parsing that request. Please try again.", "mutation": None}

        try:
            if intent == "gmail_summarize":
                hours_back = calculate_seconds(
                    args.get("lookback_period_value", 12),
                    args.get("lookback_period_units", "hours")
                ) / 3600
                filtered = _demo_filter_emails(MOCK_EMAILS, hours_back)
                if not filtered:
                    return {
                        "response": f"I didn't find any emails from the last {args.get('lookback_period_value', 12)} {args.get('lookback_period_units', 'hours')}.",
                        "mutation": None,
                    }
                return {"response": prioritized_insights(filtered), "mutation": None}

            elif intent == "gmail_check_sender":
                sender = args.get("sender_name", "")
                return {"response": summarize_sender_emails(MOCK_EMAILS, sender), "mutation": None}

            elif intent == "gmail_verification_code":
                return {"response": extract_verification_code(MOCK_EMAILS), "mutation": None}

            elif intent == "gmail_draft":
                recipient   = args.get("recipient_name", "")
                description = args.get("email_description", "")
                body        = generate_draft(recipient, description)
                draft = {
                    "id":        f"d_{int(time.time())}",
                    "to":        recipient,
                    "subject":   _demo_infer_subject(recipient),
                    "body":      body,
                    "timestamp": "just now",
                }
                posthog_client.capture("demo draft created")
                return {"response": "Draft created successfully.", "mutation": {"type": "draft_created", "draft": draft}}

            elif intent == "gmail_reply":
                recipient   = args.get("reply_recipient_name", "")
                description = args.get("email_description", "")
                compact = {
                    mid: {"from": d["from"], "subject": d["subject"], "snippet": d["snippet"]}
                    for mid, d in MOCK_EMAILS.items()
                }
                match_id = find_reply_match(compact, recipient, description)
                if match_id == "none" or match_id not in MOCK_EMAILS:
                    return {"response": "I couldn't find a matching email to reply to. Please try again.", "mutation": None}
                body             = generate_reply(MOCK_EMAILS[match_id]["body"], recipient, description)
                original_subject = MOCK_EMAILS[match_id]["subject"]
                subject          = original_subject if original_subject.startswith("Re:") else f"Re: {original_subject}"
                draft = {
                    "id":        f"d_{int(time.time())}",
                    "to":        recipient,
                    "subject":   subject,
                    "body":      body,
                    "timestamp": "just now",
                }
                posthog_client.capture("demo reply created")
                return {"response": "Reply draft created successfully.", "mutation": {"type": "draft_created", "draft": draft}}

        except Exception as e:
            logger.error(f"Demo execution failed for intent {intent!r}: {e}", exc_info=True)
            return {"response": "Sorry, something went wrong. Please try again.", "mutation": None}

    return {"response": "Sorry, I couldn't handle that command.", "mutation": None}


def _demo_filter_emails(emails: dict, hours_back: float) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    return {
        mid: data for mid, data in emails.items()
        if parsedate_to_datetime(data["date"]) >= cutoff
    }


def _demo_infer_subject(recipient_name: str) -> str:
    """Returns the subject of the first mock email whose sender contains the recipient name."""
    name_lower = recipient_name.lower()
    for email_data in MOCK_EMAILS.values():
        if any(part in email_data["from"].lower() for part in name_lower.split() if len(part) > 2):
            return email_data["subject"]
    return "New Message"


#Demo Spring 2
"""Phonetically Challenging Intent"""
#print(executeCommand("gmail_summarize", {"lookback_period_units": "hours", "lookback_period_value": 12}))

""""Time Argument Parsing for Summarization"""
#print(parseArguments("Summarize my unread emails from the last 3 days", "gmail_summarize"))

"""Reply to Email"""
#print(executeCommand("gmail_reply", {"reply_recipient_name": "Connor", "email_description": "telling him that I'll be able to make the lunch meeting on Friday"}))

#Sign up Page
#What's Next? 



# Demo Sprint 1
""" Normal Intent Reasoning"""
#print(mapIntent("Summarize my unread emails"))

""" More Complex Intent Reasoning""" 
#print(mapIntent("Get the tea from my inbox"))

"""" Argument Parsing """
#print(parseArguments("Draft an email to Professor Smith asking about the upcoming assignment", "gmail_draft"))

""" Summarize Emails"""
#print(summarize_emails(get_unread()))

""" Draft Email """
#print(executeCommand("gmail_draft", {"recipient_name": "Dr. Keaney", "email_description": "asking her if she wants to get lunch at the DC this Friday"}))

""" Reply to Email """
#print(executeCommand("gmail_summarize", {"lookback_period_units": "hours", "lookback_period_value": 48}))

""" Extract Verification Code """
print(executeCommand("gmail_verification_code", {}))       