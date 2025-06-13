import time
from typing import Union

from PyQt5.QtCore import pyqtSignal, QObject, QTimer


DEFAULT_CONNECTION_TIMEOUT = 10
DEFAULT_WRITE_TIMEOUT = 1


def make_signal_dct(value, old_val, lower_ctrl_limit, upper_ctrl_limit, units='', is_moving=False, prec=5, obj=None):
    mov = 0
    if is_moving:
        mov = 1
    signal_dct = {'old_value': old_val,
         'value': value,
         'timestamp': time.time(),
         'status': mov,
         'severity': 0,
         'precision': prec,
         'lower_ctrl_limit': lower_ctrl_limit,
         'upper_ctrl_limit': upper_ctrl_limit,
         'units': units,
         'sub_type': 'value',
         'obj': obj
    } # obj is the Signal object

    return signal_dct

def make_connection_dct(value, obj=None):
    connection_dct = {'value': value,
         'timestamp': time.time(),
         'status': value,
         'sub_type': 'value',
         'obj': obj
    } # obj is the Signal object

    return connection_dct

class ZMQBaseSignal(QObject):
    """
    A basic device that offers a base level ZMQ Signal interface
    """
    do_put = pyqtSignal(object)  # dict
    do_get = pyqtSignal(object)  # dict
    changed = pyqtSignal(object)  # dict (epics style)
    on_connect = pyqtSignal(object,object,object) # pvname=None,conn=None,pv=None
    def __init__(self, dcs_name, name, **kwargs):
        super().__init__(None)
        self.name = name
        # print(f"creating new ZMQBaseSignal instance of [{name}]")
        self.dcs_name = dcs_name
        self._units = ""
        self.connected = True
        self._read_pv_connection_callbacks = []
        self._readback = 0
        self._is_on = False

        if "desc" in kwargs.keys():
            self._desc = kwargs['desc']

        if "egu" in kwargs.keys():
            self._units = kwargs['egu']
        if "units" in kwargs.keys():
            self._units = kwargs['units']

    # def set_readback(self, value):
    #     """
    #     set the readback value
    #     """
    #     self._readback = value

    def set_on_off(self, value: Union[int, bool, str]):
        if isinstance(value, int):
            self._is_on = value != 0
        elif isinstance(value, bool):
            self._is_on = value
        elif isinstance(value, str):
            self._is_on = value.lower() != "off"

    def get_on_off_status(self):
        return self._is_on

    def set_connected(self, con):
        """
        set connected attribute
        """
        self.connected = con

    def is_connected(self):
        """
        todo: make this accurately reflect if the zmq device is connected or not

        """
        return self.connected

    def get_desc(self):
        if hasattr(self, "_desc"):
            return self._desc
        else:
            return self.name

    def get_units(self):
        return self._units

    def set_units(self, units):
        self._units = units

    # @doc_annotation_forwarder(Signal)
    def subscribe(self, callback, event_type=None, run=True):
        self.changed.connect(callback)

    def get(self, **kwargs):
        "Get the value from the associated attribute"
        # print(f"ZMQBaseSignal: TOFIX [{self.name}]: get: getting the value [{self._readback}]")
        # self.do_get.emit({'command': 'GET', 'name':self.name, 'dcs_name':self.dcs_name})
        return self._readback


#######################################################################################################

class ZMQSignalRO(ZMQBaseSignal):
    """
    A basic device that offers a base level ZMQ Signal interface
    """

    def __init__(self, name, dcs_name, **kwargs):
        super().__init__(name, dcs_name, **kwargs)

    def put(self, value, **kwargs):
        """Write to the associated attribute"""

        print(f"ZMQSignalRO: put: putting the value [{value}]")
        self.do_put.emit({'command': 'GET', 'name': self.name, 'dcs_name': self.dcs_name})


