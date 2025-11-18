from django.utils.html import format_html
from wagtail import hooks

# Comment out these for now - they're causing the sidebar crash
# @hooks.register('register_admin_menu_item')
# def register_menu_item():
#     return [  # Or whatever - skip it
#         {'location': 'after_explorer', 'label': 'Test Hook', ...}
#     ]
#
# @hooks.register('register_admin_url')
# def register_test_url():
#     return ('test-hook', 'tours.views.test_hook', 'test-hook')


@hooks.register('insert_editor_js')
def pricing_and_infant_controller():
    js = """
    <script>
        document.addEventListener('DOMContentLoaded', function () {
            console.log('FINAL VERSION LOADED');

            // 1. PRICING TYPE TOGGLER — already working
            function initPricingToggle() {
                const select = document.querySelector('select[name="pricing_type"]');
                if (!select) return;

                const roomPanel = document.querySelector('.per-room-panel');
                const personPanel = document.querySelector('.per-person-panel');
                const combinedPanel = document.querySelector('.combined-pricing-panel');

                function toggle() {
                    const val = select.value;
                    [roomPanel, personPanel, combinedPanel].forEach(p => {
                        if (p) {
                            p.style.display = 'none';
                            p.querySelectorAll('input, select, textarea').forEach(el => el.disabled = true);
                        }
                    });

                    if (val === 'Per_room' && roomPanel) {
                        roomPanel.style.display = 'block';
                        roomPanel.querySelectorAll('input, select, textarea').forEach(el => el.disabled = false);
                    }
                    if (val === 'Per_person' && personPanel) {
                        personPanel.style.display = 'block';
                        personPanel.querySelectorAll('input, select, textarea').forEach(el => el.disabled = false);
                    }
                    if (val === 'Combined' && combinedPanel) {
                        combinedPanel.style.display = 'block';
                        combinedPanel.querySelectorAll('input, select, textarea').forEach(el => el.disabled = false);
                    }
                }

                toggle();
                select.addEventListener('change', toggle);
            }

            // 2. INFANT FIELDS — THIS WORKS IN WAGTAIL 6+
            function updateInfantFields(block) {
                const typeSelect = block.querySelector('select[id*="infant_price_type"]');
                if (!typeSelect) return;

                // WAGTAIL 6+ USES data-field-name
                const percentField = block.querySelector('[data-field-name="infant_percent_of_adult"]')?.closest('.w-field');
                const fixedField   = block.querySelector('[data-field-name="infant_fixed_amount"]')?.closest('.w-field');

                function toggle() {
                    const val = typeSelect.value;

                    if (percentField) percentField.style.display = 'none';
                    if (fixedField) fixedField.style.display = 'none';

                    if (val === 'percent' && percentField) percentField.style.display = 'block';
                    if (val === 'fixed' && fixedField) fixedField.style.display = 'block';
                }

                toggle();
                typeSelect.addEventListener('change', toggle);
            }

            function scanBlocks() {
                document.querySelectorAll('.struct-block').forEach(block => {
                    if (block.querySelector('select[id*="infant_price_type"]')) {
                        updateInfantFields(block);
                    }
                });
            }

            // Run everything
            initPricingToggle();
            scanBlocks();

            // Watch for new blocks
            const observer = new MutationObserver(() => {
                setTimeout(scanBlocks, 50);
            });
            observer.observe(document.body, { childList: true, subtree: true });
        });
    </script>
    """
    return format_html(js.replace('{', '{{').replace('}', '}}'))

@hooks.register('insert_editor_css')
def pricing_admin_css():
    return format_html(
        '<style>'
        '.per-room-panel, .per-person-panel, .combined-pricing-panel { transition: opacity 0.3s; }'
        '.per-room-panel[style*="none"], .per-person-panel[style*="none"], .combined-pricing-panel[style*="none"] { opacity: 0.6; }'
        '</style>'
    )

