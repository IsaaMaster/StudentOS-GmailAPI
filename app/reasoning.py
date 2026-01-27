import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

GROQ_API_URL = os.getenv("GROQ_API_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

intent_descriptions = {
    "gmail_summarize": "Summarize unread Emails",
    "gmail_draft": "Draft an Email in a completely new email chain",
    "gmail_reply": "Reply to Email in a current email chain",
    "none" : "Select this if none of the other actions are applicable"
}

intent_aruguments = {
    "gmail_draft": ["email description"],
    "gmail_reply": ["reply recipient (name)", "email description"]}

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
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a command classifier for a student voice assistant. "
                    "Your task is to output EXACTLY one of the provided action keys and NOTHING else. "
                    "Do not include conversational text, do not include quotes, and do not explain your reasoning."
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
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": "You are a helpful assistant that outputs only valid JSON."
            },
            {
                "role": "user",
                "content": f"Given the user command '{command}', extract arguments for the intent '{intent}': {intent_aruguments.get(intent,[])}. Return as a JSON object with only the 2 keys: {intent_aruguments.get(intent,[])}. If an argument is not present in the command, return an empty string for that argument."
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
    



