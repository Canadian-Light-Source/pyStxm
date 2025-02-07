
from bcm.devices.zmq.zmq_device import ZMQBaseDevice, ZMQSignal
class ZMQMBBo(ZMQBaseDevice):
    """
    Simple bo device
    """
    def __init__(self, base_signal_name=None, **kwargs):
        super().__init__(base_signal_name, name=base_signal_name, **kwargs)

        self.attrs = ("VAL","OUT","NAME","DESC","ZRVL","ONVL","TWVL","THVL","FRVL",
            "FVVL","SXVL","SVVL","EIVL","NIVL","TEVL","ELVL","TVVL","TTVL","FTVL",
            "FFVL","ZRST","ONST","TWST","THST","FRST","FVST","SXST","SVST","EIST",
            "NIST","TEST","ELST","TVST","TTST","FTST","FFST" )
        # self.main_dev = self.add_device(base_signal_name)
        # self.changed = self.main_dev.changed
        # self.on_connect = self.main_dev.on_connect
        # self.is_connected = self.main_dev.is_connected

        for _attr in self.attrs:
            _name = f"{base_signal_name}_{_attr.upper()}"
            setattr(self, _attr, ZMQSignal(_name, _name))

    def get_position(self):
        return self.get("VAL")

    def get(self, _attr):
        if hasattr(self, _attr):
            obj = getattr(self, _attr)
            return obj.get()

    def put(self, val=None):
        obj = getattr(self, "VAL")
        # restrict value to 0 thru 7
        val = val % 7
        return obj.set(val)

