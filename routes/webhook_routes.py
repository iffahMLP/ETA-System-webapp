from flask import Blueprint, request, jsonify
import logging
import json
from config import SECRET_KEY
from config import QUEUE_FILE, FULFILLED_QUEUE_FILE
from services.queue_handler import load_queue, save_queue, process_queue
from services.order_processor import process_order, remove_fulfilled_sku
from services.order_processor import check_and_notify_eta_updates
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

    queue = load_queue(QUEUE_FILE)
    fulfilled_queue = load_queue(FULFILLED_QUEUE_FILE)
    order_number = "Unknown"
    raw_data = request.data
    cleaned_data = clean_json(raw_data)

    try:
        data = json.loads(cleaned_data)
        if not data:
            queue.append({
                "error": "No valid JSON data after cleaning",
                "order_number": order_number,
                "raw_data": raw_data.decode('utf-8')
            })
            save_queue(queue, QUEUE_FILE)
            return jsonify({"status": "queued", "message": "Order queued with error: No valid JSON data"}), 200

        order_number = data.get("order_number", "Unknown")
        action = request.args.get('action', '')

        if action == 'addNewOrders':
            queue.append(data)
            save_queue(queue, QUEUE_FILE)
            process_queue(QUEUE_FILE, process_order)
            return jsonify({"status": "queued", "message": f"Order {order_number} added to queue"}), 200
        elif action == 'removeFulfilledSKU':
            fulfilled_queue.append(data)
            save_queue(fulfilled_queue, FULFILLED_QUEUE_FILE)
            process_queue(FULFILLED_QUEUE_FILE, remove_fulfilled_sku)
            return jsonify({"status": "queued", "message": f"Order {order_number} added to queue"}), 200
        else:
            error_data = {
                "error": f"Invalid action: {action}",
                "order_number": order_number,
                "raw_data": raw_data.decode('utf-8')
            }
            queue.append(error_data)
            save_queue(queue, QUEUE_FILE)
            return jsonify({"status": "queued", "message": f"Order {order_number} queued with error: Invalid action"}), 200

    except ValueError as e:
        logger.error(f"Failed to parse JSON: {str(e)}")
        error_data = {
            "error": f"Invalid JSON: {str(e)}",
            "order_number": order_number,
            "raw_data": raw_data.decode('utf-8')
        }
        # Decide queue based on action
        if request.args.get('action', '') == 'removeFulfilledSKU':
            fulfilled_queue.append(error_data)
            save_queue(fulfilled_queue, FULFILLED_QUEUE_FILE)
        else:
            queue.append(error_data)
            save_queue(queue, QUEUE_FILE)
        return jsonify({"status": "queued", "message": f"Order {order_number} queued with error: Invalid JSON"}), 200

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        error_data = {
            "error": str(e),
            "order_number": order_number,
            "raw_data": raw_data.decode('utf-8')
        }
        # Decide queue based on action
        if request.args.get('action', '') == 'removeFulfilledSKU':
            fulfilled_queue.append(error_data)
            save_queue(fulfilled_queue, FULFILLED_QUEUE_FILE)
        else:
            queue.append(error_data)
            save_queue(queue, QUEUE_FILE)
        return jsonify({"status": "queued", "message": f"Order {order_number} queued with error: {str(e)}"}), 200


@webhook_bp.route('/check_eta_updates', methods=['GET'])
def check_all_eta_updates():
    provided_key = request.args.get('key')
    if provided_key != SECRET_KEY:
        return jsonify({"error": "Access Denied"}), 403

    check_and_notify_eta_updates()
    return jsonify({"status": "success", "message": "ETA updates check complete!"}), 200
