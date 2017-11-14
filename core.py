import json
import datetime
from fuzzywuzzy import process, fuzz
import unicodedata


class Core():
    """Contains shared core operations."""

    def __init__(self):
        """Initializes object and parses config."""
        self.parse_config()

    def parse_config(self, config_path="config.json"):
        """Parses config and sets config variables."""
        config = json.load(open(config_path, 'r'))
        self.zen_creds = {
            'email' : config.get('zendesk_email'),
            'token' : config.get('zendesk_token'),
            'subdomain': config.get('zendesk_subdomain')
            }
        self.toggl_creds = (
            config.get('toggl_token'), 'api_token'
            )
        self.fb_creds = {
            'token': config.get('freshbooks_token'),
            'subdomain': config.get('freshbooks_subdomain')
            }

    def log(self, entry, silent=True):
        """Logs entries to system.log, also prints if not silent."""
        entry = str(entry).strip()
        if not silent:
            print(entry)
        with open('system.log', 'a') as log:
            log.write(str(datetime.datetime.now()) + ' ' + entry + '\n')

    def print(self, string, format=None):
        """Prints string according to different formats."""
        HEADER = '\033[95m'
        OKBLUE = '\033[94m'
        OKGREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'
        if format == 'warn':
            string = WARNING + BOLD + string
        elif format == 'bold':
            string = BOLD + string
        elif format == 'cross':
            string = FAIL + '\u2718 ' + string
        elif format == 'ok':
            string = OKGREEN + '\u2713 ' + string
        print(string + ENDC)

    def print_divider(self, length):
        print("=" * length)

    def clear_lines(self, no_of_lines):
        """Clears specified number of lines in terminal output."""
        CURSOR_UP_ONE = '\x1b[1A'
        ERASE_LINE = '\x1b[2K'
        print((CURSOR_UP_ONE + ERASE_LINE) * no_of_lines + CURSOR_UP_ONE)

    def print_splash(self):
        """Prints some nice ASCII art when invoked."""
        splash = r"""
     ___T_     WorkAutomation!
    | o o |   /
    |__-__|
    /| []|\
  ()/|___|\()
     |_|_|
     /_|_\
        """
        print(splash)

    def fuzzy_match(self, query, choices, cutoff=0):
        """Returns best approximate match in a list of strings by fuzzy matching.
           Set cutoff score to specify accuracy (value between 0-100).
           Returns None if results are too inaccurate."""
        results = process.extract(query, choices)
        print('score', results[0][1])
        print('cutoff', cutoff)
        if results[0][1] < cutoff:
            return None
        if results[0][1] == results[1][1]:
            # Use token set ratio on best results as a tie breaker
            best_results = [r[0] for r in results[:15]]
            results = process.extract(query, best_results, scorer=fuzz.token_set_ratio)
        best_match = results[0][0]
        return best_match

    def normalize_string(self, string):
        """Normalizes special characters in string because the FreshBooks API never heard of utf-8."""
        string = unicodedata.normalize('NFKD', string)
        return string.encode('ASCII', 'ignore').decode('utf-8')
