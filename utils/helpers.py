
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

def clean_json(raw_data):
    try:
        if isinstance(raw_data, bytes):
            raw_data = raw_data.decode('utf-8')
        lines = [line.strip() for line in raw_data.splitlines() if line.strip()]
        cleaned = '\n'.join(lines)
        cleaned = re.sub(r',(\s*[\]}])', r'\1', cleaned)
        return cleaned
    except Exception as e:
        logger.error(f"Error cleaning JSON: {str(e)}")
        return raw_data

def format_date(date_str):
    try:
        date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return f"{date.year}-{str(date.month).zfill(2)}-{str(date.day).zfill(2)}"
    except Exception as e:
        logger.error(f"Error formatting date {date_str}: {str(e)}")
        return "Invalid Date"
