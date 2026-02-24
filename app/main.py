from fastapi import FastAPI
from app.intent_reasoning import mapIntent, parseArguments
from app.gmail_services import get_unread, upsert_draft, upsert_reply
from app.generation_layer import summarize_emails, generate_draft, generate_reply
from app.gmail_reasoning import find_reply_match

app = FastAPI(title="StudentOS API")


intent_aruguments = {
    "gmail_draft": ["recipient_name", "email_description"],
    "gmail_reply": ["reply_recipient_name", "email_description"]}


from fastapi import Header, HTTPException

@app.get("/gmail/{command}")
def read_root(command: str, authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        return "Please link your Gmail account in the Alexa app."
    
    access_token = authorization.split(" ")[1]

    intent = mapIntent(command)
    
    if intent == "none":
        return "Sorry, I couldn't understand your command."

    arguments = {}
    if intent in intent_aruguments:
        arguments = parseArguments(command, intent)
    
    try: 
        result = executeCommand(intent, arguments, access_token)
        return result
    except Exception as e:
        print(f"Server Error: {e}")
        return "There's a problem with the server. Please try again later."   


def executeCommand(intent: str, arguments: dict, access_token: str) -> str:
    if  intent == "gmail_summarize":
        try: 
            emails = get_unread(access_token=access_token)
        except Exception as e:
            print(f"Gmail Error: {e}")
            return f"There's a problem with the Gmail server. I couldn't retrieve your emails. Please try again later."
        
        aggregated_emails = ""
        for email in emails.values():
            aggregated_emails += email["from"] + ": " + email['body'] + "\n---\n"
        return summarize_emails(aggregated_emails)
    
    elif intent == "gmail_draft":
        draft = generate_draft(arguments['recipient_name'], arguments['email_description'])
        success, result = upsert_draft(draft, access_token=access_token)
        if success:
            return "Draft created successfully."
        else:
            return "I was unable to create the draft. Please try again later."
    
    elif intent == "gmail_reply":
        try: 
            emails = get_unread(hours_back=72, max_results=8, access_token=access_token)
        except Exception as e:
            print(f"Gmail Error: {e}")
            return f"There's a problem with the Gmail servier. I couldn't retrieve your emails. Please try again later."

        best_match_id = find_reply_match(emails, arguments['reply_recipient_name'], arguments['email_description'])
        reply = generate_reply(emails[best_match_id], arguments['reply_recipient_name'], arguments['email_description'])
        success, result = upsert_reply(reply, best_match_id, rfc_id=emails[best_match_id]['rfc-id'], subject=emails[best_match_id]['subject'], to_email=emails[best_match_id]['from-email'], access_token=access_token)
        if success:
            return "Reply created successfully."
        else:
            return "I was unable to create the reply. Please try again later."



# Demo
## Normal Intent
#print(mapIntent("Summarize my unread emails"))

## More Complex Intent
#print(mapIntent("Get the tea from my inbox"))

## Argument Parsing
#print(parseArguments("Draft an email to Professor Smith asking about the upcoming assignment", "gmail_draft"))

## Summarize Emails
#print(summarize_emails(get_unread()))

## Draft Email
#print(upsert_draft(generate_draft("Professor Smith", "asking for an extension on the upcoming assignment because I have been sick")))