import requests
import json
import logging
from datetime import date

logger = logging.getLogger(__name__)

def get_store_url(config):
    store_url = f"https://{config['API_KEY']}:{config['PASSWORD']}@{config['SHOP_NAME']}.myshopify.com/admin/api/{config['API_VERSION']}/graphql.json"
    return store_url

def update_note(order, config):
    shopurl = get_store_url(config)
    today = date.today().strftime("%d/%m/%Y")
    new_note = f"Customer Updated {today}:\n"

    for item in order['Line Items']:
        eta = 'Reserved' if item['Latest ETA On Hand'] == 'Ready' else item['Latest ETA On Hand']
        new_note += f"{item['sku']} x {str(item['quantity'])} - {eta}\n"

    # Step 1: Get order global ID (GraphQL)
    order_id = order['Order ID']  # ✅ Make sure your order dict includes GraphQL order ID!
    query_note = """
    query {
      order(id: "%s") {
        id
        name
        note
      }
    }
    """ % order_id


    response_query = requests.post(
        shopurl,
        json={"query": query_note}
    )
    result_query = response_query.json()
    try:
        order_data = result_query['data']['order']
        existing_note = order_data['note'] or ''
        logger.info(f"Retrieved existing note for order {order_data['name']}")
    except (KeyError, TypeError):
        logger.error(f"Failed to retrieve order data for {order['Order Number']}")
        return

    # Step 2: Combine old + new note
    if not existing_note:
        combined_note = new_note
    else:
      combined_note = existing_note + "\n" + new_note

    # Step 3: Run the mutation to update the note
    mutation = """
    mutation orderUpdate($input: OrderInput!) {
      orderUpdate(input: $input) {
        order {
          id
          note
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    variables = {
        "input": {
            "id": order_id,
            "note": combined_note
        }
    }

    response_update = requests.post(
        shopurl,
        json={"query": mutation, "variables": variables}
    )

    result_update = response_update.json()
    if result_update.get("errors"):
        logger.error(f"GraphQL error: {result_update['errors']}")
    elif result_update['data']['orderUpdate']['userErrors']:
        logger.warning(f"User errors: {result_update['data']['orderUpdate']['userErrors']}")
    else:
        logger.info(f"Note updated for order {order_data['name']}")
    print(f"Note updated for order {order_data['name']}")


def get_order_data(order_number, config):
    shopurl = get_store_url(config)

    # Step 1: Get order data (GraphQL)
    query_order = """
    query {
      orders(first: 1, query: "name:%s") {
        edges {
          node {
            id
            name
            statusPageUrl
            customer {
              firstName
              locale
            }
          }
        }
      }
    }
  """ % order_number


    response_query = requests.post(
        shopurl,
        json={"query": query_order}
    )
    result_query = response_query.json()
    try:
        order_response = result_query['data']['orders']['edges'][0]['node']
        logger.info(f"Retrieved data for order {order_number}")

        order_data = {
            'Order ID': order_response['id'],
            'Order Number': order_response['name'],
            'Customer First Name': order_response['customer']['firstName'],
            'Locale': order_response['customer']['locale'],
            'Domain': order_response['statusPageUrl'],
        }
        return order_data

    except (KeyError, TypeError):
        logger.error(f"Failed to retrieve order data for {order_number}")
        return