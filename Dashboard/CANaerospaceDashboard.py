import argparse
import struct
import threading

import can
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go

from flaputils import get_flap_symbol, get_optimal_flap, get_empty_mass

parser = argparse.ArgumentParser(description='Read position updates from can-bus and print it')
parser.add_argument('-channel', metavar='channel', type=str, default='can0', help='Canbus, default=can0')
args = parser.parse_args()
channel = args.channel

CAN_SFF_MASK = 0x000007FF

# Global variables for storing the latest values from CAN bus
lat = lon = gs = tt = ias = tas = cas = alt = vario = enl = flap = None
pilot_mass = 0

CAN_IDS = {
    315: 'ias',
    316: 'tas',
    317: 'cas',
    322: 'alt',
    340: 'flap',
    354: 'vario',
    1036: 'lat',
    1037: 'lon',
    1039: 'gs',
    1040: 'tt',
    1200: 'utc',
    1316: 'pilot_mass',
    1506: 'enl'
}

bus = can.interface.Bus(channel=channel, interface='socketcan')
bus.set_filters([{"can_id": can_id, "can_mask": CAN_SFF_MASK} for can_id in CAN_IDS.keys()])


def getFloat(canMsg):
    return struct.unpack('>f', canMsg.data[4:8])[0]


def getDoubleL(canMsg):
    return struct.unpack('>l', canMsg.data[4:8])[0] / 1E7


def getUshort(canMsg):
    return struct.unpack('>H', canMsg.data[4:6])[0]


def getChar(canMsg):
    return struct.unpack('B', canMsg.data[4:5])[0]


def can_receive_loop():
    global lat, lon, gs, tt, ias, tas, cas, alt, vario, enl, flap, pilot_mass
    try:
        for canMsg in bus:
            if canMsg.arbitration_id not in CAN_IDS:
                print(f"Unknown ID {canMsg.arbitration_id}: {canMsg.data.hex()}")
                continue

            if canMsg.arbitration_id == 1200:  # UTC
                pass  # getChar4(canMsg)
            elif canMsg.arbitration_id == 315:
                ias = getFloat(canMsg)
            elif canMsg.arbitration_id == 316:
                tas = getFloat(canMsg)
            elif canMsg.arbitration_id == 317:
                cas = getFloat(canMsg)
            elif canMsg.arbitration_id == 322:
                alt = getFloat(canMsg)
            elif canMsg.arbitration_id == 340:
                flap = getChar(canMsg)
            elif canMsg.arbitration_id == 354:
                vario = getFloat(canMsg)
            elif canMsg.arbitration_id == 1036:
                lat = getDoubleL(canMsg)
            elif canMsg.arbitration_id == 1037:
                lon = getDoubleL(canMsg)
            elif canMsg.arbitration_id == 1039:
                gs = getFloat(canMsg)
            elif canMsg.arbitration_id == 1040:
                tt = getFloat(canMsg)
            elif canMsg.arbitration_id == 1316:
                pilot_mass = getUshort(canMsg)
            elif canMsg.arbitration_id == 1506:
                enl = getUshort(canMsg)
    except Exception as e:
        print(f"CAN receive error: {e}")


# Start CAN receiver in a separate thread
threading.Thread(target=can_receive_loop, daemon=True).start()

app = Dash(__name__)

app.layout = html.Div([
    html.Div([
        dcc.Graph(id="gauge", style={'display': 'inline-block'}),
        html.Div(id="flap-display", style={
            'display': 'inline-block',
            'verticalAlign': 'middle',
            'fontSize': '48px',
            'marginLeft': '20px',
            'fontWeight': 'bold'
        }),
        html.Div(id="optimal-flap-display", style={
            'display': 'inline-block',
            'verticalAlign': 'middle',
            'fontSize': '48px',
            'marginLeft': '20px',
            'fontWeight': 'bold',
            'color': 'green'
        }),
        html.Div(id="tas-display", style={
            'display': 'inline-block',
            'verticalAlign': 'middle',
            'fontSize': '48px',
            'marginLeft': '20px',
            'fontWeight': 'bold',
            'color': 'blue'
        })
    ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'}),
    dcc.Interval(id="timer", interval=500)
])


@app.callback(
    [Output("gauge", "figure"),
     Output("flap-display", "children"),
     Output("optimal-flap-display", "children"),
     Output("tas-display", "children")],
    Input("timer", "n_intervals")
)
def update_dashboard(n):
    ias_kmh = ias * 3.6 if ias is not None else 0
    tas_kmh = tas * 3.6 if tas is not None else 0
    tas_display = f"TAS (km/h) {round(tas_kmh, 1)}"

    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(ias_kmh, 0),
        title={'text': "IAS (km/h)"},
        gauge={"axis": {"range": [50, 300]}}
    ))

    if flap is not None:
        symbol = get_flap_symbol(flap)
        flap_text = f"Flap: {symbol if symbol is not None else '??'} ({flap})"
    else:
        flap_text = "Flap: N/A"

    optimal_flap_text = "Opt: N/A"
    if ias is not None:
        total_mass = (get_empty_mass() or 0) + (pilot_mass or 0)
        opt_flap = get_optimal_flap(total_mass, ias_kmh)
        if opt_flap:
            optimal_flap_text = f"Opt: {opt_flap}"

    return fig, flap_text, optimal_flap_text, tas_display


if __name__ == '__main__':
    app.run(debug=True)
