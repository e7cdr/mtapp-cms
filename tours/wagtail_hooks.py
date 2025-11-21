# tours/wagtail_hooks.py
from wagtail import hooks
from django.utils.html import format_html


@hooks.register('insert_editor_js')
def pricing_and_infant_controller():
    js = """
    <script>
    console.log("PRICING CONTROLLER LOADED – FINAL BULLETPROOF VERSION");

    function initPricingSwitcher() {
        const select = document.querySelector('select[name="pricing_type"]');
        if (!select) {
            console.warn("Pricing type select not found");
            return;
        }
        console.log("Found pricing_type select:", select.value);

        // Find the three pricing panels by their exact classname
        const panels = {
            Per_room:   document.querySelector('.per-room-panel'),
            Per_person: document.querySelector('.per-person-panel'),
            Combined:   document.querySelector('.combined-pricing-panel')
        };

        // Find the hidden JSON inputs (these exist because use_json_field=True)
        const inputs = {
            Per_room:   document.querySelector('input[name="per_room_pricing"]'),
            Per_person: document.querySelector('input[name="per_person_pricing"]'),
            Combined:   document.querySelector('input[name="combined_pricing_tiers"]')
        };

        console.log("Found panels:", panels);
        console.log("Found inputs:", inputs);

        function update() {
            const value = select.value;
            console.log("Pricing type changed to:", value);

            // 1. Hide ALL panels completely
            Object.values(panels).forEach(p => {
                if (p) p.style.display = 'none';
            });

            // 2. Show only the active one
            if (panels[value]) {
                panels[value].style.display = 'block';
                console.log("Showing panel:", value);
            }

            // 3. Clear unused StreamFields → no more -count errors
            Object.keys(inputs).forEach(type => {
                const input = inputs[type];
                if (type !== value && input) {
                    input.value = '[]';
                    input.dispatchEvent(new Event('change'));
                    console.log("Cleared field:", input.name);
                }
            });
        }

        // Run now
        update();

        // Run on every change
        select.addEventListener('change', update);

        // Run again if Wagtail rebuilds the form (e.g. after adding a block)
        new MutationObserver(update).observe(document.body, { childList: true, subtree: true });
    }

    // Run after everything is loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPricingSwitcher);
    } else {
        initPricingSwitcher();
    }
    </script>
    """
    return format_html(js.replace("{", "{{").replace("}", "}}"))


# Optional: tiny CSS so collapsed panels don't look broken
@hooks.register('insert_editor_css')
def pricing_admin_css():
    return format_html("<style>.per-room-panel, .per-person-panel, .combined-pricing-panel { transition: none; }</style>")