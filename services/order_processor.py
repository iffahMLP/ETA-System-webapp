
import logging
import json
from flask import jsonify
from datetime import datetime
from config import SPREADSHEET_ID, get_store_configs
from utils.helpers import format_date
from services.sheets_service import get_service, update_sheet_with_retry
from utils.formulas import delete_rows, delete_duplicate_rows
from utils.eta import get_eta, build_eta_lookup, load_sheet_data
from utils.email_utils import first_draft, send_email, follow_up_draft
from utils.shopify_graphql import update_note, get_order_data

logger = logging.getLogger(__name__)
service = get_service()

stores = ['UK', 'US', 'EU']

ARRIVAL_SHEET_ID = "1hElJ_sWXGy1-Psk9x2EPrXeZuFjKreR_B7cj3voxBIA"
arrival_data = load_sheet_data(ARRIVAL_SHEET_ID, "General!A1:G")
eta_map = build_eta_lookup(arrival_data)

WEBSTOCKS_SHEET_ID = "102UjR-rv6X5k3p22x0wE6r-5BWe7e4-FNjx3SbB05Gg"
webstocks_data = load_sheet_data(WEBSTOCKS_SHEET_ID, "webstocks!A2:A")
stock_data = set(row[0] for row in webstocks_data if row)  # Flatten to set of SKUs/barcodes

def group_skus_by_vendor(line_items):
    sku_by_vendor = {}
    has_vin_by_vendor = {}
    for item in line_items:
        sku, vendor, vin = item.get('sku', 'Unknown SKU'), item.get('vendor', 'Unknown Vendor'), item.get('vin', '')
        if vendor not in sku_by_vendor:
            sku_by_vendor[vendor] = [sku]
            has_vin_by_vendor[vendor] = bool(vin)
        else:
            sku_by_vendor[vendor].append(sku)
            if vin:
                has_vin_by_vendor[vendor] = True
    return sku_by_vendor, has_vin_by_vendor

def get_last_row(SPREADSHEET_ID, SHEET_NAME):
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f'{SHEET_NAME}!A:A'
        ).execute()
        values = result.get('values', [])
        return len(values) + 1 if values else 2
    except Exception as e:
        logger.error(f"Error getting last row: {str(e)}")
        return 2

def get_sheet_id(SPREADSHEET_ID, SHEET_NAME):
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    for sheet in spreadsheet['sheets']:
        if sheet['properties']['title'] == SHEET_NAME:
            return sheet['properties']['sheetId']
    raise Exception(f"Sheet ID not found for {SHEET_NAME}")

