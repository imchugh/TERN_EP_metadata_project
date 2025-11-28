#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 28 10:53:08 2025

@author: imchugh
"""

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# --- Configuration ---
SERVICE_ACCOUNT_FILE = "service_account.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = "YOUR_SPREADSHEET_ID"  # From the Sheet URL
READ_RANGE = "Sheet1!A1:D5"
WRITE_RANGE = "Sheet1!A10"

# --- Authenticate and build service ---
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build("sheets", "v4", credentials=creds)

# --- READ from the sheet ---
result = service.spreadsheets().values().get(
    spreadsheetId=SPREADSHEET_ID,
    range=READ_RANGE
).execute()

values = result.get("values", [])
print("📖 Data read from sheet:")
for row in values:
    print(row)

# --- WRITE to the sheet ---
values_to_write = [
    ["Timestamp", "Message"],
    ["Now", "Hello from Python!"]
]

body = {"values": values_to_write}

service.spreadsheets().values().update(
    spreadsheetId=SPREADSHEET_ID,
    range=WRITE_RANGE,
    valueInputOption="RAW",
    body=body
).execute()

print("✅ Data written successfully!")
