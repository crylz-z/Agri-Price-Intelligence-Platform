# Benchmark Price List (The PDF Standard)
# This file serves as the "Judge" for market prices.
# It defines the expected price range (Low-High) and Prevailing Price for commodities.

BENCHMARK_PRICES = {
    # RICE
    'Rice Special': {'min': 50, 'max': 65, 'prevailing': 55},
    'Rice Premium': {'min': 45, 'max': 58, 'prevailing': 50},
    'Rice Well Milled': {'min': 40, 'max': 52, 'prevailing': 45},
    'Rice Regular Milled': {'min': 38, 'max': 50, 'prevailing': 42},
    
    # MEAT
    'Beef Rump': {'min': 390, 'max': 480, 'prevailing': 420},
    'Beef Brisket': {'min': 350, 'max': 410, 'prevailing': 370},
    'Pork Kasim': {'min': 290, 'max': 340, 'prevailing': 310},
    'Pork Liempo': {'min': 340, 'max': 390, 'prevailing': 360},
    'Whole Chicken': {'min': 170, 'max': 210, 'prevailing': 190},
    'Chicken Egg (Medium)': {'min': 7, 'max': 9, 'prevailing': 8},
    
    # FISH
    'Bangus': {'min': 150, 'max': 220, 'prevailing': 180},
    'Tilapia': {'min': 110, 'max': 160, 'prevailing': 130},
    'Galunggong (Local)': {'min': 200, 'max': 280, 'prevailing': 240},
    
    # VEGETABLES
    'Ampalaya': {'min': 80, 'max': 140, 'prevailing': 100},
    'Sitao': {'min': 70, 'max': 120, 'prevailing': 90},
    'Pechay (Native)': {'min': 60, 'max': 100, 'prevailing': 80},
    'Squash': {'min': 30, 'max': 60, 'prevailing': 40},
    'Eggplant': {'min': 60, 'max': 110, 'prevailing': 80},
    'Tomato': {'min': 50, 'max': 90, 'prevailing': 70},
    'Red Onion': {'min': 80, 'max': 140, 'prevailing': 100},
    'White Onion': {'min': 70, 'max': 120, 'prevailing': 90},
    'Garlic (Imported)': {'min': 100, 'max': 160, 'prevailing': 130},
    'Ginger': {'min': 90, 'max': 150, 'prevailing': 120},
    'Chili (Labuyo)': {'min': 300, 'max': 600, 'prevailing': 450}, # Highly Volatile
}

def get_status(commodity_name, price):
    """
    Returns the market status: 'Cheap', 'Fair', 'Expensive', or 'No Benchmark'.
    """
    # Simple fuzzy matching (token based)
    norm_name = str(commodity_name).lower()
    
    best_match = None
    best_score = 0
    
    for bench_name, data in BENCHMARK_PRICES.items():
        # exact substring match?
        if bench_name.lower() in norm_name:
            if len(bench_name) > best_score:
                best_match = data
                best_score = len(bench_name)
    
    if not best_match:
        return {'status': 'Unknown', 'color': 'grey'}
        
    if price < best_match['min']:
        return {'status': 'Cheap (Below SRP)', 'color': 'green'}
    elif price > best_match['max']:
        return {'status': 'Expensive (Above SRP)', 'color': 'red'}
    else:
        return {'status': 'Fair Value', 'color': 'orange'}
