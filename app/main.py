from fastapi import FastAPI
from app.intent_reasoning import mapIntent, parseArguments
from app.gmail_services import get_unread, upsert_draft
from app.generation_layer import summarize_emails, generate_draft

app = FastAPI(title="StudentOS API")

intent_aruguments = {
    "gmail_draft": ["email description"],
    "gmail_reply": ["reply recipient (name)", "email description"]}


@app.get("/gmail/{command}")
def read_root(command: str):
    intent = mapIntent(command)

    arguments = {}
    if intent in intent_aruguments:
        arguments = parseArguments(command, intent)

    executeCommand(intent, arguments)
    return {"intent": intent, "arguments": arguments}

def executeCommand(intent: str, arguments: dict):
    if  intent == "summarize_emails":
        return summarize_emails(get_unread())
    elif intent == "gmail_draft":
        draft = generate_draft(arguments['recipient (name)'], arguments['email description'])
        return upsert_draft(draft)

read_root("Draft an email to Dr. Keaney asking her to get lunch")