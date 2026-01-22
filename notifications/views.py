from .models import Notification
from django.views.generic import ListView
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin



class AdminNotificationListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model: Notification
    template_name = 'notifications/admin_list.html'
    context_object_name = 'notifications'

    def test_func(self):
        return self.request.user.is_staff
    
    def get_queryset(self):
        qs = super().get_queryset().filter(recipient=self.request.user)
        qs.filter(is_read=False).update(is_read=True)
        return qs


class FrontendNotificationListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Notification
    template_name = 'notifications/frontend_list.html'
    context_object_name = 'notifications'

    def test_func(self):
        return self.request.user.is_staff
    
    # def get_queryset(self):
    #     qs = super().get_queryset().filter(recipient=self.request.user)
        
    #     # Mark all unread as read (even older ones)
    #     qs.filter(is_read=False).update(is_read=True)
        
    #     # Then return only latest 5 for display
    #     return qs.order_by('-created_at')[:5]

    def get_queryset(self):
        # Get base queryset: all notifications for this user, newest first
        base_qs = super().get_queryset().filter(recipient=self.request.user).order_by('-created_at')
        
        # Get PKs of the latest 5 unread notifications (slicing allowed here for values_list)
        unread_pks = list(base_qs.filter(is_read=False).values_list('pk', flat=True)[:5])
        
        # If there are any, mark ONLY those as read (no slice on the update queryset)
        if unread_pks:
            Notification.objects.filter(pk__in=unread_pks).update(is_read=True)
        
        # Return the latest 5 for display
        return base_qs[:5]
        

def unread_count(request):
    if request.user.is_authenticated and request.user.is_staff:
        count = Notification.objects.filter(recipient=request.user, is_read=False)
        return HttpResponse(count)
    return HttpResponse(0)


@login_required
def notifications_json(request):
    if not request.user.is_staff:
        return JsonResponse({'notifications': []}, safe=False)

    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:5]

    data = [{
        'id': n.id,
        'message': n.message,
        'created_at': n.created_at.strftime('%Y-%m-%d %H:%M'),
        'is_read': n.is_read,
    } for n in notifications]

    # notifications.filter(is_read=False).update(is_read=True)

    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

    return JsonResponse({
        'notifications': data,
        'unread_count': unread_count
    })