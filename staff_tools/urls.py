from django.urls import path
from . import views
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path


urlpatterns = [
    path('tasks/', views.manage_tasks, name='manage_tasks'),
    path('create-tour/', views.create_tour, name='create_tour'),
    path('partners/', views.manage_partners, name='manage_partners'),
    path('bookings/', views.manage_bookings, name='manage_bookings'),
    path('dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('tasks/<int:task_id>/', views.task_detail, name='task_detail'),
    path('chart/<str:chart_type>/', views.chart_data, name='chart_data'),
    path('logout/', LogoutView.as_view(next_page='home'), name='staff_logout'),
    path('reports/<int:report_id>/', views.report_detail, name='report_detail'),
    path('availability/', views.manage_availability, name='manage_availability'),
    path('bookings/<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('partners/<int:partner_id>/', views.partner_detail, name='partner_detail'),
    path('send-communication/', views.send_communication, name='send_communication'),
    path('login/', LoginView.as_view(template_name='staff_tools/login.html'), name='staff_login'),
]
