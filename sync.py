# Create Toggl projects based on Zendesk tickets
from main import Automation
import sys

if __name__ == '__main__':
    try:
        days = int(sys.argv[1])
    except:
        days = 1
    auto = Automation()
    auto.sync(days)