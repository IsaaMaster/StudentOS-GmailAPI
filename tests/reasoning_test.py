import pytest
from app.intent_reasoning import mapIntent, parseArguments
import time


intent_aruguments = {
    "gmail_draft": ["recipient_name", "email_description"],
    "gmail_reply": ["reply_recipient_name", "email_description"]}

@pytest.mark.medium
@pytest.mark.llm
@pytest.mark.parametrize("user_input, expected_endpoint", [
    # Standard Commands ---
    ("Summarize my emails", "gmail_summarize"),
    ("Write an email to Dr. Keaney asking her to get lunch", "gmail_draft"),
    ("Give me a quick summary of my recent emails", "gmail_summarize"),
    ("Draft an email to my professor about the assignment", "gmail_draft"),
    ("What's new in my inbox?", "gmail_summarize"),
    ("Compose an email to my boss telling him I can't make it", "gmail_draft"),
    ("Reply to Connor telling him that I am available", "gmail_reply"),
    ("Respond to Ashwin's email telling him the time works", "gmail_reply"),
    ("Send an email to Mom telling her I'll be gone", "gmail_draft"),
    ("Reply to Mike's email about the project update", "gmail_reply"),

    # Phonetic Errors
    ("Summer eyes my inbox", "gmail_summarize"),  
    ("Draft and email to the dean", "gmail_draft"),
    ("Read play to Will about the frisbee game", "gmail_reply"), 
    ("Send a male to Sarah", "gmail_draft"), 
    ("Re-lie to the message from Brian", "gmail_reply"), 
    ("What's in my in-boxer?", "gmail_summarize"), 
    ("Right an email to Steve", "gmail_draft"), 
    ("Got any new emale?", "gmail_summarize"),
    ("Somare eyes my mess ages", "gmail_summarize"),
    ("Send them new em ale to my Mom about the weekend", "gmail_draft"),
    ("Reply to Ashwin's email telling him the thyme works", "gmail_reply"),

    # Slang/Casual Language
    ("Respond to current thread with yes", "gmail_reply"),
    ("Check my mail for me", "gmail_summarize"),
    ("Start a new message to the registrar", "gmail_draft"),
    ("What's up with my mail?", "gmail_summarize"),
    ("Answer the email from the library", "gmail_reply"), 
    ("Brief me on my messages", "gmail_summarize"),
    ("Get me a new email for John", "gmail_draft"),
    ("I need to send a fresh note to the coach", "gmail_draft"),
    ("Give me the tea on my inbox", "gmail_summarize"),
    ("Hit him back and say thanks", "gmail_reply"), 
    ("Make a draft for my TA", "gmail_draft"),
    ("Catch me up on my mail", "gmail_summarize"),
    ("Go back to that thread with a 'will do'", "gmail_reply"),
    ("Shoot an email over to the team", "gmail_draft"),

    # More Complex Commands
    ("I want to reply to the email I just got from my advisor and say thank you", "gmail_reply"),
    ("Can you please summarize everything I haven't read yet from today?", "gmail_summarize"),
    ("Create a totally new email to the pizza place asking for a refund", "gmail_draft"),
    ("Check my unread messages and tell me what they say", "gmail_summarize"),
    ("Tell the person who just emailed me that I'm busy", "gmail_reply"),
    ("Draft a formal letter to the scholarship committee", "gmail_draft"),
    ("Respond to the thread about the senior seminar", "gmail_reply"),
    ("Look at my inbox and give me the highlights", "gmail_summarize"),
    ("Reach out to Dave with a brand new email regarding the keys", "gmail_draft"),
    ("Follow up on that email from earlier", "gmail_reply"),

    # Negative Cases
    ("What time is it right now?", "none"),
    ("Play some music on Spotify", "none"),
    ("Set an alarm for 8am", "none"),
    ("Tell me a joke", "none"),
    ("How is the weather in Santa Barbara?", "none"),
])
def test_command_mapping(user_input, expected_endpoint):
    result = mapIntent(user_input)
    time.sleep(2) # To avoid hitting rate limits
    assert result == expected_endpoint

@pytest.mark.short
@pytest.mark.llm
@pytest.mark.parametrize("user_input, expected_endpoint", [
    ("Can you summarize my unread emails?", "gmail_summarize"),
    ("Draft an email to my professor", "gmail_draft"),
    ("Please reply to Ashwin telling him that I'm available for the meeting", "gmail_reply"),])
def test_command_mapping_short(user_input, expected_endpoint):
    result = mapIntent(user_input)
    assert result == expected_endpoint


@pytest.mark.medium
@pytest.mark.llm
@pytest.mark.short
@pytest.mark.llm
@pytest.mark.parametrize("command, intent, expected_keywords", [
    (
        "Draft an email to the Registrar asking about my graduation status",
        "gmail_draft",
        ["graduation"]
    ),
    (
        "Reply to Professor Ryu and tell him I'll be ten minutes late to the seminar",
        "gmail_reply",
        ["ten", "seminar"]
    ),
    (
        "Right a message to Mom saying I'm coming home for the weekend",
        "gmail_draft",
        ["weekend"]
    ),
    (
        "Read play to the message from Brian with a big thank you",
        "gmail_reply",
        ["thank you"]
    ),
    (
        "Hit up Sarah and ask if she wants to grab coffee at the DC",
        "gmail_draft",
        ["DC", "coffee"]
    ),
    (
        "Hit Mike back and say that sounds like a plan",
        "gmail_reply",
        ["plan"]
    ),
    (
        "Draft a new mail to the coach regarding the practice schedule change",
        "gmail_draft",
        ["practice", "schedule"]
    ),
    (
        "Compose an email to my lab partner asking if they finished the data analysis",
        "gmail_draft",
        ["analysis"]
    ),
    (
        "Reply to the financial aid office saying I sent the documents yesterday",
        "gmail_reply",
        ["document"]
    ),
])
def test_parse_arguments(command, intent, expected_keywords):
    result = parseArguments(command, intent)
    for arugment in intent_aruguments[intent]:
        assert arugment in result

    print(result["email_description"])
    for keyword in expected_keywords:
        assert keyword in result["email_description"]


@pytest.mark.short
@pytest.mark.llm
@pytest.mark.parametrize("command, intent, expected_keywords", [
    (
        "Write an email to Dr. Keaney asking her to get lunch",
        "gmail_draft",
        ["lunch"]
    ),
    (
        "Reply to Ashwin's email telling him that the interview time works, and that I look forward to it",
        "gmail_reply",
        ["interview", "time"]
    ),
    (
        "Reply to Mike's email about the project update telling him that sounds like a plan",
        "gmail_reply",
        ["plan"]
    ),
])
def test_parse_arguments_short(command, intent, expected_keywords):
    result = parseArguments(command, intent)
    for arugment in intent_aruguments[intent]:
        assert arugment in result

    for keyword in expected_keywords:
        assert keyword in result["email_description"].lower()
    