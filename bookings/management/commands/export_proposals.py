# bookings/management/commands/export_proposals.py

import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Export ALL proposals with FULL detail data to CSV"

    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, default='proposals_full.csv')
        parser.add_argument('--token', type=str, help='API token')
        parser.add_argument('--url', type=str, default=None)
        parser.add_argument('--threads', type=int, default=10, help='Parallel downloads (default 10)')

    def handle(self, *args, **options):
        token = options['token'] or getattr(settings, 'WAGTAIL_API_TOKEN', None)
        if not token:
            self.stdout.write(self.style.ERROR("No token!"))
            return

        base_url = (options['url'] or getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')).rstrip('/')
        list_url = f"{base_url}/api/v2/proposal_list/"          # ← list endpoint (shallow)
        headers = {"Authorization": f"Token {token}"}

        self.stdout.write("Step 1: Getting list of all proposals...")
        proposals = self.paginate(list_url, headers)

        if not proposals:
            self.stdout.write(self.style.WARNING("No proposals found!"))
            return

        detail_urls = [p['meta']['detail_url'] for p in proposals]
        self.stdout.write(f"Step 2: Downloading full details for {len(detail_urls)} proposals (parallel)...")

        full_proposals = []
        with ThreadPoolExecutor(max_workers=options['threads']) as executor:
            future_to_id = {
                executor.submit(self.fetch_detail, url, headers): url
                for url in detail_urls
            }
            for i, future in enumerate(as_completed(future_to_id), 1):
                data = future.result()
                if data:
                    full_proposals.append(data)
                self.stdout.write(self.style.SUCCESS(f"   [{i}/{len(detail_urls)}] Downloaded"))

        self.save_to_csv(full_proposals, options['output'])

    def paginate(self, url, headers):
        items = []
        while url:
            r = requests.get(url, headers=headers)
            if r.status_code != 200:
                raise Exception(f"List error: {r.text}")
            data = r.json()
            items.extend(data.get("items", []))
            url = data.get("meta", {}).get("next")
            time.sleep(0.1)
        return items

    def fetch_detail(self, url, headers):
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()
        else:
            self.stdout.write(self.style.ERROR(f"Failed {url}: {r.status_code}"))
            return None

    def save_to_csv(self, proposals, output_file):
        if not proposals:
            return

        # Flatten everything (room_config_options_0_singles, etc.)
        flattened = []
        for p in proposals:
            row = {}
            for k, v in p.items():
                if isinstance(v, dict):
                    for sk, sv in v.items():
                        if isinstance(sv, list):
                            # Handle lists like room_config.options or children_ages
                            for idx, item in enumerate(sv):
                                if isinstance(item, dict):
                                    for ssk, ssv in item.items():
                                        row[f"{k}_{sk}_{idx}_{ssk}"] = ssv
                                else:
                                    row[f"{k}_{sk}_{idx}"] = item
                        else:
                            row[f"{k}_{sk}"] = sv if sv is not None else ""
                else:
                    row[k] = v
            flattened.append(row)

        keys = sorted({k for r in flattened for k in r.keys()})
        path = Path(output_file)
        path.parent.mkdir(parents=True, exist_ok=True)

        import csv
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(flattened)

        self.stdout.write(self.style.SUCCESS(
            f"\nDONE! {len(proposals)} full proposals exported → {path.resolve()}"
        ))