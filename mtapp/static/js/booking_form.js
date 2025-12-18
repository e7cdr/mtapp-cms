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
        if (typeof updateChildAgesJSON === 'function') {
            updateChildAgesJSON(false);
        }

        clearTimeout(pricingTimeout);
        pricingTimeout = setTimeout(() => {
            const formData = new FormData(document.getElementById('bookingForm'));
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
    document.getElementById('submitProposal')?.addEventListener('click', function (e) {
        e.preventDefault();
        const form = document.getElementById('bookingForm');
        const formData = new FormData(form);
        const tourId = parseInt(document.getElementById('id_tour_id').value);
        const saveUrl = form.action;

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
            if (!r.ok) return r.json().then(data => { throw { errors: data.errors || data }; });
            return r.json();
        })
        .then(data => {
            if (!data.success) throw { errors: data.errors || { __all__: ['Please correct the errors below.'] } };

            const tourType = document.querySelector('#id_tour_type').value;
            return fetch(`/bookings/confirm/${tourType}/${tourId}/`, {
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

            Object.keys(errors).forEach(field => {
                const fieldErrors = errors[field];
                if (Array.isArray(fieldErrors)) {
                    fieldErrors.forEach(msg => {
                        let text = typeof msg === 'object' && msg.message ? msg.message : msg;
                        if (field === 'captcha' || String(text).toLowerCase().includes('captcha')) {
                            messages.push('Please complete the CAPTCHA correctly');
                        } else {
                            messages.push(text);
                        }

                        if (field === 'captcha') {
                            document.querySelector('input[name="captcha_1"]')?.classList.add('is-invalid');
                            document.querySelector('.captcha-section')?.classList.add('border', 'border-danger', 'border-2');
                        } else {
                            const input = document.querySelector(`[name="${field}"]`) || document.getElementById(`id_${field}`);
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

            if (messages.length === 0) messages.push('Please check all fields and try again.');
            showError(messages.join('<br>'), 'Validation Error');
        });
    });

    // ────────────────────── Confirm Submit in Modal ──────────────────────
    document.addEventListener('click', function (e) {
        if (e.target.id !== 'confirmSubmit') return;

        const modalForm = document.querySelector('#confirmationForm');
        if (!modalForm) return alert('Error: No form found.');

        const submitButton = e.target;
        const originalText = submitButton.innerText.trim();
        submitButton.innerHTML = '<span class="spinner"></span> Loading...';
        submitButton.disabled = true;

        const formData = new FormData();
        modalForm.querySelectorAll('input[type="hidden"]').forEach(input => {
            formData.append(input.name, input.value);
        });

        const tourType = modalForm.dataset.tourType;
        const tourId = modalForm.dataset.tourId;
        const url = `/bookings/submit-proposal/${tourType}/${tourId}/`;

        fetch(url, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                window.location.href = `/bookings/proposal-success/${data.proposal_id}/`;
            } else {
                alert(data.error);
                submitButton.innerText = originalText;
                submitButton.disabled = false;
            }
        })
        .catch(() => {
            alert('Error submitting. Please try again.');
            submitButton.innerText = originalText;
            submitButton.disabled = false;
        });
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

        fetch('/api/captcha-refresh/')
            .then(r => r.ok ? r.json() : Promise.reject())
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
            .catch(() => { });
    });
});