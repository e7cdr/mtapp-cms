from django.urls import path
from .views import AdminNotificationListView, FrontendNotificationListView, notifications_json, unread_count

app_name = 'notifications'
urlpatterns = [
    path('admin/', AdminNotificationListView.as_view(), name='admin_list'),
    path('', FrontendNotificationListView.as_view(), name='frontend_list'),
    path('unread-count/', unread_count, name='unread_count'),
    path('json/', notifications_json, name='notifications_json'),
]
