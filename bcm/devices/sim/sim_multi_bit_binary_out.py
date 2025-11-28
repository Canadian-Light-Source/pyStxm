
from bcm.devices import report_fields
from bcm.devices.sim.sim_base_object import BaseSimObject

DO_SIM = False

class SimMbbo(BaseSimObject):
    """
    Simple mbbo input device, based on EPICS MBBO record
    16 bit multi bit binary output
    0-15 values
    16 string values
    16 output values
    """

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

        # super(Mbbo, self).__init__(base_signal_name, write_pv=base_signal_name + '.VAL', **cb_kwargs)
        super(SimMbbo, self).__init__(
            base_signal_name, write_pv=base_signal_name, **cb_kwargs
        )

        if DO_SIM:
            self.attrs = ("VAL", "OUT", "NAME", "DESC")
        else:
            self.attrs = (
                "VAL",
                "OUT",
                "NAME",
                "DESC",
                "ZRVL",
                "ONVL",
                "TWVL",
                "THVL",
                "FRVL",
                "FVVL",
                "SXVL",
                "SVVL",
                "EIVL",
                "NIVL",
                "TEVL",
                "ELVL",
                "TVVL",
                "TTVL",
                "FTVL",
                "FFVL",
                "ZRST",
                "ONST",
                "TWST",
                "THST",
                "FRST",
                "FVST",
                "SXST",
                "SVST",
                "EIST",
                "NIST",
                "TEST",
                "ELST",
                "TVST",
                "TTST",
                "FTST",
                "FFST",
            )

        self.val_flds = [
            "ZRVL",
            "ONVL",
            "TWVL",
            "THVL",
            "FRVL",
            "FVVL",
            "SXVL",
            "SVVL",
            "EIVL",
            "NIVL",
            "TEVL",
            "ELVL",
            "TVVL",
            "TTVL",
            "FTVL",
            "FFVL",
        ]
        self.str_flds = [
            "ZRST",
            "ONST",
            "TWST",
            "THST",
            "FRST",
            "FVST",
            "SXST",
            "SVST",
            "EIST",
            "NIST",
            "TEST",
            "ELST",
            "TVST",
            "TTST",
            "FTST",
            "FFST",
        ]
        self.main_dev = self.add_device(base_signal_name)
        self.changed = self.main_dev.changed
        self.on_connect = self.main_dev.on_connect
        self.is_connected = self.main_dev.is_connected

        for _attr in self.attrs:
            # sig_name = self.base_signal_name + self._delim + '%s' % _attr
            # self.add_device(sig_name, write_pv=sig_name)
            self.add_device(_attr, is_dev_attr=True)

        report_fields(self)

    def get_position(self):
        return self.get()

    def get(self, _attr=None):
        if _attr in self.devs.keys():
            return self.devs[_attr].get()
        else:
            return self.devs["VAL"].get()

    def put(self, _attr=None, val=None):
        if _attr in self.devs.keys():
            return self.devs[_attr].put(val)
        elif val is None:
            # then this is just a put without the _attr set such as 'put(val)' so treat it as such
            val = _attr
            _attr = "VAL"
            self.devs[_attr].put(val)
        elif _attr is None:
            # then they specified val= but no attr so assume VAL
            _attr = "VAL"
            self.devs[_attr].put(val)
        elif _attr not in self.attrs:
            _attr = "VAL"
            self.devs[_attr].put(val)
        else:
            print("Mbbo: put: something is not right here, cannot PUT")