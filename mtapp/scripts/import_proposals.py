import requests
import json

URL = "http://localhost:8000/api/v2/proposals/"
TOKEN = "your-super-secret-token"  # create in Wagtail → Settings → API Tokens

headers = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json"
}

# Load from your exported CSV → convert to JSON first, or just paste data
data = [
    {
        "prop_id": "P2025-1000",
        "customer_name": "Carlos Rivera",
        "customer_email": "carlos@example.com",
        "travel_date": "2025-11-20",
        "tour_content_type": "tours.landtourpage",
        "tour_object_id": 15,
        "number_of_adults": 2,
        "estimated_price": "2890.00",
        "status": "CONFIRMED"
    }
]

for item in data:
    r = requests.post(URL, json=item, headers=headers)
    if r.status_code == 201:
        print("Created:", item["prop_id"])
    else:
        print("Error:", r.status_code, r.text)