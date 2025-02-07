# NOTE: this device assumes that the waveform has already been programmed into the generator on the E712
import time

from ophyd import Component as Cpt, EpicsSignal, Device
from ophyd.status import DeviceStatus, SubscriptionStatus

class E712WGDevice(Device):
    run = Cpt(EpicsSignal, "ExecWavgen", kind="omitted", put_complete=True)
    num_cycles = Cpt(EpicsSignal, "NumCycles", kind="omitted", put_complete=True)

    def __init__(self, prefix, name):
        super(E712WGDevice, self).__init__(prefix, name=name)

    def report(self):
        print("name = %s, type = %s" % (str(self.__class__), self.name))

    def trigger(self):

        def check_value(*, old_value, value, **kwargs):
            "Return True when the acquisition is complete, False otherwise."
            #print(f"E712WGDevice: trigger: old_value={old_value} value={value}")
            return (old_value == 0 and value == 1)

        status = SubscriptionStatus(self.run, check_value, settle_time=10.0)

        self.run.put(1, wait=True)

        return status

    def unstage(self):
        st = super().unstage()
        self.run.put(0)
        return st

