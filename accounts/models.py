# accounts/models.py

from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.dispatch import receiver
from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.core.exceptions import ValidationError
from wagtail.snippets.models import register_snippet


@register_snippet
class ReferralCode(models.Model):
    """
    Permanent referral identifier for affiliates.
    One per user. Used for attribution/commission.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referral_code'
    )
    code = models.CharField(
        max_length=12,
        unique=True,
        editable=False,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.code:
            prefix = "MT-"
            length = 8 - len(prefix)
            while True:
                random_part = get_random_string(length).upper()
                self.code = f"{prefix}{random_part}"
                if not ReferralCode.objects.filter(code=self.code).exists():
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} → {self.code}"

    @classmethod
    def get_user_by_code(cls, code: str):
        if not code:
            return None
        try:
            return cls.objects.get(code=code.strip().upper(), is_active=True).user
        except cls.DoesNotExist:
            return None

@register_snippet
class DiscountCode(models.Model):
    """
    Promotional codes that can give discounts.
    Can be created by affiliates. Applied only via URL.
    """
    code = models.CharField(
        max_length=16,
        unique=True,
        db_index=True,
        help_text="Uppercase code the customer will use via URL ?promo=..."
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_discount_codes'
    )
    discount_type = models.CharField(
        max_length=20,
        choices=[('percentage', 'Percentage'), ('fixed', 'Fixed Amount')],
        default='percentage'
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0, editable=False)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    min_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Minimum proposal estimated_price to apply"
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['active', 'valid_from', 'valid_until']),
        ]

    def clean(self):
        if self.discount_type == 'percentage' and not (0 < self.discount_value <= 100):
            raise ValidationError("Percentage must be >0 and ≤100")
        if self.discount_type == 'fixed' and self.discount_value <= 0:
            raise ValidationError("Fixed amount must be positive")

    def is_valid_for(self, amount: Decimal) -> bool:
        now = timezone.now()
        if not self.active:
            return False
        if now < self.valid_from or (self.valid_until and now > self.valid_until):
            return False
        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False
        if amount < self.min_amount:
            return False
        return True

    def apply_to(self, original_amount: Decimal) -> tuple[Decimal, Decimal]:
        """Returns (final_amount, discount_amount)"""
        if not self.is_valid_for(original_amount):
            return original_amount, Decimal('0.00')

        if self.discount_type == 'percentage':
            discount = (original_amount * self.discount_value / Decimal('100')).quantize(Decimal('0.01'))
        else:  # fixed
            discount = self.discount_value

        final = max(Decimal('0.00'), original_amount - discount)
        return final, discount

    def __str__(self):
        val = f"{self.discount_value}%"
        if self.discount_type == 'fixed':
            val = f"${self.discount_value}"
        return f"{self.code} ({val})"


# Utility function (can be in accounts/utils.py or models.py)
def get_mtweb_user():
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        return User.objects.get(username='MTWEB')
    except User.DoesNotExist:
        # You may want to create it automatically in a data migration
        # For now, raise error in development
        raise ValueError("MTWEB system user does not exist. Please create it.")
    

@receiver(post_save, sender=get_user_model())
def create_referral_code_for_new_user(sender, instance, created, **kwargs):
    if not created:
        return

    # Only create ReferralCode if user belongs to the Referrers group
    try:
        referrers_group = Group.objects.get(name='Referrers')
        if not instance.groups.filter(name='Referrers').exists():
            return
    except Group.DoesNotExist:
        # If group doesn't exist yet → skip silently (safe during initial migrations)
        return

    # Skip MTWEB anyway (extra safety)
    if instance.username == 'MTWEB':
        return

    ReferralCode.objects.get_or_create(user=instance)