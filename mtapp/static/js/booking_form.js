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

    if (isInquiryOnly) {
        document.querySelector('#pricing-options')?.closest('.card')?.remove();

        const btn = document.getElementById('submitProposal');
        if (btn) btn.textContent = 'Review & Send Inquiry';

        window.loadPricing = function () { };

        Object.defineProperty(window, 'loadPricing', {
            value: () => { },
            writable: false,
            configurable: false
        });
    }

    // ────────────────────── Child Ages Management ──────────────────────
    const childrenInput = document.querySelector('input[name="number_of_children"]');
    const agesGroup = document.getElementById('children-ages-group');
    const childAgesContainer = document.getElementById('child-ages-selects');

    // Defined first so loadPricing can use it safely
    function updateChildAgesJSON(triggerPricing = true) {
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

        // Only trigger pricing if explicitly requested (i.e., from user change)
        if (triggerPricing && typeof loadPricing === 'function' && !isInquiryOnly) {
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

        // Recreate hidden input every time
        html += `<input type="hidden" name="child_ages" id="id_child_ages" value="[]">`;

        childAgesContainer.innerHTML = html;

        // Re-attach listeners
        childAgesContainer.querySelectorAll('.child-age-input').forEach(select => {
            select.addEventListener('change', () => updateChildAgesJSON(true));
        });

        // Apply prefill
        childAgesContainer.querySelectorAll('.child-age-input').forEach((select, i) => {
            if (prefillAges[i] !== undefined) {
                select.value = prefillAges[i];
            }
        });

        // Final sync
        updateChildAgesJSON(false);
    }

    function toggleAges() {
        const numChildren = parseInt(childrenInput?.value || 0);
        if (agesGroup) agesGroup.classList.toggle('d-none', numChildren === 0);

        if (numChildren > 0) {
            let prefill = [];
            const hidden = document.getElementById('id_child_ages');
            if (hidden) {
                try {
                    prefill = JSON.parse(hidden.value || '[]');
                } catch (e) { }
            }
            renderChildAges(numChildren, prefill);
        } else {
            if (childAgesContainer) childAgesContainer.innerHTML = '';
        }
    }

    if (childrenInput) {
        childrenInput.addEventListener('change', toggleAges);
        toggleAges();
    }

    // ────────────────────── Dynamic Pricing Load ──────────────────────
    let pricingTimeout;

    function loadPricing() {
        if (isInquiryOnly) return;

        const pricingContainer = document.getElementById('pricing-options');
        if (!pricingContainer) return;

        // Ensure child ages are synced before request
        // if (typeof updateChildAgesJSON === 'function') {
        //     updateChildAgesJSON(false);
        // }

        updateChildAgesJSON(false); // sync ages

        clearTimeout(pricingTimeout);
        pricingTimeout = setTimeout(() => {
            const form = document.getElementById('bookingForm'); 
            const formData = new FormData(form);
            // const formData = new FormData(document.getElementById('bookingForm'));
            if (!formData.has('captcha_0') || !formData.has('captcha_1')) {
            console.warn('CAPTCHA fields missing in pricing request');
            }
            const tourType = document.querySelector('#id_tour_type').value;
            const tourId = document.querySelector('#id_tour_id').value;
            const languagePrefix = BOOKING_DATA.languagePrefix || 'en';
            const url = `/${languagePrefix}/bookings/calculate_pricing/${tourType}/${tourId}/`.replace(/\/+/g, '/');

            const csrfToken = getCookie('csrftoken');

            fetch(url, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken || ''
                }
            })
            .then(response => response.ok ? response.text() : '')
            .then(html => {
                if (pricingContainer) {
                    pricingContainer.innerHTML = html;
                    setTimeout(() => {
                    }, 50);
                }
            })
            .catch(error => console.error('Pricing fetch error:', error));
        }, 300);
    }

    // Initial load
    setTimeout(() => !isInquiryOnly && loadPricing(), 200);

    // Change listeners
    document.addEventListener('change', function (event) {
        if (event.target.matches('input[name="number_of_adults"], input[name="number_of_children"], #id_travel_date')) {
            loadPricing();
        }
    });

    document.addEventListener('input', function (event) {
        if (event.target.matches('input[name="number_of_adults"], input[name="number_of_children"]')) {
            loadPricing();
        }
    });

    // ────────────────────── Submit Proposal (Modal Flow) ──────────────────────
