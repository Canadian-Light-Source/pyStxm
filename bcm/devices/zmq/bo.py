
from bcm.devices.zmq.zmq_device import ZMQBaseDevice, ZMQSignal

class ZMQBo(ZMQBaseDevice):
    """
    Simple bo device

        def __init__(
        self,
        base_signal_name=None,
        write_pv=None,
        desc=None,
        egu="",
        cb=None,
        ret_kwarg="value",
        **cb_kwargs
    ):

        super(Bo, self).__init__(
            base_signal_name, write_pv=base_signal_name + ".VAL", **cb_kwargs
        )

    """
    def __init__(self, base_signal_name=None, **kwargs):
        super().__init__(base_signal_name, name=base_signal_name, **kwargs)

        self.attrs = ("VAL", "OUT", "NAME", "DESC", "ZNAM", "ONAM")
        # self.main_dev = self.add_device(base_signal_name)
        # self.changed = self.main_dev.changed
        # self.on_connect = self.main_dev.on_connect
        # self.is_connected = self.main_dev.is_connected

        for _attr in self.attrs:
            #_name = f"{base_signal_name}_{_attr.upper()}"
            setattr(self, _attr, ZMQSignal(base_signal_name, base_signal_name))

    def get_position(self):
        return self.get("VAL")

    def get(self, _attr):
        if hasattr(self, _attr):
            obj = getattr(self, _attr)
            return obj.get()

    def put(self, val=None):
        obj = getattr(self, "VAL")

        #restrict value to 0 or 1
        val = val % 2
        return obj.set(val)