def process_order(data):
    if not service:
        logger.error("Google Sheets service not initialized")
        return False
    try:
        store = data.get("store")
        SHEET_NAME = f"Orders {store}"
        order_number = data.get("order_number", "Unknown")
        logger.info(f"Processing order {order_number}")
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f'{SHEET_NAME}!A:A'
        ).execute()
        order_numbers = [row[0] for row in result.get('values', []) if row]
        if str(order_number) in order_numbers:
            logger.warning(f"Duplicate order {order_number}")
            return True

        order_id = data.get("order_id", "")
        order_country = data.get("order_country", "Unknown")
        customer_lang = data.get("customer_lang", "en-GB")
        customer_email = data.get("customer_email", "Unknown")
        customer_name = data.get("customer_name", "Unknown")
        is_dealer = data.get("is_dealer", False)
        order_created = format_date(data.get("order_created", ""))
        line_items = data.get("line_items", [])
        
        if not line_items:
            logger.warning(f"Order {order_number} has no line items")
            return True

        rows_data = []
        for idx, item in enumerate(line_items):
            title, quantity, sku, vendor, barcode = item['title'], item['quantity'], item['sku'], item['vendor'], item['barcode']
            inventory, url = item['inventory'], item['url']
            eta = get_eta(sku, vendor, store, barcode, inventory, order_created, eta_map, stock_data)
            
            item["Latest ETA On Hand"] = eta
            item["Index"] = idx  # Store index for later updates

            if "mlperformance.co.uk" in url:
                order_country = "GB"
            elif "mlpautoteile.de" in url and customer_lang == "en-DE":
                order_country = "DE"
            elif store == "US":
                order_country = "GB"
            elif "mlpautoteile.de" in url and customer_lang != "en-DE":
                order_country = "GB"

            rows_data.append([order_number, title, quantity, sku, vendor, eta, customer_email])

        start_row = max(2, get_last_row(SPREADSHEET_ID, SHEET_NAME))
        range_to_write = f'{SHEET_NAME}!A{start_row}'
        body = {'values': rows_data}
        update_sheet_with_retry(service, SPREADSHEET_ID, range_to_write, body)

        delete_rows()
        delete_duplicate_rows()

        # Check if rows still exist after deletion
        result_check = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SHEET_NAME}!A:A'
        ).execute()
        current_order_numbers = [row[0] for row in result_check.get('values', []) if row]

        if order_number == '#MLP152009' and order_number in current_order_numbers:
            # Send email
            if not is_dealer and customer_email and customer_email not in ['sales@mlperformanceusa.com', 'hello@masata.co.uk']:
                store_configs, _ = get_store_configs()
                store_db = store_configs.get(store, store_configs["UK"])  # fallback to UK

                order_info = {
                    "Order Number": order_number,
                    "Order ID": order_id,
                    "Line Items": line_items
                }

                draft = first_draft(order_info, customer_name, store_db, store, order_country)
                send_email(customer_email, draft, store_db)

                # Update columns I and K
                for item in line_items:
                    row_index = start_row + item["Index"]
                    service.spreadsheets().values().update(
                        spreadsheetId=SPREADSHEET_ID,
                        range=f'{SHEET_NAME}!H{row_index}',
                        valueInputOption='RAW',
                        body={'values': [[str(item["Latest ETA On Hand"])]]}
                    ).execute()
                    service.spreadsheets().values().update(
                        spreadsheetId=SPREADSHEET_ID,
                        range=f'{SHEET_NAME}!J{row_index}',
                        valueInputOption='RAW',
                        body={'values': [[f"Sent On {datetime.today().strftime('%d-%m-%Y')}"]]}
                    ).execute()

                if store == "US":
                    update_note(order_info, store_configs["UK"])
                    order_info['Order ID'] = 'gid://shopify/Order/' + str(data.get("order_id_us", ""))
                update_note(order_info, store_db)

                logger.info(f"Email sent to {customer_email} and spreadsheet updated for {order_number}")
            else:
                logger.info(f"No email sent for dealer or skipped emails for {order_number}")
        else:
            logger.info(f"Order {order_number} was removed as duplicate or invalid. Skipping email.")

        return True
    except Exception as e:
        logger.error(f"Error processing order {order_number}: {str(e)}")
        return False


def remove_fulfilled_sku(data):
    try:
        store = data.get("store")
        SHEET_NAME = f"Orders {store}"
        order_number = data.get("order_number", "Unknown")
        line_items = data.get("line_items", [])
        logger.info(f"Processing remove_fulfilled_sku for order {order_number}, line_items: {line_items}")

        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f'{SHEET_NAME}!A:N'
        ).execute()
        values = result.get('values', [])
        logger.info(f"Retrieved {len(values)} rows from sheet")

        rows_to_delete = []

        for i, row in enumerate(values):
            if len(row) > 1 and row[0] == order_number:
                row_sku = str(row[3])
                if not line_items:
                    rows_to_delete.append(i)
                    continue
                for item in line_items:
                    sku = str(item.get('sku'))
                    if sku == row_sku:
                        rows_to_delete.append(i)

        if rows_to_delete:
            rows_to_delete.sort(reverse=True)
            sheet_id = get_sheet_id(SPREADSHEET_ID, SHEET_NAME)
            requests = [{
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": i,
                        "endIndex": i + 1
                    }
                }
            } for i in rows_to_delete]
            service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID, body={"requests": requests}
            ).execute()
            logger.info(f"Deleted rows: {rows_to_delete}")


        return jsonify({"status": "success", "message": "Fulfilled SKUs removed or rows deleted"}), 200
    except Exception as e:
        logger.error(f"Error in remove_fulfilled_sku for order {order_number}: {str(e)}")
        return jsonify({"status": "error", "message": f"Processing failed: {str(e)}"}), 500


