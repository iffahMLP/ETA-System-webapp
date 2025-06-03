import os

def get_configs():
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
            "WEBSITE": os.getenv(f"{store}_WEBSITE", "www.mlperformance.co.uk")
        }

    # If you have a special "Dumbledore" config as fallback
    dumbledore_config = {
        "SENDER_EMAIL": os.getenv("DB_SENDER_EMAIL", ""),
        "SENDER_PASSWORD": os.getenv("DB_SENDER_PASSWORD", "")
    }

    return store_configs, dumbledore_config
