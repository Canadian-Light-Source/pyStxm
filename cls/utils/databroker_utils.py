import os

# Set up a RunEngine and use metadata backed by a sqlite file.
from bluesky import RunEngine
from bluesky.utils import get_history

RE = RunEngine(get_history())

# Set up a Broker.
from databroker import Broker

db = Broker.named("pystxm_amb_bl10ID1")

# and subscribe it to the RunEngine
RE.subscribe(db.insert)

# 203e8664-ef19-496f-b214-07226037b6dc
