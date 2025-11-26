# mtapp/blog/wagtail_hooks.py
from django.templatetags.static import static
from django.utils.html import format_html
from django.urls import reverse, path
from django.http import HttpResponse
from django.contrib import messages
import csv

from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.models import Page

from blog.models import BlogDetailPage


# 1. Read time column
@hooks.register("construct_page_listing_buttons")
def add_read_time_column(buttons, page, user, context=None, **kwargs):
    if isinstance(page.specific, BlogDetailPage):
        rt = page.specific.get_read_time_display()
        buttons.append({
            "label": format_html('<span title="Read time"> {} </span>', rt),
            "classname": "button button-small button-secondary",
        })


# 2. Custom admin CSS
@hooks.register("insert_global_admin_css")
def global_admin_css():
    return format_html('<link rel="stylesheet" href="{}">', static("css/admin-custom.css"))


# 3. View in other languages
@hooks.register("construct_page_header_buttons")
def add_translation_buttons(buttons, page, user, **kwargs):
    if hasattr(page, "get_translations"):
        for translation in page.get_translations(inclusive=False):
            lang = translation.locale.language_code.upper()
            buttons.append({
                "url": translation.url,
                "label": f"View {lang}",
                "classname": "button button-small button-secondary",
            })




# 5. Quick translate dropdown
@hooks.register("register_page_header_extras")
def quick_translate_dropdown(page, user):
    if isinstance(page.specific, BlogDetailPage):
        current = page.locale.language_code
        links = []
        for code in ["pl", "is", "es", "en"]:
            if code != current:
                url = f"/admin/pages/{page.id}/edit/?translate_to={code}"
                links.append(f'<a href="{url}" class="button button-small button-secondary">To {code.upper()}</a>')
        if links:
            return format_html('<div class="wagtail-action-dropdown ms-2">{} </div>', " ".join(links))
    return ""


# 6. Custom logo in admin menu
@hooks.register("construct_main_menu")
def add_custom_logo(request, menu_items):
    menu_items[:0] = [
        MenuItem(
            "Milano Travel",
            reverse("wagtailadmin_home"),
            icon_name="home",
            classname="logo-menu-item",
        )
    ]


# 7. Export Blog to CSV — NEW Wagtail 5+/6+ method (no modeladmin!)
def export_blog_csv_view(request):
    if not request.user.is_superuser:
        messages.error(request, "Only admins can export.")
        return HttpResponse("Forbidden", status=403)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="milano-travel-blog-2025.csv"'

    writer = csv.writer(response)
    writer.writerow(["Title", "Date", "Country", "Category", "Tags", "URL"])

    for post in BlogDetailPage.objects.live().order_by("-date_published"):
        writer.writerow([
            post.title,
            post.date_published,
            post.source_country or "General",
            post.category.name if post.category else "",
            ", ".join(tag.name for tag in post.tags.all()),
            request.build_absolute_uri(post.url),
        ])

    return response


@hooks.register("register_admin_urls")
def register_export_csv_url():
    return [
        path("blog/export-csv/", export_blog_csv_view, name="blog_export_csv"),
    ]


@hooks.register("register_admin_menu_item")
def add_export_csv_menu_item():
    return MenuItem(
        "Export Blog CSV",
        reverse("blog_export_csv"),
        icon_name="download",
        classname="button button-secondary",
        order=10000,
    )