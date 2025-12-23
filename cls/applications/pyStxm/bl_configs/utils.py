import os

from bcm.devices import BaseDevice
from bcm.devices.sim.sim_base_device import BaseSimDevice


def make_basedevice(cat, sig_nm, name="YOUNEEDTOPROVIDEANAME", desc="", units="", rd_only=False, devcfg=None,
                    backend="epics"):
    dev = BaseDevice(sig_nm, name=name, desc=desc, units=units, rd_only=rd_only, backend=backend)
    return dev

def make_base_simdevice(cat, sig_nm, name="YOUNEEDTOPROVIDEANAME", desc="", units="", rd_only=False, devcfg=None,
                    backend="epics"):
    dev = BaseSimDevice(sig_nm, name=name, desc=desc, units=units, rd_only=rd_only, backend=backend)
    return dev

def get_config_name(fname):
    nm = fname.split(os.path.sep)[-1].replace(".py", "")
    return nm


