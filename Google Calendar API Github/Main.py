import datetime
from datetime import timedelta
import pytz
import sqlite3
import os.path
from dateutil import parser
import sys
import Login as L
from sys import argv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def create_hours_table():
    try:
        conn = sqlite3.connect('hours.db')
        cur = conn.cursor()
        print("Opened database successfully")
        cur.execute('''CREATE TABLE IF NOT EXISTS hours
            (DATE DATE NOT NULL,
            CATEGORY TEXT NOT NULL,
            HOURS INT NOT NULL);''')
        conn.commit()
        print("Table exists or created successfully.")
    except sqlite3.Error as error:
        print(f"An error occurred while creating the table: {error}")
    finally:
        conn.close()

def commitHours(hours, category):
    try:
        conn = sqlite3.connect('hours.db')
        cur = conn.cursor()
        print("Opened database successfully")
        
        date = datetime.date.today() 
        cur.execute('INSERT INTO hours VALUES(?, ?, ?);', (date, category, hours))
        conn.commit()
        print(f'{hours} hours committed to {category} successfully.')
        
    except sqlite3.Error as error:
        print(f"An error occurred: {error}")
    finally:
        conn.close()

def main():
    create_hours_table()
    app = L.Login()
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    if len(sys.argv) < 2:
        print("Usage: python3 upcomingevents.py <command> <args>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "add":
        if len(sys.argv) < 5:
            print("Usage: python3 upcomingevents.py add <start_time> <end_time> <description>")
            sys.exit(1)
        start_time = sys.argv[2] 
        end_time = sys.argv[3]    
        description = sys.argv[4] 
        addEvent(creds, start_time, end_time, description)
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("Usage: python3 upcomingevents.py delete <description>")
            sys.exit(1)
        description = sys.argv[2]  
        events = get_upcoming_events(creds)
        deleteEventByDescription(creds, events, description)

    elif command == "availability":
        availability = optimalTimes(creds)
        print(availability)

    elif command == "commit":
        if len(sys.argv) < 3:
            print("Usage: python3 upcomingevents.py commit <hours> [category]")
            sys.exit(1)
        hours = float(sys.argv[2]) 
        category = sys.argv[3] if len(sys.argv) > 3 else 'CODING'  
        commitHours(hours, category)

# Example usage:
# python3 upcomingevents.py add 3:00PM 6:00PM "practice"
# python3 upcomingevents.py delete "practice"
# python3 upcomingevents.py availability

def parse_time(time_str):
    time_obj = datetime.datetime.strptime(time_str, "%I:%M%p")
    return time_obj

def addEvent(creds, start_time_str, end_time_str, description):
    eastern = pytz.timezone("America/New_York")
    today = datetime.datetime.now().date()  
    start_dt = eastern.localize(datetime.datetime.strptime(f"{today} {start_time_str}", "%Y-%m-%d %I:%M%p"))
    end_dt = eastern.localize(datetime.datetime.strptime(f"{today} {end_time_str}", "%Y-%m-%d %I:%M%p"))

    start_formatted = start_dt.isoformat()
    end_formatted = end_dt.isoformat()

    event = {
        'summary': description,
        'start': {
            'dateTime': start_formatted,
            'timeZone': 'America/New_York',
        },
        'end': {
            'dateTime': end_formatted,
            'timeZone': 'America/New_York',
        },
    }

    service = build("calendar", "v3", credentials=creds)
    
    event_result = service.events().insert(calendarId="YOUR CALENDAR ID HERE", body=event).execute()
    
    print(f"Event created: {event_result.get('htmlLink')}")


def deleteEventByDescription(creds, events, description):
    service = build("calendar", "v3", credentials=creds)

    description_normalized = description.strip().lower() 

    for event in events:
        event_description = event.get('summary', '').strip().lower()

        if description_normalized == event_description:
            service.events().delete(
                calendarId="YOUR CALENDAR ID HERE",  
                eventId=event['id']
            ).execute()
            print(f"Event '{description}' deleted successfully.")
            return
    print(f"Event '{description}' not found.")


def get_upcoming_events(creds):
    """Fetch the upcoming events from Google Calendar."""
    service = build("calendar", "v3", credentials=creds)

    # Get the list of events
    events_result = service.events().list(
        calendarId="YOUR CALENDAR ID HERE",  
        timeMin=datetime.datetime.now(datetime.timezone.utc).isoformat(),  
        maxResults=10,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    return events_result.get('items', [])

def optimalTimes(creds):
    events = get_upcoming_events(creds)
    eastern = pytz.timezone("America/New_York")
    
    # Set the start and end of the day
    start_of_day = eastern.localize(datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
    end_of_day = eastern.localize(datetime.datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999))

    # Sort events by start time
    events.sort(key=lambda event: event['start'].get('dateTime'))

    # Initialize available times list
    available_slots = []

    # Check for free time before the first event
    if events:
        first_event_start_str = events[0]['start'].get('dateTime')
        first_event_start = datetime.datetime.fromisoformat(first_event_start_str)
        if start_of_day < first_event_start:
            available_slots.append((start_of_day, first_event_start))

    # Find gaps between consecutive events
    for i in range(len(events) - 1):
        end_current_event_str = events[i]['end'].get('dateTime')
        start_next_event_str = events[i + 1]['start'].get('dateTime')
        end_current_event = datetime.datetime.fromisoformat(end_current_event_str)  
        start_next_event = datetime.datetime.fromisoformat(start_next_event_str)  
        if end_current_event < start_next_event:
            available_slots.append((end_current_event, start_next_event))

    # Check for free time after the last event
    if events:
        last_event_end_str = events[-1]['end'].get('dateTime')
        last_event_end = datetime.datetime.fromisoformat(last_event_end_str)  
        if last_event_end < end_of_day:
            available_slots.append((last_event_end, end_of_day))

    # Find the largest free slot
    free = datetime.timedelta(0)
    bestStart, bestEnd = None, None
    for timeSlot in available_slots:
        difference = timeSlot[1] - timeSlot[0]
        if difference > free:
            free = difference
            bestStart, bestEnd = timeSlot[0], timeSlot[1]

    # Format the free slots
    free_slots_str = "Free Slots\n----------------\n"
    for slot in available_slots:
        start_str = slot[0].strftime("%I:%M%p").lstrip("0")
        end_str = slot[1].strftime("%I:%M%p").lstrip("0")
        free_slots_str += f"{start_str} - {end_str}\n"

    # Format the most available time slot and its duration
    best_start_str = bestStart.strftime("%I:%M%p").lstrip("0")
    best_end_str = bestEnd.strftime("%I:%M%p").lstrip("0")
    
    # Calculate duration
    duration = free
    hours = duration.seconds // 3600
    minutes = (duration.seconds % 3600) // 60
    
    # Build the duration string
    if minutes == 0:
        duration_str = f"{hours} hours"
    else:
        duration_str = f"{hours} hours and {minutes} minutes"

    # Return the formatted string
    return (f"{free_slots_str}----------------\n"
            f"The most optimal time slot you have is from {best_start_str} to {best_end_str} for {duration_str}.")
 
if __name__ == "__main__":
  main()