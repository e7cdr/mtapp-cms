from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.contrib.admin.views.decorators import staff_member_required
import requests
from urllib.parse import urlencode


@staff_member_required  # Keep if the tool is truly staff-only; remove if public users should access
@require_GET
@csrf_exempt           # Only if you really need it (e.g. future POST support); otherwise remove
@never_cache
def nominatim_proxy(request):
    """
    Proxy to Nominatim (OpenStreetMap) search/reverse endpoint.
    Enforces GET, adds required headers, limits abuse potential.
    """
    params = request.GET.copy()

    # Enforce format and useful defaults (Nominatim requires format=json)
    params['format'] = 'json'
    params.setdefault('addressdetails', '1')   # Richer address hierarchy

    # Optional: cap results to prevent huge responses / abuse
    params.setdefault('limit', '8')

    # Determine endpoint securely
    if 'lat' in params and 'lon' in params:
        endpoint = 'reverse'
        # For reverse: zoom is very useful → default to city level if missing
        params.setdefault('zoom', '14')
    elif 'q' in params or 'street' in params or 'city' in params:
        endpoint = 'search'
    else:
        return HttpResponseBadRequest("Missing required parameters (lat+lon for reverse or q/street/city for search)")

    base_url = "https://nominatim.openstreetmap.org"
    full_url = f"{base_url}/{endpoint}?{urlencode(params)}"

    headers = {
        'User-Agent': 'MilanoTravelRoutePlanner/1.0 (contact@yourdomain.com)',  # ← CHANGE THIS!
        'Referer': request.build_absolute_uri(),  # Helps Nominatim identify source
        'Accept': 'application/json',
    }

    try:
        resp = requests.get(
            full_url,
            headers=headers,
            timeout=10,                # Shorter than 15s is usually fine
            allow_redirects=False      # Prevent following suspicious redirects
        )
        resp.raise_for_status()

        data = resp.json()

        # Optional safety: ensure we only return list or dict (Nominatim reverse returns dict, search returns list)
        if isinstance(data, (dict, list)):
            return JsonResponse(data, safe=False)
        else:
            return JsonResponse({"error": "Unexpected response format from Nominatim"}, status=502)

    except requests.Timeout:
        return JsonResponse({"error": "Nominatim request timed out"}, status=504)
    except requests.RequestException as e:
        return JsonResponse({"error": f"Nominatim service error: {str(e)}"}, status=502)
    except ValueError:
        # JSON decode error
        return JsonResponse({"error": "Invalid response from Nominatim"}, status=502)
    
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .models import PlannedRoute  # Assuming you have a Route model
import json

@login_required
@require_POST
@csrf_exempt  # If needed for AJAX; otherwise remove
def save_route(request):
    try:
        route_data = json.loads(request.POST.get('route_data', '{}'))
        name = request.POST.get('route_name', '').strip()
        route_id = request.POST.get('route_id', '').strip()

        if not name:
            return JsonResponse({'error': 'Route name is required'}, status=400)

        waypoints = route_data.get('waypoints', [])
        summary = route_data.get('summary', {})

        if route_id:
            # Update existing route
            route = PlannedRoute.objects.get(id=route_id, user=request.user)
            route.name = name
            route.waypoints = waypoints
            route.summary = summary
            route.save()
            return JsonResponse({'success': True, 'message': 'Route updated', 'id': route.id})
        else:
            # Create new
            route = PlannedRoute.objects.create(
                user=request.user,
                name=name,
                waypoints=waypoints,
                summary=summary
            )
            return JsonResponse({'success': True, 'message': 'Route created', 'id': route.id})

    except PlannedRoute.DoesNotExist:
        return JsonResponse({'error': 'Route not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    


