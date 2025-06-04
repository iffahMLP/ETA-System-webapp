
from flask import Blueprint, request, jsonify
import os
import json
import logging
from config import SECRET_KEY, FAILED_ORDERS_FILE
from services.queue_handler import load_queue

view_bp = Blueprint('view_routes', __name__)
logger = logging.getLogger(__name__)

@view_bp.route('/queue', methods=['GET'])
def view_queue():
    provided_key = request.args.get('key')
    if provided_key != SECRET_KEY:
        return jsonify({"error": "Access Denied"}), 403
    try:
        queue = load_queue()
        logger.info(f"Queue accessed. Size: {len(queue)}")
        return jsonify({"queue_size": len(queue), "orders": queue}), 200
    except Exception as e:
        logger.error(f"Error viewing queue: {str(e)}")
        return jsonify({"error": str(e)}), 500

@view_bp.route('/queue_fulfilled', methods=['GET'])
def view_queue_fulfilled():
    provided_key = request.args.get('key')
    if provided_key != SECRET_KEY:
        return jsonify({"error": "Access Denied"}), 403
    try:
        queue = load_queue()
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

@view_bp.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200
