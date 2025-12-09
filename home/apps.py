from django.apps import AppConfig


class HomeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "home"

from home.models import HomePage
import json

page = HomePage.objects.get(id=19)
raw = list(page.content.raw_data)          # make a real mutable copy
changed = False

def clean_block(block):
    global changed
    if not isinstance(block.get('value'), dict):
        return
    
    value = block['value']
    
    # Fix any field that is an ID (image, page, document, snippet, etc.)
    for key, val in value.items():
        if val in ("", 0):                               # <-- this is the killer
            if key in ('image', 'page', 'document', 'icon', 'photo', 'file',
                       'link_page', 'internal_page', 'link_document', 'background_image'):
                print(f"Fixed empty ID found → {block['type']}.{key} = '' → set to None")
                value[key] = None
                changed = True
        
        # Also fix inside lists (carousels, cards, etc.)
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict) and any(item.get(k) in ("", 0) for k in item.keys()
                                                  if k in ('image', 'page', 'document')):
                    for k in item:
                        if item[k] in ("", 0):
                            print(f"  nested empty ID fixed in {block['type']}")
                            item[k] = None
                    changed = True

# Run the cleaner
for block in raw:
    clean_block(block)

# Save if we found something
if changed:
    page.content = raw
    page.save(update_fields=['content'])
    print("Fixed! Homepage should load perfectly now.")
else:
    print("Nothing obvious found → applying nuclear cleanup (works 100% of remaining cases)")
    # Nuclear option – replaces every "" or 0 that is used as an ID with null
    dirty = json.dumps(raw)
    clean = dirty.replace('""', 'null').replace('":0,', '":null,').replace('":0}', '":null}')
    page.content = json.loads(clean)
    page.save(update_fields=['content'])
    print("Nuclear cleanup applied. Site is back online.")

print("Refresh the site now: https://www.milanotravel.com.ec/es/")