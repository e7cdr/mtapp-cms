from django.urls import path, re_path
from .views import nominatim_proxy, save_route

urlpatterns = [
    re_path(r'^nominatim-proxy(?:/.*)?$', nominatim_proxy),  # catch prefixed or not
    path('save-route/', save_route, name='save_route'),

]

