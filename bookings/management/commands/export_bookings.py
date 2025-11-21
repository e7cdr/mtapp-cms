# bookings/management/commands/export_bookings.py

import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Export ALL bookings with full detail data (customer, rooms, tour, status, etc.) to CSV"

    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, default=None,
                            help='Output file (e.g. exports/bookings_2025.csv). Auto-generated if omitted.')
        parser.add_argument('--token', type=str, help='API token (or set BOOKINGS_API_TOKEN in settings)')
        parser.add_argument('--url', type=str, default=None, help='Base URL (default: SITE_URL or http://127.0.0.1:8000)')
        parser.add_argument('--threads', type=int, default=15, help='Parallel detail downloads (default: 15)')

    def handle(self, *args, **options):
        token = options['token'] or getattr(settings, 'BOOKINGS_API_TOKEN', None)
        if not token:
            self.stdout.write(self.style.ERROR("No token! Use --token or set BOOKINGS_API_TOKEN in settings.py"))
            return

        base_url = (options['url'] or getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')).rstrip('/')
        list_url = f"{base_url}/api/v2/bookings/"        # your list endpoint
        headers = {"Authorization": f"Token {token}"}

        # Step 1: Get the shallow list + pagination
        self.stdout.write("Fetching list of all bookings...")
        shallow_items = self.fetch_all_pages(list_url, headers)

        if not shallow_items:
            self.stdout.write(self.style.WARNING("No bookings found!"))
            return

        detail_urls = [item['meta']['detail_url'] for item in shallow_items]
        self.stdout.write(f"Found {len(detail_urls)} bookings → downloading full details in parallel...")

        # Step 2: Parallel download of full objects
        full_bookings = []
        with ThreadPoolExecutor(max_workers=options['threads']) as executor:
            futures = {executor.submit(self.fetch_json, url, headers): i for i, url in enumerate(detail_urls)}
            for future in as_completed(futures):
                data = future.result()
                if data:
                    full_bookings.append(data)
                self.stdout.write(self.style.SUCCESS(f"   Downloaded {len(full_bookings)}/{len(detail_urls)}"))

        # Step 3: Save beautiful flat CSV
        self.save_to_csv(full_bookings, options['output'])

    def fetch_all_pages(self, url, headers):
        items = []
        while url:
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            data = r.json()
            items.extend(data.get("items", []))
            url = data.get("meta", {}).get("next")
            time.sleep(0.1)
        return items

    def fetch_json(self, url, headers):
        r = requests.get(url, headers=headers, timeout=30)
        return r.json() if r.status_code == 200 else None

    def save_to_csv(self, bookings, output_arg):
        if not bookings:
            return

        # Super-smart flattening (handles nested dicts + lists like room_config.options)
        flat_rows = []
        for b in bookings:
            row = {}
            for key, value in b.items():
                if isinstance(value, dict) and value:
                    for sk, sv in value.items():
                        if isinstance(sv, list):
                            for idx, item in enumerate(sv):
                                if isinstance(item, dict):
                                    for ssk, ssv in item.items():
                                        row[f"{key}_{sk}_{idx}_{ssk}"] = ssv
                                else:
                                    row[f"{key}_{sk}_{idx}"] = item
                        else:
                            row[f"{key}_{sk}"] = sv if sv is not None else ""
                else:
                    row[key] = value
            flat_rows.append(row)

        keys = sorted({k for row in flat_rows for k in row.keys()})

        filename = output_arg or f"bookings_full_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        path = Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)

        import csv
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(flat_rows)

        self.stdout.write(self.style.SUCCESS(
            f"\nExported {len(bookings)} bookings with full details → {path.resolve()}"
        ))