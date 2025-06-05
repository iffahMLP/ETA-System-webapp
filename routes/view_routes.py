
from flask import Blueprint, request, jsonify
import os
import json
import logging
from config import SECRET_KEY, FAILED_ORDERS_FILE, QUEUE_FILE, FULFILLED_QUEUE_FILE
from services.queue_handler import load_queue
from services.order_processor import check_and_notify_eta_updates

view_bp = Blueprint('view_routes', __name__)
logger = logging.getLogger(__name__)

@view_bp.route('/queue', methods=['GET'])
def view_queue():
    provided_key = request.args.get('key')
    if provided_key != SECRET_KEY:
        return jsonify({"error": "Access Denied"}), 403
    try:
        queue = load_queue(QUEUE_FILE)
        logger.info(f"Queue accessed. Size: {len(queue)}")
        return jsonify({"queue_size": len(queue), "orders": queue}), 200
    except Exception as e:
        logger.error(f"Error viewing queue: {str(e)}")
        return jsonify({"error": str(e)}), 500

@view_bp.route('/fulfilled_queue', methods=['GET'])
def view_fulfilled_queue():
    provided_key = request.args.get('key')
    if provided_key != SECRET_KEY:
        return jsonify({"error": "Access Denied"}), 403
    try:
        queue = load_queue(FULFILLED_QUEUE_FILE)
        logger.info(f"Queue accessed. Size: {len(queue)}")
        return jsonify({"queue_size": len(queue), "orders": queue}), 200
    except Exception as e:
        logger.error(f"Error viewing queue: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@view_bp.route('/failed_orders', methods=['GET'])
def view_failed_orders():
    provided_key = request.args.get('key')
    if provided_key != SECRET_KEY:
        return jsonify({"error": "Access Denied"}), 403
    try:
        failed_orders = []
        if os.path.exists(FAILED_ORDERS_FILE):
            with open(FAILED_ORDERS_FILE, 'r') as f:
                for line in f:
                    if line.strip():
                        failed_orders.append(json.loads(line))
        logger.info(f"Failed orders accessed. Count: {len(failed_orders)}")
        return jsonify({"failed_orders_count": len(failed_orders), "failed_orders": failed_orders}), 200
    except Exception as e:
        logger.error(f"Error reading failed orders: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@view_bp.route('/clear_queue', methods=['POST'])
def clear_queue_view():
    provided_key = request.args.get('key')
    if provided_key != SECRET_KEY:
        return jsonify({"error": "Access Denied"}), 403

    queue_type = request.args.get('type', 'orders')  # default: orders queue
    if queue_type == 'fulfilled':
        queue_file = FULFILLED_QUEUE_FILE
    else:
        queue_file = QUEUE_FILE

    try:
        with open(queue_file, 'w') as f:
            json.dump([], f)  # Clear the queue

        logger.info(f"Cleared {queue_type} queue from view route.")
        return jsonify({"status": "success", "message": f"{queue_type.capitalize()} queue cleared."}), 200

    except Exception as e:
        logger.error(f"Error clearing queue: {str(e)}")
        return jsonify({"error": f"Failed to clear {queue_type} queue: {str(e)}"}), 500

@view_bp.route('/check_eta_updates', methods=['GET'])
def check_all_eta_updates():
    provided_key = request.args.get('key')
    if provided_key != SECRET_KEY:
        return jsonify({"error": "Access Denied"}), 403

    check_and_notify_eta_updates()
    return jsonify({"status": "success", "message": "ETA updates check complete!"}), 200


@view_bp.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200
