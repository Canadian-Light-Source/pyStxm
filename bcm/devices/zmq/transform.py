
from bcm.devices.zmq.zmq_device import ZMQBaseDevice, ZMQSignal

class ZMQTransform(ZMQBaseDevice):
    """
    Simple bo device
    """
    def __init__(self, dcs_name, name=None, **kwargs):
        super().__init__(dcs_name, name=name, **kwargs)

        self.attr_fmts = {"CLC%s": "CLC%s"}
        self.attrs = ["COPT", "PREC", "PINI", "DESC", "PROC"]
        self.rows = "ABCDEFGHIJKLMNOP"
        self.all_rows = [
            "A",
            "B",
            "C",
            "D",
            "E",
            "F",
            "G",
            "H",
            "I",
            "J",
            "K",
            "L",
            "M",
            "N",
            "O",
            "P",
        ]
        self._attr_keys = []
        for fmt in list(self.attr_fmts.values()):
            for let in self.rows:
                self.attrs.append(fmt % let)

        for _attr in self.attrs:
            _name = f"{dcs_name}_{_attr.upper()}"
            setattr(self, _attr, ZMQSignal(_name, _name))
            self._attr_keys.append(_attr)

    def get_position(self):
        return self.get("VAL")

    def get(self, _attr):
        if hasattr(self, _attr):
            obj = getattr(self, _attr)
            return obj.get()

    def put(self, attr_name, val=None):
        if attr_name in self._attr_keys:
            obj = getattr(self, attr_name)
            return obj.set(val)


