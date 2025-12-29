import json
import os

def load_flap_table(filepath='flapDescriptor.json'):
    """Loads the flap position to symbol mapping table and optimal speeds from a JSON file."""
    if not os.path.exists(filepath):
        # Fallback to absolute path or search in the same directory as the script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(script_dir, filepath)

    with open(filepath, 'r') as f:
        data = json.load(f)
    return data

# Load the data once at module initialization
_ALL_DATA = load_flap_table()
_FLAP_DATA = _ALL_DATA['flap2symbol']
_OPTIMAL_SPEED_DATA = _ALL_DATA.get('speedpolar', {}).get('optimale_fluggeschwindigkeit_kmh', {})

_TABLE = _FLAP_DATA['table']
_TOLERANCE = _FLAP_DATA['tolerance']
_EMPTY_MASS = _ALL_DATA.get('speedpolar', {}).get('empty_mass')

def get_empty_mass():
    """Returns the empty mass of the aircraft."""
    return _EMPTY_MASS

_WEIGHTS = _OPTIMAL_SPEED_DATA.get('gewicht_kg', [])
_BEREICHE = _OPTIMAL_SPEED_DATA.get('bereiche', [])

def get_flap_symbol(position, flap_data=None):
    """
    Finds the flap symbol for a given position based on the provided table and tolerance.
    If flap_data is None, it uses the module-level _TABLE and _TOLERANCE.
    """
    if flap_data is None:
        table = _TABLE
        tolerance = _TOLERANCE
    else:
        table = flap_data['table']
        tolerance = flap_data['tolerance']
    
    for target_pos, symbol in table:
        if abs(position - target_pos) <= tolerance:
            return symbol
    
    return None

def get_optimal_flap(gewicht, geschwindigkeit):
    """
    Finds the optimal flap symbol (wk) for a given weight and speed.
    Interpolates speed boundaries for arbitrary weights.
    """
    if not _WEIGHTS or not _BEREICHE:
        return None

    # Handle weight out of bounds
    if gewicht <= _WEIGHTS[0]:
        w1 = w2 = _WEIGHTS[0]
        factor = 0
    elif gewicht >= _WEIGHTS[-1]:
        w1 = w2 = _WEIGHTS[-1]
        factor = 0
    else:
        # Find the two weights to interpolate between
        idx = 0
        while idx < len(_WEIGHTS) - 1 and _WEIGHTS[idx+1] < gewicht:
            idx += 1
        w1 = _WEIGHTS[idx]
        w2 = _WEIGHTS[idx+1]
        factor = (gewicht - w1) / (w2 - w1)

    for bereich in _BEREICHE:
        speed_data = bereich.get('geschwindigkeit', {})
        
        # Get speed boundaries for the two weights
        # Note: keys in JSON are strings
        v1_range = speed_data.get(str(w1))
        v2_range = speed_data.get(str(w2))

        if v1_range and v2_range:
            # Interpolate boundaries
            v_min = v1_range[0] + factor * (v2_range[0] - v1_range[0])
            v_max = v1_range[1] + factor * (v2_range[1] - v1_range[1])

            if v_min <= geschwindigkeit <= v_max:
                return bereich['wk']
        elif v1_range: # Fallback if only one weight found (shouldn't happen with valid data)
            if v1_range[0] <= geschwindigkeit <= v1_range[1]:
                return bereich['wk']

    return None

if __name__ == "__main__":
    # Example usage/test
    try:
        data = load_flap_table()
        print(f"Loaded data: {data['flap2symbol']['Description']}")
        print(f"Empty Mass (variable): {_EMPTY_MASS} kg")
        print(f"Empty Mass (function): {get_empty_mass()} kg")
        
        print("\n--- Testing get_flap_symbol ---")
        test_positions = [94, 95, 96, 97, 84, 85, 250, 252, 0, 230, 157, 167]
        for pos in test_positions:
            symbol = get_flap_symbol(pos, data['flap2symbol'])
            print(f"Position {pos} -> Symbol: {symbol}")

        print("\n--- Testing get_optimal_flap (Interpolation) ---")
        # Test with exact weights
        test_cases = [
            (390, 70, "L"),
            (390, 85, "+1"),
            (430, 81, "+2"),
            (600, 100, "+1"),
            # Test interpolation
            (410, 78, "L"), # 410 is between 390 and 430. 
                           # L: 390 -> [0, 76], 430 -> [0, 80]. Interpolated for 410: [0, 78]
            (410, 79, "+2"), # +2: 390 -> [76, 80], 430 -> [80, 83]. Interpolated for 410: [78, 81.5]
            (500, 130, "0"), # 500 is between 430 and 550.
                             # 0: 430 -> [94, 128], 550 -> [106, 145]. 
                             # factor = (500-430)/(550-430) = 70/120 = 0.5833
                             # min = 94 + 0.5833 * (106-94) = 94 + 7 = 101
                             # max = 128 + 0.5833 * (145-128) = 128 + 0.5833 * 17 = 128 + 9.9 = 137.9
                             # 130 is within [101, 137.9]
        ]
        for w, v, expected in test_cases:
            res = get_optimal_flap(w, v)
            print(f"Weight {w}kg, Speed {v}km/h -> Optimal Flap: {res} (Expected: {expected})")

    except Exception as e:
        import traceback
        traceback.print_exc()
