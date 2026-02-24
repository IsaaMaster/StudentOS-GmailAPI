import os, dotenv, requests

dotenv.load_dotenv()

ACCESS_TOKEN = os.getenv("GMAIL_ACCESS_TOKEN")
GROQ_API_URL = os.getenv("GROQ_API_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GENERATION_MODEL = os.getenv("GENERATION_MODEL")

def summarize_emails(email_content):
    if not email_content or "no unread emails" in email_content:
        return "You have no new emails. Enjoy your day!"

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}   
    data = {
        "model": GENERATION_MODEL,
        "messages": [
            {
                "role": "system", 
                "content": (
                    "You are a minimalist voice assistant briefing a student. "
                    "Provide a single, fluid paragraph containing all updates (Less than 100 words). "
                    "CRITICAL: Use conjunctions like 'while', 'and', or 'also' to link different emails into a natural spoken flow. "
                    "Avoid choppy, short sentences. Get straight to the news without a preamble. "
                    "STRICT RULES: No lists, no special characters, no transaction IDs, no links, and NO announcement of the summary. "
                    "Use only words meant to be spoken aloud. "
                    "Avoid run-on sentences."
                    "Example: 'The Dean invited you to a social this Friday, and your Amazon package has arrived.'"
                ),
            }, 
            {
                "role": "user", 
                "content": f"Summarize these emails into one smooth spoken update:\n\n{email_content}"
            }
        ],
        "temperature": 0.3, # Slight increase from 0.0 helps the model find better "flow" words
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content'] 
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return "Sorry, I had trouble summarizing your emails."


def generate_draft(recipient_name: str, email_description: str) -> str:
    """
    Generates a draft email based on the recipient and description provided.
    """
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
                    "You are a professional writing assistant for a student. "
                    "Do no include any preamble annoucing the draft at all. Start the response with a greeting or the body text directly. "
                    "Your task is to write a clear, polite, and concise email body. "
                    "STRICT RULES: Do not include a subject line. Do not include a preamble like 'Certainly!' or 'Here is your draft'. "
                    "DO NOT use placeholders like '[Your Name]'. Use a natural, friendly tone."
                    "Do not sign the email with a name."
                )
            },
            {
                "role": "user",
                "content": f"Write an email to {recipient_name}. The core message is: {email_description}."
            }
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=data)
    
    if response.status_code == 200:
        result = response.json()
        return True, result["choices"][0]["message"]["content"].strip()
    else:
        return False, f"Error: {response.status_code}, {response.text}"
    

def generate_reply(thread_body: str, recipient_name: str, reply_description: str) -> str:
    """
    Generates a reply email based on the thread body and description provided.
    """
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
                    "You are a professional writing assistant for a student. "
                    "Your task is to write a polite and concise email reply based on a provided thread. "
                    "STRICT RULES: \n"
                    "1. No preamble (e.g., 'Here is your reply'). Start with the greeting.\n"
                    "2. Do not include a subject line.\n"
                    "3. DO NOT use placeholders like '[Your Name]'.\n"
                    "4. Do not sign the email with a name.\n"
                    "5. Ensure the tone matches the previous thread but prioritize the user's specific reply instructions."
                )
            },
            {
                "role": "user",
                "content": (
                    f"--- PREVIOUS THREAD CONTEXT ---\n{thread_body}\n\n"
                    f"--- REPLY INSTRUCTIONS ---\n"
                    f"Recipient: {recipient_name}\n"
                    f"My Intent: {reply_description}\n\n"
                    f"Write the reply now:"
                )
            }
        ],
        "temperature": 0.7,
        "max_tokens": 600
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=data)
    
    if response.status_code == 200:
        result = response.json()
        return True, result["choices"][0]["message"]["content"].strip()
    else:
        return False, f"Error: {response.status_code}, {response.text}"


