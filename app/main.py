from fastapi import FastAPI
from matplotlib.patheffects import Normal
from app.intent_reasoning import mapIntent, parseArguments
from app.gmail_services import get_unread, get_user_first_name, upsert_draft, upsert_reply, get_emails
from app.generation_layer import summarize_emails, generate_draft, generate_reply, prioritized_insights
from app.gmail_reasoning import find_reply_match
from app.utils import calculate_seconds
import os
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

app = FastAPI(title="StudentOS API")


intent_arguments = {
    "gmail_summarize": ["lookback_period_units", "lookback_period_value"],
    "gmail_draft": ["recipient_name", "email_description"],
    "gmail_reply": ["reply_recipient_name", "email_description"]}


from fastapi import Header, HTTPException

@app.get("/gmail/{command}")
def read_root(command: str, authorization: str = Header(None)):
    logger.info(f"Received command: {command}")

    if not authorization:
        logger.warning("Missing or invalid authorization header")
        return "Please link your Gmail account in the Alexa app."

    access_token = authorization.split(" ")[1]

    try:
        intent = mapIntent(command)
        logger.info(f"Mapped intent: {intent}")
    except Exception as e:
        logger.error(f"Error mapping intent: {e}", exc_info=True)
        return "Sorry, I'm having trouble reaching the server. Please try again later."

    if intent == "none":
        logger.info("Intent classified as 'none'")
        return "Sorry, I couldn't understand your command."

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
                return "Draft created successfully."
            else:
                logger.error(f"Failed to upsert draft: {result}")
                return "Sorry, I was unable to create the draft. Please try again later."
        except Exception as e:
            logger.error(f"Error in gmail_draft: {e}", exc_info=True)
            return "Sorry, I was unable to create the draft. Please try again later."

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
                return "Reply created successfully."
            else:
                logger.error(f"Failed to upsert reply: {result}")
                return "Sorry, I was unable to create the reply. Please try again later."
        except Exception as e:
            logger.error(f"Error in gmail_reply: {e}", exc_info=True)
            return "Sorry, I was unable to create the reply. Please try again later."



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
#print(executeCommand("gmail_summarize", {"lookback_period_units": "days", "lookback_period_value": 15}))
