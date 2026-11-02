
import json
import os
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://mygeisha.ro"
COLLECTION = "oos"
STATE_FILE = Path("products_seen.json")

TOKEN = os.environ["PUSHOVER_TOKEN"]
USER = os.environ["PUSHOVER_USER"]


def request_json(url, data=None):
    headers = {
        "User-Agent": "myGeishaCollectionMonitor/1.0"
    }

    if data is not None:
        data = urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    req = Request(url, data=data, headers=headers)

    with urlopen(req, timeout=30) as response:
        return json.load(response)


def get_products():
    products = {}

    for page in range(1, 101):
        url = (
            f"{BASE_URL}/collections/{COLLECTION}/products.json"
            f"?limit=250&page={page}"
        )

        result = request_json(url)

        if not isinstance(result.get("products"), list):
            raise ValueError("Invalid Shopify response")

        batch = result["products"]

        for product in batch:
            product_id = str(product["id"])

            products[product_id] = {
                "title": product["title"],
                "url": (
                    f"{BASE_URL}/products/"
                    f"{product['handle']}"
                ),
            }

        if len(batch) < 250:
            return products

        time.sleep(0.3)

    raise RuntimeError("Collection page limit exceeded")


def notify(product):
    product_name = product["title"]
    product_url = product["url"]

    message = (
        "New product added to OOS!\n\n"
        f"Product: {product_name}\n\n"
        f"Link: {product_url}"
    )

    result = request_json(
        "https://api.pushover.net/1/messages.json",
        {
            "token": TOKEN,
            "user": USER,
            "title": "myGeisha - New OOS Product",
            "message": message,
            "url": product_url,
            "url_title": "View product on myGeisha",
            "priority": 0,
            "sound": "pushover",
        },
    )

    if result.get("status") != 1:
        raise RuntimeError(
            f"Pushover notification failed: {result}"
        )

    print(f"Notification sent: {product_name}")


def main():
    current = get_products()

    print(f"Found {len(current)} products")

    if not STATE_FILE.exists():
        STATE_FILE.write_text(
            json.dumps(
                current,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        print("Initial baseline saved. No alerts sent.")
        return

    previous = json.loads(
        STATE_FILE.read_text(encoding="utf-8")
    )

    new_ids = current.keys() - previous.keys()

    for product_id in sorted(new_ids):
        product = current[product_id]
        notify(product)

    STATE_FILE.write_text(
        json.dumps(
            current,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Completed. New products: {len(new_ids)}")


if __name__ == "__main__":
    main()
