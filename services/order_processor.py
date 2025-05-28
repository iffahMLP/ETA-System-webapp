
import logging
import json
from flask import jsonify
from config import SPREADSHEET_ID, SHEET_NAME
from utils.helpers import format_date
from services.sheets_service import get_service, update_sheet_with_retry
from utils.formulas import apply_formulas, delete_rows, delete_duplicate_rows

logger = logging.getLogger(__name__)
service = get_service()

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

def get_last_row():
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f'{SHEET_NAME}!A:N'
        ).execute()
        values = result.get('values', [])
        return len(values) + 1 if values else 2
    except Exception as e:
        logger.error(f"Error getting last row: {str(e)}")
        return 2

def process_order(data):
    if not service:
        logger.error("Google Sheets service not initialized")
        return False
    try:
        order_number = data.get("order_number", "Unknown")
        logger.info(f"Processing order {order_number}")
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f'{SHEET_NAME}!B:B'
        ).execute()
        order_numbers = [row[0] for row in result.get('values', []) if row]
        if str(order_number) in order_numbers:
            logger.warning(f"Duplicate order {order_number}")
            return True

        order_id = data.get("order_id", "").replace("gid://shopify/Order/", "https://admin.shopify.com/store/mlperformance/orders/")
        order_country = data.get("order_country", "Unknown")
        order_created = format_date(data.get("order_created", ""))
        line_items = data.get("line_items", [])
        order_total = float(data.get("order_total", "0") or 0)

        tags = data.get("tags", [])
        if isinstance(tags, str):
            tags_list = [tag.strip() for tag in tags.split(",")]
        else:
            tags_list = tags
        has_vin_tag = any(tag in ["Call for VIN Alert Sent", "VIN Request Email Sent"] for tag in tags_list)
        status = "TBC (No)" if order_total > 500 and has_vin_tag else ""

        if not line_items:
            logger.warning(f"Order {order_number} has no line items")
            return True

        sku_by_vendor, has_vin_by_vendor = group_skus_by_vendor(line_items)
        rows_data = [
            [order_created, order_number, order_id, ', '.join(skus), vendor, order_country, "", "", "", status, "", "Please Check VIN" if has_vin_by_vendor[vendor] else "", "", ""]
            for vendor, skus in sku_by_vendor.items()
        ]

        start_row = max(2, get_last_row())
        range_to_write = f'{SHEET_NAME}!A{start_row}'
        body = {'values': rows_data}
        update_sheet_with_retry(service, SPREADSHEET_ID, range_to_write, body)

        apply_formulas()
        delete_rows()
        delete_duplicate_rows()

        return True
    except Exception as e:
        logger.error(f"Error processing order {order_number}: {str(e)}")
        return False


def add_backup_shipping_note(data):
    try:
        order_number = data.get("order_number")
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f'{SHEET_NAME}!B:B'
        ).execute()
        order_numbers = [row[0] for row in result.get('values', []) if row and row[0]]

        if str(order_number) in order_numbers:
            logger.warning(f"Duplicate order number {order_number} found in column B, skipping processing")
            return jsonify({"status": "skipped", "message": f"Order {order_number} is a duplicate"}), 200

        order_id = data.get("order_id").replace("gid://shopify/Order/", "https://admin.shopify.com/store/mlperformance/orders/")
        order_country = data.get("order_country")
        backup_note = data.get("backup_shipping_note")
        order_created = format_date(data.get("order_created"))
        line_items = data.get("line_items", [])
        order_total = float(data.get("order_total", "0") or 0)

        tags = data.get("tags", [])
        if isinstance(tags, str):
            tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        elif isinstance(tags, list):
            tags_list = [tag.strip() for tag in tags if isinstance(tag, str)]
        else:
            tags_list = []
        has_vin_tag = any(tag in ["Call for VIN Alert Sent", "VIN Request Email Sent"] for tag in tags_list)
        status = "TBC (No)" if order_total > 500 and has_vin_tag else ""

        sku_by_vendor, has_vin_by_vendor = group_skus_by_vendor(line_items)
        rows_data = [
            [order_created, order_number, order_id, ', '.join(skus), vendor, order_country, "", "", "", status, "", "Please Check VIN" if has_vin_by_vendor[vendor] else "", backup_note, ""]
            for vendor, skus in sku_by_vendor.items()
        ]

        start_row = max(2, get_last_row())
        range_to_write = f'{SHEET_NAME}!A{start_row}:N{start_row + len(rows_data) - 1}'
        body = {'values': rows_data}
        update_sheet_with_retry(service, SPREADSHEET_ID, range_to_write, body)

        apply_formulas()
        delete_rows()
        delete_duplicate_rows()

        return jsonify({"status": "success", "message": "Data with backup shipping note added successfully"}), 200
    except Exception as e:
        logger.error(f"Error in add_backup_shipping_note for order {order_number}: {str(e)}")
        return jsonify({"status": "error", "message": f"Processing failed: {str(e)}"}), 500

def remove_fulfilled_sku(data):
    try:
        order_number = data.get("order_number", "Unknown").lstrip("#")
        line_items = data.get("line_items", [])
        logger.info(f"Processing remove_fulfilled_sku for order {order_number}, line_items: {line_items}")

        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=f'{SHEET_NAME}!A:N'
        ).execute()
        values = result.get('values', [])
        logger.info(f"Retrieved {len(values)} rows from sheet")

        rows_to_delete = []
        rows_to_update = []

        for i, row in enumerate(values):
            if len(row) > 1 and row[1].lstrip("#") == order_number:
                skus = row[3].split(', ') if len(row) > 3 and row[3] else []
                if not line_items:
                    rows_to_delete.append(i)
                    continue
                for item in line_items:
                    sku = item.get('sku')
                    if sku in skus:
                        skus.remove(sku)
                if not skus:
                    rows_to_delete.append(i)
                else:
                    row[3] = ', '.join(skus)
                    rows_to_update.append((i, row))

        if rows_to_delete:
            rows_to_delete.sort(reverse=True)
            sheet_id = SPREADSHEET_ID
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

        for i, row in rows_to_update:
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f'{SHEET_NAME}!A{i+1}:N{i+1}',
                valueInputOption='RAW',
                body={'values': [row]}
            ).execute()
            logger.info(f"Updated row {i+1} with SKUs: {row[3]}")

        return jsonify({"status": "success", "message": "Fulfilled SKUs removed or rows deleted"}), 200
    except Exception as e:
        logger.error(f"Error in remove_fulfilled_sku for order {order_number}: {str(e)}")
        return jsonify({"status": "error", "message": f"Processing failed: {str(e)}"}), 500
