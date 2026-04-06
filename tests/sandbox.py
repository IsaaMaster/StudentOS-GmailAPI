from app.generation_layer import summarize_emails, generate_draft, generate_reply, prioritized_insights
for batch_number in range(1, 11):    
    with open(f"tests/mock_data/email_batch_{batch_number}.txt", "r") as f:
        email_content = f.read()
        summary = prioritized_insights(email_content)
        print(summary)