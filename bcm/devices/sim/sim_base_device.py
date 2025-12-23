import sys
import time as ttime

from PyQt5 import QtWidgets, QtCore

from ophyd.device import (
    Component,
    Device,
)

from ophyd.utils.epics_pvs import data_shape, data_type
from ophyd.ophydobj import Kind
from ophyd.signal import Signal
from bcm.devices.dev_categories import dev_categories
from bcm.devices import report_fields, BACKEND
from bcm.devices.ophyd.ophyd_qt_dev import OphydQt_AIDevice, OphydQt_NodeDevice

from cls.utils.log import get_module_logger

_logger = get_module_logger(__name__)

PREC = 3
SIMULATE = False


class SimSignal(Signal):
    def __init__(
        self,
        *,
        name,
        value=0.0,
        timestamp=None,
        parent=None,
        labels=None,
        kind=Kind.omitted,
        tolerance=0.001,
        rtolerance=None,
        metadata=None,
        cl=None,
        attr_name="",
    ):
        super().__init__(
            name=name,
            value=value,
            timestamp=timestamp,
            parent=parent,
            kind=kind,
            labels=labels,
            tolerance=tolerance,
            rtolerance=rtolerance,
            metadata=metadata,
            cl=cl,
            attr_name=attr_name,
        )

    def set_enable(self, en):
        """Use this attribute to allow the read() top ignore this Signal if the user has bnot asked to use this ROI."""
        if en:
            self.kind = Kind.normal
        else:
            self.kind = Kind.omitted

    def read(self) -> dict:
        """Put the status of the signal into a simple dictionary format for data acquisition."""
        value = self.get()
        self._readback = value
        return {self.name: {"value": value, "timestamp": ttime.time()}}

    def describe(self):
        """
        Provide schema and meta-data for :meth:`~BlueskyInterface.read`.

        This keys in the `OrderedDict` this method returns must match the
        keys in the `OrderedDict` return by :meth:`~BlueskyInterface.read`.

        This provides schema related information, (ex shape, dtype), the
        source (ex PV name), and if available, units, limits, precision etc.

        Returns
        -------
        data_keys : OrderedDict
            The keys must be strings and the values must be dict-like
            with the ``event_model.event_descriptor.data_key`` schema.

        """
        value = self.get()
        return {
            self.name: {
                "source": f"{self.attr_name}",
                "dtype": data_type(value),
                "shape": data_shape(value),
                "precision": PREC,
            },
        }



