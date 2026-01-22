from wagtail.admin.menu import MenuItem
from wagtail import hooks
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from .models import Notification

@hooks.register('register_admin_menu_item')
def register_notification_menu_item():
    def get_unread_count(request):
        return Notification.objects.filter(recipient=request.user, is_read=False).count()
    
    return MenuItem(
        _('Notifications'),
        reverse('notifications:admin_list'),
        icon_name='mail',
        order=1000,
        attrs={'data-unread-count': get_unread_count}
    )