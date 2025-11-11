from django.db.models import Sum
from bookings.models import Booking
from accounts.forms import CustomSignupForm
from allauth.account.views import SignupView
from django.views.generic import TemplateView
from revenue_management.models import Commission
from django.contrib.auth.mixins import LoginRequiredMixin

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
    