class BaseSimDevice(Device, QtCore.QObject):
    changed = QtCore.pyqtSignal(object)
    on_connect = QtCore.pyqtSignal(object)

    def __init__(
        self,
        sig_name,
        name=None,
        write_pv=None,
        rd_only=False,
        val_only=False,
        val_kw="value",
        backend=BACKEND,
        wait_for_conn_timeout=0,
        **kwargs
    ):
        super(BaseSimDevice, self).__init__(name=name, prefix=sig_name)
        # name here for compatability
        self.dcs_name = sig_name
        self.name = name
        # name here for compatability
        self.prefix = sig_name

        self.sig_name = sig_name
        self.rd_only = rd_only
        self.can_write = True
        self._ophyd_dev = None
        self._prev_val = None
        self._num_since_update = 0
        self.write_pv = None

        if "units" in kwargs.keys():
            self._units = kwargs["units"]
        else:
            self._units = "counts"

        if "desc" in kwargs.keys():
            self._desc = kwargs["desc"]
        else:
            self._desc = self.name

        if rd_only:
            self.can_write = False

        self._ophyd_dev = None

        if (write_pv is None) and self.can_write:
            self.write_pv = sig_name
        else:
            self.write_pv = write_pv


        self._attrs = {}
        for kw in kwargs:
            self._attrs[kw] = kwargs[kw]

        self.backend = backend
        self.val_only = val_only
        self.val_kw = val_kw
        self.val_kw_exists = True
        self.info = dict(called=False)

        self.signal = SimSignal(name=sig_name)

        if wait_for_conn_timeout > 0:
            self.signal.wait_for_connection(timeout=wait_for_conn_timeout)

        self.signal.subscribe(
            self._sub_fired, run=False, event_type=self.signal.SUB_VALUE
        )

        report_fields(self)

    def connected(self):
        return True

    def get_ophyd_device(self):
        return self._ophyd_dev

    def add_callback(self, func, **kwargs):
        self.signal.subscribe(func, run=False, event_type=self.signal.SUB_VALUE)

    def on_connection(self, pvname, conn, pv):
        if conn:
            # print('BaseDevice: [%s] is connected' % pvname)
            self.on_connect.emit(self)
        else:
            # print('BaseDevice: [%s] is not connected' % pvname)
            pass

    def is_connected(self):
        return self.connected()

    def set_can_write(self, val):
        """

        :param val:
        :return:
        """
        self.can_write = val

    def set_return_val_only(self, val):
        """

        :param val:
        :return:
        """
        self.val_only = val

    def get_name(self):
        return self.sig_name

    def get_position(self):
        return self.get()

    def report(self):
        """return a dict that reresents all of the settings for this device"""
        print("name = %s, type = %s" % (str(self.__class__), self.name))

    def get_report(self):
        """return a dict that reresents all
        of the settings for this device

        To be implemented by the inheriting class
        """
        dct = {}
        return dct

    def get_desc(self):
        if hasattr(self, "_desc"):
            return self._desc
        else:
            return self.get_name()

    def get_egu(self):
        return self.egu

    def get_low_limit(self):
        """
        can be overridded by inheriting class
        :return:
        """
        return None

    def get_high_limit(self):
        """
        can be overridded by inheriting class
        :return:
        """
        return None

    def get_enum_str(self):
        """
        can be overridded by inheriting class
        :return:
        """
        print("get_enum_str: NEED TO IMPLEMENT THIS")
        return []

    def get_enum_str_as_int(self):
        """

        :return:
        """
        # val = self.pv.get()
        # if (type(val) is int):
        #     final = val
        # else:
        #     final = int(self.pv.enum_strs[val])
        # return (final)
        print("get_enum_str_as_int: NEED TO IMPLEMENT THIS")
        return []

    def put(self, val, wait=False):
        if self.can_write:
            if SIMULATE:
                print("simulating a put of:  ", self.get_name(), val)
            else:
                if self.signal.connected:
                    self.signal.put(val)

    def get(self, fld="VAL"):
        # _logger.debug('GET: [%s]' % self.get_name())
        return self.signal.get()

    def get_array(self):
        return self.signal.get(as_numpy=True)

    def _sub_fired(self, **kwargs):
        """
        kwargs={'old_value': 5529854,
         'value': 5529855,
         'timestamp': 1547055932.448674,
         'sub_type': 'value',
         'obj': EpicsSignal(read_pv='TRG2400:cycles', name='TRG2400:cycles', value=5529855, timestamp=1547055932.448674,
                pv_kw={}, auto_monitor=False, string=False, write_pv='TRG2400:cycles', limits=False, put_complete=False)}
        :param kwargs:
        :return:
        """
        self.info["called"] = True
        self.info["kw"] = kwargs
        if self.val_only:
            if self.val_kw_exists:
                if self.val_kw in kwargs.keys():
                    # print(kwargs)
                    # self._num_since_update = 0
                    val = kwargs[self.val_kw]
                    if val != self._prev_val:
                        self.changed.emit(kwargs[self.val_kw])
                    else:
                        print("Skipping changed sig [%d]" % self._num_since_update)
                        self._num_since_update += 1
                    self._prev_val = kwargs[self.val_kw]
                else:
                    self.val_kw_exists = False

        else:
            # entire dict
            self.changed.emit(kwargs)

    def read(self):
        """
        provide the o
        """


if __name__ == "__main__":
    # from .base_object import BaseObject

    def mycallback(kwargs):
        print(f"mycallback: received: {kwargs}")

    app = QtWidgets.QApplication(sys.argv)
    sv = BaseSimDevice("uhvCI:counter:Waveform_RBV", name="counter0")
    sv.changed.connect(mycallback)
    print(sv.info)
    print(sv.get())
    sv.put(1234.567)
    print(sv.get())

    sys.exit(app.exec_())
