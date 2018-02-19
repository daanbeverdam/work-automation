from core import Core
from zendesk import Zendesk
from freshbooks import FreshBooks
from toggl import Toggl
import datetime
from dateutil import tz, parser
import requests
import json
import sys
import traceback
import webbrowser
from fuzzywuzzy import process, fuzz


class Automation(Core):
    """Provides all automation and integration between the services."""

    def __init__(self):
        super(Automation, self).__init__()
        self.SKIP_KEYWORDS = ['skip', 'cancel', 'break']

    def sync(self, no_of_days=1):
        """Turns Freshbooks tickets from the past x days into Toggl projects."""
        zd = Zendesk()
        tg = Toggl()
        try:
            self.print("Syncing...")
            self.print_divider(30)
            tickets = zd.get_tickets(no_of_days)
            for ticket in tickets:
                project_title = self.format_title(ticket.id, ticket.subject)
                if ticket.organization:
                    client_id = tg.get_client_id(name=ticket.organization.name)
                    if not client_id:
                        new_client = tg.create_client(ticket.organization.name)
                        client_id = new_client['id']
                else:
                    client_id = False
                    self.print("Ticket '%s' has no associated organization!" % (project_title))
                all_projects = tg.get_projects()
                if not self.already_created(ticket.id, all_projects):
                    self.print("Creating project '%s'..." % (project_title))
                    result = tg.create_project(project_title, client_id, is_private=False)
                    self.print("Toggl response:")
                    self.log(result, silent=False)
                else:
                    self.print("There is already a Toggl project for Zendesk ticket #%s!" % ticket.id)
                    pass
                    # TODO: edit Toggl project
                    # tg.edit_project(project_id, name=ticket.subject)
                self.print_divider(30)
            self.print("Done!")
        except:
            self.log(traceback.format_exc(), silent=False)

    def time_tracking(self):
        """Starts interactive time tracking session. Updates Freshbooks based on Toggl entries."""
        fb = FreshBooks()
        tg = Toggl()
        self.print_splash()
        self.print("Tip: You can always enter 'skip' when you want to skip a time entry.", format='warn')
        days = self.get_interactive_days()  # number of days to go back
        self.print("OK, I'll run you through the Toggl time entries of the past %i day(s)." % (days))
        timestamp = self.get_timestamp(days)  # unix timestamp including tz
        time_entries = tg.get_time_entries(timestamp)
        if len(time_entries) == 0:
            self.print("No Toggl entries in this time span!", 'warn')
            return False
        time_entries = self.merge_toggl_time_entries(time_entries)  # merge Toggl entries
        fb_projects = fb.get_projects()
        # Loop through merged Toggl time entries:
        for entry in time_entries:
            # Get and convert all necessary info:
            client_id = tg.get_client_id(project_id=entry.get('pid'))
            client_name = tg.get_client_name(client_id)
            project = tg.get_project(entry.get('pid'))
            duration = int(entry['duration']) / 60 / 60  # convert duration to hours
            duration = round(duration * 4 ) / 4  # round hours to nearest .25
            description = self.format_description(project['name'], entry['description'])
            date = str(parser.parse(entry['start']).date())
            # Print info in a nice way:
            self.print_divider(30)
            self.print("Description: " + description)
            self.print("Date: " + date)
            self.print("Hours spent: " + str(duration))
            # Skip if Toggl entry is already booked:
            if entry.get('tags') and tg.BOOKED_TAG in entry['tags']:
                self.print("Skipping this entry because it is already in Freshbooks.", 'cross')
            # Skip if duration is below 0.25:
            elif duration < 0.25:
                self.print("Skipping this entry because there are less than 0.25 hours spent.", 'cross')
            # If billable, add to Freshbooks:
            elif entry['billable']:
                # Get FreshBooks project name through interactive search:
                try:
                    self.print("Project: \U0001F50D ")
                    fb_project_name = self.interactive_search(fb_projects.keys(), client_name)
                # Handle KeyboardInterrupt
                except KeyboardInterrupt:
                    answer = input("\nKeyboardInterrupt! Skip current entry or quit time tracking? (S/q) ")
                    if answer.lower() == 's' or answer == '':
                        self.clear_lines(1)
                        self.print("Skipping this entry.", 'cross')
                        continue
                    else:
                        self.clear_lines(1)
                        self.print("Ok, stopping time tracking.", 'cross')
                        sys.exit()
                # If user requests so, skip this entry:
                self.clear_lines(1)
                if not fb_project_name:
                    self.print("Skipping this entry.", 'cross')
                    continue
                # Otherwise, add entry to FreshBooks and tag Toggl entry/entries:
                self.print("Project: " + fb_project_name)
                project_id = fb.get_project_id(fb_project_name)
                fb.add_entry(project_id, duration, description, date)
                tg.tag_projects(entry['merged_ids'], tg.BOOKED_TAG)
            # If not billable, skip entry:
            else:
                self.print("Skipping this entry because it is not billable.", 'cross')
        self.print_divider(30)
        answer = input("All done! Open FreshBooks in browser to verify? (Y/n) ")
        if answer.lower() == 'y' or answer == '':
            webbrowser.open('https://%s.freshbooks.com/timesheet' % fb.fb_creds['subdomain'])

    def interactive_search(self, choices, query=None):
        """Starts interactive search, allows user to make a selection.
        Accepts array of strings and optional (user) query. Returns string chosen by user."""
        if query:
            match = self.get_interactive_match(choices, query)
            if match:
                self.print("Matched query to '%s'." % (match))
                answer = input("Is that correct? (Y/n) ")
                self.clear_lines(1)
                if answer.lower() == 'y' or answer == '':
                    self.clear_lines(1)
                    return match
                else:
                    self.clear_lines(1)
                    return self.interactive_search(choices)
            else:
                return None
        else:
            query = input("Please type a query: ")
            self.clear_lines(1)
            return self.interactive_search(choices, query)

    def get_interactive_match(self, choices, query):
        """Returns string that best matches query out of a list of choices.
        Prompts user if unsure about best match."""
        if query in self.SKIP_KEYWORDS:
            return None
        results = process.extract(query, choices, limit=10)  # fuzzy string matching
        best_match = results[0]
        second_best_match = results[1]
        if best_match[1] == second_best_match[1] or best_match[1] < 50:  # if inconclusive or low score
            self.print("Couldn't find a conclusive match for '%s'. Best matches:" % (query))
            i = 0
            for result in results:
                i += 1
                print(" [%i] %s" % (i, result[0]))
            answer = input("Choose one or specify a less ambiguous query: ")
            self.clear_lines(2 + len(results))
            if answer.isdigit() and int(answer) <= len(results):
                return results[int(answer) - 1][0]
            else:
                return self.get_interactive_match(choices, answer)
        else:
            return best_match[0]

    def get_interactive_days(self):
        """Asks an user how many days to go back. Returns int."""
        answer = input("Press return to get entries of past day or input number of days to go back in time: ")
        if answer == '':
            days = 1
        else:
            try:
                days = int(answer)
            except:
                print("You didn't enter a number, assuming 1 day.")
                days = 1
        return days

    def already_created(self, ticket_id, toggl_projects):
        """Hacky way to check if this function already made a Toggl project based on a Zendesk ticket ID."""
        project_prepends = [p['name'].split()[0][1:] for p in toggl_projects]
        if str(ticket_id) in project_prepends:
            return True
        return False

    def format_title(self, ticket_id, subject):
        """Formats id and subject into a suitable (Freshbooks) title."""
        # TODO: strip block tags?
        title = "#%i %s" % (ticket_id, subject)
        return title.strip()

    def format_description(self, project_name, description):
        """Formats Toggl project name and description into (Freshbooks) description."""
        description = description if description else ''
        return "%s %s" % (project_name, '- ' + description)

    def merge_toggl_time_entries(self, time_entries):
        """Merges toggle time entries with same project name. Sums duration if billable."""
        tg = Toggl()
        d = {}
        for entry in time_entries:
            if entry.get('billable'):
                if entry.get('tags') and tg.BOOKED_TAG in entry['tags']:
                    status = 'booked'
                else:
                    status = 'not-booked'
                date = parser.parse(entry['start']).date()
                if not entry.get('pid'):
                    self.log("Couldn't find associated project for entry: %s" % (str(entry)))
                    continue
                unique_id = str(entry['pid']) + str(date) + status
                if not entry.get('description'):
                    entry['description'] = ""
                if d.get(unique_id):
                    d[unique_id]['duration'] += entry['duration']
                    d[unique_id]['merged_ids'].append(entry['id'])
                    if d[unique_id].get('description'):
                        if entry['description'].strip() not in d[unique_id]['description']:
                            d[unique_id]['description'] += ' / ' + entry['description']
                    else:
                        d[unique_id]['description'] = entry['description']
                else:
                    entry['merged_ids'] = [entry['id']]
                    d[unique_id] = entry
        return d.values()

    def get_timestamp(self, days=1):
        """Returns isoformat string of beginning of past x day(s).
        Assumes Europe/Amsterdam locale."""
        offset = datetime.datetime.utcnow().date() - datetime.timedelta(days=days-1)
        # est = tz.gettz('Europe/Amsterdam')
        # temporary dirty fix for timezone:
        timezone = '+02:00'
        start = datetime.datetime(offset.year, offset.month, offset.day)
        return start.isoformat() + timezone
