document.addEventListener('DOMContentLoaded', function () {
    // Elements
    const form = document.getElementById('filterForm');
    const resultsContainer = document.getElementById('resultsContainer');
    const clearBtn = document.getElementById('clearFilters');
    let paginator = document.querySelector('.pagination-nav'); // ← will be updated after replace
    const basePath = window.location.pathname.replace(/\/+$/, '') || '/';

    let isLoading = false;
    let currentPage = 1;

    // Debounce utility
    const debounce = (func, wait) => {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    };

    // Loading state
    const showLoading = () => {
        if (!resultsContainer.classList.contains('loading')) {
            resultsContainer.classList.add('loading');
            resultsContainer.innerHTML = `
                <div class="text-center p-5">
                    <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
                        <span class="visually-hidden">Loading product...</span>
                    </div>
                    <p class="mt-3 text-muted">Updating results...</p>
                </div>
            `;
        }
    };

    const hideLoading = () => {
        resultsContainer.classList.remove('loading');
    };

    // Fetch and update results
    const updateResults = (queryString = '') => {
        if (isLoading) return;
        isLoading = true;
        showLoading();

        const url = queryString ? `${basePath}?${queryString}` : basePath;
        console.log('Fetching:', url);

        fetch(url, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(response => response.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');

            const newResults = doc.querySelector('#resultsContainer');
            const newPaginator = doc.querySelector('.pagination-nav');

            if (newResults) {
                resultsContainer.innerHTML = newResults.innerHTML;
            }

            // FIXED: Safe paginator replacement
            if (newPaginator && paginator) {
                const cloned = newPaginator.cloneNode(true);
                paginator.replaceWith(cloned);
                paginator = cloned; // ← Keep reference alive!
            }

            initAmenitiesCount();
            hideLoading();
            isLoading = false;

            // Scroll to results
            if (currentPage === 1) {
                resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        })
        .catch(err => {
            console.error('AJAX failed:', err);
            resultsContainer.innerHTML = `
                <div class="alert alert-danger text-center p-5">
                    <h5>Error loading product</h5>
                    <button class="btn btn-primary" onclick="location.reload()">Retry</button>
                </div>
            `;
            hideLoading();
            isLoading = false;
        });
    };

    // Serialize form — removes empty values
    const getQueryString = () => {
        const formData = new FormData(form);
        const params = new URLSearchParams();

        for (const [key, value] of formData.entries()) {
            if (value !== '' && value !== null && value !== undefined) {
                params.append(key, value);
            }
        }

        if (currentPage > 1) {
            params.set('page', currentPage);
        }

        return params.toString();
    };

    // Update URL
    const updateURL = (qs) => {
        const newURL = qs ? `${basePath}?${qs}` : basePath;
        history.replaceState({ filters: qs }, '', newURL);
    };

    // Debounced filter update
    const debouncedUpdate = debounce(() => {
        currentPage = 1;
        const qs = getQueryString();
        updateResults(qs);
        updateURL(qs);
    }, 300);

    // Listen to form changes
    form.addEventListener('change', debouncedUpdate);
    form.addEventListener('input', (e) => {
        if (e.target.matches('input[type="text"], input[type="number"], textarea')) {
            debouncedUpdate();
        }
    });

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        debouncedUpdate();
    });

    // Clear filters
    if (clearBtn) {
        clearBtn.addEventListener('click', (e) => {
            e.preventDefault();
            form.reset();
            currentPage = 1;
            updateResults('');
            history.replaceState({}, '', basePath);
        });
    }

    // Infinite scroll
    window.addEventListener('scroll', () => {
        if (
            !isLoading &&
            paginator?.dataset.hasNext === 'true' &&
            window.innerHeight + window.scrollY >= document.body.offsetHeight - 100
        ) {
            currentPage++;
            const qs = getQueryString();
            updateResults(qs);
        }
    });

    // Back/forward navigation
    window.addEventListener('popstate', () => {
        const params = new URLSearchParams(window.location.search);
        const qs = params.toString();

        // Restore form state
        params.forEach((value, key) => {
            const field = form.elements[key];
            if (field) {
                if (field.type === 'checkbox' || field.type === 'radio') {
                    field.checked = field.value === value;
                } else {
                    field.value = value;
                }
            }
        });

        currentPage = parseInt(params.get('page') || '1', 10);
        updateResults(qs);
    });

    // Amenity counter
    const initAmenitiesCount = () => {
        document.querySelectorAll('.card').forEach(card => {
            const countEl = card.querySelector('.am-count');
            if (countEl) {
                const iconCount = card.querySelectorAll('.card-icon').length;
                countEl.textContent = iconCount || 0;
            }
        });
    };

    // Mobile sidebar toggle — UNCHANGED
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelector('.sidebar')?.classList.add('open');
            document.body.classList.add('overflow-hidden', 'vh-100');
        });
    });

    document.querySelectorAll('.filter-close-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelector('.sidebar')?.classList.remove('open');
            document.body.classList.remove('overflow-hidden', 'vh-100');
        });
    });

    // Dropdown overlay on mobile — UNCHANGED
    const mobileMedia = window.matchMedia('(max-width: 768.98px)');
    const overlay = document.querySelector('.overlay');
    const dropdown = document.querySelector('.sort-drop');

    const handleMobileDropdown = () => {
        if (mobileMedia.matches && dropdown && overlay) {
            const observer = new MutationObserver((mutations) => {
                mutations.forEach(mutation => {
                    if (mutation.attributeName === 'class') {
                        const isOpen = dropdown.classList.contains('show');
                        overlay.style.display = isOpen ? 'block' : 'none';
                    }
                });
            });
            observer.observe(dropdown, { attributes: true });
        }
    };

    if (mobileMedia.matches) handleMobileDropdown();
    mobileMedia.addEventListener('change', handleMobileDropdown);

    // Sticky sidebar — UNCHANGED
    if (window.StickySidebar && window.matchMedia('(min-width: 768px)').matches) {
        new StickySidebar('.sidebar', {
            topSpacing: 80,
            bottomSpacing: 20,
            containerSelector: '.main-content',
            innerWrapperSelector: '.sidebar__inner'
        });
    }

    // Initial load
    initAmenitiesCount();
});