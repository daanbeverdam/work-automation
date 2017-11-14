from core import Core
import requests
import json


class Toggl(Core):
    """Contains all Toggl related operations."""

    def __init__(self):
        super(Toggl, self).__init__()
        self.BOOKED_TAG = "\U0001F343"  # tag used for flagging Toggl projects
        self.clients = None  # will contain loaded Toggl clients

    def get_clients(self):
        """Returns dictionary of all Toggl clients with key/value name/id."""
        if self.clients:
            return self.clients
        else:
            return self.load_clients()

    def load_clients(self):
        """Loads Toggl clients from their API and saves them to object."""
        self.print("Loading Toggl clients...")
        url = 'https://www.toggl.com/api/v8/clients'
        response = requests.get(url, auth=self.toggl_creds).json()
        clients = {}
        for result in response:
            clients[result['name']] = result['id']
        self.clients = clients  # store for later use
        return clients

    def get_client_id(self, name=None, project_id=None):
        """Returns client id based on either name or project id.
           Uses fuzzy matching for matching names."""
        if project_id:
            url = 'https://www.toggl.com/api/v8/projects/' + str(project_id)
            response = requests.get(url, auth=self.toggl_creds)
            return response.json()['data'].get('cid')
        elif name:
            if self.get_clients().get(name):
                return self.get_clients()[name]
            else:
                # Fuzzy string matching ahead, beware!
                choices = self.get_clients().keys()
                best_match = self.fuzzy_match(name, choices, cutoff=90)
                if best_match:
                    self.log("Fuzzy matched '%s' to Toggl project '%s'." % (name, best_match))
                    return self.get_clients()[best_match]
                else:
                    self.log("Couldn't accurately find a client with that name.")
                    return None

    def get_client_name(self, client_id):
        """Returns name of Toggl client, accepts Toggl client id."""
        for name, _id in self.get_clients().items():
            if client_id == _id:
                return name
        return None

    def create_client(self, name, workspace_id=None):
        """Creates a new Toggl client. Returns Toggl's JSON response.
           If no workspace id is specified, the id for the first workspace will be assumed."""
        if not workspace_id:
            workspaces = self.get_workspaces()
            workspace_id = workspaces[0]['id']
            self.print("No workspace ID specified, assuming workspace id %s" % str(workspace_id), 'warn')
        headers = {
            'Content-Type': 'application/json',
            }
        data = {
            "client": {
                "name": name,
                "wid": workspace_id
                }
            }
        data = json.dumps(data)
        url = 'https://www.toggl.com/api/v8/clients'
        response = requests.post(url, headers=headers, data=data, auth=self.toggl_creds)
        client = response.json()['data']
        self.load_clients()
        return client

    def get_project(self, project_id):
        """Returns Toggl project in json format. Accepts project id."""
        url = 'https://www.toggl.com/api/v8/projects/' + str(project_id)
        response = requests.get(url, auth=self.toggl_creds)
        return response.json()['data']

    def create_project(self, title, client_id=None, is_private=True):
        """Creates Toggl project with specified title and (optional) client id.
            Returns API response in json (if possible)."""
        headers = {
            'Content-Type': 'application/json',
            }
        data = {
            "project": {
                "name": title,
                "cid": client_id if client_id else False,
                "is_private": is_private
                }
            }
        data = json.dumps(data)
        url = 'https://www.toggl.com/api/v8/projects'
        response = requests.post(url, headers=headers, data=data, auth=self.toggl_creds)
        try:
            return response.json()
        except:
            return response.text

    def tag_projects(self, id_list, tag=None):
        """Tags Toggl time entries. Accepts list of toggl time entry IDs and tag."""
        if not tag:
            tag = self.BOOKED_TAG
        headers = {
            'Content-Type': 'application/json',
            }
        data = {
            "time_entry": {
                "tags": [tag]
                }
            }
        data = json.dumps(data)
        url = 'https://www.toggl.com/api/v8/time_entries/' + ','.join(str(i) for i in id_list)
        response = requests.post(url, headers=headers, data=data, auth=self.toggl_creds)
        self.print('Tagged Toggl %s. ' % ('entry' if len(id_list) == 1 else 'entries') + self.BOOKED_TAG, 'ok')
        return response.json()

    def get_time_entries(self, timestamp):
        """Returns all Toggl time entries from specified starting point as json array.
        Timestamp should be in isoformat including timezone info."""
        self.print("Loading Toggl time entries...")
        params = {'start_date': timestamp}
        response = requests.get('https://www.toggl.com/api/v8/time_entries', params=params, auth=self.toggl_creds)
        time_entries = response.json()
        return time_entries

    def get_workspaces(self):
        """Fetches all Toggl workspaces. Returns list of (json) workspaces."""
        url = 'https://www.toggl.com/api/v8/workspaces'
        response = requests.get(url, auth=self.toggl_creds)
        workspaces = response.json()
        return workspaces
