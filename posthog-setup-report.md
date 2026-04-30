<wizard-report>
# PostHog post-wizard report

The wizard has completed a deep integration of PostHog analytics into the StudentOS FastAPI backend. A `Posthog` client instance is initialized at startup (with `enable_exception_autocapture=True`) and registered with `atexit` for clean shutdown. A FastAPI `lifespan` context manager calls `posthog_client.flush()` on app shutdown. The production `/gmail/{command}` endpoint uses `new_context()` + `identify_context()` with a SHA-256-derived anonymous user ID (from the OAuth access token) so all events in a request are correlated without storing PII. The demo `/demo/chat` endpoint uses the caller's IP as the distinct ID. All 12 planned events are instrumented across both production and demo flows.

| Event | Description | File |
|---|---|---|
| `command received` | Voice command received via Alexa at `/gmail/{command}` | `app/main.py` |
| `intent mapped` | Command successfully classified into a known intent | `app/main.py` |
| `intent mapping failed` | Intent classification returned "none" (unrecognized command) | `app/main.py` |
| `email summarized` | `gmail_summarize` completed successfully (includes `email_count`, `hours_back`) | `app/main.py` |
| `draft created` | `gmail_draft` successfully wrote a draft to Gmail | `app/main.py` |
| `reply created` | `gmail_reply` successfully wrote a reply draft to Gmail | `app/main.py` |
| `verification code found` | `gmail_verification_code` extraction completed | `app/main.py` |
| `sender checked` | `gmail_check_sender` lookup completed | `app/main.py` |
| `demo command used` | Command submitted via `/demo/chat` (includes `intent`, `command_length`) | `app/main.py` |
| `demo rate limit hit` | Demo user exceeded 10 requests/hour limit | `app/main.py` |
| `demo draft created` | Draft created in demo chat flow | `app/main.py` |
| `demo reply created` | Reply draft created in demo chat flow | `app/main.py` |

## Next steps

We've built some insights and a dashboard for you to keep an eye on user behavior, based on the events we just instrumented:

- **Dashboard – Analytics basics**: https://us.posthog.com/project/403377/dashboard/1526705
- **Daily Command Volume** (line chart, production vs demo): https://us.posthog.com/project/403377/insights/1eNq8hnM
- **Command to Success Funnel** (received → intent mapped → email summarized): https://us.posthog.com/project/403377/insights/0KmPM8la
- **Feature Usage by Intent** (bar chart of all 5 intents): https://us.posthog.com/project/403377/insights/yk3jkmoL
- **Demo Engagement Funnel** (demo command → draft created): https://us.posthog.com/project/403377/insights/IIxQNJq9
- **Demo Rate Limit Hits** (daily bar chart): https://us.posthog.com/project/403377/insights/HVlqDUM3

> **Note on package installation**: The `posthog` package needs to be installed in your virtual environment. If `pip install posthog` fails due to SSL errors, try:
> ```
> pip install posthog --trusted-host pypi.org --trusted-host files.pythonhosted.org
> ```

### Agent skill

We've left an agent skill folder in your project. You can use this context for further agent development when using Claude Code. This will help ensure the model provides the most up-to-date approaches for integrating PostHog.

</wizard-report>
