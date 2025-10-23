from bookings.models import ExchangeRate

# def exchange_rates(request):
#     return {
#         'exchange_rates': ExchangeRate.objects.all()
#     }


def exchange_rates(request):
    rates = ExchangeRate.objects.all()
    return {
        'exchange_rates': [{'currency_code': rate.currency_code, 'rate': float(rate.rate_to_usd)} for rate in rates]
    }