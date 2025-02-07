import os

from bcm.devices import BaseDevice


def make_basedevice(cat, sig_nm, name="YOUNEEDTOPROVIDEANAME", desc="", units="", rd_only=False, devcfg=None, backend="epics"):
    # RUSS FEB25 devcfg.msg_splash("connecting to %s: [%s]" % (cat, nm))
    dev = BaseDevice(sig_nm, name=name, desc=desc, units=units, rd_only=rd_only, backend=backend)
    return dev

def get_config_name(fname):
    nm = fname.split(os.path.sep)[-1].replace(".py", "")
    return nm


