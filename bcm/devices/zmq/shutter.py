"""
Created on Mar 23, 2013

@author: User
"""
import time
import math
import logging
import ctypes

from PyQt5.QtCore import QObject, Qt, pyqtSignal
import numpy as np

from bcm.devices.zmq.zmq_device import ZMQBaseDevice, make_signal_dct
from ophyd import DeviceStatus

from cls.utils.log import get_module_logger
from cls.utils.dict_utils import dct_get, dct_put
from cls.utils.enum_utils import Enum
from bcm.devices import report_fields, BACKEND
# setup module logger with a default do-nothing handler
_logger = get_module_logger(__name__)

shutter_modes = Enum("Manual", "Auto")


class DCSShutter(ZMQBaseDevice):
    """class for shutter that are accessed as daqmx device digital output bits"""

    def __init__(self, signal_name, name, openval=1, closeval=0):
        super(DCSShutter, self).__init__(signal_name, name=name, write_pv=signal_name, backend=BACKEND)
        self.ready = True
        self.reset_to_default = False
        self._open_val = int(openval)
        self._close_val = int(closeval)
        self._mode = shutter_modes.MANUAL
        self.is_open = False
        self.ctrl_enum_strs = []  # ['Auto', 'Open', 'Close', 'Auto Line']
        self.fbk_enum_strs = []  # ['CLOSED', 'OPEN']
        self.fbk_enum_values = []
        report_fields(self)

    def set_ctrl_enum_strings(self, strs: list[str]) -> None:
        """
        set the enumerated strings used as setpoints
        """
        self.ctrl_enum_strs = strs

    def set_fbk_enum_strings(self, strs: list[str]) -> None:
        """
        set the enumerated strings used as feeedbacks
        """
        self.fbk_enum_strs = strs
        self.fbk_enum_values = list(range(len(self.fbk_enum_strs)))
    def set(self, val):
        self.put(val)
        # if val == self._open_val:
        #     self.open()
        # else:
        #     self.close()
        # st = DeviceStatus(self, done=True)
        # #st._finished = True
        # st.set_finished()
        # return st

    def add_callback(self, cb):
        self.changed.connect(cb)

    def set_to_auto(self):
        self._mode = shutter_modes.AUTO

    def set_to_manual(self):
        self._mode = shutter_modes.MANUAL

    def is_auto(self):
        if self._mode == shutter_modes.AUTO:
            return True
        else:
            return False

    def is_ready(self):
        return self.ready

    def start(self):
        self.open()
        self.is_open = True

    def stop(self):
        self.close()
        self.is_open = False

    def open(self):
        # _logger.debug("opening shutter")
        # self.signal.put(self._open_val)
        self.put(self._open_val)

    def close(self):
        # _logger.debug("closing shutter")
        # self.signal.put(self._close_val)
        self.put("VAL", self._close_val)

    def get_state(self):
        return self.signal.get()

    def clear(self):
        pass

    # self.do.clear()

    def stop_and_clear(self):
        pass

    # self.stop()
    # self.clear()

    def get_report(self):
        dct = {}
        dct_put(dct, "TO-DO", "")
        return dct

    def update_position(self, value, is_moving):
        """
        Override the base class update_position
        this function is called from update_widgets() in the ZMQDevManager while it process' the queue from PIXELATOR
        """
        # print(f"ZMQBaseDevice: update_position: [{self.name}={value}]")
        value = int(value)
        self.set_readback(value)
        lower_ctrl_limit = 0
        upper_ctrl_limit = 0
        units = ''
        if hasattr(self, '_low_limit'):
            lower_ctrl_limit = self._low_limit
        if hasattr(self, '_high_limit'):
            upper_ctrl_limit = self._high_limit
        if hasattr(self, 'egu'):
            units = self.egu

        dct = make_signal_dct(value, old_val=self._old_val, lower_ctrl_limit=lower_ctrl_limit, upper_ctrl_limit=upper_ctrl_limit, units=units, prec=5, is_moving=is_moving, obj=self)
        # print(f"DCSShutter: update_position: [{self.name}] just emitted changed of a dict[{dct}]")
        self.changed.emit(dct)



if __name__ == "__main__":
    # 	#Dev1 is the 6036
    # 	#dev2 is teh 6602
    # 	dout = DaqMxShutter('Shutter','Dev1/port0/line7:0',1)
    # 	dout.close()
    # 	print 'get_state = ' , dout.get_state()
    # 	dout.open()
    # 	print 'get_state = ' , dout.get_state()
    # 	dout.close()
    # 	print 'get_state = ' , dout.get_state()
    #
    # 	#test Task interface
    # 	dout.stop()
    # 	print 'get_state = ' , dout.get_state()
    # 	dout.start()
    # 	print 'get_state = ' , dout.get_state()
    # 	dout.stop()
    # 	print 'get_state = ' , dout.get_state()
    psht = DCSShutter("uhvDIO:shutter:ctl")


# __all__ = ['Shutter', 'DaqMxShutter']
