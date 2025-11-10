from django.db import models
from django.contrib.auth.models import User  # or CustomUser if used
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from revenue_management.models import Commission

class Profile(models.Model):
    full_name = models.CharField(max_length=55)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, help_text=_("Biography"))
    email = models.EmailField(blank=True)
    phone = models.CharField(blank=True, null=True, max_length=15)
    img = models.ImageField(blank=True, null=True)
    is_sales_rep = models.BooleanField(help_text='If True, it would get commissions per sale')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

# Automatically create a Profile when a User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

def get_monthly_commissions(self):
        # Reuse your Commission model logic
        return Commission.objects.filter(user=self.user).aggregate(total=models.Sum('amount'))['total'] or 0