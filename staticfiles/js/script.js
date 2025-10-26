document.addEventListener('DOMContentLoaded', function () {
    const itemsPerPage = 5;

    // Initialize modals
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.addEventListener('show.bs.modal', function () {
            modal.removeAttribute('aria-hidden');
            console.log('Modal shown:', modal.id);
            const bookingForm = modal.querySelector('#bookingForm');
            if (bookingForm) {
                initializeBookingForm(modal.id);
                if (typeof htmx !== 'undefined') {
                    htmx.process(modal);
                    console.log('HTMX processed for modal:', modal.id);
                } else {
                    console.warn('HTMX not loaded for modal:', modal.id);
                }
            } else {
                console.error('Booking form not found in modal:', modal.id);
            }
        });
        modal.addEventListener('hidden.bs.modal', function () {
            modal.setAttribute('aria-hidden', 'true');
            console.log('Modal hidden:', modal.id);
        });
    });

        // Handle configuration selection
    document.querySelectorAll('.select-config-btn').forEach(button => {
        button.addEventListener('click', function () {
            const index = this.dataset.configIndex;
            const selectedConfigInput = document.getElementById('selected_configuration_index');
            if (selectedConfigInput) {
                selectedConfigInput.value = index;
                console.log('Configuration selected:', index);
                document.querySelectorAll('.select-config-btn').forEach(btn => btn.classList.remove('btn-success'));
                this.classList.add('btn-success');
            } else {
                console.error('Selected configuration input not found');
            }
        });
    });

    // Debug toggle elements
    console.log('Checking toggle elements:');
    console.log('Theme toggle:', document.querySelector('#themeToggle') ? 'Found' : 'Missing');
    console.log('Currency toggle:', document.querySelector('#currencyToggle') ? 'Found' : 'Missing');
    console.log('Currency dropdown:', document.querySelector('#currencyDropdown') ? 'Found' : 'Missing');
    console.log('Currency form:', document.querySelector('#currencyForm') ? 'Found' : 'Missing');
    console.log('Currency input:', document.querySelector('#currencyInput') ? 'Found' : 'Missing');

    // Theme toggle
    const themeToggle = document.querySelector('#themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', function () {
            document.body.classList.toggle('dark');
            const isDark = document.body.classList.contains('dark');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            const icon = themeToggle.querySelector('i');
            if (icon) {
                icon.classList.toggle('bi-sun', !isDark);
                icon.classList.toggle('bi-moon', isDark);
            }
            console.log('Theme toggled:', isDark ? 'dark' : 'light');
        });
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            document.body.classList.add('dark');
            const icon = themeToggle.querySelector('i');
            if (icon) icon.classList.replace('bi-sun', 'bi-moon');
            console.log('Loaded saved theme: dark');
        }
    } else {
        console.warn('Theme toggle element missing');
    }


    // Currency form handling
    const currencyForm = document.querySelector('#currencyForm');
    const currencyToggle = document.querySelector('#currencyToggle');
    const currencyDropdown = document.querySelector('#currencyDropdown');
    const currencyInput = document.querySelector('#currencyInput');

    if (currencyForm && currencyToggle && currencyDropdown && currencyInput) {
        console.log('Currency form elements found:', { currencyForm, currencyToggle, currencyDropdown, currencyInput });

        function configureCurrencyForm(bookingForm) {
            const tourType = document.querySelector('#id_tour_type')?.value || window.bookingData?.tourType || 'land';
            const tourId = document.querySelector('#id_tour_id')?.value || window.bookingData?.tourId || '1';
            const languagePrefix = window.bookingData?.languagePrefix || 'en';
            const url = bookingForm && tourType && tourId
                ? `/${languagePrefix}/bookings/calculate_pricing/${tourType}/${tourId}/`
                : `/${languagePrefix}/set_currency/`;
            currencyForm.setAttribute('hx-post', url);
            currencyForm.setAttribute('hx-target', bookingForm ? '#pricing-options' : 'body');
            currencyForm.setAttribute('hx-swap', bookingForm ? 'innerHTML' : 'none');
            console.log('Currency form configured:', {
                'hx-post': url,
                'hx-target': bookingForm ? '#pricing-options' : 'body',
                'hx-swap': bookingForm ? 'innerHTML' : 'none'
            });
            if (bookingForm && !document.querySelector('#pricing-options')) {
                console.warn('Target #pricing-options not found in DOM');
            }
        }

        let bookingForm = document.querySelector('#bookingForm');
        configureCurrencyForm(bookingForm);

        document.querySelector('#bookingModal')?.addEventListener('show.bs.modal', function () {
            bookingForm = document.querySelector('#bookingForm');
            configureCurrencyForm(bookingForm);
        });

        currencyToggle.addEventListener('click', function (event) {
            event.preventDefault();
            currencyDropdown.classList.toggle('hidden');
            console.log('Currency dropdown toggled:', currencyDropdown.classList.contains('hidden') ? 'hidden' : 'visible');
        });

        currencyDropdown.addEventListener('click', function (event) {
            event.preventDefault();
            event.stopPropagation();
            const currencyButton = event.target.closest('.currency-option');
            if (currencyButton) {
                const currencyValue = currencyButton.dataset.currency;
                if (!currencyValue) {
                    console.error('No data-currency attribute found on button:', currencyButton.outerHTML);
                    return;
                }
                currencyInput.value = currencyValue;
                currencyToggle.querySelector('span').textContent = currencyValue;
                localStorage.setItem('selectedCurrency', currencyValue);
                console.log('Currency selected:', {
                    currency: currencyValue,
                    button: currencyButton.outerHTML,
                    formAction: currencyForm.getAttribute('hx-post')
                });

                const formData = new FormData(currencyForm);
                formData.set('form_submission', 'pricing');

                bookingForm = document.querySelector('#bookingForm');
                if (bookingForm) {
                    const bookingFormData = new FormData(bookingForm);
                    for (const [key, value] of bookingFormData) {
                        if (key !== 'currency' && key !== 'csrfmiddlewaretoken' && key !== 'form_submission') {
                            formData.set(key, value);
                        }
                    }
                }

                console.log('FormData for HTMX request:', Object.fromEntries(formData));

                htmx.ajax('POST', currencyForm.getAttribute('hx-post'), {
                    target: currencyForm.getAttribute('hx-target'),
                    swap: currencyForm.getAttribute('hx-swap'),
                    values: Object.fromEntries(formData),
                    headers: {
                        'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                    }
                }).then(() => {
                    console.log('HTMX currency update successful');
                    currencyDropdown.classList.add('hidden');
                    const errorMessage = document.getElementById('htmx-error-message');
                    if (errorMessage) errorMessage.classList.add('hidden');
                    if (bookingForm) {
                        const pricingTable = document.querySelector('#pricing-options .pricing-table');
                        if (pricingTable) {
                            window.initializePricingControls(pricingTable);
                            const configs = JSON.parse(pricingTable.dataset.configurations || '[]');
                            if (configs.length > 0 && configs[0].currency !== currencyValue) {
                                console.warn(`Currency mismatch: UI=${currencyValue}, Backend=${configs[0].currency}`);
                                if (errorMessage) {
                                    errorMessage.textContent = `Currency ${currencyValue} not available, defaulted to ${configs[0].currency}.`;
                                    errorMessage.classList.remove('hidden');
                                }
                                currencyToggle.querySelector('span').textContent = configs[0].currency;
                                localStorage.setItem('selectedCurrency', configs[0].currency);
                            }
                        }
                    }
                }).catch(error => {
                    console.error('HTMX currency update failed:', error);
                    const errorMessage = document.getElementById('htmx-error-message');
                    if (errorMessage) {
                        errorMessage.textContent = 'Failed to update currency. Please try again.';
                        errorMessage.classList.remove('hidden');
                    }
                });
            }
        });

        currencyForm.addEventListener('htmx:beforeRequest', function (event) {
            console.log('Currency form htmx:beforeRequest triggered', {
                url: event.detail.pathInfo.requestPath,
                method: event.detail.verb,
                parameters: event.detail.parameters
            });
        });

        currencyForm.addEventListener('htmx:afterRequest', function (event) {
            console.log('HTMX request completed:', {
                status: event.detail.xhr.status,
                response: event.detail.xhr.responseText.slice(0, 200) + '...',
                successful: event.detail.successful,
                headers: event.detail.xhr.getAllResponseHeaders()
            });
        });

        const savedCurrency = localStorage.getItem('selectedCurrency');
        if (savedCurrency) {
            const currencyButton = currencyDropdown.querySelector(`.currency-option[data-currency="${savedCurrency}"]`);
            if (currencyButton) {
                currencyInput.value = savedCurrency;
                currencyToggle.querySelector('span').textContent = savedCurrency;
                console.log('Restored currency from localStorage:', savedCurrency);

                const formData = new FormData(currencyForm);
                formData.set('form_submission', 'pricing');

                bookingForm = document.querySelector('#bookingForm');
                if (bookingForm) {
                    const bookingFormData = new FormData(bookingForm);
                    for (const [key, value] of bookingFormData) {
                        if (key !== 'currency' && key !== 'csrfmiddlewaretoken' && key !== 'form_submission') {
                            formData.set(key, value);
                        }
                    }
                }

                console.log('FormData for saved currency HTMX request:', Object.fromEntries(formData));

                htmx.ajax('POST', currencyForm.getAttribute('hx-post'), {
                    target: currencyForm.getAttribute('hx-target'),
                    swap: currencyForm.getAttribute('hx-swap'),
                    values: Object.fromEntries(formData),
                    headers: {
                        'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                    }
                }).then(() => {
                    console.log('HTMX saved currency update successful');
                }).catch(error => {
                    console.error('HTMX saved currency update failed:', error);
                });
            }
        }
    } else {
        console.warn('Currency form elements missing:', {
            currencyForm: !!currencyForm,
            currencyToggle: !!currencyToggle,
            currencyDropdown: !!currencyDropdown,
            currencyInput: !!currencyInput
        });
    }

    // HTMX re-initialization for navbar
    document.addEventListener('htmx:afterSwap', function (evt) {
        const target = evt.detail.target;
        console.log(`HTMX afterSwap triggered for target: ${target.id} path: ${evt.detail.pathInfo.requestPath}`);
        if (target.classList.contains('navbar') || target.contains(document.querySelector('.navbar'))) {
            console.log('Navbar content swapped, re-initializing toggles');
            // Re-attach theme toggle
            const themeToggle = document.querySelector('#themeToggle');
            if (themeToggle) {
                themeToggle.addEventListener('click', function () {
                    document.body.classList.toggle('dark');
                    const isDark = document.body.classList.contains('dark');
                    localStorage.setItem('theme', isDark ? 'dark' : 'light');
                    const icon = themeToggle.querySelector('i');
                    if (icon) {
                        icon.classList.toggle('bi-sun', !isDark);
                        icon.classList.toggle('bi-moon', isDark);
                    }
                    console.log('Theme toggled:', isDark ? 'dark' : 'light');
                });
                const savedTheme = localStorage.getItem('theme');
                if (savedTheme === 'dark') {
                    document.body.classList.add('dark');
                    const icon = themeToggle.querySelector('i');
                    if (icon) icon.classList.replace('bi-sun', 'bi-moon');
                    console.log('Loaded saved theme: dark');
                }
            } else {
                console.warn('Theme toggle element missing after HTMX swap');
            }
            // Re-attach currency toggle
            const currencyForm = document.querySelector('#currencyForm');
            const currencyToggle = document.querySelector('#currencyToggle');
            const currencyDropdown = document.querySelector('#currencyDropdown');
            const currencyInput = document.querySelector('#currencyInput');
            if (currencyForm && currencyToggle && currencyDropdown && currencyInput) {
                let bookingForm = document.querySelector('#bookingForm');
                configureCurrencyForm(bookingForm);
                currencyToggle.addEventListener('click', function (event) {
                    event.preventDefault();
                    currencyDropdown.classList.toggle('hidden');
                    console.log('Currency dropdown toggled:', currencyDropdown.classList.contains('hidden') ? 'hidden' : 'visible');
                });
                // Rest of currency logic in main block
            } else {
                console.warn('Currency form elements missing after HTMX swap:', {
                    currencyForm: !!currencyForm,
                    currencyToggle: !!currencyToggle,
                    currencyDropdown: !!currencyDropdown,
                    currencyInput: !!currencyInput
                });
            }
            // Re-attach language toggle
            const languageForm = document.querySelector('#languageForm');
            const languageToggle = document.querySelector('#languageToggle');
            const languageDropdown = document.querySelector('#languageDropdown');
            const languageInput = document.querySelector('#languageInput');
            if (languageForm && languageToggle && languageDropdown && languageInput) {
                languageToggle.addEventListener('click', function (event) {
                    event.preventDefault();
                    languageDropdown.classList.toggle('hidden');
                    console.log('Language dropdown toggled:', languageDropdown.classList.contains('hidden') ? 'hidden' : 'visible');
                });
                // Rest of language logic in main block
            } else {
                console.warn('Language form elements missing after HTMX swap:', {
                    languageForm: !!languageForm,
                    languageToggle: !!languageToggle,
                    languageDropdown: !!languageDropdown,
                    languageInput: !!languageInput
                });
            }
        }
        // Existing afterSwap logic
        if (target.id === 'booking-form-container') {
            const response = evt.detail.xhr.response;
            if (response.includes('id="bookingForm"') && response.includes('Confirm Proposal')) {
                console.log('Confirm proposal page loaded, skipping form initialization');
                return;
            }
            if (typeof htmx !== 'undefined') {
                htmx.process(target);
                console.log('Reprocessed booking-form-container with HTMX');
            }
            const modal = document.getElementById('bookingModal');
            if (modal) {
                initializeBookingForm(modal.id);
                console.log('Reprocessed modal with HTMX:', modal.id);
            }
            const pricingTable = target.querySelector('.pricing-table');
            if (!pricingTable) {
                console.log('No pricing table found after booking form swap, triggering pricing update');
                window.triggerPricingUpdate();
            }
        }
    });

    // Parse booking data
    let bookingData = {};
    try {
        const bookingDataElement = document.querySelector('#booking-data');
        const rawBookingData = bookingDataElement ? bookingDataElement.textContent.trim() : '{}';
        console.log('Raw bookingData text:', rawBookingData);
        bookingData = JSON.parse(rawBookingData);
        console.log('Parsed bookingData:', bookingData);
    } catch (error) {
        console.error('Failed to parse bookingData:', error);
    }
    window.bookingData = bookingData;

    // Initialize date picker
    function initializeDatePicker(tourType, tourId, tourDuration) {
        const travelDateInput = document.getElementById('id_travel_date');
        const endDateInput = document.getElementById('id_end_date');
        if (!travelDateInput || !endDateInput) {
            console.warn('Travel date or end date input not found:', {
                travelDateInput: !!travelDateInput,
                endDateInput: !!endDateInput
            });
            return;
        }

        // Destroy existing Flatpickr instances
        if (travelDateInput._flatpickr) {
            travelDateInput._flatpickr.destroy();
        }

        if (typeof flatpickr === 'undefined') {
            console.warn('Flatpickr is not defined. Using native date input.');
            travelDateInput.type = 'date';
            travelDateInput.min = new Date().toISOString().split('T')[0];
            travelDateInput.value = '2025-05-11';
            travelDateInput.addEventListener('change', () => {
                console.log('Native date input changed:', travelDateInput.value);
                updateEndDate(travelDateInput.value, tourDuration, endDateInput);
                window.triggerPricingUpdate();
            });
            updateEndDate('2025-05-11', tourDuration, endDateInput);
            return;
        }

        const dateUrl = `/${window.bookingData?.languagePrefix || 'en'}/api/tours/available_dates/?tour_type=${tourType}&tour_id=${tourId}`;
        console.log('Fetching dates from:', dateUrl, { tourType, tourId });

        fetch(dateUrl)
            .then(response => {
                console.log('Date fetch status:', response.status);
                if (!response.ok) {
                    return response.json().then(err => {
                        throw new Error(`HTTP ${response.status}: ${err.error || 'Unknown error'}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                console.log('Available dates response:', data);
                const today = new Date().toISOString().split('T')[0];
                let availableDates = data.available_dates || [];
                if (!availableDates.length) {
                    console.warn('No available dates returned for tour:', { tourType, tourId, error: data.error || 'No dates available' });
                    availableDates = ['2025-05-11'];
                    alert(`No available dates for this tour: ${data.error || 'Pricing will use 2025-05-11. Contact support for assistance.'}`);
                }

                const flatpickrConfig = {
                    dateFormat: 'Y-m-d',
                    enable: availableDates,
                    minDate: availableDates[0] ? Math.min(new Date(availableDates[0]), new Date(today)) : today,
                    maxDate: tourType === 'day' ? availableDates[0] : availableDates[availableDates.length - 1],
                    altInput: true,
                    altFormat: 'F j, Y',
                    locale: { firstDayOfWeek: 0 },
                    disableMobile: true,
                    defaultDate: travelDateInput.value && travelDateInput.value.includes('-') ? travelDateInput.value : availableDates[0],
                    onChange: function (selectedDates, dateStr, instance) {
                        console.log('Date selected:', dateStr);
                        travelDateInput.value = dateStr;
                        const [year, month, day] = dateStr.split('-').map(Number);
                        const utcDate = new Date(Date.UTC(year, month - 1, day));
                        const formattedDate = new Intl.DateTimeFormat('en-US', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric',
                            timeZone: 'UTC'
                        }).format(utcDate);
                        instance.altInput.value = formattedDate;
                        updateEndDate(dateStr, tourDuration, endDateInput);
                        window.updateChildAges();
                        window.triggerPricingUpdate();
                    },
                    onReady: function (selectedDates, dateStr, instance) {
                        instance.altInput.readOnly = true;
                        let initialDate = travelDateInput.value || (availableDates[0] || '2025-05-11');
                        if (initialDate && !initialDate.includes('-')) {
                            try {
                                const [year, month, day] = initialDate.split('-').map(Number);
                                initialDate = new Date(Date.UTC(year, month - 1, day)).toISOString().split('T')[0];
                            } catch (e) {
                                initialDate = availableDates[0] || '2025-05-11';
                            }
                        }
                        instance.setDate(initialDate, false);
                        travelDateInput.value = initialDate;
                        const [year, month, day] = initialDate.split('-').map(Number);
                        const utcDate = new Date(Date.UTC(year, month - 1, day));
                        const formattedDate = new Intl.DateTimeFormat('en-US', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric',
                            timeZone: 'UTC'
                        }).format(utcDate);
                        instance.altInput.value = formattedDate;
                        console.log('Set travel date:', initialDate, 'Formatted:', formattedDate);
                        updateEndDate(initialDate, tourDuration, endDateInput);
                        window.triggerPricingUpdate();
                    }
                };

                flatpickr(travelDateInput, flatpickrConfig);
            })
            .catch(error => {
                console.error('Error fetching dates:', error.message);
                const defaultDate = '2025-05-11';
                flatpickr(travelDateInput, {
                    dateFormat: 'Y-m-d',
                    minDate: today,
                    altInput: true,
                    altFormat: 'F j, Y',
                    disableMobile: true,
                    defaultDate: defaultDate,
                    onReady: function (selectedDates, dateStr, instance) {
                        instance.altInput.readOnly = true;
                        const formattedDate = new Intl.DateTimeFormat('en-US', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric'
                        }).format(new Date(dateStr));
                        instance.altInput.value = formattedDate;
                    }
                });
                travelDateInput.value = defaultDate;
                console.log('Set fallback travel date:', defaultDate);
                updateEndDate(defaultDate, tourDuration, endDateInput);
                window.triggerPricingUpdate();
            });
    }

    // Update end date
    function updateEndDate(travelDateStr, tourDuration, endDateInput) {
        if (!endDateInput || !travelDateStr || !tourDuration) {
            console.warn('Cannot update end date:', { travelDateStr, tourDuration, endDateInput });
            return;
        }
        try {
            const [year, month, day] = travelDateStr.split('-').map(Number);
            const travelDate = new Date(Date.UTC(year, month - 1, day));
            if (isNaN(travelDate)) throw new Error('Invalid travel date');
            const endDate = new Date(travelDate);
            endDate.setUTCDate(travelDate.getUTCDate() + parseInt(tourDuration) - 1);
            const formattedEndDate = new Intl.DateTimeFormat('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                timeZone: 'UTC'
            }).format(endDate);
            endDateInput.value = formattedEndDate;
            console.log('Updated end date:', formattedEndDate, 'tourDuration:', tourDuration);
        } catch (error) {
            console.error('Error updating end date:', error);
        }
    }

    // Navbar handling
    const navbarToggler = document.querySelector('.navbar-toggler');
    const navbarCollapse = document.querySelector('.navbar-collapse');
    if (navbarToggler && navbarCollapse) {
        navbarToggler.addEventListener('click', function () {
            navbarCollapse.classList.toggle('show');
            console.log('Navbar toggled:', navbarCollapse.classList.contains('show'));
        });
    }

    const navbar = document.querySelector('.navbar');
    if (navbar) {
        window.addEventListener('scroll', function () {
            navbar.classList.toggle('scrolled', window.scrollY > 50);
        }, { passive: true });
    }

    // Dropdown submenus
    const dropdownSubmenus = document.querySelectorAll('.dropdown-submenu');
    dropdownSubmenus.forEach(submenu => {
        submenu.addEventListener('mouseenter', function () {
            const subList = submenu.querySelector('.dropdown-sub-list');
            if (subList) {
                subList.style.display = 'block';
                subList.style.opacity = '1';
                subList.style.transform = 'scaleY(1)';
            }
        }, { passive: true });
        submenu.addEventListener('mouseleave', function () {
            const subList = submenu.querySelector('.dropdown-sub-list');
            if (subList) {
                subList.style.opacity = '0';
                subList.style.transform = 'scaleY(0)';
                setTimeout(() => subList.style.display = 'none', 300);
            }
        }, { passive: true });
    });

    // Prevent Enter key form submission
    document.addEventListener('keydown', function (event) {
        if (event.key === 'Enter' && event.target.closest('.booking-form')) {
            event.preventDefault();
        }
    }, { passive: true });

    // Tour carousel
    const tourCarousel = document.querySelector('#tourCarousel');
    if (tourCarousel && typeof bootstrap !== 'undefined') {
        new bootstrap.Carousel(tourCarousel, { ride: 'carousel' });
    }

    // Remove disable-htmx extension to allow controlled requests
    document.addEventListener('htmx:afterSettle', function (evt) {
        console.log('HTMX afterSettle triggered for target:', evt.detail.target.id);
        if (evt.detail.target.id === 'child-ages-container') {
            console.log('HTMX settled for child-ages-container, allowing controlled updates');
        }
        if (evt.detail.target.id === 'booking-form-container') {
            const travelDateInput = document.getElementById('id_travel_date');
            const tourTypeInput = document.getElementById('id_tour_type');
            const tourIdInput = document.getElementById('id_tour_id');
            const tourDuration = parseInt(document.getElementById('booking-form-container')?.dataset.duration || '4', 10);
            if (travelDateInput && tourTypeInput && tourIdInput) {
                initializeDatePicker(tourTypeInput.value, tourIdInput.value, tourDuration);
                console.log('Re-initialized Flatpickr for travel_date after settle');
            } else {
                console.log('Skipping date picker reinitialization, inputs missing:', {
                    travelDateInput: !!travelDateInput,
                    tourTypeInput: !!tourTypeInput,
                    tourIdInput: !!tourIdInput
                });
            }
        }
        if (evt.detail.target.id === 'pricing-options') {
            const pricingTable = evt.detail.target.querySelector('.pricing-table');
            if (pricingTable) {
                pricingTable.dataset.initialized = '';
                window.initializePricingControls(pricingTable);
                console.log('Initialized pricing controls after settle');
                window.updateSelectedConfiguration(); // Ensure configuration is updated
            }
        }
    });

    // Child age change listener with debouncing
    let childAgeDebounceTimeout = null;
    document.addEventListener('change', function (e) {
        if (e.target.matches('#child-ages-container .child-age-input')) {
            console.log('Child age select changed:', e.target.value, 'id:', e.target.id);
            e.stopPropagation();
            clearTimeout(childAgeDebounceTimeout);
            childAgeDebounceTimeout = setTimeout(() => {
                const activeSelect = document.querySelector(`#${e.target.id}`);
                window.updateChildAges(false);
                window.triggerPricingUpdate();
                if (activeSelect) {
                    console.log('Restoring focus to:', activeSelect.id);
                    setTimeout(() => activeSelect.focus(), 50);
                }
            }, 100);
        }
    });

    // Number of children change listener
    document.addEventListener('change', function (e) {
        if (e.target.matches('#id_number_of_children')) {
            const numChildren = parseInt(e.target.value || 0);
            console.log('childrenInput changed, numChildren:', numChildren);
            const childAgesContainer = document.getElementById('child-ages-container');
            if (childAgesContainer) {
                const currentChildAges = document.getElementById('id_child_ages')?.value || '[]';
                const tourType = document.getElementById('id_tour_type')?.value || window.bookingData?.tourType || 'land';
                const tourId = document.getElementById('id_tour_id')?.value || window.bookingData?.tourId || '1';
                const languagePrefix = window.bookingData?.languagePrefix || 'en';
                const hxGetUrl = `/${languagePrefix}/bookings/child_ages/?number_of_children=${encodeURIComponent(numChildren)}&child_ages=${encodeURIComponent(currentChildAges)}&tour_type=${encodeURIComponent(tourType)}&tour_id=${encodeURIComponent(tourId)}`;
                console.log('Setting hx-get to:', hxGetUrl);
                childAgesContainer.setAttribute('hx-get', hxGetUrl);
                childAgesContainer.dataset.lastHxGet = hxGetUrl;
                childAgesContainer.dataset.allowRequest = 'true';
                console.log('Triggering childAgesUpdate for child-ages-container');
                htmx.trigger(childAgesContainer, 'childAgesUpdate');
                setTimeout(() => {
                    childAgesContainer.removeAttribute('data-allow-request');
                    console.log('Cleared allow-request flag');
                }, 100);
                window.updateChildAges(false);
            }
        }
    });

    // Update child ages
    window.updateChildAges = function (triggerHtmx = true) {
        const numChildrenInput = document.getElementById('id_number_of_children');
        const childAgesContainer = document.getElementById('child-ages-container');
        const childAgesInput = document.getElementById('id_child_ages');
        const numChildren = parseInt(numChildrenInput?.value || 0);
        console.log('updateChildAges - numChildren:', numChildren);

        if (!childAgesContainer || numChildren <= 0) {
            childAgesContainer?.classList.add('d-none');
            if (childAgesInput) {
                const newAges = [];
                if (JSON.stringify(newAges) !== childAgesInput.value) {
                    childAgesInput.value = JSON.stringify(newAges);
                    console.log('Updated child_ages input:', childAgesInput.value);
                    window.triggerPricingUpdate();
                }
            }
            return;
        }

        childAgesContainer.classList.remove('d-none');
        if (triggerHtmx) {
            const currentChildAges = childAgesInput?.value ? encodeURIComponent(childAgesInput.value) : '[]';
            const tourType = document.getElementById('id_tour_type')?.value || window.bookingData?.tourType || 'land';
            const tourId = document.getElementById('id_tour_id')?.value || window.bookingData?.tourId || '1';
            const languagePrefix = window.bookingData?.languagePrefix || 'en';
            const hxGetUrl = `/${languagePrefix}/bookings/child_ages/?number_of_children=${encodeURIComponent(numChildren)}&child_ages=${currentChildAges}&tour_type=${encodeURIComponent(tourType)}&tour_id=${encodeURIComponent(tourId)}`;
            const currentHxGet = childAgesContainer.dataset.lastHxGet || '';
            if (currentHxGet !== hxGetUrl) {
                childAgesContainer.setAttribute('hx-get', hxGetUrl);
                childAgesContainer.dataset.lastHxGet = hxGetUrl;
                childAgesContainer.dataset.allowRequest = 'true';
                if (typeof htmx !== 'undefined') {
                    htmx.process(childAgesContainer);
                    console.log('Triggering childAgesUpdate for child-ages-container:', hxGetUrl);
                    htmx.trigger(childAgesContainer, 'childAgesUpdate');
                    setTimeout(() => {
                        childAgesContainer.removeAttribute('data-allow-request');
                        console.log('Cleared allow-request flag');
                    }, 50);
                }
            }
        }

        // Update child ages input with 0–12 range
        const ageInputs = document.querySelectorAll('#child-ages-container .child-age-input');
        let ages = [];
        if (ageInputs.length > 0) {
            ages = Array.from(ageInputs)
                .map(input => parseInt(input.value) || 0)
                .filter(age => age >= 0 && age <= 12);
        } else if (childAgesInput?.value) {
            try {
                ages = JSON.parse(childAgesInput.value) || [];
            } catch (e) {
                console.warn('Failed to parse child_ages:', e);
            }
        }
        if (ages.length < numChildren && numChildren > 0) {
            ages = ages.concat(Array(numChildren - ages.length).fill(0));
        } else if (ages.length > numChildren) {
            ages = ages.slice(0, numChildren);
        }
        const newAgesString = JSON.stringify(ages);
        if (newAgesString !== childAgesInput.value) {
            childAgesInput.value = newAgesString;
            console.log('Updated child_ages input:', childAgesInput.value);
            window.triggerPricingUpdate();
        }

        // Ensure details remains open
        const details = childAgesContainer.querySelector('#child-ages-details');
        if (details && !details.hasAttribute('open')) {
            details.setAttribute('open', '');
        }

        // Remove any dynamic hx-* attributes from child-age-input
        ageInputs.forEach(input => {
            if (input.hasAttribute('hx-get') || input.hasAttribute('hx-post')) {
                console.warn('Removing unexpected hx-* attributes from:', input.id);
                input.removeAttribute('hx-get');
                input.removeAttribute('hx-post');
                input.removeAttribute('hx-trigger');
            }
        });
    };

    // Enhanced HTMX debugging
    document.addEventListener('htmx:beforeRequest', function (evt) {
        console.log('HTMX beforeRequest:', {
            target: evt.detail.target.id,
            url: evt.detail.requestConfig.url,
            trigger: evt.detail.elt.className,
            triggerId: evt.detail.elt.id,
            eventType: evt.detail.triggeringEvent?.type
        });
        if (evt.detail.target.id === 'child-ages-container' && evt.detail.requestConfig.url) {
            console.log('Child ages request detected:', {
                url: evt.detail.requestConfig.url,
                numberOfChildren: new URLSearchParams(new URL(evt.detail.requestConfig.url).search).get('number_of_children'),
                time: new Date().toISOString()
            });
        }
    });

    // Handle HTMX response errors
    document.addEventListener('htmx:responseError', function (evt) {
        console.error('HTMX response error:', {
            target: evt.detail.target.id,
            url: evt.detail.pathInfo.requestPath,
            status: evt.detail.xhr.status,
            response: evt.detail.xhr.responseText.slice(0, 200) + '...'
        });
        if (evt.detail.target.id === 'child-ages-container') {
            const errorMessage = document.getElementById('htmx-error-message');
            if (errorMessage) {
                errorMessage.textContent = 'Failed to update child ages. Please try again.';
                errorMessage.classList.remove('hidden');
            }
        }
    });

    let pricingUpdateTimeout = null;
    let isPricingUpdatePending = false;
    let lastFormDataHash = '';
    let debounceTimeout;

    // Trigger pricing update
    window.triggerPricingUpdate = function () {
        if (pricingUpdateTimeout) {
            clearTimeout(pricingUpdateTimeout);
        }
        if (isPricingUpdatePending) {
            console.log('Pricing update already pending, skipping');
            return;
        }
        pricingUpdateTimeout = setTimeout(() => {
            const bookingForm = document.getElementById('bookingForm');
            const errorMessage = document.getElementById('htmx-error-message');
            const adultsInput = document.getElementById('id_number_of_adults');
            const childrenInput = document.getElementById('id_number_of_children');
            const travelDateInput = document.getElementById('id_travel_date');
            const tourTypeInput = document.getElementById('id_tour_type');
            const tourIdInput = document.getElementById('id_tour_id');
            const currencyInput = document.getElementById('currencyInput');

            if (!bookingForm || !adultsInput || !childrenInput || !travelDateInput || !tourTypeInput || !tourIdInput) {
                console.warn('Missing booking form elements:', { bookingForm, adultsInput, childrenInput, travelDateInput, tourTypeInput, tourIdInput });
                if (errorMessage) {
                    errorMessage.textContent = 'Booking form not loaded. Please refresh and try again.';
                    errorMessage.classList.remove('hidden');
                }
                return;
            }

            let numAdults = parseInt(adultsInput.value) || 1;
            let numChildren = parseInt(childrenInput.value) || 0;
            let travelDate = travelDateInput.value || '2025-05-11';
            let tourType = tourTypeInput.value || window.bookingData?.tourType || 'land';
            let tourId = tourIdInput.value || window.bookingData?.tourId || '1';
            let currency = currencyInput?.value || localStorage.getItem('selectedCurrency') || 'USD';

            if (isNaN(numAdults) || numAdults < 1) {
                numAdults = 1;
                adultsInput.value = '1';
                console.warn('Invalid number of adults, reset to 1');
                if (errorMessage) {
                    errorMessage.textContent = 'Please enter at least one adult.';
                    errorMessage.classList.remove('hidden');
                }
            }
            if (isNaN(numChildren) || numChildren < 0) {
                numChildren = 0;
                childrenInput.value = '0';
                console.warn('Invalid number of children, reset to 0');
                if (errorMessage) {
                    errorMessage.textContent = 'Number of children cannot be negative.';
                    errorMessage.classList.remove('hidden');
                }
            }
            if (!travelDate) {
                travelDate = '2025-05-11';
                travelDateInput.value = travelDate;
                console.warn('Invalid travel date, reset to 2025-05-11');
                if (errorMessage) {
                    errorMessage.textContent = 'Please select a valid travel date.';
                    errorMessage.classList.remove('hidden');
                }
            }
            if (!tourType || tourType === 'undefined') {
                tourType = 'land';
                tourTypeInput.value = tourType;
                console.warn('Invalid tour type, reset to:', tourType);
            }
            if (!tourId || tourId === 'undefined') {
                tourId = '1';
                tourIdInput.value = tourId;
                console.warn('Invalid tour ID, reset to:', tourId);
            }

            window.updateChildAges();

            const formData = new FormData(bookingForm);
            formData.set('number_of_adults', numAdults.toString());
            formData.set('number_of_children', numChildren.toString());
            formData.set('travel_date', travelDate);
            formData.set('tour_type', tourType);
            formData.set('tour_id', tourId);
            formData.set('currency', currency);
            formData.set('form_submission', 'pricing');

            // Generate a hash of critical form data to detect changes
            const formDataString = JSON.stringify({
                number_of_adults: numAdults,
                number_of_children: numChildren,
                travel_date: travelDate,
                tour_type: tourType,
                tour_id: tourId,
                currency: currency,
                child_ages: formData.get('child_ages')
            });
            if (formDataString === lastFormDataHash) {
                console.log('No changes in form data, skipping pricing update');
                return;
            }
            lastFormDataHash = formDataString;

            const languagePrefix = window.bookingData?.languagePrefix || 'en';
            const url = `/${languagePrefix}/bookings/calculate_pricing/${tourType}/${tourId}/`;
            console.log('Triggering pricing update to:', url);
            console.log('FormData entries:', Object.fromEntries(formData));

            isPricingUpdatePending = true;
            htmx.ajax('POST', url, {
                target: '#pricing-options',
                swap: 'innerHTML',
                values: Object.fromEntries(formData),
                headers: {
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                }
            }).then(() => {
                console.log('HTMX pricing update completed');
                isPricingUpdatePending = false;
                lastFormDataHash = formDataString; // Update hash on success
                if (errorMessage) errorMessage.classList.add('hidden');
                if (typeof bootstrap !== 'undefined') {
                    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
                        new bootstrap.Tooltip(el);
                    });
                }
            }).catch(error => {
                console.error('HTMX pricing update error:', error);
                if (errorMessage) {
                    errorMessage.textContent = 'Failed to update pricing. Please try again.';
                    errorMessage.classList.remove('hidden');
                }
                isPricingUpdatePending = false;
            });
        }, 500);
    };

        window.updateSelectedConfiguration = function () {
            const selectedRadio = document.querySelector('input[name="configuration"]:checked');
            const selectedConfigInput = document.getElementById('id_selected_configuration');
            if (selectedRadio && selectedConfigInput) {
                selectedConfigInput.value = selectedRadio.value;
                console.log('Selected configuration updated:', selectedConfigInput.value);
            } else {
                console.warn('Cannot update selected configuration:', {
                    selectedRadio: !!selectedRadio,
                    selectedConfigInput: !!selectedConfigInput,
                    selectedRadioValue: selectedRadio ? selectedRadio.value : 'none'
                });
                if (selectedConfigInput) {
                    // Set a default value if no radio is selected but configurations exist
                    const firstRadio = document.querySelector('input[name="configuration"]');
                    if (firstRadio) {
                        firstRadio.checked = true;
                        selectedConfigInput.value = firstRadio.value;
                        console.log('Set default configuration:', firstRadio.value);
                    } else {
                        selectedConfigInput.value = ''; // Clear if no configurations
                        console.warn('No configuration radio buttons found');
                    }
                }
            }
        };

    // Initialize pricing controls
    window.initializePricingControls = function (pricingTable) {
        console.log('initializePricingControls called with pricingTable:', pricingTable);

        if (!pricingTable) {
            pricingTable = document.querySelector('.pricing-table');
            if (!pricingTable) {
                console.error('Pricing table element not found');
                return;
            }
        }

        pricingTable.dataset.initialized = 'true';
        pricingTable.dataset.currentPage = '1';

        let configurations = [];
        if (pricingTable.dataset.configurations) {
            console.log('Raw data-configurations:', pricingTable.dataset.configurations);
            try {
                const rawConfig = pricingTable.dataset.configurations.trim();
                if (!rawConfig || rawConfig === '[]') {
                    console.warn('Empty or invalid data-configurations, using fallback');
                    configurations = [];
                } else {
                    configurations = JSON.parse(rawConfig);
                    console.log('Parsed configurations:', configurations);
                }
            } catch (error) {
                console.error('Failed to parse pricing-configurations:', error, 'Raw data:', pricingTable.dataset.configurations);
                configurations = [];
                pricingTable.dataset.configurations = '[]';
            }
        } else {
            console.warn('No configurations found in data-configurations');
            pricingTable.dataset.configurations = '[]';
        }

        const configurationItems = pricingTable.querySelectorAll('.configuration-item');
        console.log('Found configuration items:', configurationItems.length);
        configurationItems.forEach(item => console.log('Configuration item:', item.outerHTML));

        const prevButton = pricingTable.querySelector('#prev-page');
        const nextButton = pricingTable.querySelector('#next-page');
        const pageInfo = pricingTable.querySelector('#page-info');
        const totalResults = pricingTable.querySelector('#total-results');
        const applyFiltersButton = pricingTable.querySelector('#apply-filters');
        const clearFiltersButton = pricingTable.querySelector('#clear-filters');
        const filterPriceMin = pricingTable.querySelector('#filter-price-min');
        const filterPriceMax = pricingTable.querySelector('#filter-price-max');
        const filterRoomTypes = pricingTable.querySelectorAll('.filter-room-type');

        console.log('DOM Elements:', {
            configurationItems: configurationItems.length,
            prevButton: !!prevButton,
            nextButton: !!nextButton,
            pageInfo: !!pageInfo,
            totalResults: !!totalResults,
            applyFiltersButton: !!applyFiltersButton,
            clearFiltersButton: !!clearFiltersButton,
            filterPriceMin: !!filterPriceMin,
            filterPriceMax: !!filterPriceMax,
            filterRoomTypes: filterRoomTypes.length
        });

        configurationItems.forEach(item => {
            const radio = item.querySelector('input[name="configuration"]');
            if (radio) {
                radio.removeEventListener('change', window.updateSelectedConfiguration);
                radio.addEventListener('change', window.updateSelectedConfiguration);
                console.log('Radio listener attached for item:', item.dataset);
            }
        });

        const savedFilters = JSON.parse(localStorage.getItem('pricingFilters') || '{}');
        filterRoomTypes.forEach(cb => {
            cb.checked = savedFilters.roomTypes?.includes(cb.dataset.roomType) || false;
        });
        if (filterPriceMin) filterPriceMin.value = savedFilters.priceMin || '';
        if (filterPriceMax) filterPriceMax.value = savedFilters.priceMax || '';

        console.log('Initializing pagination with', configurationItems.length, 'items');
        applyFilters(pricingTable);

        // Ensure a configuration is selected after initialization
        window.updateSelectedConfiguration();
    };

    // Pagination update
    function updatePagination(pricingTable, filteredItems, page) {
        console.log('updatePagination called with filteredItems:', filteredItems ? filteredItems.length : 'default', 'page:', page);

        const configurationItems = pricingTable.querySelectorAll('.configuration-item');
        const prevButton = pricingTable.querySelector('#prev-page');
        const nextButton = pricingTable.querySelector('#next-page');
        const pageInfo = pricingTable.querySelector('#page-info');
        const totalResults = pricingTable.querySelector('#total-results');

        filteredItems = filteredItems || Array.from(configurationItems);
        const totalItems = filteredItems.length;
        const totalPages = Math.max(1, Math.ceil(totalItems / itemsPerPage));
        const currentPage = Math.max(1, Math.min(page || parseInt(pricingTable.dataset.currentPage || '1'), totalPages));

        console.log('Pagination details:', { totalItems, totalPages, currentPage });

        configurationItems.forEach(item => {
            item.classList.add('hidden');
            console.log('Hiding item:', item.dataset);
        });

        const startIndex = (currentPage - 1) * itemsPerPage;
        const endIndex = Math.min(startIndex + itemsPerPage, totalItems);
        const itemsToShow = filteredItems.slice(startIndex, endIndex);

        console.log('Items to show:', itemsToShow.map(item => item.dataset));

        itemsToShow.forEach(item => {
            item.classList.remove('hidden');
            console.log('Showing item:', item.dataset);
        });

        const configurationsContainer = pricingTable.querySelector('#configurations-container');
        const noResultsMessage = configurationsContainer.querySelector('.no-results-message');
        if (totalItems === 0 && !noResultsMessage) {
            const message = document.createElement('p');
            message.className = 'no-results-message text-sm text-gray-700 dark:text-gray-400';
            message.textContent = 'No pricing options match the selected filters.';
            configurationsContainer.appendChild(message);
        } else if (totalItems > 0 && noResultsMessage) {
            noResultsMessage.remove();
        }

        if (pageInfo) {
            pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
        }
        if (totalResults) {
            totalResults.textContent = totalItems === 1 ? ` - ${totalItems} result` : ` - ${totalItems} results`;
        }
        if (prevButton) {
            prevButton.disabled = currentPage === 1;
        }
        if (nextButton) {
            nextButton.disabled = currentPage === totalPages || totalPages === 0;
        }

        pricingTable.dataset.currentPage = currentPage;

        const visibleItem = itemsToShow[0];
        if (visibleItem && !pricingTable.querySelector('input[name="configuration"]:checked')) {
            const radio = visibleItem.querySelector('input[name="configuration"]');
            if (radio) {
                console.log('Selecting default radio for item:', visibleItem.dataset);
                radio.checked = true;
                window.updateSelectedConfiguration();
            }
        }
    }

    // Apply filters
    function applyFilters(pricingTable) {
        console.log('applyFilters called for pricingTable:', pricingTable);
        const configurationItems = pricingTable.querySelectorAll('.configuration-item');
        const filterPriceMin = pricingTable.querySelector('#filter-price-min');
        const filterPriceMax = pricingTable.querySelector('#filter-price-max');
        const filterRoomTypes = pricingTable.querySelectorAll('.filter-room-type');

        const selectedRoomTypes = Array.from(filterRoomTypes)
            .filter(cb => cb.checked)
            .map(cb => cb.dataset.roomType);
        const priceMin = filterPriceMin ? parseFloat(filterPriceMin.value) || 0 : 0;
        const priceMax = filterPriceMax ? parseFloat(filterPriceMax.value) || Infinity : Infinity;

        console.log('Filter parameters:', { selectedRoomTypes, priceMin, priceMax });

        localStorage.setItem('pricingFilters', JSON.stringify({
            roomTypes: selectedRoomTypes,
            priceMin: filterPriceMin?.value || '',
            priceMax: filterPriceMax?.value || ''
        }));

        const filteredItems = Array.from(configurationItems).filter(item => {
            const singles = parseInt(item.dataset.singles) || 0;
            const doubles = parseInt(item.dataset.doubles) || 0;
            const triples = parseInt(item.dataset.triples) || 0;
            const price = parseFloat(item.dataset.price.replace(/[^\d.]/g, '')) || 0;

            const roomTypeMatch = selectedRoomTypes.length === 0 ||
                (selectedRoomTypes.includes('singles') && singles > 0) ||
                (selectedRoomTypes.includes('doubles') && doubles > 0) ||
                (selectedRoomTypes.includes('triples') && triples > 0);

            const priceMatch = price >= priceMin && price <= priceMax;

            console.log('Item:', item.dataset, 'roomTypeMatch:', roomTypeMatch, 'priceMatch:', priceMatch);

            return roomTypeMatch && priceMatch;
        });

        console.log('Filtered items count:', filteredItems.length);
        updatePagination(pricingTable, filteredItems, 1);
    }

    // Clear filters
    function clearFilters(pricingTable) {
        console.log('clearFilters called for pricingTable:', pricingTable);
        const configurationItems = pricingTable.querySelectorAll('.configuration-item');
        const filterPriceMin = pricingTable.querySelector('#filter-price-min');
        const filterPriceMax = pricingTable.querySelector('#filter-price-max');
        const filterRoomTypes = pricingTable.querySelectorAll('.filter-room-type');

        filterRoomTypes.forEach(cb => {
            cb.checked = false;
        });
        if (filterPriceMin) filterPriceMin.value = '';
        if (filterPriceMax) filterPriceMax.value = '';

        localStorage.setItem('pricingFilters', JSON.stringify({
            roomTypes: [],
            priceMin: '',
            priceMax: ''
        }));

        console.log('Filters cleared, resetting to all items');
        updatePagination(pricingTable, Array.from(configurationItems), 1);
    }

    // Previous page
    function prevPage(pricingTable) {
        console.log('prevPage called for pricingTable:', pricingTable);
        const currentPage = parseInt(pricingTable.dataset.currentPage || '1');
        if (currentPage > 1) {
            updatePagination(pricingTable, null, currentPage - 1);
        }
    }

    // Next page
    function nextPage(pricingTable) {
        console.log('nextPage called for pricingTable:', pricingTable);
        const configurationItems = pricingTable.querySelectorAll('.configuration-item');
        const currentPage = parseInt(pricingTable.dataset.currentPage || '1');
        const totalPages = Math.ceil(configurationItems.length / itemsPerPage);
        if (currentPage < totalPages) {
            updatePagination(pricingTable, null, currentPage + 1);
        }
    }

    // Handle filter and pagination buttons
    document.addEventListener('click', function (event) {
        const target = event.target.closest('#apply-filters, #clear-filters, #prev-page, #next-page');
        if (target) {
            console.log('Button clicked:', target.id);
            const pricingTable = target.closest('.pricing-table');
            if (!pricingTable) {
                console.error('Pricing table not found for button:', target.id);
                return;
            }
            if (target.id === 'apply-filters') {
                applyFilters(pricingTable);
            } else if (target.id === 'clear-filters') {
                clearFilters(pricingTable);
            } else if (target.id === 'prev-page') {
                prevPage(pricingTable);
            } else if (target.id === 'next-page') {
                nextPage(pricingTable);
            }
        }
    });

    // Initialize booking form
    function initializeBookingForm(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) {
            console.error('Modal not found:', modalId);
            return;
        }
        console.log('initializeBookingForm called for modal:', modalId);

        const pricingOptions = document.getElementById('pricing-options');
        const tourTypeInput = document.getElementById('id_tour_type');
        const tourIdInput = document.getElementById('id_tour_id');
        const adultsInput = document.getElementById('id_number_of_adults');
        const childrenInput = document.getElementById('id_number_of_children');
        const childAgesInput = document.getElementById('id_child_ages');
        const travelDateInput = document.getElementById('id_travel_date');
        const endDateInput = document.getElementById('id_end_date');
        const currencyInput = document.getElementById('currencyInput');

        if (!adultsInput || !childrenInput || !childAgesInput || !travelDateInput || !tourTypeInput || !tourIdInput || !endDateInput) {
            console.error('Missing essential booking form inputs:', {
                adultsInput, childrenInput, childAgesInput, travelDateInput, tourTypeInput, tourIdInput, endDateInput
            });
            return;
        }

        const savedCurrency = localStorage.getItem('selectedCurrency') || 'USD';
        if (currencyInput) {
            currencyInput.value = savedCurrency;
            console.log('Set currencyInput to:', savedCurrency);
        }

        const tourType = tourTypeInput.value || window.bookingData?.tourType || 'land';
        const tourId = tourIdInput.value || window.bookingData?.tourId || '1';
        const tourDuration = parseInt(document.getElementById('booking-form-container')?.dataset.duration || '4', 10);
        console.log('tourDuration:', tourDuration);

        if (!adultsInput.value || parseInt(adultsInput.value) < 1 || isNaN(parseInt(adultsInput.value))) {
            adultsInput.value = '1';
            console.log('Set default number of adults to 1');
        }
        if (!childrenInput.value || parseInt(childrenInput.value) < 0 || isNaN(parseInt(childrenInput.value))) {
            childrenInput.value = '0';
            console.log('Set default number of children to 0');
        }

        let defaultDate = travelDateInput.value || '2025-05-11';
        if (!/^\d{4}-\d{2}-\d{2}$/.test(defaultDate)) {
            console.warn('Invalid travel date format, using fallback:', defaultDate);
            defaultDate = '2025-05-11';
        }
        updateEndDate(defaultDate, tourDuration, endDateInput);

        if (tourType && tourId) {
            initializeDatePicker(tourType, tourId, tourDuration);
        }

        adultsInput.addEventListener('input', function () {
            let value = parseInt(this.value) || 1;
            if (isNaN(value) || value < 1) {
                value = 1;
                this.value = '1';
                console.log('Sanitized number of adults to 1');
            }
            console.log('adultsInput changed, numAdults:', value);
            window.updateChildAges();
            window.triggerPricingUpdate();
        });

        childrenInput.addEventListener('input', function () {
            let value = parseInt(this.value) || 0;
            if (isNaN(value) || value < 0) {
                value = 0;
                this.value = '0';
                console.log('Sanitized number of children to 0');
            }
            console.log('childrenInput changed, numChildren:', value);
            clearTimeout(debounceTimeout);
            debounceTimeout = setTimeout(() => {
                const childAgesContainer = document.getElementById('child-ages-container');
                if (childAgesContainer) {
                    const languagePrefix = window.bookingData?.languagePrefix || 'en';
                    const tourType = tourTypeInput.value || window.bookingData?.tourType || 'land';
                    const tourId = tourIdInput.value || window.bookingData?.tourId || '1';
                    const currentChildAges = childAgesInput?.value ? encodeURIComponent(childAgesInput.value) : '[]';
                    const newUrl = `/${languagePrefix}/bookings/child_ages/?number_of_children=${encodeURIComponent(value)}&child_ages=${currentChildAges}&tour_type=${tourType}&tour_id=${tourId}`;
                    console.log('Setting hx-get to:', newUrl);
                    childAgesContainer.setAttribute('hx-get', newUrl);
                    childAgesContainer.setAttribute('hx-trigger', 'load');
                    childAgesContainer.setAttribute('hx-ext', 'preserve-details');
                    if (typeof htmx !== 'undefined') {
                        console.log('Reprocessing child-ages-container with HTMX');
                        htmx.process(childAgesContainer);
                        htmx.trigger(childAgesContainer, 'load');
                    } else {
                        console.warn('HTMX not loaded, using manual fetch');
                        fetch(newUrl)
                            .then(response => {
                                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                                return response.text();
                            })
                            .then(html => {
                                childAgesContainer.outerHTML = html;
                                console.log('Manually updated child-ages-container');
                                window.updateChildAges();
                                window.triggerPricingUpdate();
                            })
                            .catch(error => console.error('Manual fetch error:', error));
                    }
                }
            }, 300);
        });

        travelDateInput.addEventListener('change', function () {
            console.log('travelDateInput changed, value:', this.value);
            updateEndDate(this.value, tourDuration, endDateInput);
            window.triggerPricingUpdate();
        });

        const recalculateButton = document.getElementById('recalculateButton');
        if (recalculateButton) {
            recalculateButton.addEventListener('click', function () {
                console.log('Recalculate button clicked');
                window.triggerPricingUpdate();
            });
        }

        const submitButton = document.getElementById('submit-proposal');
        if (submitButton) {
            submitButton.addEventListener('click', function (event) {
                event.preventDefault();
                console.log('Submit Proposal button clicked');
                const form = document.getElementById('bookingForm');
                const errorMessage = document.getElementById('form-error') || document.getElementById('htmx-error-message');
                if (!form) {
                    console.error('Booking form not found');
                    return;
                }
                const requiredFields = form.querySelectorAll('input[required], textarea[required], select[required]');
                let isValid = true;
                requiredFields.forEach(field => {
                    if (!field.value.trim() || (field.tagName === 'SELECT' && !field.value)) {
                        isValid = false;
                        field.classList.add('border-red-500');
                        console.warn(`Required field missing or invalid: ${field.name}`);
                    } else {
                        field.classList.remove('border-red-500');
                    }
                });

                // Check configuration
                const selectedConfigInput = document.getElementById('id_selected_configuration');
                const configurationItems = document.querySelectorAll('.configuration-item');
                if (configurationItems.length > 0 && (!selectedConfigInput || !selectedConfigInput.value)) {
                    isValid = false;
                    console.warn('No valid configuration selected');
                    if (errorMessage) {
                        errorMessage.textContent = 'Please select a pricing configuration.';
                        errorMessage.classList.remove('hidden');
                    }
                }

                const numChildren = parseInt(childrenInput.value || 0);
                let childAges = [];
                try {
                    childAges = childAgesInput?.value ? JSON.parse(childAgesInput.value) : [];
                } catch (e) {
                    console.warn('Failed to parse child_ages:', e);
                }
                if (numChildren > 0 && childAges.length !== numChildren) {
                    isValid = false;
                    console.warn(`Child ages mismatch: expected ${numChildren}, got ${childAges.length}`);
                    if (errorMessage) {
                        errorMessage.textContent = 'Please select ages for all children.';
                        errorMessage.classList.remove('hidden');
                    }
                }

                if (!isValid) {
                    if (errorMessage && !errorMessage.textContent) {
                        errorMessage.textContent = 'Please fill out all required fields, including child ages and configuration.';
                        errorMessage.classList.remove('hidden');
                        errorMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                    console.error('Form submission blocked: missing required fields or configuration');
                    return;
                }

                // Ensure configuration is updated before submission
                window.updateSelectedConfiguration();
                console.log('Selected configuration before submission:', selectedConfigInput?.value || 'none');

                window.updateChildAges();
                submitButton.disabled = true;
                submitButton.textContent = 'Submitting...';
                if (typeof htmx !== 'undefined') {
                    htmx.process(form);
                    console.log('Booking form submission triggered', {
                        action: form.action,
                        method: form.method,
                        formData: Object.fromEntries(new FormData(form))
                    });
                    htmx.trigger(form, 'submit');
                } else {
                    console.error('HTMX not loaded, falling back to native submission');
                    form.submit();
                }
            });
        }

        document.body.addEventListener('htmx:responseError', function (event) {
            console.error('HTMX response error:', {
                status: event.detail.xhr.status,
                response: event.detail.xhr.responseText.slice(0, 200) + '...'
            });
            const errorMessage = document.getElementById('form-error') || document.getElementById('htmx-error-message');
            if (errorMessage) {
                errorMessage.textContent = 'An error occurred while submitting the proposal. Please try again.';
                errorMessage.classList.remove('hidden');
            }
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.textContent = 'Submit Proposal';
            }
        });

        if (typeof bootstrap !== 'undefined') {
            document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
                new bootstrap.Tooltip(el);
            });
        }

        const pricingTable = modal.querySelector('.pricing-table');
        if (pricingTable && !pricingTable.dataset.initialized) {
            window.initializePricingControls(pricingTable);
        } else {
            console.warn('Pricing table not found or already initialized in modal, triggering pricing update');
            window.triggerPricingUpdate();
        }

        window.updateChildAges();
        if (!pricingTable || pricingTable.querySelectorAll('.configuration-item').length === 0) {
            console.log('No configurations found on load, triggering pricing update');
            window.triggerPricingUpdate();
        }
    }

    const bookingForm = document.getElementById('bookingForm');
    if (bookingForm) {
        bookingForm.addEventListener('submit', function (event) {
            console.log('Booking form submission triggered', {
                action: event.target.action,
                method: event.target.method,
                formData: Object.fromEntries(new FormData(event.target))
            });
        });
    }
});