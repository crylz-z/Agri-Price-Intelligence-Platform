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
        .flatpickr-input {{
            width: 100%;
            padding: 10px;
            border-radius: 8px;
            border: 1px solid #ddd;
            font-family: 'Inter', sans-serif;
            cursor: pointer;
            background: white;
            text-align: center;
            font-weight: 500;
        }}
    </style>
    
    <input type="text" id="date-picker" class="flatpickr-input" placeholder="Select Market Date..." value="{default_date}">
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const availableDates = {dates_json};
            
            flatpickr("#date-picker", {{
                enable: availableDates,
                dateFormat: "Y-m-d",
                defaultDate: "{default_date}",
                onChange: function(selectedDates, dateStr) {{
                    if (dateStr) {{
                        // Broadcast to Streamlit via URL
                        const url = new URL(window.parent.location.href);
                        url.searchParams.set('date', dateStr);
                        window.parent.history.pushState({{}}, '', url);
                        
                        // Force a refresh if needed (Streamlit will detect query param change)
                        window.parent.location.reload();
                    }}
                }}
            }});
        }});
    </script>
    """
    
    components.html(html_code, height=400)
