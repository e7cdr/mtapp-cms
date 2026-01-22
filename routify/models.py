from django.db import models
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from wagtail.models import Page
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet
from django.contrib.auth.models import User 
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
import json

@register_snippet
class PlannedRoute(models.Model):
    name = models.CharField(max_length=255, help_text="e.g. 'Cuenca → Ingapirca via Cañar'")
    waypoints = models.JSONField(default=list, blank=True)
    route_summary = models.JSONField(default=dict, blank=True)
    notes = RichTextField(blank=True)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('User'),
        help_text=_('The user who created the reservation. Defaults to MTWEB for non-authenticated users.')
    )

    panels = [
        FieldPanel('name'),
        FieldPanel('waypoints', classname="full"),
        FieldPanel('route_summary', classname="full"),
        FieldPanel('notes'),
        FieldPanel('user'),
    ]

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Planned Route"
        verbose_name_plural = "Planned Routes"


class PlannedRouteViewSet(SnippetViewSet):
    model = PlannedRoute
    list_display = ['name']
    search_fields = ['name']


class RoutePlannerPage(Page):
    template = "routify/routeplannerpage.html"

    subpage_types = []
    parent_page_types = ['home.HomePage']

    max_count = 1  # Optional: enforce only one instance

    def get_context(self, request):
        context = super().get_context(request)
        routes_qs = PlannedRoute.objects.all().order_by('-id')
        context['routes'] = routes_qs
        context['routes_json'] = json.dumps([
            {
                'id': r.id,
                'name': r.name,
                'waypoints': r.waypoints,
                'summary': r.route_summary,
                'notes': str(r.notes),  # HTML-safe rendered notes
            } for r in routes_qs
        ])
        return context

    def serve(self, request):
        if not request.user.is_staff:
            raise Http404("Not found")

        if request.method == "POST":
            action = request.POST.get("action")

            if action == "delete":
                route_id = request.POST.get("route_id")
                if route_id:
                    try:
                        route = PlannedRoute.objects.get(id=route_id)
                        route_name = route.name  # Store for message
                        route.delete()
                        messages.success(request, f'Route "{route_name}" deleted successfully.')
                    except PlannedRoute.DoesNotExist:
                        messages.error(request, "Route not found.")
                else:
                    messages.error(request, "No route ID provided for deletion.")
                return HttpResponseRedirect(request.path)

            # Save / Update route
            try:
                payload = json.loads(request.POST.get("route_data", "{}"))
                name = request.POST.get("route_name", "").strip()
                route_id = request.POST.get("route_id")
                notes = request.POST.get("route_notes", "")

                if not name:
                    return JsonResponse({'success': False, 'error': 'Route name is required'}, status=400)

                if route_id:
                    # Update existing route
                    route = get_object_or_404(PlannedRoute, id=route_id)  # Removed user filter for legacy routes
                    route.name = name
                else:
                    # Create new route
                    route = PlannedRoute(name=name, user=request.user)

                route.waypoints = payload.get("waypoints", [])
                route.route_summary = payload.get("summary", {})
                route.notes = notes
                route.save()

                return JsonResponse({
                    'success': True,
                    'message': f'Route "{name}" {"updated" if route_id else "created"} successfully!',
                    'id': route.id
                })

            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'error': 'Invalid route data format'}, status=400)
            except PlannedRoute.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Route not found or no permission'}, status=404)
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=500)

        return super().serve(request)

    class Meta:
        verbose_name = "Route Planner Tool"