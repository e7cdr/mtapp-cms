# from django.contrib import admin
# from axes.models import AccessAttempt

# # Unregister the default Axes admin
# try:
#     admin.site.unregister(AccessAttempt)
# except admin.sites.NotRegistered:
#     pass

# @admin.register(AccessAttempt)
# class AccessAttemptAdmin(admin.ModelAdmin):
#     list_display = ['username', 'ip_address', 'failures_since_start', 'get_locked', 'user_email']  # Add custom
#     readonly_fields = ['locked']
#     list_filter = ['locked', 'failures_since_start']  # For easier filtering

#     def user_email(self, obj):
#         if obj.user:
#             return obj.user.email
#         return None
#     user_email.short_description = 'User Email'