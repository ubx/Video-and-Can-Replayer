import argparse
import struct
import threading
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict

import can
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go

from flaputils import get_flap_symbol, get_optimal_flap, get_empty_mass

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CAN_SFF_MASK = 0x000007FF

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

ID_MAP = {v: k for k, v in CAN_IDS.items()}


@dataclass
class FlightData:
    lock: threading.Lock = field(default_factory=threading.Lock)
    ias: Optional[float] = None
    tas: Optional[float] = None
    cas: Optional[float] = None
    alt: Optional[float] = None
    vario: Optional[float] = None
    flap: Optional[int] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    gs: Optional[float] = None
    tt: Optional[float] = None
    pilot_mass: float = 0
    enl: Optional[int] = None

    def update(self, key: str, value: any):
        with self.lock:
            setattr(self, key, value)

    def get_snapshot(self) -> Dict:
        with self.lock:
            return {
                'ias': self.ias,
                'tas': self.tas,
                'cas': self.cas,
                'alt': self.alt,
                'vario': self.vario,
                'flap': self.flap,
                'lat': self.lat,
                'lon': self.lon,
                'gs': self.gs,
                'tt': self.tt,
                'pilot_mass': self.pilot_mass,
                'enl': self.enl
            }


class CANReceiver:
    def __init__(self, channel: str, flight_data: FlightData):
        self.channel = channel
        self.flight_data = flight_data
        self.bus = None
        self.thread = None
        self.running = False

    def start(self):
        try:
            self.bus = can.interface.Bus(channel=self.channel, interface='socketcan')
            self.bus.set_filters([{"can_id": can_id, "can_mask": CAN_SFF_MASK} for can_id in CAN_IDS.keys()])
            self.running = True
            self.thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.thread.start()
            logger.info(f"CAN Receiver started on {self.channel}")
        except Exception as e:
            logger.error(f"Failed to start CAN bus on {self.channel}: {e}")

    def _receive_loop(self):
        while self.running:
            try:
                can_msg = self.bus.recv(timeout=1.0)
                if can_msg is None:
                    continue

                arb_id = can_msg.arbitration_id
                if arb_id not in CAN_IDS:
                    logger.debug(f"Unknown ID {arb_id}: {can_msg.data.hex()}")
                    continue

                name = CAN_IDS[arb_id]
                if name == 'utc':
                    pass
                elif name in ['ias', 'tas', 'cas', 'alt', 'vario', 'gs', 'tt']:
                    self.flight_data.update(name, self._get_float(can_msg))
                elif name in ['lat', 'lon']:
                    self.flight_data.update(name, self._get_double_l(can_msg))
                elif name == 'flap':
                    self.flight_data.update(name, self._get_char(can_msg))
                elif name in ['pilot_mass', 'enl']:
                    self.flight_data.update(name, self._get_ushort(can_msg))

            except Exception as e:
                logger.error(f"Error in CAN receive loop: {e}")

    @staticmethod
    def _get_float(can_msg):
        return struct.unpack('>f', can_msg.data[4:8])[0]

    @staticmethod
    def _get_double_l(can_msg):
        return struct.unpack('>l', can_msg.data[4:8])[0] / 1E7

    @staticmethod
    def _get_ushort(can_msg):
        return struct.unpack('>H', can_msg.data[4:6])[0]

    @staticmethod
    def _get_char(can_msg):
        return struct.unpack('B', can_msg.data[4:5])[0]


# Main initialization
parser = argparse.ArgumentParser(description='Read position updates from can-bus and print it')
parser.add_argument('-channel', metavar='channel', type=str, default='can0', help='Canbus, default=can0')
args = parser.parse_args()

flight_state = FlightData()
receiver = CANReceiver(args.channel, flight_state)
receiver.start()

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
    data = flight_state.get_snapshot()
    ias = data['ias']
    tas = data['tas']
    flap = data['flap']
    pilot_mass = data['pilot_mass']

    ias_kmh = ias * 3.6 if ias is not None else 0
    tas_kmh = tas * 3.6 if tas is not None else 0
    tas_display = f"TAS (km/h) {round(tas_kmh, 1)}"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(ias_kmh, 0),
        title={'text': "IAS (km/h)"},
        gauge={"axis": {"range": [30, 300]}}
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
