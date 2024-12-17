import os
import json

my_secret = os.environ.get("GOOGLE_SERVICE")
folder_id = os.environ.get("FOLDER_ID")
my_secret = json.loads(my_secret) if my_secret else None


import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from utils import compute_hash, HashGuard

# Set up Google API credentials
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly"
]
creds = Credentials.from_service_account_info(my_secret, scopes=SCOPES) if my_secret else None

# Initialize gspread and Google Drive API clients
client = gspread.authorize(creds) if creds else None
drive_service = build('drive', 'v3', credentials=creds) if client else None


# Function to find a folder in Google Drive by name and return its ID
def find_folder_id(folder_name):
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    folders = results.get('files', [])
    if not folders:
        print(f"No folder found with name: {folder_name}")
        return None
    else:
        folder_id = folders[0]['id']  # Take the first matching folder
        print(f"Found folder '{folder_name}' with ID: {folder_id}")
        return folder_id

# Function to list all Google Sheets in a specific folder
def list_sheets_in_folder(folder_id):
    folder_metadata = drive_service.files().get(fileId=folder_id, fields="id, name, mimeType").execute()
    if folder_metadata['mimeType'] != 'application/vnd.google-apps.folder':
        raise ValueError(f"The provided ID '{folder_id}' is not a folder.")

    query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet'"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    sheets = results.get('files', [])
    if not sheets:
        print("No Google Sheets found in the folder.")
        return []
    else:
        print("Sheets found:")
        for sheet in sheets:
            print(f"- {sheet['name']} (ID: {sheet['id']})")
        return sheets

# Function to read and print content of all sheets in a folder
# Throws FileNotFoundError error if not able to read

# Returns falsey data if no data needs to be updated
# Returns {...} if data for processing found.
def read_sheets_google_api():
    
    if drive_service is None:
        raise FileNotFoundError("Google Sheets API not configured.")

    hash_guard = HashGuard("google_api")

    output = {}
    sheets = list_sheets_in_folder(folder_id)
    for sheet in sheets:
        sheet_id = sheet['id']
        google_sheet = client.open_by_key(sheet_id)
        
        if sheet['name'] == "Publish":
            continue
        
        print(f"\nReading '{sheet['name']}'...")
        for worksheet in google_sheet.worksheets():
            print(f"  Worksheet: {worksheet.title}")
            records = worksheet.get_all_values()

            # Convert the list of dictionaries to an array of arrays format
            if records:
                hash_record = hash_guard.get(sheet_id)
                if hash_record is not None and type(hash_record) != str:
                    hash_record = hash_record.get("hash", None)
                current_hash = compute_hash(records)

                if hash_record and hash_record == current_hash:
                    print("  Skip: hash matches previous version.")
                    continue
                hash_guard.update(sheet_id, sheet['name'], current_hash)
                # Combine headers and rows
                output[sheet['name']] = records
            else:
                output[sheet['name']] = None
    return output, hash_guard
