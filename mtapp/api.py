# api.py

from wagtail.api.v2.views import PagesAPIViewSet
from wagtail.api.v2.router import WagtailAPIRouter
from wagtail.images.api.v2.views import ImagesAPIViewSet
from wagtail.documents.api.v2.views import DocumentsAPIViewSet
from rest_framework.permissions import IsAuthenticated

from bookings import api_views

# Create the router. "wagtailapi" is the URL namespace
api_router = WagtailAPIRouter('wagtailapi')

# Add the three endpoints using the "register_endpoint" method.
# The first parameter is the name of the endpoint (such as pages, images). This
# is used in the URL of the endpoint
# The second parameter is the endpoint class that handles the requests

class PagesAPIViewSet(PagesAPIViewSet):
    permission_classes = (IsAuthenticated,)

class ImagesAPIViewSet(ImagesAPIViewSet):
    permission_classes = (IsAuthenticated,)

class DocumentsAPIViewSet(DocumentsAPIViewSet):
    permission_classes = (IsAuthenticated,)

api_router.register_endpoint('pages', PagesAPIViewSet)
api_router.register_endpoint('images', ImagesAPIViewSet)
api_router.register_endpoint('documents', DocumentsAPIViewSet)
api_router.register_endpoint('proposal_list', api_views.ProposalsAPIView)
api_router.register_endpoint('booking_list', api_views.BookingsAPIView)
