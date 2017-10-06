# Start timetracking in Freshbooks based on your Toggl entries
from main import EasyLife

if __name__ == '__main__':
    el = EasyLife()
    el.create_fb_time_entries()