from core import Core
from zendesk import Zendesk
from freshbooks import FreshBooks
from toggl import Toggl
import datetime
from dateutil import tz, parser
import requests
import json
import traceback


class Automation(Core):
    """Provides all automation and integration between the services."""

    def sync(self, no_of_days=1):
        """Turns Freshbooks tickets from the past x days into Toggl projects."""
        zd = Zendesk()
        tg = Toggl()
        try:
            self.print("Syncing...")
            tickets = zd.get_tickets(no_of_days)
            for ticket in tickets:
                self.print_divider(30)
                project_title = self.format_title(ticket.id, ticket.subject)
                if ticket.organization:
                    client_id = tg.get_client_id(name=ticket.organization.name)
                else:
                    client_id = False
                    self.print("Ticket '%s' has no associated organization!" % (project_title))
                self.print("Creating project '%s'..." % (project_title))
                result = tg.create_project(project_title, client_id)
                self.print("Toggl response:")
                self.log(result, silent=False)
            self.print("Done!")
        except:
            self.log(traceback.format_exc(), silent=False)

    def time_tracking(self):
        """Starts interactive time tracking session. Updates Freshbooks based on Toggl entries."""
        self.print_splash()  # prints some nice ASCII art before we begin
        self.print("You can always enter 'skip' when you want to skip a time entry.", format='tip')
        days = self.get_no_of_days_interactive()
        original_entries = self.get_toggl_time_entries(days)
        time_entries = self.merge_toggl_time_entries(original_entries)
        self.print("OK, I'll run you through the Toggl time entries of the past %i day(s)." % (days))
        for entry in time_entries:
            self.print_divider(30)
            client_id = self.get_toggl_client_id(project_id=entry.get('pid'))
            client_name = self.get_toggle_client(client_id)
            project = self.get_toggl_project(entry.get('pid'))
            duration = int(entry['duration']) / 60 / 60
            duration = round(duration * 4 ) / 4  # convert to fb hours format
            description = "%s %s" % (project['name'], '- ' + entry['description'] if entry.get('description') else '')
            date = str(parser.parse(entry['start']).date())
            self.print("Description: " + description)
            self.print("Date: " + date)
            self.print("Hours spent: " + str(duration))
            if entry.get('tags') and self.BOOKED_TAG in entry['tags']:
                self.print("Skipping this entry because it is already in Freshbooks.", 'cross')
            elif entry['billable']:
                client_name = self.fb_project_search(client_name)
                if not client_name:
                    self.print("Skipping this entry.", 'cross')
                    continue
                project_id = self.get_fb_project_id(client_name)
                answer = input("Do you want to enter above information in Freshbooks? (Y/n) ")
                if answer.lower() == "y" or answer == "":
                    self.tag_toggl_projects(entry['merged_ids'], self.BOOKED_TAG)
                    self.add_fb_entry(project_id, duration, description, date)
                else:
                    self.print("Did not add entry to Freshbooks.", 'cross')
            else:
                self.print("Skipping this entry because it is not billable.", 'cross')
        self.print_divider(30)
        self.print("All done!")

    def format_title(self, ticket_id, subject):
        """Formats id and subject into a suitable (Freshbooks) title."""
        # TODO: strip block tags?
        title = "#%i %s" % (ticket_id, subject)
        return title

    def get_no_of_days_interactive(self):
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

    def merge_toggl_time_entries(self, time_entries):
        d = {}
        for entry in time_entries:
            if entry.get('tags') and self.BOOKED_TAG in entry['tags']:
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