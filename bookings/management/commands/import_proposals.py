from django.core.management.base import BaseCommand, CommandError
from django.contrib.contenttypes.models import ContentType
import requests
import json
from datetime import datetime

class Command(BaseCommand):
    help = 'Import proposals from JSON file via API'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str, help='JSON file path')
        parser.add_argument('--endpoint', default='proposals', help='API endpoint')
        parser.add_argument('--dry-run', action='store_true', help='Test without saving')

    def handle(self, *args, **options):
        with open(options['file'], 'r') as f:
            data = json.load(f)['items']  # Assume exported API JSON structure

        token = 'YOUR_TOKEN_HERE'  # Or from env
        headers = {'Authorization': f'Token {token}', 'Content-Type': 'application/json'}
        url = f"http://localhost:8000/api/v2/{options['endpoint']}/"

        for item in data:
            # Resolve tour
            if 'tour' in item and item['tour']:
                tour_type = item['tour']['type']
                tour_id = item['tour']['id']
                app_label, model = tour_type.split('.') if '.' in tour_type else ('tours', tour_type)
                ct = ContentType.objects.get(app_label=app_label, model=model)
                item['content_type'] = ct.id
                item['object_id'] = tour_id
                del item['tour']

            if options['dry_run']:
                self.stdout.write(f"Dry run: {item.get('prop_id', 'New')}")
                continue

            r = requests.post(url, json=item, headers=headers)
            if r.status_code == 201:
                self.stdout.write(self.style.SUCCESS(f"Imported: {item.get('prop_id')}"))
            else:
                self.stderr.write(self.style.ERROR(f"Failed {item.get('prop_id')}: {r.text}"))

        self.stdout.write(self.style.SUCCESS(f'Import complete: {datetime.now()}'))