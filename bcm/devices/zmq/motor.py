from PyQt5.QtCore import Qt
from bcm.devices.zmq.zmq_device import ZMQBaseDevice, ZMQSignal
from bcm.devices.zmq.pixelator.positioner_defines import MAX_DELTA_FINE_RANGE_UM
from cls.utils.roi_dict_defs import *

DEFAULT_CONNECTION_TIMEOUT = 10
DEFAULT_WRITE_TIMEOUT = 1

spmg_enumerations = {"Stop": 0, "Pause": 1, "Move": 2, "Go": 3}

class motor_msta(object):
    """
    a class that takes the integer value of the .MSTA EPICS motor field and sets the correct attribute fields
    accordingly
    """

    def __init__(self, msta):
        self.msta_fields = {}
        self.msta_fields["minus_ls"] = {"bit": 13, "val": False}  # minus limit switch
        self.msta_fields["comm_err"] = {"bit": 12, "val": False}  # communications error
        self.msta_fields["gain_support"] = {
            "bit": 11,
            "val": False,
        }  # gain support, the motor supports closed loop position control
        self.msta_fields["moving"] = {
            "bit": 10,
            "val": False,
        }  # non zero velocity present
        self.msta_fields["problem"] = {
            "bit": 9,
            "val": False,
        }  # motor driver stopped polling
        self.msta_fields["present"] = {"bit": 8, "val": False}  # encoder is present
        self.msta_fields["home"] = {"bit": 7, "val": False}  # if motor is at home
        self.msta_fields["position"] = {
            "bit": 5,
            "val": False,
        }  # closed loop position control enabled
        self.msta_fields["homels"] = {
            "bit": 3,
            "val": False,
        }  # state of home limit switch
        self.msta_fields["plus_ls"] = {"bit": 2, "val": False}  # plus limit switch
        self.msta_fields["done"] = {"bit": 1, "val": False}  # motion is complete
        self.msta_fields["direction"] = {
            "bit": 0,
            "val": False,
        }  # last raw (0: neg,  1:pos)

        self.set_msta(int(msta))

    def _set_bool(self, bit, msta):
        """
        if the shifted bit is a 1 then True else False
        :param bit:
        :param val:
        :return:
        """
        if msta & (1 << bit):
            return True
        else:
            return False

    def set_msta(self, msta):
        self._msta = msta
        for k, v_dct in self.msta_fields.items():
            v_dct["val"] = self._set_bool(v_dct["bit"], msta)


