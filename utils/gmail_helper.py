from googleapiclient.discovery import build
from google.oauth2 import service_account
import base64
import re
import logging
from datetime import datetime
from utils.eta import calculate_eta_from_email
from services.sheets_service import get_service
from config import SPREADSHEET_ID

service = get_service()
logger = logging.getLogger(__name__)

def check_new_eta_emails():

    # Search for relevant emails (adjust query as needed)
    results = service.users().messages().list(
        userId='me',
        q='subject:"You\'ve been mentioned on order"'  # Example: adapt to your real subject
    ).execute()

    messages = results.get('messages', [])
    updates = []

    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        parts = msg_data['payload'].get('parts', [])
        body_data = ""

        # Extract body text
        for part in parts:
            if part['mimeType'] == 'text/plain':
                data = part['body']['data']
                body_data = base64.urlsafe_b64decode(data).decode('utf-8')

        # Parse order number, SKU, and ETA
        order_number_match = re.search(r'#(MLP\w+)', body_data)
        sku_match = re.search(r'(\d{3,})', body_data)
        eta_match = re.search(r'(\d+ to \d+ weeks|\d+ weeks|\d+ to \d+ days|\d+ days|No ETA|Ready|Early \w+ \d{4}|Mid \w+ \d{4}|Late \w+ \d{4}|Early \w+|Mid \w+|Late \w+)', body_data, re.IGNORECASE)

        if order_number_match and sku_match and eta_match:
            order_number = order_number_match.group(1)
            sku = sku_match.group(1)
            eta_str = eta_match.group(1)

            # Calculate exact ETA
            order_created = msg_data['internalDate']  # Milliseconds since epoch
            order_created_dt = datetime.fromtimestamp(int(order_created) / 1000.0).isoformat()
            exact_eta = calculate_eta_from_email(order_created_dt, eta_str)

            updates.append({
                "order_number": order_number,
                "sku": sku,
                "new_eta": eta_str,
                "exact_eta_date": exact_eta
            })

    return updates

def get_sheet_name_from_order_number(order_number: str) -> str:
    if "MLPEU" in order_number:
        return "Orders EU"
    elif "MLPUS" in order_number:
        return "Orders US"
    else:
        return "Orders UK"

def update_latest_eta_in_sheet(updates):
    sheet_updates = []
    for update in updates:
        order_number = update['order_number']
        sku = update['sku']
        new_eta = update['exact_eta_date']

        sheet_name = get_sheet_name_from_order_number(order_number)

        # Fetch data from that sheet
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f'{sheet_name}!A:N'
        ).execute()
        rows = result.get('values', [])
        header = rows[0]

        order_number_idx = header.index('Order Number')
        sku_idx = header.index('SKU')
        latest_eta_on_hand_idx = header.index('Latest ETA On Hand')

        for i, row in enumerate(rows[1:], start=2):
            if len(row) > max(order_number_idx, sku_idx):
                if row[order_number_idx] == order_number and row[sku_idx] == sku:
                    logger.info(f"Updating {sheet_name} row {i} with new ETA: {new_eta}")
                    sheet_updates.append({
                        'range': f'{sheet_name}!F{i}',  # Column F
                        'values': [[new_eta]]
                    })
                    break  # found it, stop searching

    # Perform batch update
    if sheet_updates:
        body = {'valueInputOption': 'RAW', 'data': sheet_updates}
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=SPREADSHEET_ID, body=body
        ).execute()
        logger.info(f"Updated {len(sheet_updates)} rows across all sheets.")
    else:
        logger.info("No rows matched for update.")

