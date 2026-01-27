from fastapi import FastAPI
from app.reasoning import mapIntent, parseArguments
from app.services import summarizeEmails

app = FastAPI(title="StudentOS API")

@app.get("/gmail/{command}")
def read_root(command: str):
    intent = mapIntent(command)
    arguments = parseArguments(command, intent)
    executeCommand(intent, arguments)
    return {"intent": intent, "arguments": arguments}

def executeCommand(intent: str, arguments: dict):
    if  intent == "summarize_emails":
        return summarizeEmails(arguments)
    # Placeholder for command execution logic
    return {"status": "success", "intent": intent, "arguments": arguments}