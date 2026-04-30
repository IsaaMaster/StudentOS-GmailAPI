from datetime import timedelta

# Offsets are applied at request time so timestamps are always fresh relative
# to when the user loads the page — not relative to server start.
MOCK_EMAILS = {
    "e3": {
        "from":       "Google <no-reply@accounts.google.com>",
        "from-email": "no-reply@accounts.google.com",
        "offset":     timedelta(minutes=3),
        "subject":    "Your Google verification code",
        "body": (
            "Your Google verification code is 847291. "
            "This code expires in 10 minutes. "
            "If you didn't request this, you can ignore this email. "
            "Do not share this code with anyone."
        ),
        "rfc-id":  "<otp.847291@accounts.google.com>",
        "snippet": "Your verification code is 847291. Expires in 10 minutes.",
    },
    "e2": {
        "from":       "Connor Walsh <connorw@gmail.com>",
        "from-email": "connorw@gmail.com",
        "offset":     timedelta(minutes=45),
        "subject":    "Study session tonight?",
        "body": (
            "Hey! Are you still coming to the study session tonight at the library? "
            "We're starting at 7pm in the group study room on the 2nd floor. "
            "Let me know if you can make it — I'll grab us a table."
        ),
        "rfc-id":  "<study.session@gmail.com>",
        "snippet": "Are you still coming to the study session tonight at 7pm at the library?",
    },
    "e1": {
        "from":       "Professor David Chen <d.chen@university.edu>",
        "from-email": "d.chen@university.edu",
        "offset":     timedelta(hours=4),
        "subject":    "Problem Set 3 Due Friday",
        "body": (
            "Hi everyone,\n\n"
            "Just a reminder that Problem Set 3 is due this Friday at 11:59 PM. "
            "Please submit via Gradescope. The assignment covers lecture material from weeks 8 and 9. "
            "Let me know if you have any questions.\n\n"
            "– Prof. Chen"
        ),
        "rfc-id":  "<ps3.reminder@university.edu>",
        "snippet": "Reminder: Problem Set 3 is due this Friday at 11:59 PM via Gradescope.",
    },
    "e5": {
        "from":       "Amazon <shipment-tracking@amazon.com>",
        "from-email": "shipment-tracking@amazon.com",
        "offset":     timedelta(hours=20),
        "subject":    "Your order has shipped",
        "body": (
            "Your Amazon order (#113-4829201-8847362) has shipped and is on its way. "
            "You can track your package using the Amazon app or website.\n\n"
            "Order: Wireless Noise-Cancelling Headphones\n"
            "Carrier: UPS\n"
            "Tracking: 1Z999AA10123456784"
        ),
        "rfc-id":  "<ship.confirm@amazon.com>",
        "snippet": "Order #113-4829201 shipped. Track via the Amazon app.",
    },
    "e4": {
        "from":       "Financial Aid Office <finaid@university.edu>",
        "from-email": "finaid@university.edu",
        "offset":     timedelta(hours=24),
        "subject":    "Action Required: Your Aid Package Has Been Updated",
        "body": (
            "Dear Student,\n\n"
            "Your financial aid package for the upcoming semester has been updated. "
            "Please log in to the student portal to review your award letter. "
            "You must accept or decline your aid by May 15th to secure your funding.\n\n"
            "If you have questions, contact our office at finaid@university.edu.\n\n"
            "Financial Aid Office"
        ),
        "rfc-id":  "<aid.update@university.edu>",
        "snippet": "Your aid package has been updated. Accept or decline by May 15th.",
    },
    "e6": {
        "from":       "Mom <mom@gmail.com>",
        "from-email": "mom@gmail.com",
        "offset":     timedelta(hours=48),
        "subject":    "Checking in",
        "body": (
            "Hi honey! Just wanted to check in and see how you're doing with finals coming up. "
            "Your dad and I are thinking about you. Don't forget to eat and sleep! "
            "Call us when you get a chance — we miss you.\n\n"
            "Love you,\nMom"
        ),
        "rfc-id":  "<checkin@gmail.com>",
        "snippet": "Just checking in — call us when you get a chance. Love, Mom.",
    },
    "e7": {
        "from":       "CS Club <newsletter@csclub.university.edu>",
        "from-email": "newsletter@csclub.university.edu",
        "offset":     timedelta(hours=60),
        "subject":    "CS Club Weekly Digest — Hackathon Recap & Upcoming Events",
        "body": (
            "Welcome to this week's CS Club newsletter!\n\n"
            "• Spring Hackathon recap: 80+ participants, 22 projects, 3 winning teams. "
            "See highlights on our website.\n"
            "• Next meeting: Tuesday at 6pm in Eng Hall 201.\n"
            "• Job board: New postings from Google, Microsoft, and several early-stage startups.\n"
            "• Workshop: Intro to LLM APIs — Friday at 4pm, room 305."
        ),
        "rfc-id":  "<digest@csclub.university.edu>",
        "snippet": "Hackathon recap, Tuesday meeting, job board updates, LLM workshop Friday.",
    },
}
