# WorkAutomation

A simple script that (semi-)automates tedious administrative tasks at work.

## What does it do?

Features:
1. Automatically creates Toggl projects based on tickets in Zendesk.
2. Provides a command line tool for adding time entries to FreshBooks in a semi-automated way.

## How do I use it?

Make a `config.json` file and fill in your details, use `config.json.example` as a reference. It needs your API keys for Toggl, ZenDesk, and FreshBooks (depending on what features you use). Only python 3 is supported, so make sure that's installed. The script depends on the `fuzzywuzzy` and `zenpy` packages which can be easily installed using `pip`. 

```
pip install fuzzywuzzy
pip install zenpy
```

### Toggle-Zendesk sync
To automatically create Toggle projects from the latest Zendesk tickets, use:

```
python sync-zendesk-toggle.py
```

💡 Pro-tip: make it a cron job! I advise every 5 minutes or so, but be sure to fire it up at least once a day.

### CLI for FreshBooks time tracking

To add time entries to FreshBooks based on your Toggle entries, use:

```
python freshbooks-timetracking.py
```
