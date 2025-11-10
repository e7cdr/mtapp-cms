from allauth.account.forms import SignupForm
from profiles.models import Profile

class CustomSignupForm(SignupForm):
    def save(self, request):
        user = super().save(request)
        # Post-save: Set profile attrs if from form
        profile = user.profile
        profile.is_sales_rep = self.cleaned_data.get('is_sales_rep', False)  # If adding to form
        profile.save()
        return user