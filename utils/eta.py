from datetime import datetime, timedelta
import re

from services.sheets_service import get_service

def load_sheet_data(spreadsheet_id, sheet_name):
    service = get_service()
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=sheet_name
    ).execute()
    return result.get("values", [])


def extract_days(eta: str) -> int | None:
    match = re.findall(r'\d+', eta)
    if not match:
        return None
    days = int(match[-1])
    return days * 5 if "week" in eta.lower() else days

def add_business_days(start_date_str: str, days_to_add: int) -> str:
    date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
    count = 0
    while count < days_to_add:
        date += timedelta(days=1)
        if date.weekday() < 5:
            count += 1
    return date.strftime("%d/%m/%Y")

def calculate_eta(order_created: str, eta_str: str) -> str:
    days = extract_days(eta_str)
    if not days:
        return "ETA Not Available"
    return add_business_days(order_created, days)

def build_eta_lookup(arrival_data):
    eta_map = {}
    for row in arrival_data[1:]:
        sku_or_vendor = str(row[1]).strip()
        store = str(row[6]).strip().lower() if len(row) > 6 and row[6] else ""
        badge = str(row[2]).strip() if len(row) > 2 else ""

        eta_map[f"{sku_or_vendor}|{store}"] = badge
        eta_map[sku_or_vendor] = eta_map.get(sku_or_vendor) or badge
    return eta_map

def get_eta(sku, vendor, store, barcode, order_created, eta_map, stock_data):
    store_key = store.lower().strip()
    check_stock = "3 - 4 Days" if sku in stock_data or barcode in stock_data else None

    lookup_keys = [
        f"{sku}|{store_key}",
        sku,
        f"{vendor}|{store_key}",
        vendor
    ]

    eta = check_stock
    for key in lookup_keys:
        if key in eta_map:
            eta = eta_map[key]
            break

    if not eta:
        return "Awaiting Update"

    if eta.lower() == "stock order":
        eta = "2 weeks"

    if any(x in eta.lower() for x in ["day", "week"]):
        return calculate_eta(order_created, eta)
    if "no eta" in eta.lower():
        return "Awaiting Update"
    return eta
