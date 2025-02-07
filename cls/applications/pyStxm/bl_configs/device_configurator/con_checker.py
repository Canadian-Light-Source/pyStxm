from epics._version import get_versions

__version__ = get_versions()["version"]
del get_versions

__doc__ = """
   Epics Channel Access Python module

   version: %s
   Principal Authors:
      Matthew Newville <newville@cars.uchicago.edu> CARS, University of Chicago
      Ken Lauer, David Chabot, Angus Gratton

== License:
   Except where explicitly noted, this file and all files in this distribution
   are licensed under the Epics Open License See LICENSE in the top-level
   directory of this distribution.

== Overview:
   Python Interface to the Epics Channel Access protocol of the Epics control system.

""" % (
    __version__
)


import time
import sys
import threading
from epics import ca
from epics import dbr
from epics import pv
from epics import alarm
from epics import device
from epics import motor
from epics import multiproc


PV = pv.PV
Alarm = alarm.Alarm
Motor = motor.Motor
Device = device.Device
poll = ca.poll

get_pv = pv.get_pv

CAProcess = multiproc.CAProcess
CAPool = multiproc.CAPool

# some constants
NO_ALARM = 0
MINOR_ALARM = 1
MAJOR_ALARM = 2
INVALID_ALARM = 3

_PVmonitors_ = {}


def con_check_many(
    pvlist,
    as_string=False,
    as_numpy=True,
    count=None,
    timeout=1.0,
    connection_timeout=5.0,
    conn_timeout=None,
):
    """caget_many(pvlist, as_string=False, as_numpy=True, count=None,
                 timeout=1.0, connection_timeout=5.0, conn_timeout=None)
    get values for a list of PVs, working as fast as possible

    Arguments
    ---------
     pvlist (list):        list of pv names to fetch
     as_string (bool):     whether to get values as strings [False]
     as_numpy (bool):      whether to get values as numpy arrys [True]
     count  (int or None): max number of elements to get [None]
     timeout (float):      timeout on *each* get()  [1.0]
     connection_timeout (float): timeout for *all* pvs to connect [5.0]
     conn_timeout (float):  back-compat alias or connection_timeout

    Returns
    --------
      list of values, with `None` signifying 'not connected' or 'timed out'.

    Notes
    ------
       this does not cache PV objects.

    """
    chids, connected, out = [], [], []
    for name in pvlist:
        chids.append(ca.create_channel(name, auto_cb=False, connect=False))

    all_connected = False
    if conn_timeout is not None:
        connection_timeout = conn_timeout
    expire_time = time.time() + connection_timeout
    while not all_connected and (time.time() < expire_time):
        connected = [dbr.CS_CONN == ca.state(chid) for chid in chids]
        all_connected = all(connected)
        poll()

    # for (chid, conn) in zip(chids, connected):
    #     if conn:
    #         ca.get(chid, count=count, as_string=as_string, as_numpy=as_numpy,
    #                wait=False)
    #
    # poll()
    # for (chid, conn) in zip(chids, connected):
    #     val = None
    #     if conn:
    #         val = ca.get_complete(chid, count=count, as_string=as_string,
    #                               as_numpy=as_numpy, timeout=timeout)
    #     out.append(val)
    # return out
    return connected
