# ToggleDesk

A simple script that keeps Toggl projects up to date by pulling the latest Zendesk tickets.

## What does it do?

1. Gets Zendesk tickets of past day via API
2. Matches Zendesk organization name to appropriate client name in Toggl (via fuzzy string matching if needed)
3. Creates project in Toggle for each ticket via API

## How do I use it?

Make a `config.json` file and fill in your details, use `config.json.example` as a reference. Only python 3 is supported, so make sure that's installed. The script depends on the `fuzzywuzzy` and `zenpy` packages which can be easily installed using `pip`. The main script can be easily executed using:

```
python main.py
```

💡 Pro-tip: make it a cron job! I advise every 5 minutes or so, but be sure to fire it up at least once a day.
