from rest_framework.fields import Field

class TourFieldSerializer(Field):
    """
    A custom serializer field to handle GenericForeignKey relationships.
    """
    def to_representation(self, value):
        # 'value' is the content_object (e.g., a Page, Image, or Snippet instance)
        if not value:
            return None

        # You can return any representation you need:
        # For a Wagtail Page:
        if hasattr(value, 'name') and hasattr(value, 'code_id'):
            return {
                'id': value.code_id,
                'name': value.name,
                'destination': value.destination,
                # 'type': value._meta.verbose_name.lower(),
            }

        # # For other models/snippets, customize the output as needed:
        # if hasattr(value, 'name'):
        #     return {
        #         'id': value.id,
        #         'name': value.name,
        #         'type': value._meta.verbose_name.lower(),
        #     }

        return str(value) # Fallback to string representation


