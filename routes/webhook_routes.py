
from flask import Blueprint, request, jsonify
import logging
import json
from config import SECRET_KEY
from services.queue_handler import load_queue, save_queue, process_queue
from services.order_processor import add_backup_shipping_note, remove_fulfilled_sku
from utils.helpers import clean_json

webhook_bp = Blueprint('webhook_routes', __name__)
logger = logging.getLogger(__name__)

@webhook_bp.route('/webhook', methods=['POST'])
def handle_webhook():
    provided_key = request.args.get('key')
    if provided_key != SECRET_KEY:
        return jsonify({"error": "Access Denied"}), 403

    logger.info(f"Raw request data: {request.data.decode('utf-8')}")
    logger.info(f"Request headers: {request.headers}")

    queue = load_queue()
    order_number = "Unknown"
    raw_data = request.data
    cleaned_data = clean_json(raw_data)

    try:
        data = json.loads(cleaned_data)
        if not data:
            queue.append({"error": "No valid JSON data after cleaning", "order_number": order_number, "raw_data": raw_data.decode('utf-8')})
            save_queue(queue)
            return jsonify({"status": "queued", "message": "Order queued with error: No valid JSON data"}), 200

        order_number = data.get("order_number", "Unknown")
        action = request.args.get('action', '')

        if action == 'addNewOrders':
            queue.append(data)
            save_queue(queue)
            process_queue()
            return jsonify({"status": "queued", "message": f"Order {order_number} added to queue"}), 200
        elif action == 'removeFulfilledSKU':
            return remove_fulfilled_sku(data)
        else:
            queue.append({"error": f"Invalid action: {action}", "order_number": order_number, "raw_data": raw_data.decode('utf-8')})
            save_queue(queue)
            return jsonify({"status": "queued", "message": f"Order {order_number} queued with error: Invalid action"}), 200

    except ValueError as e:
        logger.error(f"Failed to parse JSON: {str(e)}")
        queue.append({"error": f"Invalid JSON: {str(e)}", "order_number": order_number, "raw_data": raw_data.decode('utf-8')})
        save_queue(queue)
        return jsonify({"status": "queued", "message": f"Order {order_number} queued with error: Invalid JSON"}), 200
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        queue.append({"error": str(e), "order_number": order_number, "raw_data": raw_data.decode('utf-8')})
        save_queue(queue)
        return jsonify({"status": "queued", "message": f"Order {order_number} queued with error: {str(e)}"}), 200
