from core import Core
from zenpy import Zenpy
import datetime
import requests
import json


class Zendesk(Core):
    """Contains all Zendesk related operations."""

    def __init__(self):
        super(Zendesk, self).__init__()
        self.client = Zenpy(**self.zen_creds)  # initialize client connection to Zendesk

    def get_tickets(self, days=1):
        """Returns array of ticket objects for past X days."""
        yesterday = datetime.datetime.now() - datetime.timedelta(days=days)
        tickets = []
        for ticket in self.client.search(type="ticket", created_greater_than=(yesterday)):
            tickets.append(ticket)
        return tickets
