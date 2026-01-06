from django.http import JsonResponse

from django.db import connection
from django.views.decorators.http import require_http_methods
from django.db.utils import OperationalError
from django.shortcuts import render
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
from django_ratelimit.core import _split_rate, _make_cache_key  # Import internals for key building (safe)
from django.db.models import Sum
from bookings.models import Booking
from accounts.forms import CustomSignupForm
from allauth.account.views import SignupView
from django.views.generic import TemplateView
from revenue_management.models import Commission
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.admin.views.decorators import staff_member_required

class CustomSignupView(SignupView):
    template_name = 'accounts/signup.html'  # We'll create this
    form_class = CustomSignupForm


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'profiles/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile = user.profile  # Safe: Signal creates it

        # Gating: Only show commissions if sales rep
        if profile.is_sales_rep:
            context['total_commission'] = Commission.objects.filter(
                user=user  # Still uses User FK; adjust if needed
            ).aggregate(total=Sum('amount'))['total'] or 0
            # Add notices here if un-commented
        else:
            context['total_commission'] = 0

        context['bookings'] = Booking.objects.filter(user=user).order_by('-booking_date')[:10]
        context['total_bookings'] = context['bookings'].count()

        #TODO: Add notices
                    # Notices (global or user-specific; filter by read/unread if you add that)
            # context['notices'] = Notice.objects.filter(
            #     Q(user=user) | Q(user__isnull=True)  # Personal or general
            # ).order_by('-created_at')[:5]  # Latest 5

        return context


def ratelimit_exceeded(request, exception):
    # Reconstruct the cache key (mimics django-ratelimit's _make_cache_key)
    group = request.resolver_match.func.__module__ + '.' + request.resolver_match.func.__name__  # e.g., 'bookings.views.bookingstartview'
    rate = '5/h'  # Match your decorator's rate; make dynamic if multi-rates
    value = request.META.get('REMOTE_ADDR', 'unknown')  # For key='ip'; use str(request.user.pk) for 'user'
    methods = request.method.upper()  # e.g., 'POST'

    # Build exact key (from core.py source)
    limit, period = _split_rate(rate)
    safe_rate = f"{limit}/{period}s"  # e.g., '5/3600s'
    window = int(timezone.now().timestamp()) // period * period  # Current window start
    cache_key = _make_cache_key(group, window, rate, value, methods)  # Uses core func

    # Fetch data from cache
    data = cache.get(cache_key)
    hits = data.get('count', 0) if data else 0  # Ratelimit stores {'count': N, ...}
    max_hits = limit  # From rate
    expiry = timezone.now() + timedelta(hours=1)  # Default for 'h'; compute from period
    time_left = expiry - timezone.now()

    context = {
        'reason': 'Rate limit exceeded',
        'hits': hits,
        'max_hits': max_hits,
        'time_left': time_left,
        'retry_after': max(time_left.total_seconds(), 60),
        'form_url': request.POST.get('next', '') or request.path,
    }
    return render(request, 'ratelimit_blocked.html', context, status=429)



@staff_member_required
@require_http_methods(["GET"])
def inspect_ratelimit(request):
    all_keys = []
    try:
        # PA MySQL: Cache table is 'default' (from LOCATION='default')
        TABLE_NAME = 'default'
        with connection.cursor() as cursor:
            # Query prefixed table with backticks
            cursor.execute(f"SELECT cache_key FROM `{TABLE_NAME}` WHERE cache_key LIKE %s", ['rl:%'])
            raw_keys = [row[0] for row in cursor.fetchall()]

        for key in raw_keys:
            value = cache.get(key)
            all_keys.append({
                'key': key,
                'value': value,
                'expiry_remaining': None  # Optional: value.get('expire') if stored
            })
    except OperationalError as e:
        # Fallback: Query without prefix (Django auto-handles in some cases)
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT cache_key FROM `default` WHERE cache_key LIKE %s", ['rl:%'])
                raw_keys = [row[0] for row in cursor.fetchall()]
            # ... same for loop as above
            for key in raw_keys:
                value = cache.get(key)
                all_keys.append({
                    'key': key,
                    'value': value,
                    'expiry_remaining': None
                })
        except OperationalError as e2:
            return JsonResponse({'error': f'Query failed: {str(e2)}. Table may need manual check.'}, status=500)
    except Exception as e:
        return JsonResponse({'error': f'Cache inspection failed: {str(e)}'}, status=500)

    return JsonResponse({'locks': all_keys})

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from captcha.helpers import captcha_image_url
from captcha.models import CaptchaStore

@csrf_exempt
@require_GET
def captcha_refresh(request):
    # Generate new CAPTCHA hash
    new_hash = CaptchaStore.generate_key()
    return JsonResponse({'hash': new_hash})