#######################################################################################################
class ZMQSignal(ZMQBaseSignal):
    """
    A basic device that offers a base level ZMQ Signal interface
    """
    SUB_VALUE = "user_readback"
    def __init__(self, name, dcs_name, **kwargs):
        super().__init__(name, dcs_name, **kwargs)
        self._read_pv = QObject()
        self._read_pv.connection_callbacks = []

    def set(self, value, *, timeout=DEFAULT_WRITE_TIMEOUT, settle_time=None):
        """
        Set the value of the Signal and return a Status object.

        """
        self._readback = value
        # do not send back to the DCS that a user_readback value needs to be changed
        if self.name.find('user_readback') == -1:
            nm_lst = self.name.split(':')
            dcs_name = nm_lst[0]
            if len(nm_lst) > 1:
                attr = nm_lst[1]
                print(f"ZMQSignal: set: send to ZMQ [{self.name}:PUT:{value}  attr={attr}]")
            else:
                print(f"ZMQSignal: set: send to ZMQ [{self.name}:PUT:{value}]")
                attr = None

            self.do_put.emit({'command': 'PUT', 'name': self.name, 'dcs_name': dcs_name, 'attr': attr, 'value': value})



#######################################################################################################
class ZMQBaseDevice(ZMQBaseSignal):
    """
    A basic device that offers a base level interface

    the signal emitted should mirror aan epics dict that is returned by epics callbacks

    {'old_value': 199.85000000000002,
     'value': 199.85000000000002,
     'timestamp': 1726004583.452123,
     'status': <AlarmStatus.NO_ALARM: 0>,
     'severity': <AlarmSeverity.NO_ALARM: 0>,
     'precision': 5,
     'lower_ctrl_limit': -9000.0,
     'upper_ctrl_limit': 9000.0,
     'units': 'mm',
     'sub_type': 'value',
     'obj': EpicsSignalRO(read_pv='SMTR1610-3-I12-45.RBV',
        name='SMTR1610-3-I12-45',
        parent='SMTR1610-3-I12-45',
        value=199.85000000000002,
        timestamp=1726004583.452123,
        auto_monitor=True,
        string=False)}


    """

    def __init__(self, dcs_name, name=None, **kwargs):
        super().__init__(name, dcs_name, kwargs=kwargs)
        self.name = name
        if name == None:
            self.name = dcs_name
        else:
            self.name = name
        self.dcs_name = dcs_name
        self._user_readback = 0
        self._user_setpoint = 0
        self.is_moving = False
        self._old_val = 0
        self._old_is_moving = 0
        self._egu = ""
        self.val_only = 0
        self._positioner_dct = {}
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._init_feedback)

        if "desc" in kwargs.keys():
            self._desc = kwargs['desc']

        if "egu" in kwargs.keys():
            self._egu = kwargs['egu']

    def set_readback(self, value):
        """
        set the _user_readback value
        """
        self._user_readback = value
        self._readback = value

    def set_connected(self, con):
        """
        set connected attribute
        """
        #call base class set_connected
        super().set_connected(con)

        dct = make_connection_dct(con, obj=self)
        #self.on_connect.emit(dct)
        self.on_connect.emit(None, con, self) # pvname=None,conn=con,pv=self
        #start singleshot timer to init the feedback
        self._timer.start(100)

    def _init_feedback(self):
        # print(f"_init_feedback: {self.name}")
        self.update_position(self.get_position(), is_moving=False)
    def get_position(self):
        return self._user_readback
    def get_ophyd_device(self):
        return self
    def get_name(self):
        return self.name
    def get_dcs_name(self):
        return self.dcs_name
    def set_desc(self, desc):
        self._desc = desc
    def get_desc(self):
        if hasattr(self, "_desc"):
            return self._desc
        else:
            return self.name

    def set_units(self, unit):
        # pyStxm should not be setting units, it should be set by the DCS server
        #self._egu = unit
        pass

    def get_egu(self):
        if len(self._egu) == 0 or self._egu is None:
            val = self.get_positioner_dct_value('unit')
            if val is None:
                self._egu = ""
            else:
                self._egu = val
        return self._egu

    def get_units(self):
        return self.get_egu()

    def set_positioner_dct(self, dct):
        """
        set the positioner dct that was given by the DCS server when connection to the DCS server was initialized
        """
        self._positioner_dct = dct

    def get_positioner_dct_value(self, key):
        """
        get the value from the positioner dct
        :param key: the key to get from the positioner dct
        :return: the value from the positioner dct
        """
        if key in self._positioner_dct.keys():
            return self._positioner_dct[key]
        return None

    def update_device_status(self, value):
        """
        this function is called from update_widgets() in the ZMQDevManager while it process' the queue from PIXELATOR
        """
        # print(f"ZMQBaseDevice: update_status: [{self.name}={value}]")
        self.set_on_off(value)

    def update_position(self, value, is_moving=False):
        """
        this function is called from update_widgets() in the ZMQDevManager while it process' the queue from PIXELATOR
        """
        # print(f"ZMQBaseDevice: update_position: [{self.name}={value}]")
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

        if hasattr(self, 'enums'):
            if value > len(self.enums):
                #make zero based
                value = len(self.enums) -1

        if hasattr(self, 'enum_values'):
            # turn the value sent by the DCS server into an index to the enumerations and set value to the integer index
            # the attribute enum_value_to_idx_dct was created uin device_loader.py when the device was created, the
            # devs.py definitions for this device specified values and enumerations
            if value in self.enum_value_to_idx_dct.keys():
                value = self.enum_value_to_idx_dct[value]


        dct = make_signal_dct(value, old_val=self._old_val, lower_ctrl_limit=lower_ctrl_limit, upper_ctrl_limit=upper_ctrl_limit, units=units, prec=5, is_moving=is_moving, obj=self)
        # print(f"ZMQBaseDevice: update_position: [{self.name}] just emitted changed of a dict[{dct}]")
        self.changed.emit(dct)
        self._old_val = value
        #if this is the motor record then set our ZMQSignal attribute so that its changed signal will fire

        if hasattr(self, 'user_readback'):
            self.user_readback._readback = value
            # print(f"ZMQBaseDevice: update_position: [{self.name}.user_readback] just emitted changed of a dict[{dct}]")
            self.user_readback.changed.emit(dct)

        # check also for a device with _user_readback
        if hasattr(self, '_user_readback'):
            self._user_readback = value

        if hasattr(self, 'motor_done_move'):
            #remember this is for DONE moving so invert it
            value = False if is_moving else True
            dct = make_signal_dct(value, old_val=self._old_is_moving, lower_ctrl_limit=lower_ctrl_limit,
                                  upper_ctrl_limit=upper_ctrl_limit, units=units, prec=5, is_moving=is_moving, obj=self)
            self.motor_done_move.changed.emit(dct)
            self._old_is_moving = is_moving

    # def get(self):
    #     return self._user_readback


    def get(self, **kwargs):
        "Get the value from the associated attribute"
        #print(f"ZMQBaseDevice: [{self.name}]: get: getting the value [{self._readback}]")
        #self.do_get.emit({'command': 'GET', 'name':self.name, 'dcs_name':self.dcs_name})
        return self._readback

    def set(self, attr="user_setpoint", value=None):
        self._user_setpoint = value
        self.put(attr, value)

    def put(self, attr, value=None):
        """
        for backward compatability
        """
        if value == None:
            # no attr specified so assume its the setpoint and also assign trhe readback because this may only be an
            # app device meaning there is no corresponding DCS server devices
            value = attr
            self._user_setpoint = value
            self.update_position(value, False)
            #print(f"ZMQBaseDevice: put: [{self.name}] needs to send to ZMQ [{self.name}:PUT:{value}]")
            self.do_put.emit({'command': 'PUT', 'name': self.name, 'dcs_name': self.dcs_name, 'attr':'', 'value': value})
        else:
            #print(f"ZMQBaseDevice: put: [{self.name}] needs to send to ZMQ [{self.name}->{attr}:PUT:{value}]")
            self.do_put.emit({'command': 'PUT', 'name': self.name, 'dcs_name': self.dcs_name, 'attr': attr, 'value': value})

    def set_return_val_only(self, val):
        """

        :param val:
        :return:
        """
        self.val_only = val

    def send_dcs_command(self, dct):
        """
        accept a dict comprised of a dict, example:{'command': 'STOP', 'value': 1} and emit it so that the zmq Dev
        manager will send it to the DCS
        """
        self.do_put.emit(dct)

    def unstage(self):
        return True



if __name__ == "__main__":
    import sys
    from PyQt5 import QtWidgets, QtCore

    def mycallback(kwargs):
        print(kwargs)

    app = QtWidgets.QApplication(sys.argv)
    t = Bo("BL1610-I10:ENERGY:uhv:enabled", val_only=False, val_kw="value")
    t.get("VAL")
    t.changed.connect(mycallback)

    sys.exit(app.exec_())
