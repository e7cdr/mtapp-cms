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

# The star: JS injection
@hooks.register('insert_editor_js')
def editor_js():
    return format_html("""
        <script>
            console.log('{{ }}🎉 Wagtail Editor JS INJECTED');
            $(document).ready(function() {{
                console.log('{{ }}📋 jQuery Ready - Hunting panels...');
                
                setTimeout(function() {{
                    const selectWrapper = $('.pricing-type-selector');
                    const selectEl = selectWrapper.find('select')[0];
                    const roomPanel = $('.per-room-panel')[0];
                    const personPanel = $('.per-person-panel')[0];
                    
                    console.log('{{ }}🔍 Pricing wrapper:', !!selectWrapper.length);
                    console.log('{{ }}🔍 Select:', !!selectEl);
                    console.log('{{ }}🔍 Per Room panel:', !!roomPanel);
                    console.log('{{ }}🔍 Per Person panel:', !!personPanel);
                    
                    if (selectEl && roomPanel && personPanel) {{
                        console.log('{{ }}✅ Locked & loaded - Toggle time!');
                        
                        function togglePanels(isInitial) {{
                            const val = selectEl.value;
                            console.log('{{ }}🔄 Toggle: Value = "{{ }}' + val + '{{ }}" (initial: ' + isInitial + ')');
                            
                            if (val === 'Per_room') {{
                                // Clear/hide Per Person (inactive)
                                $(personPanel).find('input, select, textarea').val('').end().hide().find('input, select, textarea, .field').prop('disabled', true);
                                console.log('{{ }}👥 Per Person: CLEAR & HIDE (inactive)');
                                
                                // Show/enable Per Room (active - no clear!)
                                $(roomPanel).show().find('input, select, textarea, .field').prop('disabled', false);
                                console.log('{{ }}🛏️ Per Room: SHOW & ENABLE (active)');
                            }} else if (val === 'Per_person') {{
                                // Clear/hide Per Room (inactive)
                                $(roomPanel).find('input, select, textarea').val('').end().hide().find('input, select, textarea, .field').prop('disabled', true);
                                console.log('{{ }}🛏️ Per Room: CLEAR & HIDE (inactive)');
                                
                                // Show/enable Per Person (active - no clear!)
                                $(personPanel).show().find('input, select, textarea, .field').prop('disabled', false);
                                console.log('{{ }}👥 Per Person: SHOW & ENABLE (active)');
                            }} else {{
                                console.log('{{ }}⚠️ Unknown: Both hidden');
                                $(roomPanel).hide().find('input, select, textarea, .field').prop('disabled', true);
                                $(personPanel).hide().find('input, select, textarea, .field').prop('disabled', true);
                            }}
                            
                            if (!isInitial) {{
                                console.log('{{ }}💾 Values cleared on change - Save to persist');
                            }}
                        }}
                        
                        // Initial: No clear (preserve existing values)
                        togglePanels(true);
                        
                        // On change: Clear inactive
                        $(selectEl).on('change', function() {{ togglePanels(false); }});
                        
                        console.log('{{ }}🎯 Toggle bound! Enter prices, toggle, save to test.');
                    }} else {{
                        console.error('{{ }}❌ Missing elements - Verify classnames');
                    }}
                }}, 1500);
            }});
        </script>
    """)