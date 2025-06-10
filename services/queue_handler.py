
import json
import os
import logging
import time
from config import FAILED_ORDERS_FILE
from services.order_processor import process_order

logger = logging.getLogger(__name__)

def load_queue(queue_file):
    try:
        if os.path.exists(queue_file):
            with open(queue_file, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Error loading queue: {str(e)}")
        return []

def save_queue(queue, queue_file):
    try:
        with open(queue_file, 'w') as f:
            json.dump(queue, f)
    except Exception as e:
        logger.error(f"Error saving queue: {str(e)}")

def process_queue(queue_file, processor_func):
    queue = load_queue(queue_file)
    if not queue:
        logger.info("Queue is empty, nothing to process")
        return

    updated_queue = []
    max_retries = 3

    for order in queue:
        order_number = order.get("order_number", "Unknown")
        logger.info(f"Inspecting queued order {order_number}")

        if "error" in order:
            logger.info(f"Order {order_number} has an error, keeping in queue: {order['error']}")
            updated_queue.append(order)
            continue

        retries = order.get("retries", 0)
        if retries >= max_retries:
            logger.error(f"Order {order_number} exceeded {max_retries} retries, moving to failed orders")
            try:
                with open(FAILED_ORDERS_FILE, 'a') as f:
                    json.dump(order, f)
                    f.write('\n')
            except Exception as e:
                logger.error(f"Error saving to failed orders: {str(e)}")
            continue

        order["retries"] = retries + 1
        logger.info(f"Attempting to process valid order {order_number}, retry {retries + 1}/{max_retries}")
        success = processor_func(order)

        if success:
            logger.info(f"Order {order_number} processed successfully, removing from queue")
        else:
            if processor_func.__name__ == 'remove_fulfilled_sku':
                logger.warning(f"Order {order_number} not found in sheet, removing from queue permanently")
                # 🚫 Do not re-add to updated_queue
            else:
                logger.warning(f"Order {order_number} failed processing, keeping in queue")
                updated_queue.append(order)

        time.sleep(1)

    save_queue(updated_queue, queue_file)
    logger.info(f"Queue processing complete. New queue size: {len(updated_queue)}")
    time.sleep(2)
