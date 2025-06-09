from flask import Blueprint, request, jsonify
from utils.gmail_helper import check_new_eta_emails, update_latest_eta_in_sheet
from services.order_processor import check_and_notify_eta_updates
import logging
from config import SECRET_KEY

gmail_bp = Blueprint('gmail_routes', __name__)
logger = logging.getLogger(__name__)


@gmail_bp.route('/gmail-eta-update', methods=['POST'])
def gmail_eta_update():
    provided_key = request.args.get('key')
    if provided_key != SECRET_KEY:
        return jsonify({"error": "Access Denied"}), 403

    logger.info("Triggered Gmail ETA update check.")

    try:
        updates = check_new_eta_emails()
        update_latest_eta_in_sheet(updates)

        check_and_notify_eta_updates()

        return jsonify({
            "status": "success",
            "message": f"Checked Gmail. Found {len(updates)} updates.",
            "updates": updates
        }), 200

    except Exception as e:
        logger.error(f"Error processing Gmail ETA update: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
