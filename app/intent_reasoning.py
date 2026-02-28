import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

GROQ_API_URL = os.getenv("GROQ_API_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
REASONING_MODEL = os.getenv("REASONING_MODEL")

intent_descriptions = {
    "gmail_summarize": "Summarize unread Emails",
    "gmail_draft": "Draft an Email in a completely new email chain",
    "gmail_reply": "Reply to Email in a current email chain",
    "none": "Select this if none of the other actions are applicable"
}

intent_arguments = {
    "gmail_summarize": ["lookback_period_units", "lookback_period_value"],
    "gmail_draft": ["recipient_name", "email_description"],
    "gmail_reply": ["reply_recipient_name", "email_description"]}

def mapIntent(command: str, intent_descriptions = intent_descriptions) -> str:
    """
    Maps user intent to a specific action using Groq's API. 
    
    :param command: User command as given by the a command given through Alexa
    :type command: str
    :param action: A dictionary representing the action to be performed
    :type action: dict
    :return: The mapped action that corresponds to the user intent
    :rtype: str
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}",
    }   
    data = {
        "model": REASONING_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a command classifier for a student voice assistant. "
                    "Your task is to output EXACTLY one of the provided action keys and NOTHING else. "
                    "Do not include conversational text, do not include quotes, and do not explain your reasoning."
                    "Watch out for phenetic errors like 'summer eyes' which actually means 'summarize', or 'read play' which actually means 'reply'." 
                )
            },
            {
                "role": "user",
                "content": (
                    f"Valid Action Keys: {list(intent_descriptions.keys())}\n"
                    f"Action Descriptions: {intent_descriptions}\n"
                    f"Command: '{command}'\n"
                    "Classification:"
                )
            }
        ],
        "temperature": 0.0, # CRITICAL: Set temperature to 0 for deterministic mapping
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        result = response.json()
        raw_output = result["choices"][0]["message"]["content"]
        
        # SANITIZATION: Remove quotes, whitespace, and periods
        clean_output = raw_output.strip().replace("'", "").replace('"', "").replace(".", "")
        
        # If it returned a full sentence anyway, try to find the key inside it
        for key in intent_descriptions.keys():
            if key in clean_output:
                return key
                
        return clean_output
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")
    

def parseArguments(command : str, intent : str) -> dict:
    """
    Given an command, and intent, parses the neccesssary arugments for that intent. 
    
    :param command: User command as given by the a command given through Alexa
    :type command: str
    :param intent: The mapped intent for the command (e.g "gmail_summarize")
    :type intent: str
    :return: The parsed arguments for the intent
    :rtype: dict
    """

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}",
    }

    data = {
        "model": REASONING_MODEL,
        "messages": [
            {
                "role": "system", 
                "content": (
                    "You are a strict semantic parser. You MUST output a JSON object using the exact keys provided by the user.\n\n"
                    "RULES:\n"
                    "1. KEY CASING: Use only the exact casing provided in the 'Required JSON Keys'.\n"
                    "2. LOOKBACK_PERIOD_VALUE: Extract only the digit/number (e.g., '22' or '5'). \n"
                    "   - If no number is mentioned but a unit is (e.g., 'the last hour'), use '1'.\n"
                    "   - Return as an INTEGER or a numeric string.\n"
                    "3. LOOKBACK_PERIOD_UNITS: Extract the time unit (e.g., 'minutes', 'hours', 'days').\n"
                    "   - Always use the plural form: 'minutes', 'hours', or 'days'.\n"
                    "4. RECIPIENT_NAME: Extract the person or entity. Strip lead-in words like 'to' or 'send to'.\n"
                    "5. EMAIL_DESCRIPTION: Keep exact phrasing of the message. Do not summarize or change perspective.\n"
                    "6. EMPTY VALUES: Use '' for missing text. IMPORTANT: Default lookback_period_value to 24 and units to 'hours' if unspecified.\n"
                    "7. OUTPUT: Return ONLY valid JSON. No preamble, no markdown."
                )
            },
            {
                "role": "user",
                "content": (
                    f"User Command: '{command}'\n"
                    f"Intent: '{intent}'\n"
                    f"Required JSON Keys: {list(intent_arguments.get(intent, []))}\n"
                    "Target JSON Schema: Return an object with these exact keys."
                )
            }
        ],
        "response_format": {"type": "json_object"} 
    }
    response = requests.post(GROQ_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        result = response.json()
        # The content is returned as a STRING that looks like JSON
        raw_content = result["choices"][0]["message"]["content"]

        return dict(json.loads(raw_content))
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")
    

print(parseArguments("get the tea in my inbox", "gmail_summarize"))