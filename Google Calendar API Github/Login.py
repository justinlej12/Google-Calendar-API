import datetime
import pytz
import os.path
import tkinter as tk
from Main import addEvent, commitHours
from tkinter import simpledialog, messagebox
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar"]

class Login:
    def __init__(self):
        self.is_authenticated = False
        self.username = None
        self.password = None
        self.creds = None

        if not self.is_authenticated:
            self.authenticate_user()  

        if self.is_authenticated:
            self.creds = self.get_google_creds()  
            self.run() 

    def authenticate_user(self):
        #python login for fun
        """Prompt for username and password only once."""
        root = tk.Tk()
        root.withdraw() 

        expected_username = "YOUR USERNAME HERE"
        expected_password = "YOUR PASSWORD HERE"

        self.username = simpledialog.askstring("Username", "Enter your username:")
        self.password = simpledialog.askstring("Password", "Enter your password:", show="*")

        if self.username == expected_username and self.password == expected_password:
            messagebox.showinfo("Success", "Login successful!")
            self.is_authenticated = True  
        else:
            messagebox.showerror("Error", "Invalid username or password.")
            self.is_authenticated = False  

    def get_google_creds(self):
        """Retrieve or refresh Google Calendar API credentials."""
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
        return creds

    def run(self):
        """Run the main functionality."""
        import sys
        if len(sys.argv) > 1:
            command = sys.argv[1]
            if command == "add":
                if len(sys.argv) > 4:
                    start_time = sys.argv[2]
                    end_time = sys.argv[3]
                    description = sys.argv[4]
                    addEvent(self.creds, start_time, end_time, description)
            elif command == "commit":
                if len(sys.argv) > 2:
                    hours = float(sys.argv[2])
                    category = sys.argv[3] if len(sys.argv) > 3 else "CODING"
                    commitHours(hours, category)
        else:
            self.show_greeting()
            self.list_todays_events()

    def show_greeting(self):
        """Show a time-appropriate greeting."""
        timezone = pytz.timezone("US/Eastern")
        curr_time = datetime.datetime.now(timezone)
        current_hour = curr_time.hour

        if 5 <= current_hour < 12:
            greeting = "Good morning Justin!"
        elif 12 <= current_hour < 17:
            greeting = "Good afternoon Justin!"
        elif 17 <= current_hour < 21:
            greeting = "Good evening Justin!"
        else:
            greeting = "What are you doing up so late Justin?"

        print(f"{greeting} The time is {curr_time.strftime('%I:%M %p')} and the date is {curr_time.date()}.")

    def list_todays_events(self):
        """Fetch and display today's events from Google Calendar."""
        try:
            service = build("calendar", "v3", credentials=self.creds)

            today = datetime.datetime.now().date()
            start_of_day = datetime.datetime.combine(today, datetime.time(0, 0, 0))
            end_of_day = datetime.datetime.combine(today, datetime.time(23, 59, 59))

            events_result = service.events().list(
                calendarId="YOUR CALENDAR ID HERE",
                timeMin=start_of_day.isoformat() + "Z",
                timeMax=end_of_day.isoformat() + "Z",
                singleEvents=True,
                orderBy="startTime",
                timeZone="America/New_York"
            ).execute()

            events = events_result.get("items", [])

            if not events:
                print("No events scheduled for today.")
                return

            print("Today's events:")
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                end = event["end"].get("dateTime", event["end"].get("date"))

                start_time = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
                end_time = datetime.datetime.fromisoformat(end.replace("Z", "+00:00"))

                formatted_start = start_time.strftime('%I:%M%p').lstrip('0')
                formatted_end = end_time.strftime('%I:%M%p').lstrip('0')

                event_description = event.get("summary", "No Description")

                print(f"{formatted_start} - {formatted_end} -> {event_description}")

        except HttpError as error:
            print(f"An error occurred: {error}")

if __name__ == "__main__":
    app = Login()