from core import Core
from xml.dom import minidom
import requests
import json


class FreshBooks(Core):
    """Contains all Freshbooks related operations."""

    def __init__(self):
        super(FreshBooks, self).__init__()
        self.projects = None

    def add_entry(self, project_id, duration, description, date, task_id=2):
        """Adds timetracking entry to Freshbooks. Returns API response."""
        description = self.normalize_string(description)
        xml_request = """
        <?xml version="1.0" encoding="utf-8"?>
        <request method="time_entry.create">
          <time_entry>
            <project_id>%s</project_id>
            <task_id>%s</task_id>
            <hours>%s</hours>
            <notes><![CDATA[%s]]></notes>
            <date>%s</date>
          </time_entry>
        </request>
        """ % (str(project_id), str(task_id), str(duration), description, date)
        url = 'https://' + self.fb_creds['subdomain'] + '.freshbooks.com/api/2.1/xml-in'
        response = requests.post(url, data=xml_request, auth=(self.fb_creds['token'], 'X'))
        xml = minidom.parseString(response.text)
        elements = xml.getElementsByTagName('response')
        status = elements[0].attributes['status'].value
        if status == 'ok':
            self.print("Entry added to Freshbooks.", 'ok')
            self.log(response.text, silent=True)
        else:
            self.print("Whoops something went wrong on Freshbooks end!", 'cross')
            self.log(response.text, silent=False)
            raise ValueError("Unexpected response from Freshbooks!"
                             "Incident has been logged.")
        return response.text

    def get_project_id(self, name):
        """Returns Freshbooks project id by name."""
        return self.get_projects().get(name)

    def get_projects(self):
        """Returns dictionary of all Freshbooks projects. Key-value pair: name-id."""
        # Additional note: their API is really shitty.
        if self.projects:
            return self.projects
        print("Loading Freshbooks projects from their shitty XML API...")
        result = {}
        projects = ['project']
        i = 1
        while len(projects) != 0:
            xml_request = """
            <?xml version="1.0" encoding="utf-8"?>
            <request method="project.list">     <!-- Hey Freshbooks, -->
              <page>%i</page>                   <!-- your API sucks! -->
              <per_page>100</per_page>          <!-- Ever heard of JSON? -->
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
        # Did I mention their API is really shitty?
        self.projects = result
        return result
