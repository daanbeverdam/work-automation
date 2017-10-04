from zenpy import Zenpy
import datetime
import requests
import sqlite3
from fuzzywuzzy import process
import json
import traceback


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
        self.toggl_clients = self.get_toggl_clients()

    def check(self):
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

    def log(self, entry):
        entry = entry.strip()
        print(entry)
        with open('system.log', 'a') as log:
            log.write(str(datetime.datetime.now()) + ' ' + entry + '\n')

if __name__ == '__main__':
    el = EasyLife()
    el.check()
