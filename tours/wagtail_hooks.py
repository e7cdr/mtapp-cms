from django.utils.html import format_html
from wagtail import hooks

from django.utils.html import format_html
from wagtail import hooks

@hooks.register('insert_editor_js')
def pricing_and_infant_controller():
    js = """
    <script>
    document.addEventListener('DOMContentLoaded', function () {
        const pricingSelect = document.querySelector('select[name="pricing_type"]');
        if (!pricingSelect) return;

        // The actual StreamField containers (Wagtail wraps them in a div with this class)
        const roomField     = document.querySelector('#id_per_room_pricing').closest('.w-field__wrapper');
        const personField   = document.querySelector('#id_per_person_pricing').closest('.w-field__wrapper');
        const combinedField = document.querySelector('#id_combined_pricing_tiers').closest('.w-field__wrapper');

        // The visual panels (the MultiFieldPanel wrappers)
        const roomPanel     = document.querySelector('.per-room-panel');
        const personPanel   = document.querySelector('.per-person-panel');
        const combinedPanel = document.querySelector('.combined-pricing-panel');

        function toggle() {
            const value = pricingSelect.value;

            // 1. Hide/show the big collapsible panels (purely cosmetic)
            [roomPanel, personPanel, combinedPanel].forEach(p => p?.classList.add('collapsed'));

            if (value === 'Per_room') {
                roomPanel?.classList.remove('collapsed');
            } else if (value === 'Per_person') {
                personPanel?.classList.remove('collapsed');
            } else if (value === 'Combined') {
                combinedPanel?.classList.remove('collapsed');
            }

            // 2. CRITICAL: Never hide the actual StreamField wrapper with display:none
            //     Instead we move the hidden ones off-screen but keep them rendered
            const offscreen = { position: 'absolute', left: '-9999px', top: '-9999px', visibility: 'hidden' };
            const visible   = { position: '', left: '', top: '', visibility: '' };

            // Reset all
            [roomField, personField, combinedField].forEach(f => {
                if (f) Object.assign(f.style, offscreen);
            });

            // Show only the active one
            if (value === 'Per_room' && roomField)     Object.assign(roomField.style, visible);
            if (value === 'Per_person' && personField) Object.assign(personField.style, visible);
            if (value === 'Combined' && combinedField) Object.assign(combinedField.style, visible);
        }

        // Run on load + on change
        toggle();
        pricingSelect.addEventListener('change', toggle);

        // Re-run after Wagtail re-initializes fields (e.g. when adding a new block)
        const observer = new MutationObserver(toggle);
        observer.observe(document.body, { childList: true, subtree: true });
    });
    </script>
    """
    return format_html(js)

@hooks.register('insert_editor_css')
def pricing_admin_css():
    return format_html("""
    <style>
        /* Make collapsed panels look disabled but still take space or not */
        .per-room-panel.collapsed > div > div,
        .per-person-panel.collapsed > div > div,
        .combined-pricing-panel.collapsed > div > div {
            opacity: 0.5;
            pointer-events: none;
        }
        /* Optional: completely hide the header text when collapsed */
        .per-room-panel.collapsed h2,
        .per-person-panel.collapsed h2,
        .combined-pricing-panel.collapsed h2 {
            color: #999;
        }
    </style>
    """)


