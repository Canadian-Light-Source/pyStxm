from event_model import RunRouter
from suitcase.csv import Serializer
from bluesky import RunEngine
from databroker import Broker
from ophyd.sim import det1, det2, motor
from bluesky.plans import count, scan


def factory(name, start_doc):

    serializer = Serializer("C:/controls/sandbox/pyStxm3/cls/data_io/tests")
    # serializer(start_doc)

    return [serializer], []


db = Broker.named("pystxm_amb_bl10ID1")

RE = RunEngine({})

# Insert all metadata/data captured into db.
RE.subscribe(db.insert)

rr = RunRouter([factory])

dets = [det1, det2]

RE.subscribe(rr)
RE(scan(dets, motor, -1, 1, 10))
