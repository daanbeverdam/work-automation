from zenpy import Zenpy
import datetime
import requests
from fuzzywuzzy import process, fuzz
import json
import traceback
from xml.dom import minidom


class EasyLife():

    def __init__(self):
        config = json.load(open('config.json','r'))
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
        self.toggl_clients = self.get_toggl_clients()
        self.fb_projects = []

    def sync(self, no_of_days):
        try:
            tickets = self.get_zd_tickets(no_of_days)
            for ticket in tickets:
                self.log("============================")
                project_title = self.format_title(ticket.id, ticket.subject)
                if ticket.organization:
                    client_id = self.get_toggl_client_id(name=ticket.organization.name)
                else:
                    self.log("Ticket '%s' has no associated organization in Zendesk! Creating Toggl project anyway." % (project_title))
                    client_id = False
                self.log("Creating project '%s'." % (project_title))
                result = self.create_toggl_project(project_title, client_id)
                print("Toggl response:")
                self.log(result)
        except:
            self.log(traceback.format_exc())

    def get_toggl_client_id(self, name=None, project_id=None):
        if project_id:
            url = 'https://www.toggl.com/api/v8/projects/' + str(project_id)
            response = requests.get(url, auth=self.toggl_creds)
            return response.json()['data'].get('cid')
        elif name:
            name = name.lower()
            if self.toggl_clients.get(name):
                return self.toggl_clients[name]
            else:
                # Fuzzy string matching ahead, beware!
                choices = self.toggl_clients.keys()
                best_match = self.fuzzy_match(name, choices)
                self.log("Fuzzy matched '%s' to Toggl project '%s'." % (name, best_match))
                return self.toggl_clients[best_match]

    def fuzzy_match(self, query, choices):
        """Returns best approximate match in a list of strings."""
        results = process.extract(query, choices)
        if results[0][1] == results[1][1]:
            # Use token set ratio on best results as a tie breaker
            best_results = [r[0] for r in results[:15]]
            results = process.extract(query, best_results, scorer=fuzz.token_set_ratio)
        best_match = results[0][0]
        return best_match

    def format_title(self, _id, subject):
        # TODO: strip block tags?
        title = "#%i %s" % (_id, subject)
        return title

    def get_zd_tickets(self, days=1):
        """Returns array of ticket objects for past X days."""
        client = Zenpy(**self.zen_creds)
        yesterday = datetime.datetime.now() - datetime.timedelta(days=days)
        tickets = []
        for ticket in client.search(type="ticket", created_greater_than=(yesterday)):
            tickets.append(ticket)
        return tickets

    def create_toggl_project(self, title, client_id=None):
        """Creates project in Toggle."""
        headers = {
            'Content-Type': 'application/json',
            }
        data = {
            "project": {
                "name": title,
                "cid": client_id if client_id else False
                }
            }
        data = json.dumps(data)
        url = 'https://www.toggl.com/api/v8/projects'
        response = requests.post(url, headers=headers, data=data, auth=self.toggl_creds)
        return response.text

    def get_toggl_clients(self):
        """Returns Toggl clients."""
        url = 'https://www.toggl.com/api/v8/clients'
        response = requests.get(url, auth=self.toggl_creds).json()
        clients = {}
        for result in response:
            clients[result['name'].lower()] = result['id']
        return clients

    def get_toggle_client(self, _id):
        """Returns name of Toggl client, accepts Toggl client id."""
        for name, client_id in self.toggl_clients.items():
            if _id == client_id:
                return name
        return None

    def get_toggl_project(self, project_id):
        url = 'https://www.toggl.com/api/v8/projects/' + str(project_id)
        response = requests.get(url, auth=self.toggl_creds)
        return response.json()['data']

    def get_no_of_days_interactive(self):
        answer = input("Press return to start adding time entries of past day or type number of days you want to go back. ")
        if answer == '':
            days = 1
        else:
            try:
                days = int(answer)
            except:
                print("You didn't enter a number, assuming 1 day.")
                days = 1
        return days

    def create_fb_time_entries(self):
        days = self.get_no_of_days_interactive()
        time_entries = self.get_toggl_time_entries(days)
        print("OK, I'll run you through the Toggl time entries of the past %i day(s)." % (days))
        print("Tip: when in Freshbooks project search mode, you can always enter 'skip' to skip the entry.")
        self.fb_projects = self.get_fb_projects()
        for entry in time_entries:
            print("========================================")
            client_id = self.get_toggl_client_id(project_id=entry.get('pid'))
            client_name = self.get_toggle_client(client_id)
            project = self.get_toggl_project(entry.get('pid'))
            duration = int(entry['duration']) / 60 / 60
            duration = round(duration * 4 ) / 4  # convert to fb hours format
            description = "%s %s" %(project['name'], '/ ' + entry['description'] if entry.get('description') else '')
            date = entry['start']
            print("Description: " + description)
            print("Date: " + date)
            print("Hours spent: " + str(duration))
            if entry['billable']:
                client_name = self.fb_project_search(client_name)
                if not client_name:
                    print("\u2718 Skipping this entry.")
                    continue
                project_id = self.get_fb_project_id(client_name)
                answer = input("Do you want to enter above information in Freshbooks? (Y/n) ")
                if answer.lower() == "y" or answer == "":
                    self.add_fb_entry(project_id, duration, description, date)
                    print("\u2713 Entry added to Freshbooks.")
                else:
                    print("\u2718 Did not add entry to Freshbooks.")
            else:
                print("\u2718 Skipping this entry because it is not billable.")
        print("All done!")

    def get_fb_project_id(self, name):
        return self.fb_projects[name]

    def fb_project_search(self, name):
        if name == 'skip' or name == 'cancel':
            return None
        elif name:
            choices = self.fb_projects.keys()
            results = process.extract(name, choices, limit=10)
            best_match = results[0][0]
            if results[0][1] == results[1][1] or results[0][1] < 50:
                print("Couldn't find a Freshbooks project that exactly matches '%s'. Best matches:" % (name))
                i = 0
                for result in results:
                    i += 1
                    print(" [%i] %s" % (i, result[0]))
                answer = input("Choose one or specify a less ambiguous query: ")
                self.clear_lines(2 + len(results))
                if answer.isdigit() and int(answer) <= len(results):
                    answer = results[int(answer) - 1][0]
                return self.fb_project_search(answer)
            print("Matched query to Freshbooks project '%s'." % (best_match))
            answer = input("Is that correct? (Y/n) ")
            self.clear_lines(2)
            if answer.lower() == 'y' or answer == '':
                print("Project: " + best_match)
                return best_match
            else:
                return self.fb_project_search(None)
        else:
            answer = input("Search for a Freshbooks project: ")
            self.clear_lines(1)
            return self.fb_project_search(answer)

    def clear_lines(self, no_of_lines):
        CURSOR_UP_ONE = '\x1b[1A'
        ERASE_LINE = '\x1b[2K'
        print((CURSOR_UP_ONE + ERASE_LINE) * no_of_lines + CURSOR_UP_ONE)

    def add_fb_entry(self, project_id, duration, description, date, task_id=2):
        xml_request = """
        <?xml version="1.0" encoding="utf-8"?>
        <request method="time_entry.create">
          <time_entry>
            <project_id>%s</project_id>
            <task_id>%s</task_id>
            <hours>%s</hours>
            <notes>%s</notes>
            <date>%s</date>
          </time_entry>
        </request>
        """ % (str(project_id), str(task_id), str(duration), description, date)
        url = 'https://' + self.fb_creds['subdomain'] + '.freshbooks.com/api/2.1/xml-in'
        response = requests.post(url, data=xml_request, auth=(self.fb_creds['token'], 'X'))
        self.log(response.text, silent=True)

    def get_fb_projects(self):
        # Can you tell I hate XML?
        print("Getting Freshbooks projects from their shitty XML API...")
        result = {}
        projects = ['project']
        i = 1
        while len(projects) != 0:
            xml_request = """
            <?xml version="1.0" encoding="utf-8"?>
            <request method="project.list">
              <page>%i</page>
              <per_page>100</per_page>
            </request>
            """ % (i)
            i += 1
            url = 'https://' + self.fb_creds['subdomain'] + '.freshbooks.com/api/2.1/xml-in'
            response = requests.post(url, data=xml_request, auth=(self.fb_creds['token'], 'X'))
            xmldoc = minidom.parseString(response.text)
            projects = xmldoc.getElementsByTagName('project')
            if len(projects):
                for project in projects:
                    name = project.getElementsByTagName("name")[0].firstChild.nodeValue
                    project_id = project.getElementsByTagName("project_id")[0].firstChild.nodeValue
                    result[name] = project_id
        return result

    def get_toggl_time_entries(self, days=1):
        timezone_shift = '+02:00'  # TODO: make this dynamic
        yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        params = {'start_date': yesterday.isoformat() + timezone_shift}
        response = requests.get('https://www.toggl.com/api/v8/time_entries', params=params, auth=self.toggl_creds)
        time_entries = response.json()
        return time_entries

    def log(self, entry, silent=False):
        entry = entry.strip()
        if not silent:
            print(entry)
        with open('system.log', 'a') as log:
            log.write(str(datetime.datetime.now()) + ' ' + entry + '\n')