def check_and_notify_eta_updates():
    for store in stores:
        logger.info(f"Checking ETA updates for {store} store")
        try:
            SHEET_NAME = f"Orders {store}"
            # Fetch the data
            result = service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID, range=f'{SHEET_NAME}!A:N'
            ).execute()
            rows = result.get('values', [])

            if not rows:
                logger.info("No data found.")
                return

            # Identify indices
            header = rows[0]
            latest_eta_on_hand_idx = header.index('Latest ETA On Hand')
            email_idx = header.index('Email')
            latest_eta_quoted_idx = header.index('Latest ETA Quoted')
            order_number_idx = header.index('Order Number')
            sku_idx = header.index('SKU')
            title_idx = header.index('Product')
            quantity_idx = header.index('Quantity')

            # Prepare updates
            updates = []
            for i, row in enumerate(rows[1:], start=2):  # Skip header, 1-based index
                latest_eta_on_hand = row[latest_eta_on_hand_idx] if len(row) > latest_eta_on_hand_idx else ""
                latest_eta_quoted = row[latest_eta_quoted_idx] if len(row) > latest_eta_quoted_idx else ""
                email = row[email_idx] if len(row) > email_idx else ""
                order_number = row[order_number_idx] if len(row) > order_number_idx else ""
                sku = row[sku_idx] if len(row) > sku_idx else ""
                title = row[title_idx] if len(row) > title_idx else ""
                quantity = row[quantity_idx] if len(row) > quantity_idx else ""
                

                # Check for mismatch
                if latest_eta_quoted and latest_eta_on_hand and latest_eta_on_hand != latest_eta_quoted and order_number == "#MLP152009":
                    logger.info(f"ETA update found for row {i}: {email}")
                    
                    store_configs, _ = get_store_configs()
                    store_db = store_configs.get(store, store_configs["UK"])  # fallback to UK

                    order_info = {
                        "Order Number": order_number,
                        "Order ID": '',
                        "Line Items": [{
                            "title": title,  # Adjust based on your actual column index for title
                            "quantity": quantity,
                            "sku": sku,
                            "Latest ETA On Hand": latest_eta_on_hand
                        }]
                    }

                    graphql_order_data = get_order_data(order_number, store_db)
                    order_info['Order ID'] = graphql_order_data.get('Order ID', '')
                    domain = graphql_order_data.get('Domain', '')
                    customer_lang = graphql_order_data.get('Locale', 'en-GB')
                    customer_name = graphql_order_data.get('Customer First Name', 'Customer')

                    if "mlperformance.co.uk" in domain:
                        order_country = "GB"
                    elif "mlpautoteile.de" in domain and customer_lang == "en-DE":
                        order_country = "DE"
                    elif store == "US":
                        order_country = "GB"
                    elif "mlpautoteile.de" in domain and customer_lang != "en-DE":
                        order_country = "GB"
            
                    draft = follow_up_draft(order_info, customer_name, store_db, store, order_country)
                    send_email(email, draft, store_db)  # your existing email sender!

                    # Update Latest ETA Quoted
                    updates.append({
                        'range': f'{SHEET_NAME}!H{i}',  # Column H for Latest ETA Quoted
                        'values': [[latest_eta_on_hand]]
                    })

                    updates.append({
                        'range': f'{SHEET_NAME}!K{i}',  # Column J: Last Email Sent?
                        'values': [[f"Sent On {datetime.today().strftime('%d-%m-%Y')}"]]
                    })

                    update_note(order_info, store_db)
                    if store == "US":
                        store_db = store_configs["UK"]
                        graphql_order_data = get_order_data(order_number, store_db)
                        order_info['Order ID'] = graphql_order_data.get('Order ID', '')
                        update_note(order_info, store_configs["UK"])
                    
            # Batch update to Google Sheets
            if updates:
                body = {'valueInputOption': 'RAW', 'data': updates}
                service.spreadsheets().values().batchUpdate(
                    spreadsheetId=SPREADSHEET_ID, body=body
                ).execute()
                logger.info("Updated Latest ETA Quoted for all notified rows.")
            else:
                logger.info("No ETA updates found.")

        except Exception as e:
            logger.error(f"Error in check_and_notify_eta_updates: {str(e)}")
