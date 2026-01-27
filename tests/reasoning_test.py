import pytest
from app.reasoning import mapIntent, parseArguments


intent_aruguments = {
    "gmail_draft": ["email description"],
    "gmail_reply": ["reply recipient (name)", "email description"]}

@pytest.mark.medium
@pytest.mark.llm
@pytest.mark.parametrize("user_input, expected_endpoint", [
    ("Summarize my emails", "gmail_summarize"),
    ("Write an email to Dr. Keaney asking her to get lunch", "gmail_draft"),
    ("Give me a quick summary of my recent emails", "gmail_summarize"),
    ("Draft an email to my professor about the gassignment", "gmail_draft"),
    ("What's new in my inbox?", "gmail_summarize"),
    ("Compose an email to my boss telling him I can't make it to lunch today", "gmail_draft"),
    ("Reply to Connor telling him that I am available for the meeting", "gmail_reply"),
    ("Repond to Ashwin's email telling him that the interview time works, and that I look forward to it", "gmail_reply"),
    ("Send an email to Mom telling her I'll be gone for the weekend", "gmail_draft"),
    ("Reply to Mike's email about the project update", "gmail_reply"),

])
def test_command_mapping(user_input, expected_endpoint):
    result = mapIntent(user_input)
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
        "Reply to Mike's email about the project update",
        "gmail_reply",
        ["project"]
    ),
])
def test_parse_arguments(command, intent, expected_keywords):
    result = parseArguments(command, intent)
    for arugment in intent_aruguments[intent]:
        assert arugment in result

    for keyword in expected_keywords:
        assert keyword in result["email description"]
    