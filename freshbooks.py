from core import Core
from xml.dom import minidom
import requests
import json


class FreshBooks(Core):
    """All Freshbooks related operations."""
    projects = None

    def add_entry(self, project_id, duration, description, date, task_id=2):
        """Adds timetracking entry to Freshbooks. Returns API response."""
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
        self.print("Entry added to Freshbooks.", 'ok')
        self.log(response.text, silent=True)
        return response.text

    def get_fb_project_id(self, name):
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
            <request method="project.list">     <!-- Hey Freshbooks, --->
              <page>%i</page>                   <!-- your API sucks! --->
              <per_page>100</per_page>          <!-- Ever heard of JSON? --->
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
        return result

    # TODO: make this function more generic and move to Automation
    def fb_project_search(self, name):
        """Provides interactive search prompt."""
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