// ────────────────────── Submit Proposal (Save to Session & Open Confirmation) ──────────────────────
    document.getElementById('submitProposal')?.addEventListener('click', function (e) {
        e.preventDefault();

        const form = document.getElementById('bookingForm');
        if (!form) {
            console.error('Booking form not found');
            return;
        }

        // Use the entire form — this automatically includes ALL fields + CAPTCHA
        const formData = new FormData(form);

        console.log('Submitting first step with FormData:');
        for (let [key, value] of formData.entries()) {
            console.log(key, ':', value);
        }

        const saveUrl = form.action;

        fetch(saveUrl, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => {
            console.log('First step response status:', response.status);
            if (!response.ok) {
                return response.json().then(err => { throw err; });
            }
            return response.json();
        })
        .then(data => {
            console.log('First step success:', data);
            if (!data.success) throw data;

            const tourType = document.querySelector('#id_tour_type').value;
            const tourId = document.getElementById('id_tour_id').value;

            return fetch(`/bookings/confirm/${tourType}/${tourId}/`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });
        })
        .then(r => r.text())
        .then(html => {
            console.log('Confirmation partial loaded');
            document.getElementById('confirmationContent').innerHTML = html;
            new bootstrap.Modal(document.getElementById('confirmationModal')).show();
        })
        .catch(err => {
            console.error('First step failed:', err);
            alert('Failed to save booking data. See console for details.');
        });
    });

    // ────────────────────── Confirm Submit in Modal ──────────────────────
    document.addEventListener('click', async function (e) {
        if (e.target.id !== 'confirmSubmit') return;

        console.log('=== CONFIRM SUBMIT BUTTON CLICKED ===');
        console.log('Target element:', e.target);

        const modalForm = document.querySelector('#confirmationForm');
        if (!modalForm) {
            console.error('Confirmation form not found in DOM');
            alert('Error: Confirmation form not found.');
            return;
        }
        console.log('Modal form found:', modalForm);

        const submitButton = e.target;
        const originalText = submitButton.innerText.trim();
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Loading...';
        submitButton.disabled = true;

        const formData = new FormData();

        modalForm.querySelectorAll('input[type="hidden"]').forEach(input => {
            formData.append(input.name, input.value);
        });

        // Forward CAPTCHA from main form
        const mainForm = document.getElementById('bookingForm');
        if (mainForm) {
            const captchaHash = mainForm.querySelector('input[name="captcha_0"]');
            const captchaAnswer = mainForm.querySelector('input[name="captcha_1"]');
            if (captchaHash) formData.append('captcha_0', captchaHash.value);
            if (captchaAnswer) formData.append('captcha_1', captchaAnswer.value);
        }

        console.log('Final submit FormData contents:');
        for (let [key, value] of formData.entries()) {
            console.log(key, ':', value);
        }

        const tourType = modalForm.dataset.tourType;
        const tourId = modalForm.dataset.tourId;
        const languagePrefix = BOOKING_DATA.languagePrefix || 'en';
        const url = `/${languagePrefix}/bookings/submit-proposal/${tourType}/${tourId}/`.replace(/\/+/g, '/');

        console.log('Sending FINAL POST to:', url);
        console.log('With CSRF header (from cookie):', getCookie('csrftoken'));
        console.log('FormData has csrfmiddlewaretoken:', formData.has('csrfmiddlewaretoken'));

        try {
            console.log('Attempting to send POST fetch...');

            // Build URL-encoded body (most reliable for Django POST parsing)
            const bodyParams = new URLSearchParams();
            for (let [key, value] of formData.entries()) {
                bodyParams.append(key, value);
            }
            console.log('Final body (urlencoded):', bodyParams.toString());

            const response = await fetch(url, {
                method: 'POST',
                body: bodyParams.toString(),
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                credentials: 'same-origin'
            });

            console.log('Fetch completed with status:', response.status);

            if (!response.ok) {
                const errData = await response.json();
                console.log('Error response data:', errData);
                throw errData;
            }

            const data = await response.json();
            console.log('Final submit success:', data);

            if (data.success) {
                window.location.href = `/bookings/proposal-success/${data.proposal_id}/`;
            } else {
                alert(data.error || 'Submission failed. Please try again.');
                submitButton.innerText = originalText;
                submitButton.disabled = false;
            }
        } catch (fetchError) {
            console.error('FETCH THREW ERROR BEFORE OR DURING NETWORK:', fetchError);
            console.error('Full stack trace:', fetchError.stack);
            alert('Fetch failed — check console for details.');
            submitButton.innerText = originalText;
            submitButton.disabled = false;
        }
    });

    // ────────────────────── CAPTCHA Refresh ──────────────────────
    document.addEventListener('click', function (e) {
    if (e.target.id !== 'refresh-captcha') return;
    e.preventDefault();

    const section = e.target.closest('.captcha-section');
    if (!section) return;

    const img = section.querySelector('img[src*="/captcha/image/"]');
    const hidden = section.querySelector('input[name="captcha_0"]');
    const input = section.querySelector('input[name="captcha_1"]');

    if (!img || !hidden || !input) return;

    const button = e.target;
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = 'Refreshing...';

    fetch('/api/captcha-refresh/', { credentials: 'same-origin' })
        .then(r => {
            if (!r.ok) throw new Error('Refresh failed');
            return r.json();
        })
        .then(data => {
            hidden.value = data.hash;
            img.src = `/captcha/image/${data.hash}/?v=${Date.now()}`;
            input.value = '';
            input.focus();
            button.textContent = 'Refreshed!';
            setTimeout(() => {
                button.textContent = originalText;
                button.disabled = false;
            }, 1200);
        })
        .catch(err => {
            console.error(err);
            button.textContent = 'Refresh failed';
            setTimeout(() => {
                button.textContent = originalText;
                button.disabled = false;
            }, 2000);
        });
});
});