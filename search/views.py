from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.template.response import TemplateResponse
from django.shortcuts import render  # Add this import
from wagtail.models import Page, Locale  # Add Locale for Issue 2

# To enable logging of search queries for use with the "Promoted search results" module
# <https://docs.wagtail.org/en/stable/reference/contrib/searchpromotions.html>
# uncomment the following line and the lines indicated in the search function
# (after adding wagtail.contrib.search_promotions to INSTALLED_APPS):

# from wagtail.contrib.search_promotions.models import Query


def search(request):
    search_query = request.GET.get("query", None)
    page = request.GET.get("page", 1)

    current_language = request.LANGUAGE_CODE  # For locale filtering (Issue 2)

    # Search
    if search_query:
        try:
            locale = Locale.objects.get(language_code=current_language)
        except Locale.DoesNotExist:
            # Fallback to default locale if current language not found
            locale = Locale.get_default()
        
        search_results = Page.objects.live().filter(locale=locale).search(search_query)        # To log this query for use with the "Promoted search results" module:

        # query = Query.get(search_query)
        # query.add_hit()

    else:
        search_results = Page.objects.none()

    # Pagination
    paginator = Paginator(search_results, 10)
    try:
        search_results = paginator.page(page)
    except PageNotAnInteger:
        search_results = paginator.page(1)
    except EmptyPage:
        search_results = paginator.page(paginator.num_pages)

    return render(  # Switch to render
        request,
        ["search/search.html", "search/search_bar.html"],
        {
            "search_query": search_query,
            "search_results": search_results,
        },
    )


        
