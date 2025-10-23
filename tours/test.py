from django.db.models import Count
from tours.models import LandTourPage

# Check for duplicate code_id
duplicates_code = LandTourPage.objects.values('code_id').annotate(count=Count('id')).filter(count__gt=1)
print("Duplicate code_id values:", duplicates_code)

# Fix duplicate code_id
for dup in duplicates_code:
    if dup['code_id']:
        pages = LandTourPage.objects.filter(code_id=dup['code_id'])
        for i, page in enumerate(pages[1:], 1):  # Keep the first, update the rest
            page.code_id = f"{page.code_id}-{i}"
            page.save()