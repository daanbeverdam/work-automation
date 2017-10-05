from zenpy import Zenpy
import datetime
import requests
from fuzzywuzzy import process
import json
import traceback
from xml.dom import minidom


class EasyLife():

    def __init__(self):
        config = json.load(open('config.json','r'))
        self.zen_creds = {
            'email' : config['zendesk_email'],
            'token' : config['zendesk_token'],
            'subdomain': config['zendesk_subdomain']
            }
        self.toggl_creds = (
            config['toggl_token'], 'api_token'
            )
        self.fb_creds = {
            'token': config.get('freshbooks_token'),
            'subdomain': config.get('freshbooks_subdomain')
        }
        self.toggl_clients = self.get_toggl_clients()

    def sync(self):
        try:
            tickets = self.get_zd_tickets(1)
            for ticket in tickets:
                project_title = self.format_title(ticket.id, ticket.subject)
                if ticket.organization:
                    client_id = self.get_toggl_client_id(ticket.organization.name)
                    self.log("Creating project '%s'. Associated client: '%s'." % (project_title, ticket.organization.name))
                    result = self.create_toggl_project(project_title, client_id)
                    self.log(result)
                else:
                    self.log("Ticket '%s' has no associated organization!" % (project_title))
        except:
            self.log(traceback.format_exc())

    def get_toggl_client_id(self, name):
        name = name.lower()
        if self.toggl_clients.get(name):
            return self.toggl_clients[name]
        else:
            # Fuzzy string matching ahead, beware!
            choices = self.toggl_clients.keys()
            results = process.extract(name, choices)
            best_match = results[0][0]
            self.log("Fuzzy matched %s (Zendesk) to %s (Toggl)." % (name, best_match))
            if len(results) > 4:
                self.log("Other matches: " + str(results[:5]))
            return self.toggl_clients[best_match]

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

    def get_toggl_client_id(self, project_id):
        url = 'https://www.toggl.com/api/v8/projects/' + str(project_id)
        response = requests.get(url, auth=self.toggl_creds)
        return response.json()['data'].get('cid')

    def create_fb_time_entries(self):
        answer = input("Press return to start adding time entries of past day or type number of days you want to go back. ")
        if answer == '':
            days = 1
        else:
            try:
                days = int(answer)
            except:
                print("You didn't enter a number, assuming 1 day.")
                days = 1
        time_entries = self.get_toggl_time_entries(days)
        print("OK, I'll run you through the Toggl time entries of the past %i day(s)." % (days))
        for entry in time_entries:
            print("========================================")
            client_id = self.get_toggl_client_id(project_id=entry.get('pid'))
            client_name = self.get_toggle_client(client_id)
            duration = int(entry['duration']) / 60 / 60  # duration in hours
            print("Toggl client: " + client_name)
            print("Toggl description: " + str(entry.get('description')))
            print("Hours spent: " + str(duration))
            if entry['billable']:
                answer = input("Do you want to enter this in Freshbooks? (Y/n) ")
                if answer.lower() == "y" or answer == "":
                    self.add_fb_entry(client_name, duration, str(entry.get('description')))
                    print("\u2713 Entry added to Fresbooks.")
                else:
                    print("\u2573 Did not add entry to Freshbooks.")
            else:
                print("\u2573 Skipping this entry because it is not billable.")

    def add_fb_entry(self, client_name, duration, description):
        # Can you tell i hate XML?
        xml_request = """
        <?xml version="1.0" encoding="utf-8"?>
        <request method="time_entry.create">
          <time_entry>
            <project_id>1</project_id>        <!-- (Required) -->
            <task_id>1</task_id>              <!-- (Required) -->
            <staff_id>1</staff_id>            <!-- (Optional) -->
            <hours>4.5</hours>                <!-- (Optional) -->
            <notes>Phone consultation</notes> <!-- (Optional) -->
            <date>2007-01-01</date>           <!-- (Optional) -->
          </time_entry>
        </request>
        """

    def get_fb_projects(self):
        xml_request = """
        <?xml version="1.0" encoding="utf-8"?>
        <request method="project.list">
          <page>1</page>
          <per_page>999999</per_page>
        </request>
        """
        url = 'https://' + self.fb_creds['subdomain'] + '.freshbooks.com/api/2.1/xml-in'
        response = requests.post(url, data=xml_request, auth=(self.fb_creds['token'], 'X'))
        xmldoc = minidom.parseString(response.text)
        projects = xmldoc.getElementsByTagName('project')

    def get_toggl_time_entries(self, days=1):
        timezone_shift = '+02:00'  # TODO: make this dynamic
        yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        params = {'start_date': yesterday.isoformat() + timezone_shift}
        response = requests.get('https://www.toggl.com/api/v8/time_entries', params=params, auth=(self.fb_creds['token'], 'api_token'))
        time_entries = response.json()
        return time_entries

    def log(self, entry):
        entry = entry.strip()
        print(entry)
        with open('system.log', 'a') as log:
            log.write(str(datetime.datetime.now()) + ' ' + entry + '\n')

if __name__ == '__main__':
    el = EasyLife()
    # el.sync()
    # el.create_fb_time_entries()
    el.get_fb_projects()