class ZMQMotor(ZMQBaseDevice):
    """
    A basic device that offers a positioner interface
    """

    def __init__(self, dcs_name, name, **kwargs):
        super().__init__(name, dcs_name, **kwargs)
        self._low_limit = -10000
        self._high_limit = 10000
        self._spmg_enum = 0
        self._at_low_limit_val = False
        self._at_high_limit_val = False
        self._velocity = 0
        self._acceleration = 0
        self.position = 0

        if 'low_limit' in kwargs.keys():
            self._low_limit = kwargs['low_limit']
        if 'high_limit' in kwargs.keys():
            self._high_limit = kwargs['high_limit']

        self.attrs = ['low_limit_val','high_limit_val', 'motor_done_move',
                     'spmg_enum', 'at_low_limit_val', 'at_high_limit_val',
                     'user_readback', 'user_setpoint', 'velocity', 'acceleration',
                     'max_velo']

        for _attr in self.attrs:
            # use a colon to separate prefix from attribute
            _name = f"{dcs_name}:{_attr}"
            setattr(self, _attr, ZMQSignal(_name, _name))

        if "ignore_msta" not in kwargs.keys():
            #self.msta_dct = motor_msta(self.ctrlr_status.get())
            self.msta_dct = motor_msta(0)

        # force this for now: Todo: figure out how to set connected based on actual information about zmq socket
        self.connected = True
        self.set_low_limit(self._low_limit)
        self.set_high_limit(self._high_limit)
        self.spmg_enum.set(spmg_enumerations['Go'])

    def calc_scan_range(self, roi):
        """
        take an roi dict and return min max of the range
        """
        min = roi[START]
        max = roi[STOP]
        return(min, max)

    def do_position_check(self, mtr, setpoint):
        """
        take a motor and check to see if its feedback position is within a deadband of the setpoint
        """
        import math
        fbk = mtr.user_readback.get()
        if math.fabs(fbk - setpoint) > 5.0:
            return False
        else:
            return True

    def is_fine_already_near_center(self, center):
        """
        check to see if the fine motor is already near the given center of position, and near the middle of its voltage range
        """
        pos_chk = self.do_position_check(self._fine_mtr, center)
        volt_chk = self.do_voltage_check()
        if pos_chk and volt_chk:
            return(True)
        else:
            return(False)

    def is_fine_in_range(self, roi):
        """
        This function makes the assumption that the abstract motor is at the center of the previous scan
        given a roi dict determine if the fine motor is currently in range to perform the scan given in the roi
        """
        nr_cntr = self.is_fine_already_near_center(roi[CENTER])
        smin_in_range = False
        smax_in_range = False
        smin, smax = self.calc_scan_range(roi)
        fbk = self._fine_mtr.user_readback.get()
        # now calc max range from current center
        cmin = fbk - MAX_DELTA_FINE_RANGE_UM
        cmax = fbk + MAX_DELTA_FINE_RANGE_UM
        # if it is then check to see if the scan range will work
        if smin > cmin:
            smin_in_range = True
        if smax < cmax:
            smax_in_range = True

        return (smin_in_range and smax_in_range)

    def set_piezo_power_on(self):
        """
        stubbed in for scan support
        """
        pass

    def get_name(self):
        return self.name

    def set_readback(self, value):
        """
        set the _user_readback value
        position is here for backward compatibility
        """
        self._user_readback = value
        self.position = value
        self.user_readback.set(self._user_readback)

    def set_low_limit(self, val):
        self._low_limit = val
        self.low_limit_val.set(self._low_limit)

    def set_high_limit(self, val):
        self._high_limit = val
        self.high_limit_val.set(self._high_limit)

    def get(self, attr_name=None):
        if attr_name is None:
            return self.get_position()

        line_attr_name = f"_{attr_name}"
        if hasattr(self, line_attr_name):
            a = getattr(self, line_attr_name)
            return a
        elif hasattr(self, attr_name):
            a = getattr(self, attr_name)
            return a.get()
        return None

    def get_position(self):
        #self.do_get.emit({'command': 'GET', 'name':self.name, 'dcs_name':self.dcs_name})
        # self.position = self.get('user_readback')
        # return self.position
        return self._user_readback

    def add_callback(self, attr, func, **kwargs):
        """
        attach the attributes .changed to the callback
        """
        if hasattr(self, attr):
            dev = getattr(self, attr)
            dev.changed.connect(func, Qt.QueuedConnection)
            #dev.subscribe(func, **kwargs)
        else:
            print("ZMQMotor: add_callback: ERROR! [%s] does not exist" % attr)

    def on_connection(self, pvname, conn, pv):
        if conn:
            # print('BaseDevice: [%s] is connected' % pvname)
            self.on_connect.emit(self)
        else:
            # print('BaseDevice: [%s] is not connected' % pvname)
            pass

    def is_connected(self):
        return self.connected
    def _make_attr_signal(self, attr_name):
        value = ZMQSignal(attr_name, attr_name)
        setattr(self, attr_name, value)


    def update_msta(self, controller_status):
        self.msta_dct = motor_msta(controller_status)

    def move(self, value, wait=False):
        if hasattr(self, 'enums'):
            if hasattr(self, 'enum_values'):
                #the dev definition has specified alternate enumerated values
                # the passed in value is an index
                value = self.enum_values[value]
            elif value > len(self.enums):
                value = len(self.enums)
        self.set('user_setpoint', value)

    def get_low_limit(self):
        # if self.connected:
        #     return self.low_limit_val.get()
        # else:
        #     # print('get_low_limit: motor [%s] not connected' % self.get_name())
        #     # return (None)
        #     # try anyway
        #     # return self.low_limit_val.get()
        return  self._low_limit

    def get_high_limit(self):
        # if self.connected:
        #     return self.high_limit_val.get()
        # else:
        #     # print('get_high_limit: motor [%s] not connected' % self.get_name())
        #     # return(None)
        #     # try anyway
        #     # return self.high_limit_val.get()
        return self._high_limit


    def is_hard_stopped(self):
        # return self.spmg_enum.get() == 0
        return False

    def at_low_limit(self):
        if self.at_low_limit_val.connected:
            return self.at_low_limit_val.get() != 0

    def at_high_limit(self):
        if self.at_high_limit_val.connected:
            return self.at_high_limit_val.get() != 0

    def stop(self):
        """
        send a stop command over ZMQ to pixelator

        """
        self.send_dcs_command({'command': 'STOP', 'dev_name': self.dcs_name, 'value': 1})

    def get_max_velo(self):
        """
        return max velocity
        """
        vmax = self.max_velo.get()
        if vmax == 0.0:
            vmax = self.velocity.get()
        return vmax

    def check_scan_limits(self, start, stop):
        """
        check the start stop values against current soft limits
        return False if beyond else True if they are reachable
        """
        if start <= self.get_low_limit():
            return(False)
        if stop >= self.get_high_limit():
            return(False)
        return(True)

    def set_power(self, val):
        """
        here for compatibility
        """
        pass

    def set_piezo_power_off(self):
        """
        here for compatibility
        """
        pass

    def do_voltage_check(self):
        """
        here for compatibility
        """
        return True

    def do_autozero(self):
        """
        here for compatibility
        """
        return True

    def do_interferometer_check(self):
        """
        here for compatibility
        """
        return True

    def move_coarse_to_scan_start(self, start=0.0, stop=0.0, npts=1, dwell=1.0, start_in_center=False, line_scan=True):
        """
        here for compatibility
        """
        return True

    def move_coarse_to_position(self, pos, do_interfer_reset=False):
        """
        here for compatibility
        """
        return True
    
    def move_fine_to_coarse_fbk_pos(self):
        """
        here for compatibility
        """
        pass

    def within_limits(self, val):
        """ returns whether a value for a motor is within drive limits with dial=True
        dial limits are used (default is user limits)

        """
        return (val <= self.get_high_limit() and val >= self.get_low_limit())

    def confirm_stopped(self):
        print("ZMQMotor: confirm_stopped: NOT IMPLEMENTED YET")
        pass


    def set_position(self, position, dial=False, step=False, raw=False):
        """
        set the motor position
        """
        print(f"ZMQMotor: set_position: setting position to {position} NOT IMPLEMENTED YET")
        pass

    def move_and_zero(self, pos):
        self.move(pos)
        # print 'waiting for %s to stop' % self.signal_name
        self.confirm_stopped()
        # print '%s has now stopped' % self.signal_name
        self.set_position(0.0)
        # print '%s setting zero' % self.signal_name

    def wait_for_stopped_and_zero(self):
        # print 'waiting for %s to stop' % self.signal_name
        self.confirm_stopped()
        # print '%s has now stopped' % self.signal_name
        self.set_position(0.0)
        # print '%s setting zero' % self.signal_name

