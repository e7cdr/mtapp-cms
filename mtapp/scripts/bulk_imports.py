import requests
import csv
from django.contrib.contenttypes.models import ContentType  # Run in Django shell if needed

API_BASE = 'http://localhost:8000/api/v2/'
TOKEN = 'YOUR_TOKEN_HERE'  # From Wagtail admin
HEADERS = {
    'Authorization': f'Token {TOKEN}',
    'Content-Type': 'application/json'
}

def resolve_tour(content_type_model, object_id):
    """Resolve GenericFK from CSV strings like 'tours.fulltourpage' + '42'"""
    if not content_type_model or not object_id:
        return None
    app_label, model = content_type_model.split('.')
    ct = ContentType.objects.get(app_label=app_label, model=model)
    return {'content_type': ct.id, 'object_id': int(object_id)}

def import_from_csv(csv_file, endpoint):
    """Import from CSV (columns match your export)"""
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Resolve tour GenericFK
            tour_data = resolve_tour(row.get('tour_type', ''), row.get('tour_id', ''))
            payload = {**row, **tour_data}  # Merge
            del payload['tour_type']  # Clean up CSV columns
            del payload['tour_id']
            
            # POST (create) or PUT (update if ID exists)
            if 'id' in payload and payload['id']:
                url = f"{API_BASE}{endpoint}/{payload['id']}/"
                r = requests.put(url, json=payload, headers=HEADERS)
            else:
                url = f"{API_BASE}{endpoint}/"
                r = requests.post(url, json=payload, headers=HEADERS)
            
            if r.status_code in [200, 201]:
                print(f"Success: {row.get('prop_id', 'New')} ({r.status_code})")
            else:
                print(f"Error: {r.status_code} - {r.text}")

# Usage
import_from_csv('proposals_export.csv', 'proposals')
# import_from_csv('bookings_export.csv', 'bookings')