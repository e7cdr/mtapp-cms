// Mobile/Dropdown Overlay
const mediaQuerymobile = window.matchMedia("(max-width: 768.98px)");
if (mediaQuerymobile.matches) {
  $(".sort-drop").on("show.bs.dropdown", function () {
    $(".overlay").show();
  });
  $(".sort-drop").on("hide.bs.dropdown", function () {
    $(".overlay").hide();
  });
}

$(".filter-btn").click(function () {
  $(".sidebar").addClass("open");
  $("body").addClass("overflow-hidden vh-100");
});
$(".filter-close-btn").click(function () {
  $(".sidebar").removeClass("open");
  $("body").removeClass("overflow-hidden vh-100");
});

// Sidebar Sticky
const mediaQuerySM = window.matchMedia('(min-width: 768px)');
if (mediaQuerySM.matches) {
  if (typeof StickySidebar !== 'undefined') {
    var sidebar = new StickySidebar('.sidebar', {
      topSpacing: 80,
      bottomSpacing: 20,
      containerSelector: '.main-content',
      innerWrapperSelector: '.sidebar__inner'
    });
  }
}

// Enhanced Dynamic Filtering
$(document).ready(function() {
    console.log('JS loaded: jQuery version', $.fn.jquery);  // TEMP
    const $form = $('#filterForm');
    const $results = $('#resultsContainer');
    const $clearBtn = $('#clearFilters');
    let $paginator = $('.pagination-nav');  // let for re-assign
    const currentFullUrl = new URL(window.location.href);
    let basePath = currentFullUrl.pathname.replace(/^\/+/, '/');  // Strip leading /
    console.log('Normalized base path:', basePath);
    let isLoading = false;
    let liveFilterEnabled = true;

    // Custom Debounce
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Loading State
    function showLoading() {
        $results.addClass('loading').html(`
            <div class="text-center p-4">
                <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
                    <span class="visually-hidden">Loading tours...</span>
                </div>
                <p class="mt-2">Updating results...</p>
            </div>
        `);
    }

    function hideLoading() {
        $results.removeClass('loading');
    }

    const debouncedUpdate = debounce(function(queryString) {
        if (isLoading) return;
        isLoading = true;
        showLoading();
        updateResults(queryString);
    }, 300);

    // Helper: Build query string from form
    function getQueryString() {
        return $form.serialize();
    }

    // Live Filtering on Changes
    if (liveFilterEnabled && $form.length) {
        $form.find('input, select').on('change', handleInputChange);
        $form.find('input[type="text"], input[type="number"], input[type="email"], textarea').on('input', handleInputChange);

        function handleInputChange() {
            const queryString = getQueryString();
            console.log('Form query string:', queryString);  // TEMP
            debouncedUpdate(queryString);
            const newFullUrl = new URL(currentFullUrl);
            newFullUrl.search = queryString ? '?' + queryString : '';
            history.pushState({ filters: queryString }, '', newFullUrl.toString());
        }
    } else if ($form.length) {
        $form.on('submit', function(e) {
            e.preventDefault();
            const queryString = getQueryString();
            debouncedUpdate(queryString);
            const newFullUrl = new URL(currentFullUrl);
            newFullUrl.search = queryString ? '?' + queryString : '';
            history.pushState({ filters: queryString }, '', newFullUrl.toString());
        });
    }

    // Clear Filters
    if ($clearBtn.length) {
        $clearBtn.on('click', function(e) {
            e.preventDefault();
            $form[0].reset();
            debouncedUpdate('');
            const newFullUrl = new URL(currentFullUrl);
            newFullUrl.search = '';
            history.pushState({}, '', newFullUrl.toString());
        });
    }

    // Infinite Scroll
    let currentPage = 1;
    $(window).on('scroll', function() {
        if ($(window).scrollTop() + $(window).height() >= $(document).height() - 100 &&
            $paginator.data('has-next') === true && !isLoading) {
            currentPage++;
            const currentQuery = getQueryString();
            const urlParams = new URLSearchParams(currentQuery);
            urlParams.set('page', currentPage);
            const queryString = urlParams.toString();
            debouncedUpdate(queryString);
        }
    });

    // Popstate
    $(window).on('popstate', function(e) {
        const state = e.originalEvent.state;
        const queryString = state && state.filters || '';
        debouncedUpdate(queryString);
        const newFullUrl = new URL(currentFullUrl);
        newFullUrl.search = queryString ? '?' + queryString : '';
    });

    // Core Update Function
    function updateResults(queryString) {
        const ajaxUrl = queryString ? basePath + '?' + queryString : basePath;
        console.log('AJAX URL (relative):', ajaxUrl);  // TEMP
        $.get(ajaxUrl)
            .done(function(response) {
                console.log('AJAX success: Response length', response.length);  // TEMP
                const $doc = $(response);
                const $newResults = $doc.find('#resultsContainer');
                console.log('New results found:', $newResults.length, 'HTML snippet length:', $newResults.html().length);  // TEMP
                if ($newResults.length) {
                    $results.html($newResults.html());
                    console.log('HTML swapped, new card count:', $('.card').length);  // TEMP
                }
                hideLoading();
                isLoading = false;

                // Update paginator
                const $newPaginator = $doc.find('.pagination-nav');
                if ($newPaginator.length && $paginator.length) {
                    $paginator.replaceWith($newPaginator);
                }
                $paginator = $('.pagination-nav');  // Re-select

                // Re-init
                initAmenitiesCount();
            })
            .fail(function(jqXHR, textStatus, errorThrown) {
                console.error('AJAX fail:', { status: jqXHR.status, textStatus, errorThrown, url: ajaxUrl });
                $results.html(`
                    <div class="alert alert-danger text-center">
                        Error loading tours. <button class="btn btn-sm btn-primary" onclick="location.reload()">Retry</button>
                    </div>
                `);
                hideLoading();
                isLoading = false;
            });
    }

    // Amenities Count
    function initAmenitiesCount() {
        $('.card').each(function() {
            const $card = $(this);
            const $countEl = $card.find('.tour-am-count');
            if ($countEl.length) {
                const iconCount = $card.find('.card-icon').length;
                $countEl.text(iconCount || 0);
            }
        });
    }
    initAmenitiesCount();
});