import streamlit as st
import streamlit.components.v1 as components
import json

def render_custom_calendar(available_dates, selected_date=None):
    """
    Renders a Flatpickr.js calendar that only allows selection from 'available_dates'.
    Selection updates the parent URL with ?date=YYYY-MM-DD.
    """
    
    # Ensure available_dates are strings for JS
    dates_json = json.dumps(available_dates)
    default_date = selected_date if selected_date else (available_dates[0] if available_dates else "")

    html_code = f"""
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css">
    <script src="https://cdn.jsdelivr.net/npm/flatpickr"></script>
    <style>
        body {{ margin: 0; padding: 0; overflow: hidden; display: flex; justify-content: center; }}
        #date-picker {{ display: none; }}
        .flatpickr-calendar {{ 
            box-shadow: none !important; 
            border: none !important; 
            background: transparent !important;
            margin: 0 auto !important;
        }}
    </style>
    
    <input type="text" id="date-picker" value="{default_date}">
    <div id="inline-calendar"></div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const availableDates = {dates_json};
            
            flatpickr("#inline-calendar", {{
                inline: true,
                enable: availableDates,
                dateFormat: "Y-m-d",
                defaultDate: "{default_date}",
                onChange: function(selectedDates, dateStr) {{
                    if (dateStr) {{
                        const url = new URL(window.parent.location.href);
                        url.searchParams.set('date', dateStr);
                        window.parent.history.pushState({{}}, '', url);
                        window.parent.location.reload();
                    }}
                }}
            }});
        }});
    </script>
    """
    
    components.html(html_code, height=320)
