#!/usr/bin/python
from bcm.devices import BaseObject, report_fields


class Mbbi(BaseObject):
    """
    Simple mbbi input device
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
        super(Mbbi, self).__init__(base_signal_name, **cb_kwargs)

        self.attrs = (
            "VAL",
            "INP",
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
        self._delim = "."

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

    def get(self, _attr):
        if _attr in self.devs.keys():
            return self.devs[_attr].get()

    def put(self, _attr, val):
        if _attr in self.devs.keys():
            return self.devs[_attr].put(val)
