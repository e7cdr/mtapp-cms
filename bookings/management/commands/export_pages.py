# core/management/commands/export_pages.py   (or in any app)

import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Export ALL Wagtail pages with full detail data (StreamField, custom fields, etc.) to CSV"

    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, default=None,
                            help='Output CSV file. Auto-generated if omitted.')
        parser.add_argument('--token', type=str, help='API token (or set WAGTAIL_API_TOKEN in settings)')
        parser.add_argument('--url', type=str, default=None, help='Base URL (default: SITE_URL or localhost)')
        parser.add_argument('--threads', type=int, default=20, help='Parallel downloads (default 20)')
        parser.add_argument('--fields', type=str, default='*',
                            help='Fields to include in list (use "*" for all, or comma-separated)')

    def handle(self, *args, **options):
        token = options['token'] or getattr(settings, 'WAGTAIL_API_TOKEN', None)
        if not token:
            self.stdout.write(self.style.ERROR("No token! Use --token or set WAGTAIL_API_TOKEN"))
            return

        base_url = (options['url'] or getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')).rstrip('/')
        list_url = f"{base_url}/api/v2/pages/"
        
        # Optional: request extra fields already in the list view
        headers = {"Authorization": f"Token {token}"}

        self.stdout.write("Fetching all pages (list view)...")
        shallow_pages = self.fetch_all_pages(list_url, headers, params=None)

        if not shallow_pages:
            self.stdout.write(self.style.WARNING("No pages found!"))
            return

        detail_urls = [page['meta']['detail_url'] for page in shallow_pages]
        self.stdout.write(f"Found {len(detail_urls)} pages → downloading full details in parallel...")

        full_pages = []
        with ThreadPoolExecutor(max_workers=options['threads']) as executor:
            futures = {executor.submit(self.fetch_json, url, headers): url for url in detail_urls}
            for i, future in enumerate(as_completed(futures), 1):
                data = future.result()
                if data:
                    full_pages.append(data)
                self.stdout.write(self.style.SUCCESS(f"   [{i}/{len(detail_urls)}] Downloaded"))

        self.save_to_csv(full_pages, options['output'])

    def fetch_all_pages(self, url, headers, params=None):
        items = []
        while url:
            r = requests.get(url, headers=headers, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            items.extend(data.get("items", []))
            url = data.get("meta", {}).get("next")
            time.sleep(0.1)
        return items

    def fetch_json(self, url, headers):
        r = requests.get(url, headers=headers, timeout=30)
        return r.json() if r.status_code == 200 else None

    def save_to_csv(self, pages, output_arg):
        if not pages:
            return

        # Smart flattening (handles StreamField, nested dicts, lists, images, etc.)
        flat_rows = []
        for page in pages:
            row = {
                "id": page.get("id"),
                "title": page.get("title"),
                "page_type": page.get("meta", {}).get("type"),
                "slug": page.get("meta", {}).get("slug"),
                "url_path": page.get("meta", {}).get("html_url"),
                "detail_url": page.get("meta", {}).get("detail_url"),
                "status": page.get("meta", {}).get("status", {}).get("status"),
                "first_published_at": page.get("meta", {}).get("first_published_at"),
                "last_published_at": page.get("meta", {}).get("last_published_at"),
                "locale": page.get("meta", {}).get("locale"),
            }

            # Flatten all top-level custom fields
            for key, value in page.items():
                if key == "meta":
                    continue
                if isinstance(value, (dict, list)):
                    # For StreamField / rich content, stringify or flatten deeply
                    if isinstance(value, list):
                        # Common: body StreamField → convert to readable text
                        if key == "body" or "stream" in key.lower():
                            text_parts = []
                            for block in value:
                                block_type = block.get("type", "")
                                block_value = block.get("value", "")
                                if isinstance(block_value, str):
                                    text_parts.append(block_value)
                                elif isinstance(block_value, dict):
                                    text_parts.append(str(block_value.get("text") or block_value.get("caption") or ""))
                            row[f"{key}_text"] = " | ".join(filter(None, text_parts))[:500]
                        else:
                            row[key] = str(value)[:1000]
                    else:
                        for sk, sv in value.items():
                            row[f"{key}_{sk}"] = sv if sv is not None else ""
                else:
                    row[key] = value

            flat_rows.append(row)

        keys = sorted({k for row in flat_rows for k in row.keys()})
        filename = output_arg or f"wagtail_pages_full_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        path = Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)

        import csv
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(flat_rows)

        self.stdout.write(self.style.SUCCESS(
            f"\nSUCCESS! {len(pages)} pages exported with full details → {path.resolve()}"
        ))