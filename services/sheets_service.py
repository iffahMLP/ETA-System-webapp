
import json
import logging
import time
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
from config import SCOPES, GOOGLE_CREDENTIALS, IS_RENDER

logger = logging.getLogger(__name__)
service = None

print("GOOGLE_CREDENTIALS set:", bool(GOOGLE_CREDENTIALS))

def init_service():
    global service
    try:
        if IS_RENDER:
            if not GOOGLE_CREDENTIALS:
                raise ValueError("GOOGLE_CREDENTIALS environment variable is not set on Render")
            logger.info("Loading credentials from GOOGLE_CREDENTIALS on Render")
            creds = service_account.Credentials.from_service_account_info(
                json.loads(GOOGLE_CREDENTIALS), scopes=SCOPES)
        else:
            logger.info("Running locally, falling back to credentials.json")
            creds = service_account.Credentials.from_service_account_file(
                'credentials.json', scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        logger.info("Google Sheets API initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Google Sheets API: {str(e)}")
        service = None

def get_service():
    return service

def update_sheet_with_retry(service, spreadsheet_id, range_to_write, body, max_attempts=3, valueInputOption='RAW'):
    for attempt in range(max_attempts):
        try:
            return service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id, range=range_to_write,
                valueInputOption=valueInputOption, body=body
            ).execute()
        except HttpError as e:
            logger.error(f"Attempt {attempt + 1} failed for range {range_to_write}: {str(e)}")
            if attempt < max_attempts - 1:
                time.sleep(2 ** attempt)
            else:
                raise
        except Exception as e:
            logger.error(f"Unexpected error updating sheet: {str(e)}")
            raise
