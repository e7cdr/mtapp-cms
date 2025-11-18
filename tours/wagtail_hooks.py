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
def pricing_type_panel_controller():
    js = """<script>
        document.addEventListener('DOMContentLoaded', function () {
            function init() {
                const select = document.querySelector('.pricing-type-selector select');
                const roomPanel = document.querySelector('.per-room-panel');
                const personPanel = document.querySelector('.per-person-panel');
                const combinedPanel = document.querySelector('.combined-pricing-panel');  // ← NEW

                if (!select) {
                    setTimeout(init, 100);
                    return;
                }

                function toggle() {
                    const val = select.value;

                    // Reset all
                    [roomPanel, personPanel, combinedPanel].forEach(p => {
                        if (p) {
                            p.style.display = 'none';
                            p.querySelectorAll('input, select, textarea, button').forEach(el => {
                                el.disabled = true;
                            });
                        }
                    });

                    if (val === 'Per_room' && roomPanel) {
                        roomPanel.style.display = 'block';
                        roomPanel.querySelectorAll('input, select, textarea, button').forEach(el => el.disabled = false);

                    } else if (val === 'Per_person' && personPanel) {
                        personPanel.style.display = 'block';
                        personPanel.querySelectorAll('input, select, textarea, button').forEach(el => el.disabled = false);

                    } else if (val === 'Combined' && combinedPanel) {
                        combinedPanel.style.display = 'block';
                        combinedPanel.querySelectorAll('input, select, textarea, button').forEach(el => el.disabled = false);
                    }
                }

                toggle();
                select.addEventListener('change', toggle);
            }

            init();

            // Re-init when Wagtail dynamically adds panels
            document.addEventListener('wagtail:panel-init', init);
        });
    </script>"""

    # Escape { and } for format_html
    safe_js = js.replace('{', '{{').replace('}', '}}')
    return format_html(safe_js)