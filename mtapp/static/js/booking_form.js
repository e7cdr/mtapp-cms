document.addEventListener('DOMContentLoaded', function () {
    function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
    const bookingData = JSON.parse(document.getElementById('booking-data').textContent);
    const isInquiryOnly = bookingData.collect_price === false;

    if (isInquiryOnly) {
        console.log('Inquiry-only tour → no pricing, modal WILL appear');

        // 1. Remove pricing card from DOM
        document.querySelector('#pricing-options')?.closest('.card')?.remove();

        // 2. Change button text
        const btn = document.getElementById('submitProposal');
        if (btn) btn.textContent = 'Review & Send Inquiry';

        // 3. COMPLETELY DISABLE loadPricing() — override before it's even called
        window.loadPricing = function() {
            console.log('loadPricing() blocked for inquiry-only tour');
            return; // Do nothing
        };

        // 4. Remove all event listeners that trigger pricing
        const inputs = document.querySelectorAll('input, select');
        inputs.forEach(el => {
            el.removeEventListener('change', loadPricing);
            el.removeEventListener('input', loadPricing);
        });

        // 5. Override the function even if it's defined later
        Object.defineProperty(window, 'loadPricing', {
            value: () => console.log('Pricing blocked'),
            writable: false,
            configurable: false
        });
    }

    // ────────────────────── Dynamic Pricing Load ──────────────────────
    let pricingTimeout;
    const pricingInputs = [
        'input[name="number_of_adults"]',
        'input[name="number_of_children"]',
        '#id_travel_date'
    ];
    function loadPricing() {
    // INQUIRY-ONLY: DO NOTHING + SILENT
    if (isInquiryOnly) {
        console.log('loadPricing() blocked — inquiry-only tour');
        return;
    }

    // Safety check: if pricing container was removed (should never happen, but safe)
    const pricingContainer = document.getElementById('pricing-options');
    if (!pricingContainer) {
        console.log('Pricing container not found — skipping loadPricing()');
        return;
    }

    clearTimeout(pricingTimeout);
    pricingTimeout = setTimeout(() => {
        const formData = new FormData(document.getElementById('bookingForm'));
        const tourType = document.querySelector('#id_tour_type').value;
        const tourId = document.querySelector('#id_tour_id').value;
        const url = `/bookings/calculate_pricing/${tourType}/${tourId}/`;

        fetch(url, {
            method: 'POST',
            body: formData,
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(response => response.text())
        .then(html => {
            // Final safety — double-check container still exists
            if (document.getElementById('pricing-options')) {
                document.getElementById('pricing-options').innerHTML = html;
                setTimeout(() => {
                    initializeFilters();
                    rebindRadioSelection();
                }, 50);
            }
        })
        .catch(error => {
            // Only log real errors — not expected nulls
            if (document.getElementById('pricing-options')) {
                console.error('Pricing fetch error:', error);
                document.getElementById('pricing-options').innerHTML = 
                    '<div class="alert alert-warning">Pricing temporarily unavailable.</div>';
            }
            // Otherwise: silent (inquiry mode or container gone)
        });
    }, 300);
}

    // Bind events ONLY if NOT inquiry-only
    if (!isInquiryOnly) {
        pricingInputs.forEach(selector => {
            document.addEventListener('change', function (event) {
                if (event.target.matches(selector)) loadPricing();
            });
        });
        loadPricing(); // Initial load
    }

    // function loadPricing() {
    //     clearTimeout(pricingTimeout);
    //     pricingTimeout = setTimeout(() => {
    //         const formData = new FormData(document.getElementById('bookingForm'));
    //         const tourType = document.querySelector('#id_tour_type').value;
    //         const tourId = document.querySelector('#id_tour_id').value;
    //         const url = `/bookings/calculate_pricing/${tourType}/${tourId}/`;

    //         fetch(url, {
    //             method: 'POST',
    //             body: formData,
    //             headers: { 'X-Requested-With': 'XMLHttpRequest' }
    //         })
    //             .then(response => response.text())
    //             .then(html => {
    //                 document.getElementById('pricing-options').innerHTML = html;
    //                 setTimeout(() => {
    //                     initializeFilters();
    //                     rebindRadioSelection();
    //                 }, 50);
    //             })
    //             .catch(error => {
    //                 console.error('Pricing fetch error:', error);
    //                 document.getElementById('pricing-options').innerHTML = '<div class="alert alert-warning">Pricing unavailable—please try again.</div>';
    //             });
    //     }, 300);
    // }

    // pricingInputs.forEach(selector => {
    //     document.addEventListener('change', function (event) {
    //         if (event.target.matches(selector)) loadPricing();
    //     });
    // });

    // if (!isInquiryOnly) {
    //     loadPricing();  // Initial
    // }


    // ────────────────────── Submit Proposal (Modal Flow) ──────────────────────
    // document.getElementById('submitProposal').addEventListener('click', function (e) {
    //     e.preventDefault();
    //     const form = document.getElementById('bookingForm');
    //     const formData = new FormData(form);
    //     const tourId = parseInt(document.getElementById('id_tour_id').value);
    //     const saveUrl = form.action;

    //     // Step 1: POST to save session (validate form) — WITH DEBUG
    //     fetch(saveUrl, {
    //         method: 'POST',
    //         body: formData,
    //         headers: {
    //             'X-Requested-With': 'XMLHttpRequest',
    //             'X-CSRFToken': getCookie('csrftoken')
    //         }
    //     })
    //     .then(response => {
    //         console.log('First POST response:', response);
    //         console.log('Status:', response.status);
    //         console.log('Headers:', [...response.headers.entries()]);

    //         if (!response.ok) {
    //             return response.text().then(text => {
    //                 console.error('Server returned error HTML:', text.substring(0, 500));
    //                 throw new Error(`Server error ${response.status}`);
    //             });
    //         }

    //         // Check content-type before parsing JSON
    //         const contentType = response.headers.get('content-type');
    //         if (!contentType || !contentType.includes('application/json')) {
    //             return response.text().then(text => {
    //                 console.error('Expected JSON but got HTML:', text.substring(0, 500));
    //                 throw new Error('Invalid response from server');
    //             });
    //         }

    //         return response.json();
    //     })
    //     .then(data => {
    //         console.log('First POST success:', data);
    //         if (!data.success) throw new Error('Validation failed');

    //         // Now load confirmation modal
    //         return fetch(`/bookings/confirm/${tourId}/`, {
    //             headers: {
    //                 'X-Requested-With': 'XMLHttpRequest',
    //                 'X-CSRFToken': getCookie('csrftoken')
    //             }
    //         });
    //     })
    //     .then(response => {
    //         if (!response.ok) throw new Error('Failed to load confirmation');
    //         return response.text();
    //     })
    //     .then(html => {
    //         document.getElementById('confirmationContent').innerHTML = html;
    //         new bootstrap.Modal(document.getElementById('confirmationModal')).show();
    //     })
    //     .catch(error => {
    //         console.error('Booking error:', error);
    //         alert('Error: ' + error.message + '. Please refresh and try again.');
    //     });
    // });
    // ────────────────────── Submit Proposal (Modal Flow) ──────────────────────
    document.getElementById('submitProposal').addEventListener('click', function (e) {
        e.preventDefault();
        const form = document.getElementById('bookingForm');
        const formData = new FormData(form);
        const tourId = parseInt(document.getElementById('id_tour_id').value);
        const saveUrl = form.action;

        // Beautiful error toast
        function showError(message, title = 'Oops!') {
            let container = document.getElementById('errorToastContainer');
            if (!container) {
                container = document.createElement('div');
                container.id = 'errorToastContainer';
                container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
                container.style.zIndex = '9999';
                document.body.appendChild(container);
            }
            const html = `
                <div class="toast align-items-center text-white bg-danger border-0" role="alert">
                    <div class="d-flex">
                        <div class="toast-body">
                            <strong>${title}</strong><br>${message}
                        </div>
                        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                    </div>
                </div>`;
            container.innerHTML = html;
            new bootstrap.Toast(container.firstElementChild).show();
        }

        // Clear old errors
        document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
        document.querySelectorAll('.invalid-feedback').forEach(el => el.remove());

        fetch(saveUrl, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(r => {
            if (!r.ok) {
                return r.json().then(data => { throw { status: r.status, errors: data.errors || data }; });
            }
            return r.json();
        })
        .then(data => {
            if (!data.success) {
                throw { errors: data.errors || { __all__: ['Please correct the errors below.'] } };
            }

            // SUCCESS → Open modal
            return fetch(`/bookings/confirm/${tourId}/`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });
        })
        .then(r => r.text())
        .then(html => {
            document.getElementById('confirmationContent').innerHTML = html;
            new bootstrap.Modal(document.getElementById('confirmationModal')).show();
        })
        .catch(err => {
            const errors = err.errors || {};
            const messages = [];

            // Handle ALL fields — including captcha, name, email, etc.
            Object.keys(errors).forEach(field => {
                const fieldErrors = errors[field];
                if (Array.isArray(fieldErrors)) {
                    fieldErrors.forEach(msg => {
                        let text = msg;
                        if (typeof msg === 'object' && msg.message) text = msg.message;

                        // Special friendly message for CAPTCHA
                        if (field === 'captcha' || String(text).toLowerCase().includes('captcha')) {
                            messages.push('Please complete the CAPTCHA correctly');
                        } else {
                            messages.push(text);
                        }

                        // Highlight the field (captcha has two inputs)
                        if (field === 'captcha') {
                            document.querySelector('input[name="captcha_1"]')?.classList.add('is-invalid');
                            document.querySelector('.captcha-section')?.classList.add('border', 'border-danger', 'border-2');
                        } else {
                            const input = document.querySelector(`[name="${field}"]`) || 
                                        document.getElementById(`id_${field}`);
                            if (input) {
                                input.classList.add('is-invalid');
                                const fb = document.createElement('div');
                                fb.className = 'invalid-feedback';
                                fb.textContent = text;
                                input.parentNode.appendChild(fb);
                            }
                        }
                    });
                }
            });

            if (messages.length === 0) {
                messages.push('Please check all fields and try again.');
            }

            showError(messages.join('<br>'), 'Validation Error');
        });
    });
    // ────────────────────── Confirm Submit in Modal ──────────────────────
    document.addEventListener('click', function (e) {
        if (e.target.id === 'confirmSubmit') {
            const modalForm = document.querySelector('#confirmationForm');
            if (!modalForm) {
                alert('Error: No form found.');
                return;
            }

            const submitButton = e.target;
            const originalText = submitButton.innerText.trim();
            submitButton.innerHTML = '<span class="spinner"></span> Loading...';
            submitButton.style.backgroundColor = 'green';
            submitButton.disabled = true;

            const formData = new FormData();
            modalForm.querySelectorAll('input[type="hidden"]').forEach(input => {
                formData.append(input.name, input.value);
            });
            const url = modalForm.dataset.action;

                fetch(url, { 
                    method: 'POST', 
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    }
                })                
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        window.location.href = `/bookings/proposal-success/${data.proposal_id}/`;
                    } else {
                        alert(data.error);
                        submitButton.innerText = originalText;
                        submitButton.disabled = false;
                    }
                })
                .catch(error => {
                    console.error('Submit error:', error);
                    alert('Error submitting. Please try again.');
                    submitButton.innerText = originalText;
                    submitButton.disabled = false;
                });
        }
    });

    const tourStartDate = bookingData.tour_start_date;
    const tourEndDate = bookingData.tour_end_date;
    const availableDaysStr = bookingData.available_days;  // e.g., "0,1,2,3"
    const availableDays = availableDaysStr ? availableDaysStr.split(',').map(d => parseInt(d.trim())) : [];  // [0,1,2,3]

    // NEW: Blackout dates (array of 'YYYY-MM-DD' strings from model)
    const blackoutDates = bookingData.blackout_dates || [];
    const blackoutDateObjects = blackoutDates.map(dateStr => {
        const [year, month, day] = dateStr.split('-').map(Number);
        return new Date(year, month - 1, day);  // Date object for flatpickr
    });
    // Flatpickr
    const travelDateInput = document.getElementById('id_travel_date');
    if (travelDateInput && typeof flatpickr !== 'undefined') {
        flatpickr(travelDateInput, {
            minDate: tourStartDate || 'today',
            maxDate: tourEndDate,
            dateFormat: 'Y-m-d',
            locale: 'en',
            disable: [
                function(date) {
                    const dayOfWeek = date.getDay();  // 0=Sun, 6=Sat (adjust if tour uses Sun=0)
                    if (availableDays.length > 0 && !availableDays.includes(dayOfWeek)) {
                        return true;  // Disable
                    }
                    return false;  // Enable
                },
                ...blackoutDateObjects
            ],
            onChange: function (selectedDates, dateStr) {
                const tourDuration = parseInt(document.getElementById('booking-form-container').dataset.duration || 0);
                const endDateInput = document.getElementById('end_date');
                updateEndDate(dateStr, tourDuration, endDateInput);
                loadPricing();
                const tourType = document.querySelector('#id_tour_type').value;
                const tourId = document.querySelector('#id_tour_id').value;
                if (tourId && dateStr) {
                    fetch(`/api/available-dates/?tour_type=${tourType}&tour_id=${tourId}&travel_date=${dateStr}`)
                        .then(r => r.json())
                    .then(data => {
                        const statusEl = document.getElementById('capacity-status');
                        if (statusEl) {
                            if (data.is_full) {
                                statusEl.innerHTML = 'Fully booked for the trip!';
                            } else {
                                statusEl.innerHTML = `Min remaining for trip: ${data.remaining_capacity} spots`;
                            }
                        }
                    }).catch(err => console.error('Capacity fetch error:', err));
                }
            }
        });

        // Initial end date
        const initialTourDuration = parseInt(document.getElementById('booking-form-container').dataset.duration || 0);
        const initialEndDateInput = document.getElementById('end_date');
        if (travelDateInput.value && initialTourDuration > 0) {
            updateEndDate(travelDateInput.value, initialTourDuration, initialEndDateInput);
        }
    }

    // End Date Function
    function updateEndDate(travelDateStr, tourDuration, endDateInput) {
        if (!endDateInput || !travelDateStr || !tourDuration) return;
        try {
            const [year, month, day] = travelDateStr.split('-').map(Number);
            const travelDate = new Date(Date.UTC(year, month - 1, day));
            const endDate = new Date(travelDate);
            endDate.setUTCDate(travelDate.getUTCDate() + parseInt(tourDuration) - 1);
            endDateInput.value = endDate.toISOString().split('T')[0];
        } catch (error) {
            console.error('Error updating end date:', error);
        }
    }

    // Update selected config on radio change
    window.updateSelectedConfiguration = function () {
        const selectedRadio = document.querySelector('input[name="configuration"]:checked');
        if (selectedRadio) {
            document.getElementById('selected_configuration').value = selectedRadio.value;
            console.log('Selected config index:', selectedRadio.value);
        }
    };


    function rebindRadioSelection() {
        const radios = document.querySelectorAll('input[name="configuration"]');
        radios.forEach(radio => {
            radio.addEventListener('change', updateSelectedConfiguration);
        });
        const selectedId = document.getElementById('selected_configuration').value;
        if (selectedId) {
            const selectedRadio = document.querySelector(`input[name="configuration"][value="${selectedId}"]`);
            if (selectedRadio) selectedRadio.checked = true;
        }
        console.log('Radios re-bound:', radios.length);
    }

    // Filters
    function initializeFilters() {
        const pricingTable = document.querySelector('.pricing-table');
        if (!pricingTable) return;

        const configs = JSON.parse(pricingTable.dataset.configurations || '[]');
        const container = document.getElementById('configurations-container');
        if (!container) return;

        const items = container.querySelectorAll('.configuration-item');
        const pricingType = pricingTable.dataset.pricingType || 'Per_room';
        const noResultsMsg = '<p class="text-sm text-gray-700 dark:text-gray-400 text-center py-4">No pricing options match the filters. Try adjusting them.</p>';

        function applyFilters() {
            const minPrice = parseFloat(document.getElementById('filter-price-min')?.value) || 0;
            const maxPrice = parseFloat(document.getElementById('filter-price-max')?.value) || Infinity;
            const roomTypes = Array.from(document.querySelectorAll('.filter-room-type:checked')).map(cb => cb.dataset.roomType);
            let visibleCount = 0;

            items.forEach((item, index) => {
                const config = configs[index];
                if (!config) return;

                const price = config.total_price;
                let roomMatch = true;
                if (roomTypes.length > 0 && (pricingType === 'Per_room' || pricingType === 'Combined')) {                    roomMatch = roomTypes.some(type =>
                        (type === 'singles' && config.singles > 0) ||
                        (type === 'doubles' && config.doubles > 0) ||
                        (type === 'triples' && config.triples > 0)
                    );
                }

                const show = price >= minPrice && price <= maxPrice && roomMatch;
                item.style.display = show ? 'block' : 'none';
                if (show) visibleCount++;
            });

            // No-results
            let noResultsEl = container.querySelector('.no-results-msg');
            if (visibleCount === 0 && items.length > 0) {
                if (!noResultsEl) {
                    noResultsEl = document.createElement('div');
                    noResultsEl.className = 'no-results-msg';
                    noResultsEl.innerHTML = noResultsMsg;
                    container.appendChild(noResultsEl);
                }
            } else if (noResultsEl) {
                noResultsEl.remove();
            }

            const totalResultsEl = document.getElementById('total-results');
            if (totalResultsEl) {
                totalResultsEl.textContent = visibleCount === 1 ? '1 result' : `${visibleCount} results`;
            }

            console.log(`Filtered to ${visibleCount} options`);
        }

        // Button events
        const applyBtn = document.getElementById('apply-filters');
        const clearBtn = document.getElementById('clear-filters');
        if (applyBtn) applyBtn.addEventListener('click', (e) => { e.preventDefault(); applyFilters(); });
        if (clearBtn) clearBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const minEl = document.getElementById('filter-price-min');
            const maxEl = document.getElementById('filter-price-max');
            if (minEl) minEl.value = '';
            if (maxEl) maxEl.value = '';
            document.querySelectorAll('.filter-room-type').forEach(cb => cb.checked = false);
            applyFilters();
        });

        // Real-time
        const minEl = document.getElementById('filter-price-min');
        const maxEl = document.getElementById('filter-price-max');
        if (minEl) minEl.addEventListener('input', applyFilters);
        if (maxEl) maxEl.addEventListener('input', applyFilters);
        document.querySelectorAll('.filter-room-type').forEach(cb => cb.addEventListener('change', applyFilters));

        setTimeout(applyFilters, 100);
        console.log('Filters initialized');
    }

    // Children Ages
    const childrenInput = document.querySelector('input[name="number_of_children"]');
    const agesGroup = document.getElementById('children-ages-group');
    const childAgesHidden = document.getElementById('id_child_ages');
    const childAgesContainer = document.getElementById('child-ages-selects');

    if (childrenInput && agesGroup && childAgesHidden) {
        const minAge = parseInt(agesGroup.dataset.minAge || 0);
        const maxAge = parseInt(agesGroup.dataset.maxAge || 12);
        const ageRange = Array.from({ length: maxAge - minAge + 1 }, (_, i) => minAge + i);

        function renderChildAges(numChildren, prefillAges = []) {
            let html = '';
            if (numChildren > 0) {
                prefillAges = prefillAges.slice(0, numChildren);
                for (let i = 0; i < numChildren; i++) {
                    const selected = prefillAges[i] || ageRange[0];
                    html += `
                        <div class="mb-2">
                            <label for="child_age_${i + 1}" class="form-label small">Child ${i + 1} Age</label>
                            <select name="child_age_${i + 1}" id="child_age_${i + 1}" class="form-control child-age-input">
                                ${ageRange.map(age => `<option value="${age}" ${age == selected ? 'selected' : ''}>${age}</option>`).join('')}
                            </select>
                        </div>
                    `;
                }
            }
            childAgesContainer.innerHTML = html;

            // Listeners
            childAgesContainer.querySelectorAll('.child-age-input').forEach(select => {
                select.addEventListener('change', updateChildAgesJSON);
            });
            updateChildAgesJSON();
            console.log('Children ages rendered for', numChildren, 'with prefill', prefillAges);
        }

        function updateChildAgesJSON() {
            const selects = childAgesContainer.querySelectorAll('.child-age-input');
            const ages = Array.from(selects).map(s => parseInt(s.value)).filter(age => !isNaN(age));
            childAgesHidden.value = JSON.stringify(ages);
            console.log('Updated child_ages:', ages);
            if (typeof window.loadPricing === 'function' && !isInquiryOnly) {
                window.loadPricing();
        }
        }

        function toggleAges() {
            const numChildren = parseInt(childrenInput.value || 0);
            agesGroup.classList.toggle('d-none', numChildren === 0);
            if (numChildren > 0) {
                const prefill = JSON.parse(childAgesHidden.value || '[]');
                renderChildAges(numChildren, prefill);
            } else {
                childAgesContainer.innerHTML = '';
                childAgesHidden.value = '[]';
            }
        }

        childrenInput.addEventListener('change', toggleAges);
        toggleAges();  // Initial

    }


    document.addEventListener('click', function(e) {
        if (e.target.id !== 'refresh-captcha') return;
        e.preventDefault();
        console.log('Refresh clicked! API path');

        const $captchaSection = e.target.closest('.captcha-section');
        if (!$captchaSection) return console.error('Section missing');

        const $captchaImg = $captchaSection.querySelector('img[src*="/captcha/image/"]');
        const $hiddenInput = $captchaSection.querySelector('input[name="captcha_0"]');
        const $textInput = $captchaSection.querySelector('input[name="captcha_1"]');

        if (!$captchaImg || !$hiddenInput || !$textInput) return console.error('Elements missing');

        const refreshUrl = `/api/captcha-refresh/`;
        console.log('Fetching:', refreshUrl);
        fetch(refreshUrl)
            .then(r => {
                if (!r.ok) throw new Error(`HTTP ${r.status}`);
                return r.json();
            })
            .then(data => {
                console.log('New hash:', data.hash);
                $hiddenInput.value = data.hash;
                $captchaImg.src = `/captcha/image/${data.hash}/?v=${Date.now()}`;  // Lib image
                $textInput.value = '';

                e.target.textContent = 'Refreshed!';
                e.target.disabled = true;
                setTimeout(() => {
                    e.target.textContent = 'Refresh Image';
                    e.target.disabled = false;
                }, 1000);

                $textInput.focus();
            })
            .catch(err => console.error('Err:', err));
    });
    console.log('API CAPTCHA listener added');

});
