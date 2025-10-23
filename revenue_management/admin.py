from django.contrib import admin
from django import forms
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.db.models import F
from unfold.admin import ModelAdmin
from .models import Commission

# Form for setting custom commission amount
class SetCommissionAmountForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    new_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        label="New Commission Amount",
        help_text="Enter the new commission amount for selected commissions."
    )

@admin.register(Commission)
class CommissionAdmin(ModelAdmin):
    list_display = ['user', 'booking', 'amount', 'status', 'created_at', 'updated_at']
    list_filter = ['status', 'user', 'created_at']
    search_fields = ['booking__book_id', 'user__username']
    list_per_page = 20
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    fieldsets = (
        (None, {
            'fields': ('user', 'booking', 'amount', 'status', 'created_at', 'updated_at')
        }),
    )
    actions = ['mark_paid', 'mark_pending', 'mark_cancelled', 'increase_amount', 'decrease_amount', 'set_custom_amount']

    def get_action_choices(self, request, default_choices=None):
        """
        Override get_action_choices to avoid formatting errors.
        Returns a list of tuples (action_name, description) without string formatting.
        """
        choices = []
        for action in self.get_actions(request).keys():
            method = getattr(self, action, None)
            description = getattr(method, 'short_description', action)
            choices.append((action, description))
        return choices

    @admin.action(description="Mark paid")
    def mark_paid(self, request, queryset):
        updated = queryset.update(status='PAID')
        self.message_user(request, f"{updated} commission(s) marked as Paid.", messages.SUCCESS)

    @admin.action(description="Mark pending")
    def mark_pending(self, request, queryset):
        updated = queryset.update(status='PENDING')
        self.message_user(request, f"{updated} commission(s) marked as Pending.", messages.SUCCESS)

    @admin.action(description="Mark cancelled")
    def mark_cancelled(self, request, queryset):
        updated = queryset.update(status='CANCELLED')
        self.message_user(request, f"{updated} commission(s) marked as Cancelled.", messages.SUCCESS)

    @admin.action(description="Increase by 10%")
    def increase_amount(self, request, queryset):
        updated = queryset.update(amount=F('amount') * 1.10)
        self.message_user(request, f"{updated} commission(s) amount increased by 10%.", messages.SUCCESS)

    @admin.action(description="Decrease by 10%")
    def decrease_amount(self, request, queryset):
        updated = queryset.update(amount=F('amount') * 0.90)
        self.message_user(request, f"{updated} commission(s) amount decreased by 10%.", messages.SUCCESS)

    @admin.action(description="Set amount")
    def set_custom_amount(self, request, queryset):
        if 'apply' in request.POST:
            form = SetCommissionAmountForm(request.POST)
            if form.is_valid():
                new_amount = form.cleaned_data['new_amount']
                updated = queryset.update(amount=new_amount)
                self.message_user(request, f"{updated} commission(s) updated with new amount ${new_amount}.", messages.SUCCESS)
                return HttpResponseRedirect(request.get_full_path())
        else:
            form = SetCommissionAmountForm(
                initial={'_selected_action': request.POST.getlist(admin.ACTION_CHECKBOX_NAME)}
            )

        return render(
            request,
            'admin/revenue_management/commission/set_commission_amount_intermediate.html',
            {
                'commissions': queryset,
                'form': form,
                'title': 'Set Custom Commission Amount',
            }
        )