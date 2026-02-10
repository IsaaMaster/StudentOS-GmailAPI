import base64, re

def get_email_body(payload):
    """Recursively finds the text/plain part of the email and ignores HTML/Attachments."""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data')
                return base64.urlsafe_b64decode(data).decode('utf-8') if data else ""
            elif 'parts' in part: # Nested multipart
                result = get_email_body(part)
                if result: return result
    else:
        data = payload.get('body', {}).get('data')
        return base64.urlsafe_b64decode(data).decode('utf-8') if data else ""
    return ""

def clean_emails(email_body):
    email_body = re.sub(r'\s+', ' ', email_body).strip()  # Remove excessive whitespace
    for link_pattern in [r'http\S+', r'www\.\S+']:
        email_body = re.sub(link_pattern, '', email_body)
    email_body = re.sub(r'\S+@\S+', '', email_body) 

    if len(email_body) > 2000:
        email_body = email_body[:3000] + " ... [truncated]"
    return email_body 
