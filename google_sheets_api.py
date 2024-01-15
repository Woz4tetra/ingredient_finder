# Based on quickstart.py from Google Sheets API
# https://developers.google.com/sheets/api/quickstart/python
import json
import os.path
from typing import Generator, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


class GoogleSheetsAPI:
    def __init__(self, query: str) -> None:
        self.query = query
        self.creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists("token.json"):
            self.creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open("token.json", "w") as token:
                token.write(self.creds.to_json())

        with open("spreadsheet_id.json") as file:
            self.spreadsheet_id = json.load(file)["id"]

    def load_table(self) -> Generator[Tuple[str, ...], None, None]:
        """Shows basic usage of the Sheets API.
        Prints values from a sample spreadsheet.
        """
        service = build("sheets", "v4", credentials=self.creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        result = (
            sheet.values()
            .get(spreadsheetId=self.spreadsheet_id, range=self.query)
            .execute()
        )
        values = result.get("values", [])

        for row in values:
            yield row
