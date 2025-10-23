# bookings/management/commands/update_exchange_rates.py
import requests
from decimal import Decimal
from django.conf import settings
from bookings.models import ExchangeRate
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Update exchange rates from an external API'

    def handle(self, *args, **kwargs):
        api_key = settings.OPEN_EXCHANGE_RATES_API_KEY
        url = f"https://openexchangerates.org/api/latest.json?app_id={api_key}&base=USD"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            rates = data.get('rates', {})
            for currency_code, rate in rates.items():
                if currency_code == 'USD':
                    continue
                ExchangeRate.objects.update_or_create(
                    currency_code=currency_code,
                    defaults={'rate_to_usd': Decimal(str(rate))}
                )
            self.stdout.write(self.style.SUCCESS('Successfully updated exchange rates'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error updating exchange rates: {e}'))