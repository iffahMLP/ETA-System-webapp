
import os
import json
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = '1U4XMkEr1z28Y_nkCzLwYiDj848o1ZW6WT6OPXc2aKjc'
SHEET_NAME = 'Orders 3.2'
SECRET_KEY = os.getenv('SECRET_KEY', 'abc123')
GOOGLE_CREDENTIALS = os.getenv('GOOGLE_CREDENTIALS')
IS_RENDER = os.getenv('RENDER') == 'true'

QUEUE_FILE = '/tmp/order_queue.json' if IS_RENDER else 'order_queue.json'
FAILED_ORDERS_FILE = '/tmp/failed_orders.json' if IS_RENDER else 'failed_orders.json'
