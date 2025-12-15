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

    const BOOKING_DATA = window.BOOKING_DATA || {};
    const isInquiryOnly = BOOKING_DATA.collect_price === false;

    /* ------------------------------------------------------------------ */
    /* 1. INQUIRY-ONLY MODE — DISABLE PRICING COMPLETELY                     */
    /* ------------------------------------------------------------------ */
    if (isInquiryOnly) {
        console.log('Inquiry-only tour → no pricing, modal WILL appear');
        document.querySelector('#pricing-options')?.closest('.card')?.remove();

        const btn = document.getElementById('submitProposal');
        if (btn) btn.textContent = 'Review & Send Inquiry';

        window.loadPricing = function () {
            console.log('loadPricing() blocked for inquiry-only tour');
        };

        Object.defineProperty(window, 'loadPricing', {
            value: () => console.log('Pricing blocked'),
            writable: false,
            configurable: false
        });
    }

    /* ------------------------------------------------------------------ */
    /* 2. CHILD AGES MANAGEMENT — MUST BE DEFINED BEFORE loadPricing()      */
    /* ------------------------------------------------------------------ */
    const childrenInput = document.querySelector('input[name="number_of_children"]');
    const agesGroup = document.getElementById('children-ages-group');
    const childAgesContainer = document.getElementById('child-ages-selects');

    function updateChildAgesJSON() {
        if (!childAgesContainer) return;

        const selects = childAgesContainer.querySelectorAll('.child-age-input');
        const ages = Array.from(selects)
            .map(s => parseInt(s.value) || 0)
            .filter(age => age > 0);

        let hidden = document.getElementById('id_child_ages');
        if (!hidden) {
            hidden = document.createElement('input');
            hidden.type = 'hidden';
            hidden.name = 'child_ages';
            hidden.id = 'id_child_ages';
            childAgesContainer.appendChild(hidden);
        }

        hidden.value = JSON.stringify(ages);
        console.log('Updated child_ages hidden:', ages);

        if (typeof loadPricing === 'function' && !isInquiryOnly) {
            loadPricing();
        }
    }

    function renderChildAges(numChildren, prefillAges = []) {
        if (!childAgesContainer) return;

        let html = '';
        const ageRange = window.SELECT_AGE_RANGE || Array.from({ length: 12 }, (_, i) => i + 1);

        for (let i = 0; i < numChildren; i++) {
            const selected = prefillAges[i] || '';
            html += `
                <div class="mb-2">
                    <label for="child_age_${i}" class="block font-lora text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">
                        Child ${i + 1} Age
                    </label>
                    <select id="child_age_${i}" class="child-age-input w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400 dark:bg-gray-700 dark:border-gray-600">
                        ${ageRange.map(age => `<option value="${age}" ${age == selected ? 'selected' : ''}>${age}</option>`).join('')}
                    </select>
                </div>
            `;
        }

        // ALWAYS recreate the hidden input (ensures it exists)
        html += `<input type="hidden" name="child_ages" id="id_child_ages" value="[]">`;

        childAgesContainer.innerHTML = html;

        // Re-attach change listeners
        childAgesContainer.querySelectorAll('.child-age-input').forEach(select => {
            select.addEventListener('change', updateChildAgesJSON);
        });

        // Apply prefill values
        childAgesContainer.querySelectorAll('.child-age-input').forEach((select, i) => {
            if (prefillAges[i] !== undefined) select.value = prefillAges[i];
        });

        // Final sync
        updateChildAgesJSON();

        console.log('Children ages rendered for', numChildren, 'with prefill', prefillAges);
    }

    function toggleAges() {
        const numChildren = parseInt(childrenInput?.value || 0);
        if (agesGroup) agesGroup.classList.toggle('d-none', numChildren === 0);

        if (numChildren > 0) {
            let prefill = [];
            const hidden = document.getElementById('id_child_ages');
            if (hidden) {
                try { prefill = JSON.parse(hidden.value || '[]'); } catch (e) { prefill = []; }
            }
            renderChildAges(numChildren, prefill);
        } else {
            if (childAgesContainer) childAgesContainer.innerHTML = '';
        }
    }

    if (childrenInput) {
        childrenInput.addEventListener('change', toggleAges);
        toggleAges(); // initial render
    }

    /* ------------------------------------------------------------------ */
    /* 3. DYNAMIC PRICING LOAD                                             */
    /* ------------------------------------------------------------------ */
    let pricingTimeout;

    function loadPricing() {
        console.log('loadPricing() called');
        console.log('Adults:', document.querySelector('input[name="number_of_adults"]')?.value || '');
        console.log('Children:', document.querySelector('input[name="number_of_children"]')?.value || '');

        if (isInquiryOnly) {
            console.log('loadPricing() blocked — inquiry-only tour');
            return;
        }

        const pricingContainer = document.getElementById('pricing-options');
        if (!pricingContainer) {
            console.log('Pricing container not found — skipping loadPricing()');
            return;
        }

        // Force child ages update before sending request
        if (typeof updateChildAgesJSON === 'function') updateChildAgesJSON();

        clearTimeout(pricingTimeout);
        pricingTimeout = setTimeout(() => {
            const formData = new FormData(document.getElementById('bookingForm'));
            const hidden = document.getElementById('id_child_ages');
            console.log('Final child_ages hidden:', hidden ? hidden.value : 'NOT FOUND');

            const tourType = document.querySelector('#id_tour_type').value;
            const tourId   = document.querySelector('#id_tour_id').value;
            const lang     = BOOKING_DATA.languagePrefix || '';
            const url      = `/${lang}/bookings/calculate_pricing/${tourType}/${tourId}/`.replace(/\/+/g, '/');

            const csrfToken = getCookie('csrftoken');

            fetch(url, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken || ''
                }
            })
            .then(r => {
                if (!r.ok) {
                    console.error('Pricing fetch failed:', r.status);
                    return '';
                }
                return r.text();
            })
            .then(html => {
                if (pricingContainer) {
                    pricingContainer.innerHTML = html;
                    // Your existing filter/radio init functions go here
                    // initializeFilters();
                    // rebindRadioSelection();
                }
            })
            .catch(err => console.error('Pricing fetch error:', err));
        }, 300);
    }

    // Initial pricing load
    setTimeout(() => !isInquiryOnly && loadPricing(), 200);

    // Change listeners
    document.addEventListener('change', e => {
        if (e.target.matches('input[name="number_of_adults"], input[name="number_of_children"], #id_travel_date')) {
            console.log('Change detected:', e.target.name, e.target.value);
            loadPricing();
        }
    });

    document.addEventListener('input', e => {
        if (e.target.matches('input[name="number_of_adults"], input[name="number_of_children"]')) {
            loadPricing();
        }
    });

    /* ------------------------------------------------------------------ */
    /* 4. CAPTCHA REFRESH                                                   */
    /* ------------------------------------------------------------------ */
    document.addEventListener('click', function (e) {
        if (e.target.id !== 'refresh-captcha') return;
        e.preventDefault();

        const section = e.target.closest('.captcha-section');
        if (!section) return console.error('Section missing');

        const img = section.querySelector('img[src*="/captcha/image/"]');
        const hidden = section.querySelector('input[name="captcha_0"]');
        const input = section.querySelector('input[name="captcha_1"]');

        if (!img || !hidden || !input) return console.error('Elements missing');

        fetch('/api/captcha-refresh/')
            .then(r => r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))
            .then(data => {
                hidden.value = data.hash;
                img.src = `/captcha/image/${data.hash}/?v=${Date.now()}`;
                input.value = '';
                e.target.textContent = 'Refreshed!';
                e.target.disabled = true;
                setTimeout(() => {
                    e.target.textContent = 'Refresh Image';
                    e.target.disabled = false;
                }, 1000);
                input.focus();
            })
            .catch(err => console.error('Captcha refresh error:', err));
    });

    console.log('API CAPTCHA listener added');
});