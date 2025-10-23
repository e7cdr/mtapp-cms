# Admin Registration
from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import TourAvailability, CommunicationLog, Report, StaffTask, DashboardData, AutomatedAlert

@admin.register(TourAvailability)
class TourAvailabilityAdmin(ModelAdmin):
    list_display = ('tour', 'current_slots', 'last_updated')
    list_filter = ('last_updated',)
    search_fields = ('tour__title', 'notes')

@admin.register(CommunicationLog)
class CommunicationLogAdmin(ModelAdmin):
    list_display = ('staff_name', 'entity_type', 'entity', 'contact_date', 'method', 'follow_up_needed')
    list_filter = ('entity_type', 'method', 'follow_up_needed', 'contact_date')
    search_fields = ('staff_name', 'message')
    date_hierarchy = 'contact_date'

@admin.register(Report)
class ReportAdmin(ModelAdmin):
    list_display = ('title', 'report_type', 'start_date', 'end_date', 'generated_date', 'created_by')
    list_filter = ('report_type', 'generated_date')
    search_fields = ('title', 'created_by')
    date_hierarchy = 'generated_date'
    actions = ['generate_report']

    def generate_report(self, request, queryset):
        for report in queryset:
            report.generate_report_data()
        self.message_user(request, "Selected reports have been regenerated.")
    generate_report.short_description = "Regenerate selected reports"

@admin.register(StaffTask)
class StaffTaskAdmin(ModelAdmin):
    list_display = ('title', 'assigned_to', 'due_date', 'priority', 'status')
    list_filter = ('priority', 'status', 'due_date')
    search_fields = ('title', 'assigned_to', 'description')
    date_hierarchy = 'due_date'

@admin.register(DashboardData)
class DashboardDataAdmin(ModelAdmin):
    list_display = ('metric', 'value', 'last_updated')
    search_fields = ('metric',)

@admin.register(AutomatedAlert)
class AutomatedAlertAdmin(ModelAdmin):
    list_display = ('alert_type', 'message', 'triggered_date', 'is_resolved')
    list_filter = ('alert_type', 'is_resolved', 'triggered_date')
    search_fields = ('message',)
    date_hierarchy = 'triggered_date'