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
        body {{ 
            margin: 0; 
            padding: 0; 
            background-color: transparent; 
            font-family: 'Source Sans Pro', sans-serif; 
        }}
        .flatpickr-input {{
            width: 100%;
            font-size: 14px;
            border-radius: 8px;
            border: 1px solid #d5dce6;
            padding: 8px 12px;
            color: #31333F;
            background-color: white;
            cursor: pointer;
            box-sizing: border-box;
            font-family: inherit;
        }}
        .flatpickr-input:focus {{
            outline: none;
            border-color: #ff4b4b;
        }}
    </style>
    
    <input type="text" id="date-picker" class="flatpickr-input" value="{default_date}">
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const availableDates = {dates_json};
            
            flatpickr("#date-picker", {{
                enable: availableDates,
                dateFormat: "Y/m/d",
                defaultDate: "{default_date}",
                onChange: function(selectedDates, dateStr) {{
                    if (dateStr) {{
                        // Convert display format Y/m/d back to Y-m-d for backend compatibility
                        const internalDate = dateStr.replace(/\//g, '-');
                        const url = new URL(window.parent.location.href);
                        url.searchParams.set('date', internalDate);
                        window.parent.history.pushState({{}}, '', url);
                        window.parent.location.reload();
                    }}
                }}
            }});
        }});
    </script>
    """
    
    components.html(html_code, height=350)
