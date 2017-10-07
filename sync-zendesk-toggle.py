# Create Toggl projects based on Zendesk tickets
from main import EasyLife
import sys

if __name__ == '__main__':
    try:
        days = int(sys.argv[1])
    except:
        days = 1
    el = EasyLife()
    el.sync(days)