from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
import datetime
import os.path

class GCalendarClient():

    '''
    Api configurada, conectou corretamente, mas usando a credencia baixada
    adptar para receber a credencial do Db ou .env, e verificar qual os
    EndPoints que serão necessario para logica de negocio da aplicação
    '''
    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

    def main(self):

        creds = None

        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", self.SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", self.SCOPES
            )
            creds = flow.run_local_server(port=0)
            
            with open("token.json", "w") as token:
                token.write(creds.to_json())
                

        try:
            service = build("calendar", "v3", credentials=creds)

            
            now = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
            print("Getting the upcoming 10 events")
            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=now,
                    maxResults=10,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])

            if not events:
                print("No upcoming events found.")
                return

            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                print(start, event)

        except HttpError as error:
            print(f"An error occurred: {error}")


if __name__ == "__main__":
  f = GCalendarClient()
  f.main()