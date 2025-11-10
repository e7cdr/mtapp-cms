from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_sales_rep', 'phone']
    list_filter = ['is_sales_rep']