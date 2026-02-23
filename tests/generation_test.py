import pytest
from app.generation_layer import summarize_emails, generate_draft, generate_reply
import os, dotenv, requests

dotenv.load_dotenv()

GROQ_API_URL = os.getenv("GROQ_API_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TESTING_MODEL = os.getenv("VALIDATION_MODEL")

@pytest.mark.medium
@pytest.mark.llm
@pytest.mark.parametrize("email_batch", [
    ("email_batch_1"),
    ("email_batch_2"),
    ("email_batch_3"),
])
def test_summarize_emails(email_batch):
    with open(f"tests/mock_data/{email_batch}.txt", "r") as f:
        email_content = f.read()
        summary = summarize_emails(email_content)
        print(f"Summary for {email_batch}:\n{summary}\n")

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}   
    data = {
        "model": TESTING_MODEL,
        "messages": [
            {
                "role": "system", 
                "content": (
                    "You are a Quality Assurance Judge evaluating voice assistant summaries against a strict set of constraints. "
                    "Evaluate the provided summary based on the following specific criteria derived from the generation prompt."

                    "### THE RUBRIC (1-10):"
                    "- 10: Perfect. Fluid, single paragraph, < 150 words, no preamble, no special characters, no run-ons."
                    "- 8: High Quality. Adheres to all content rules but the 'flow' or conjunction usage could be smoother."
                    "- 6: Passable. Meets word count and avoids forbidden items, but includes a preamble or feels slightly choppy."
                    "- 3: Sub-par. Would very very hard to Alexa to read. Contains prohibited items (links, IDs, special characters) or uses a list/bullet points."
                    "- 1: Total Failure. Over 150 words, uses lists, contains links, or includes significant non-spoken text."

                    "### AUTOMATIC DEDUCTIONS (Mandatory -1 points each):"
                    "1. Preamble inclusion (e.g., 'Here are your emails' or 'I found 3 messages')."
                    "2. Special characters, links, or transaction IDs."
                    "3. Use of bullet points or numbered lists."
                    "4. Run-on sentences that lack proper conjunctions (and/while/also)."

                    "### OUTPUT FORMAT:"
                    "You must respond with a single integer score from 1 to 10 only, no additional text."
                ),
            }, 
            {
                "role": "user", 
                "content": f"Evaluate this summary for a student voice assistant:\n\n{summary}"
            }
        ],
        "temperature": 0.0,
    }
    response = requests.post(GROQ_API_URL, headers=headers, json=data)
    assert response.status_code == 200
    score = int(response.json()['choices'][0]['message']['content'].strip())
    assert score >= 6, f"Summary score too low: {score}"


@pytest.mark.medium
@pytest.mark.llm
@pytest.mark.parametrize("recipient, description", [
    ("Dr. Keaney", "asking her to get lunch"),
    ("Professor Smith", "inquiring about the upcoming assignment"),
    ("Mom", "telling her I'll be gone for the weekend"),
])
def test_generate_draft(recipient, description):
    draft = generate_draft(recipient, description)

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}   
    data = {
        "model": TESTING_MODEL,
        "messages": [
            {
                "role": "system", 
                "content": (
                    "You are a Quality Assurance Judge evaluating email drafts against a strict set of constraints. "
                    "Evaluate the provided draft based on the following specific criteria derived from the generation prompt." 

                    "Note: Greetings (e.g., 'Hi Dr. Keaney,') are acceptable and do not count as preambles."

                    "### THE RUBRIC (1-10):"
                    "- 10: Perfect. Clear, polite, concise, no subject line, no preamble, natural friendly tone."
                    "- 8: High Quality. Adheres to all content rules but could be slightly clearer or more polite."
                    "- 6: Passable. Meets basic requirements but includes a subject line or preamble."
                    "- 3: Sub-par. Lacks clarity, is impolite, or uses an unnatural tone."
                    "- 1: Total Failure. Includes a subject line, preamble, or uses placeholders like '[Your Name]'."       
                
                    "### AUTOMATIC DEDUCTIONS (Mandatory -1 points each):"
                    "1. Subject line inclusion."
                    "2. Preamble inclusion (e.g., 'Certainly!' or 'Here is your draft')."
                    "3. Use of placeholders like '[Your Name]'."
                    "4. Signing the email with a name."

                    "### OUTPUT FORMAT:"
                    "You must respond with a score from 1 to 10 only, no additional text."
                ),
            },
            {
                "role": "user", 
                "content": f"Evaluate this email draft :\n\n{draft} given that the orginal request was to write an email to {recipient} about {description}."
            }
        ],
        "temperature": 0.0,
    }
    response = requests.post(GROQ_API_URL, headers=headers, json=data)
    assert response.status_code == 200
    score = int(response.json()['choices'][0]['message']['content'].strip())
    assert score >= 6, f"Draft score too low: {score}"  


@pytest.mark.medium
@pytest.mark.llm
@pytest.mark.parametrize("email,recipient,description", [
    ("single_email_1", "Tara", "telling her I want to walk with Computer Science"),
    ("single_email_2", "Kaisa", "letting her know I can't make it to the meeting"),
    ("single_email_3", "Jill", "saying thank you for making beach vb courts available")
])
def test_generate_reply(email, recipient, description): 
    with open(f"tests/mock_data/{email}.txt", "r") as f:
        email = f.read()

    reply = generate_reply(email, recipient, description)

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    data = {
        "model": TESTING_MODEL,
        "messages": [
            {
                "role": "system", 
                "content": (
                    "You are a Quality Assurance Judge evaluating email drafts against a strict set of constraints. "
                    "Evaluate the provided draft based on the following specific criteria derived from the generation prompt." 

                    "Note: Greetings (e.g., 'Hi Dr. Keaney,') are acceptable and do not count as preambles."

                    "### THE RUBRIC (1-10):"
                    "- 10: Perfect. Clear, polite, concise, no subject line, no preamble, natural friendly tone."
                    "- 8: High Quality. Adheres to all content rules but could be slightly clearer or more polite."
                    "- 6: Passable. Meets basic requirements but includes a subject line or preamble."
                    "- 3: Sub-par. Lacks clarity, is impolite, or uses an unnatural tone."
                    "- 1: Total Failure. Includes a subject line, preamble, or uses placeholders like '[Your Name]'."       
                
                    "### AUTOMATIC DEDUCTIONS (Mandatory -1 points each):"
                    "1. Subject line inclusion."
                    "2. Preamble inclusion (e.g., 'Certainly!' or 'Here is your draft')."
                    "3. Use of placeholders like '[Your Name]'."
                    "4. Signing the email with a name."

                    "### OUTPUT FORMAT:"
                    "You must respond with a score from 1 to 10 only, no additional text."
                ),
            },
            {
                "role": "user", 
                "content": f"Evaluate this email reply:\n\n{reply} given that the orginal request was to write an email to {recipient} about {description} in response to the following message : {email}."
            }
        ],
        "temperature": 0.0,
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=data)
    assert response.status_code == 200
    score = int(response.json()['choices'][0]['message']['content'].strip())
    assert score >= 6, f"Reply score too low: {score}"
    