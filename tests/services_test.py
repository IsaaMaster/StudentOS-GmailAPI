import pytest
from app.services import summarize_emails
import os, dotenv, requests

dotenv.load_dotenv()

GROQ_API_URL = os.getenv("GROQ_API_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

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
        "model": "llama-3.3-70b-versatile",
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
                    "- 4: Sub-par. Contains prohibited items (links, IDs, special characters) or uses a list/bullet points."
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
