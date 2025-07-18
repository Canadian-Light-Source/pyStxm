
from bcm.devices.zmq.zmq_device import ZMQBaseDevice, ZMQSignal

class ZMQCommand(ZMQBaseDevice):
    """
    Simple command device

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

    """
    def __init__(self, base_signal_name=None, name=None, **kwargs):
        super().__init__(base_signal_name, name=base_signal_name, **kwargs)

        self.attrs = ("VAL", "OUT", "NAME", "DESC", "ZNAM", "ONAM")
        self.arg_keywords = kwargs.get("arg_keywords", {})

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
