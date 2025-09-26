
import os
import json
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/gmail.readonly']
SPREADSHEET_ID = '1U4XMkEr1z28Y_nkCzLwYiDj848o1ZW6WT6OPXc2aKjc' #test sheet
SPREADSHEET_ID = '102UjR-rv6X5k3p22x0wE6r-5BWe7e4-FNjx3SbB05Gg'
SHEET_NAME = 'Orders UK'
SECRET_KEY = os.getenv('SECRET_KEY', 'abc123')
GOOGLE_CREDENTIALS = os.getenv('GOOGLE_CREDENTIALS')
IS_RENDER = os.getenv('RENDER') == 'true'

QUEUE_FILE = '/tmp/order_queue.json' if IS_RENDER else 'order_queue.json'
FULFILLED_QUEUE_FILE = '/tmp/fulfilled_order_queue.json' if IS_RENDER else 'fulfilled_order_queue.json'
FAILED_ORDERS_FILE = '/tmp/failed_orders.json' if IS_RENDER else 'failed_orders.json'

def get_store_configs():
    """
    Loads environment-based configurations for different store regions.
    """

    stores = ["UK", "US", "EU"]
    store_configs = {}

    for store in stores:
        store_configs[store] = {
            "SHOP_NAME": os.getenv(f"{store}_SHOP_NAME", ""),
            "API_KEY": os.getenv(f"{store}_API_KEY", ""),
            "PASSWORD": os.getenv(f"{store}_PASSWORD", ""),
            "API_VERSION": os.getenv("API_VERSION", "2023-10"),  # fallback
            "SENDER_EMAIL": os.getenv(f"{store}_SENDER_EMAIL", ""),
            "SENDER_PASSWORD": os.getenv(f"{store}_SENDER_PASSWORD", ""),
            "COMPANY": os.getenv(f"{store}_COMPANY", "ML Performance"),
            "PHONE": os.getenv(f"{store}_PHONE", ""),
            "WEBSITE": os.getenv(f"{store}_WEBSITE", "www.mlperformance.co.uk"),
            "SENDGRID_API_KEY": os.getenv(f"DB_SENDGRID_API_KEY")
        }

    # If you have a special "Dumbledore" config as fallback
    dumbledore_config = {
        "SENDER_EMAIL": os.getenv("DB_SENDER_EMAIL", ""),
        "SENDER_PASSWORD": os.getenv("DB_SENDER_PASSWORD", ""),
        "SENDGRID_API_KEY": os.getenv(f"DB_SENDGRID_API_KEY")
    }

    return store_configs, dumbledore_config
