#!/usr/bin/env python
"""
 This module provides support for the EPICS motor record.
"""
import time
import copy
import numpy

from PyQt5 import QtWidgets
from PyQt5.QtCore import QObject, Qt, pyqtSignal
from collections import OrderedDict

from ophyd import EpicsMotor
from ophyd.signal import EpicsSignal, EpicsSignalRO
from ophyd.device import Device, Component as Cpt
from ophyd.utils.epics_pvs import data_type, data_shape

from bcm.devices.dev_categories import dev_categories
from bcm.devices import BaseDevice
from bcm.devices import report_fields
from cls.utils.dict_utils import dct_get, dct_put
from cls.utils.log import get_module_logger

_logger = get_module_logger(__name__)

WAIT_SLEEP = 0.002
START_TIMEOUT = 20
MOVE_TIMEOUT = 900000


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


class MotorQt(EpicsMotor, QObject):
    """just a convienience class so that PVs can be configured in the beamline configuration file
    and used as if they were other devices, making the rest of the code cleaner
    """
    changed = pyqtSignal(object) # for compatability
    on_connect = pyqtSignal(object) # for compatability

    move_by = Cpt(EpicsSignal, ".RLV", kind="omitted")

    description = Cpt(EpicsSignal, ".DESC", kind="omitted")
    units = Cpt(EpicsSignal, ".EGU", kind="omitted")
    high_limit_val = Cpt(EpicsSignal, ".HLM", kind="omitted")
    low_limit_val = Cpt(EpicsSignal, ".LLM", kind="omitted")
    at_high_limit_val = Cpt(EpicsSignal, ".HLS", kind="omitted")
    at_low_limit_val = Cpt(EpicsSignal, ".LLS", kind="omitted")
    use_torque = Cpt(EpicsSignal, ".CNEN", kind="omitted")
    ctrlr_status = Cpt(EpicsSignal, ".MSTA", kind="omitted")

    max_velo = Cpt(EpicsSignal, ".VMAX", kind="omitted")
    spmg_enum = Cpt(EpicsSignal, ".SPMG", kind="omitted")

    motor_res = Cpt(EpicsSignal, ".MRES", kind="omitted")
    encoder_res = Cpt(EpicsSignal, ".ERES", kind="omitted")
    raw_val = Cpt(EpicsSignal, ".RVAL", kind="omitted")
    foff = Cpt(EpicsSignal, ".FOFF", kind="omitted")

    # the following is here for compatability with e712_sample_motor

    def __init__(self, *args, **kwargs):

        stripped_kwargs = copy.copy(kwargs)

        if "pos_set" in kwargs.keys():
            del stripped_kwargs["pos_set"]
        else:
            kwargs["pos_set"] = "ES"

        if "collision_support" in kwargs.keys():
            del stripped_kwargs["collision_support"]
        else:
            kwargs["collision_support"] = False

        if "abstract_mtr" in kwargs.keys():
            del stripped_kwargs["abstract_mtr"]
        else:
            kwargs["abstract_mtr"] = False

        if "desc" in kwargs.keys():
            del stripped_kwargs["desc"]

        if "ignore_msta" in kwargs.keys():
            del stripped_kwargs["ignore_msta"]

        super(MotorQt, self).__init__(*args, **stripped_kwargs)

        if kwargs["name"] is None:
            raise MotorException("must supply motor name")

        self._name = kwargs["name"]

        if kwargs["name"].endswith(".VAL"):
            kwargs["name"] = kwargs["name"][:-4]
        if kwargs["name"].endswith("."):
            kwargs["name"] = kwargs["name"][:-1]

        self.signal_name = args[0]
        self._pos_set = kwargs["pos_set"]
        self._collision_support = kwargs["collision_support"]

        self._ctrl_vars = {}
        self._devs = {}

        if "units" in kwargs.keys():
            self._egu = kwargs["units"]
        else:
            self._egu = "um"

        if "desc" in kwargs.keys():
            self._desc = kwargs["desc"]
        else:
            self._desc = "mtr"

        # for key, val in list(self._alias.items()):
        #     devname = "%s.%s" % (self.signal_name, val)
        #     self.add_dev(devname, attr=key)

        if kwargs["collision_support"]:
            # the setpoint for this motor is the A field of a transform record :check_tr.A
            devname = "%s:check_tr.A" % (self.signal_name)
            # self.add_dev(devname, attr='check_tr.A')
            self.check_tr_A = EpicsSignal(devname, kind="omitted")

        if not kwargs["abstract_mtr"]:
            # for key, val in list(self._extras.items()):
            #     devname = "%s%s" % (self.signal_name, val)
            #     self.add_dev(devname, attr=key)
            self.disabled = EpicsSignal(
                "%s_able.VAL" % self.signal_name, kind="omitted"
            )
            self.calibPosn = EpicsSignal(
                "%s:calibPosn" % self.signal_name, kind="omitted"
            )
            self.calib_run = EpicsSignal(
                "%s:calibRun" % self.signal_name, kind="omitted"
            )
            self.calib_done = EpicsSignal(
                "%s:calibDone" % self.signal_name, kind="omitted"
            )

        # for _attr in self.attrs:
        #     self.add_attr_dev(_attr)

        self._dev_category = dev_categories.SIGNALS
        # self.set_dev_units('um')

        report_fields(self)

        if "ignore_msta" not in kwargs.keys():
            self.msta_dct = motor_msta(self.ctrlr_status.get())

        self.add_callback('user_readback', self._on_pv_changed)

    def is_connected(self):
        """

        Returns
        -------

        """
        return self.connected

    def update_msta(self):
        self.msta_dct = motor_msta(self.ctrlr_status.get())

    def set_units(self, unit):
        self._egu = unit

    def calibrate(self):
        self.calib_run.put(1)

    # def limits(self):
    #    return (self.get_low_limit(), self.get_high_limit())
    def config_start_stop(
        self, start=0.0, stop=0.0, npts=1, accRange=0.0, deccRange=1.0, line=True
    ):
        """
        config_samplex_start_stop(): to be implemented by the inheriting class, the main reason for this
        function is that if the driver needs to setup a trigger position etc that that driver call would be done here
        by teh inheriting driver class

        :param start: start description
        :type start: start type

        :param stop: stop description
        :type stop: stop type

        :param npts: npts description
        :type npts: npts type

        :param accRange=0.0: accRange=0.0 description
        :type accRange=0.0: accRange=0.0 type

        :param deccRange=0.0: accRange=0.0 description
        :type deccRange=0.0: accRange=0.0 type

        :param line=True: line=True description
        :type line=True: line=True type

        :returns: None
        """
        pass

    # @required_for_connection
    @ctrlr_status.sub_value
    def _ctrlr_status_changed(self, timestamp=None, value=None, **kwargs):
        """Callback from EPICS, indicating a change in ctrlr_status"""
        self.msta_dct = motor_msta(int(value))

    def is_ready(self):
        """
        an API function that returns if the motor is ready for scanning or not. Just check for errors and calibration
        :return:
        """
        res = (
            not self.msta_dct.msta_fields["problem"]["val"]
        ) and self.calib_done.get()
        return res

    def describe(self):
        """Return the description as a dictionary

        Returns
        -------
        dict
            Dictionary of name and formatted description string
        """
        # if(self.low_limit is None):
        #     self.get_low_limit()
        # if(self.high_limit is None):
        #     self.get_high_limit()
        # description
        # MUST CALL THE BASE CLASS DESCRIBE() FIRST!!!!!!
        desc = super().describe()
        # desc = OrderedDict()
        # print('describe for name[%s] signal_name[%s]' % (self.name, self.signal_name))
        for key in desc:
            desc[key]["units"] = self._egu
            desc[key]["lower_ctrl_limit"] = self.get_low_limit()
            desc[key]["upper_ctrl_limit"] = self.get_high_limit()
            desc[key]["desc"] = self.description.get()

        return desc

    def set_dev_category(self, category):
        self._dev_category = category

    def set_dev_units(self, units):
        self.units.put(units)

    # def stop(self):
    #     self.motor_stop.put(1, wait=False)
    #

    def set_spmg(self, state: int):
        """0=STOP, 1=PAUSE, 2=MOVE, 3=GO"""
        self.spmg_enum.put(state)

    def is_hard_stopped(self):
        return self.spmg_enum.get() == 0

    def hard_stop(self):
        self.spmg_enum.put(0, wait=False, force=True)

    def hard_stop_resume(self):
        if self.is_hard_stopped():
            self.set_spmg(3)

    def add_dev(self, devname, attr=None, **kw):
        if attr is None:
            attr = devname
        self._devs[attr] = BaseDevice(devname, **kw)
        return self._devs[attr]

    def get_dev(self, attr):
        if attr in self._devs.keys():
            return self._devs[attr]
        else:
            return None

    def add_attr_dev(self, attr, **kw):
        devname = self.signal_name + "." + attr
        self._devs[attr] = BaseDevice(devname, **kw)
        return self._devs[attr]

    def assign_exiting_attr(self, attr):
        self._devs[attr] = getattr(self, attr)

    def add_callback(self, attr, func, **kwargs):
        if hasattr(self, attr):
            dev = getattr(self, attr)
            dev.subscribe(func, **kwargs)
        else:
            print("motor_qt: add_callback: ERROR! [%s] does not exist" % attr)

    def _on_pv_changed(self, **kwargs):
        '''
        ALWAYS return 'value' plus whatever kwargs the user passed in
        :param kwargs:
                    {'old_value': <object at 0x1ac6b6fbb60>,
                         'value': 0.622,
                         'timestamp': 1729005456.052416,
                         'status': <AlarmStatus.NO_ALARM: 0>,
                         'severity': <AlarmSeverity.NO_ALARM: 0>,
                         'sub_type': 'value',
                         'obj': EpicsSignalRO(read_pv='PZAC1610-3-I12-40.RBV', name='PZAC1610-3-I12-40', parent='PZAC1610-3-I12-40', value=0.681, timestamp=1729005456.370602, auto_monitor=True, string=False)
                    }
        :return:
        '''
        self.changed.emit(kwargs['value'])
        # dct = {}
        # #'value' must be a part of default kwargs
        # if(len(self.cb_args) == 0):
        #     #only return the value by itself
        #     self.changed.emit(kwargs['value'])
        # else:
        #     #else return a dict of value plus cb_args
        #     dct['value'] = kwargs['value']
        #     for k in self.cb_args:
        #         dct[k] = kwargs[k]
        #     #emit the changed signal
        #     self.changed.emit(dct)

    def get_desc(self):
        desc = self.description.get()
        if type(desc) is numpy.ndarray:
            # convert it to a string
            desc = "".join([chr(item) for item in desc])
        return desc

    def get_units(self):
        units = self.units.get()
        if type(units) is numpy.ndarray:
            # convert it to a string
            units = "".join([chr(item) for item in units])
        return units

    #
    def report(self):
        """return a dict that reresents all of the settings for this device"""
        print("name = %s, type = %s" % (str(self.__class__), self.name))

    def get_name(self):
        return self.signal_name

    #
    def get_position(self):
        return self.user_readback.get()

    def get_low_limit(self):
        if self.connected:
            return self.low_limit_val.get()
        else:
            # print('get_low_limit: motor [%s] not connected' % self.get_name())
            # return (None)
            # try anyway
            return self.low_limit_val.get()

    def get_high_limit(self):
        if self.connected:
            return self.high_limit_val.get()
        else:
            # print('get_high_limit: motor [%s] not connected' % self.get_name())
            # return(None)
            # try anyway
            return self.high_limit_val.get()

    def at_low_limit(self):
        if self.at_low_limit_val.connected:
            return self.at_low_limit_val.get() != 0

    def at_high_limit(self):
        if self.at_high_limit_val.connected:
            return self.at_high_limit_val.get() != 0

    def set_low_limit(self, val):
        if self.low_limit_val.connected:
            return self.low_limit_val.put(val)

    def set_high_limit(self, val):
        if self.high_limit_val.connected:
            return self.high_limit_val.put(val)

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


    def get(self, attr=None):
        if attr is None:
            return getattr(self, "user_readback").get()
            # return(self._devs['RBV'].get())
        else:
            if hasattr(self, attr):
                return getattr(self, attr).get()
            else:
                print("motor_qt: get: ERROR! attr [%s] does not exist" % attr)

    #
    def put(self, attr, val, wait=1.0, timeout=5.0):
        if attr is None:
            print("motor_qt: put: ERROR! attr [%s] cannot be None")
            return
        if hasattr(self, attr):
            sig = getattr(self, attr)
            sig.put(val, wait=wait, timeout=timeout)
        else:
            print("motor_qt: put: ERROR! attr [%s] does not exist" % attr)

    #    self._devs[attr].put(val)
    #
    # def set_calibrated_position(self, pos):
    #     self.put('calibPosn', pos)
    #

    def get_max_velo(self):
        """
        return max velocity
        """
        vmax = self.max_velo.get()
        if vmax == 0.0:
            vmax = self.velocity.get()
        return vmax

    def set_velo(self, velo):
        """
        set the velocity
        """
        self.velocity.put(velo)

    def set_position(self, position, dial=False, step=False, raw=False):
        """
        Sets the motor position in user, dial or step coordinates.

        Inputs:
           position:
              The new motor position

        Keywords:
           dial:
              Set dial=True to set the position in dial coordinates.
              The default is user coordinates.

           raw:
              Set raw=True to set the position in raw steps.
              The default is user coordinates.

        Notes:
           The 'raw' and 'dial' keywords are mutually exclusive.

        Examples:
           m=epicsMotor('13BMD:m38')
           m.set_position(10, dial=True)   # Set the motor position to 10 in
                                        # dial coordinates
           m.set_position(1000, raw=True) # Set the motor position to 1000 steps
        """

        # Put the motor in "SET" mode
        self.set_use_switch.put(1)
        #set to FROZEN
        self.foff.put(1)
        #zero the offset
        self.user_offset.put(0)
        #get ERES
        eres = self.encoder_res.get()
        pos_counts = position / eres
        # if pos_counts < 0 and position < 0:
        #     #not clear how the counts sign changes the calculated position but it does
        #     pos_counts = pos_counts * -1
        #push this into RVAL
        self.raw_val.put(pos_counts)
        # Put the motor back in "Use" mode
        # self.put('set', 0)
        self.set_use_switch.put(0)

    #
    # def check_limits(self):
    #     """ check motor limits:
    #     returns None if no limits are violated
    #     raises expection if a limit is violated"""
    #     for field, msg in (('LVIO', 'Soft limit violation'),
    #                        ('HLS', 'High hard limit violation'),
    #                        ('LLS', 'Low  hard limit violation')):
    #         if self.get(field) != 0:
    #             raise MotorLimitException(msg)
    #     return
    #
    def within_limits(self, val):
        """ returns whether a value for a motor is within drive limits
        with dial=True   dial limits are used (default is user limits)

        """
        ll_name, hl_name = 'low_limit_val', 'high_limit_val'
        return (val <= self.get(hl_name) and val >= self.get(ll_name))

    # def move(self, position=None, relative=False, wait=False, timeout=300.0,
    #                    dial=False, step=False, raw=False,
    #                    ignore_limits=False, confirm_move=False):
    #     """
    #     arguments:
    #     ==========
    #      val            value to move to (float) [Must be provided]
    #      relative       move relative to current position    (T/F) [F]
    #      wait           whether to wait for move to complete (T/F) [F]
    #      dial           use dial coordinates                 (T/F) [F]
    #      raw            use raw coordinates                  (T/F) [F]
    #      step           use raw coordinates (backward compat)(T/F) [F]
    #      ignore_limits  try move without regard to limits    (T/F) [F]
    #      confirm_move   try to confirm that move has begun   (T/F) [F]
    #      timeout        max time for move to complete (in seconds) [300]
    #
    #     return values:
    #       -13 : invalid value (cannot convert to float).  Move not attempted.
    #       -12 : target value outside soft limits.         Move not attempted.
    #       -11 : drive PV is not connected:                Move not attempted.
    #        -8 : move started, but timed-out.
    #        -7 : move started, timed-out, but appears done.
    #        -5 : move started, unexpected return value from PV.put()
    #        -4 : move-with-wait finished, soft limit violation seen
    #        -3 : move-with-wait finished, hard limit violation seen
    #         0 : move-with-wait finish OK.
    #         0 : move-without-wait executed, not cpmfirmed
    #         1 : move-without-wait executed, move confirmed
    #         3 : move-without-wait finished, hard limit violation seen
    #         4 : move-without-wait finished, soft limit violation seen
    #     """
    #     if self.within_limits(position):
    #         super().move(position, wait=wait)#, wait=wait, timeout=timeout,
    #         #            dial=dial, step=step, raw=raw,
    #         #            ignore_limits=ignore_limits, confirm_move=confirm_move)
    #         return 0
    #     else:
    #         _logger.error(f"{self.name}: Move to [{position}] would violate the limits")
    #         return -12


    #
    # def move(self, val=None, relative=False, wait=False, timeout=300.0,
    #          dial=False, step=False, raw=False,
    #          ignore_limits=False, confirm_move=False):
    #     """ moves motor drive to position
    #
    #     arguments:
    #     ==========
    #      val            value to move to (float) [Must be provided]
    #      relative       move relative to current position    (T/F) [F]
    #      wait           whether to wait for move to complete (T/F) [F]
    #      dial           use dial coordinates                 (T/F) [F]
    #      raw            use raw coordinates                  (T/F) [F]
    #      step           use raw coordinates (backward compat)(T/F) [F]
    #      ignore_limits  try move without regard to limits    (T/F) [F]
    #      confirm_move   try to confirm that move has begun   (T/F) [F]
    #      timeout        max time for move to complete (in seconds) [300]
    #
    #     return values:
    #       -13 : invalid value (cannot convert to float).  Move not attempted.
    #       -12 : target value outside soft limits.         Move not attempted.
    #       -11 : drive PV is not connected:                Move not attempted.
    #        -8 : move started, but timed-out.
    #        -7 : move started, timed-out, but appears done.
    #        -5 : move started, unexpected return value from PV.put()
    #        -4 : move-with-wait finished, soft limit violation seen
    #        -3 : move-with-wait finished, hard limit violation seen
    #         0 : move-with-wait finish OK.
    #         0 : move-without-wait executed, not cpmfirmed
    #         1 : move-without-wait executed, move confirmed
    #         3 : move-without-wait finished, hard limit violation seen
    #         4 : move-without-wait finished, soft limit violation seen
    #
    #     """
    #     step = step or raw
    #
    #     NONFLOAT, OUTSIDE_LIMITS, UNCONNECTED = -13, -12, -11
    #     TIMEOUT, TIMEOUT_BUTDONE = -8, -7
    #     UNKNOWN_ERROR = -5
    #     DONEW_SOFTLIM, DONEW_HARDLIM = -4, -3
    #     DONE_OK = 0
    #     MOVE_BEGUN, MOVE_BEGUN_CONFIRMED = 0, 1
    #     NOWAIT_SOFTLIM, NOWAIT_HARDLIM = 4, 3
    #     try:
    #         val = float(val)
    #     except TypeError:
    #         return NONFLOAT
    #
    #     drv, rbv = ('setpoint', 'readback')
    #
    #     if relative:
    #         val += self.get(drv)
    #
    #     # Check for limit violations
    #     if not ignore_limits and not step:
    #         if not self.within_limits(val):
    #             return OUTSIDE_LIMITS
    #
    #     if (self._collision_support):
    #         stat = self.put('check_tr.A', val, wait=wait, timeout=timeout)
    #     else:
    #         stat = self.put(drv, val, wait=wait, timeout=timeout)
    #
    #     if stat is None:
    #         return UNCONNECTED
    #
    #     if wait and stat == -1:  # move started, exceeded timeout
    #         if self.get('DMOV') == 0:
    #             return TIMEOUT
    #         return TIMEOUT_BUTDONE
    #     if 1 == stat:
    #         if wait:  # ... and finished OK
    #             if 1 == self.get('soft_limit'):
    #                 return DONEW_SOFTLIM
    #             elif 1 == self.get('high_limit_set') or 1 == self.get('low_limit_set'):
    #                 return DONEW_HARDLIM
    #             return DONE_OK
    #         else:
    #             if 1 == self.get('soft_limit') or confirm_move:
    #                 ca.poll(evt=1.e-2)
    #             moving = False
    #             if confirm_move:
    #                 t0 = time.time()
    #                 while self.get('MOVN') == 0:
    #                     ca.poll(evt=1.e-3)
    #                     if time.time() - t0 > 0.25: break
    #             if 1 == self.get('MOVN'):
    #                 return MOVE_BEGUN_CONFIRMED
    #             elif 1 == self.get('soft_limit'):
    #                 return NOWAIT_SOFTLIM
    #             elif 1 == self.get('high_limit_set') or 1 == self.get('low_limit_set'):
    #                 return NOWAIT_HARDLIM
    #             else:
    #                 return MOVE_BEGUN
    #     return UNKNOWN_ERROR
    #
    def confirm_stopped(self):
        t = 0
        done = False
        while (not done) and (t < START_TIMEOUT):
            time.sleep(WAIT_SLEEP)
            QtWidgets.QApplication.processEvents()
            t += 1
            if self.motor_done_move.get() == 0:
                done = True
        # if(t >= START_TIMEOUT):
        #    print 'Timed out waiting to START'
        # print 'move started'
        t = 0
        done = False
        while (not done) and (t < MOVE_TIMEOUT):
            time.sleep(WAIT_SLEEP)
            QtWidgets.QApplication.processEvents()
            t += 1
            if self.motor_done_move.get() == 1:
                done = True
        if t >= MOVE_TIMEOUT:
            print("Timed out waiting to STOP")

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

    # def move_and_set_position(self, pos, setpos):
    #     self.move(pos)
    #     # print 'waiting for %s to stop' % self.signal_name
    #     self.confirm_stopped()
    #     # print '%s has now stopped' % self.signal_name
    #     self.set_position(setpos)
    #     # print '%s setting zero' % self.signal_name
    #


class MotorLimitException(Exception):
    """raised to indicate a motor limit has been reached"""

    def __init__(self, msg, *args):
        Exception.__init__(self, *args)
        self.msg = msg

    def __str__(self):
        return str(self.msg)


class MotorException(Exception):
    """raised to indicate a problem with a motor"""

    def __init__(self, msg, *args):
        Exception.__init__(self, *args)
        self.msg = msg

    def __str__(self):
        return str(self.msg)


class EnergyMotor(EpicsMotor):
    """just a convienience class so that PVs can be configured in the beamline configuration file
    and used as if they were other devices, making the rest of the code cleaner
    """

    # description = Cpt(EpicsSignal, '.DESC', kind='omitted')
    # units = Cpt(EpicsSignal, '.EGU', kind='omitted')
    # high_limit_val = Cpt(EpicsSignal, '.HLM', kind='omitted')
    # low_limit_val = Cpt(EpicsSignal, '.LLM', kind='omitted')
    # use_torque = Cpt(EpicsSignal, '.CNEN', kind='omitted')
    # ctrlr_status = Cpt(EpicsSignal, '.MSTA', kind='omitted')
    #
    # max_velo = Cpt(EpicsSignal, '.VMAX', kind='omitted')

    # the following is here for compatability with e712_sample_motor

    def __init__(self, *args, **kwargs):

        stripped_kwargs = copy.copy(kwargs)

        if "zpz_mtr" in kwargs.keys():
            zpz_mtr = kwargs["zpz_mtr"]
            del stripped_kwargs["zpz_mtr"]
        else:
            kwargs["zpz_mtr"] = False

        if "pos_set" in kwargs.keys():
            del stripped_kwargs["pos_set"]
        else:
            kwargs["pos_set"] = "ES"

        if "collision_support" in kwargs.keys():
            del stripped_kwargs["collision_support"]
        else:
            kwargs["collision_support"] = False

        if "abstract_mtr" in kwargs.keys():
            del stripped_kwargs["abstract_mtr"]
        else:
            kwargs["abstract_mtr"] = False

        super(EnergyMotor, self).__init__(*args, **stripped_kwargs)
        # self.zpz_mtr = zpz_mtr

    # def move(self, position, wait=True, **kwargs):
    #
    #     self.calc_new_zpz_pos(position)
    #     print('back from calc_new_zpz_pos()')
    #     print('calling: super().move()')
    #     st = super().move(position, wait=wait)
    #     #self.confirm_stopped()
    #     #st.set_finished()
    #     print('stopped')
    #     return (st)


if __name__ == "__main__":
    # for arg in sys.argv[1:]:
    #    m = Motor(arg)
    #    m.show_info()
    import sys
    from PyQt5 import QtWidgets
    from bluesky import RunEngine
    from bluesky.plans import scan, count
    from ophyd.sim import det1, det2

    # Make plots update live while scans run.
    from bluesky.utils import install_kicker
    from bcm.devices.ophyd.zoneplate import Zoneplate

    RE = RunEngine({})
    from bluesky.callbacks.best_effort import BestEffortCallback

    bec = BestEffortCallback()

    # Send all metadata/data captured to the BestEffortCallback.
    RE.subscribe(bec)
    from databroker import Broker

    db = Broker.named("pystxm_amb_bl10ID1")

    # Insert all metadata/data captured into db.
    RE.subscribe(db.insert)

    # app = QtWidgets.QApplication(sys.argv)

    # m = Motor_Qt('SIM_IOC:m704', name='m704', pos_set=1, collision_support=False, report_fields= True )
    zpz = MotorQt("SIM_IOC:m704", name="zpz_mtr")
    zp1 = Zoneplate("MYZONER", "zp1", zpz, -4.839514, 100, 45, 60)
    zp2 = Zoneplate("MYZONER", "zp2", zpz, -6.791682, 240, 90, 35)
    zp3 = Zoneplate("MYZONER", "zp3", zpz, -7.76662, 240, 90, 40)
    zp4 = Zoneplate("MYZONER", "zp4", zpz, -4.524239, 140, 60, 40)
    zp5 = Zoneplate("MYZONER", "zp5", zpz, -4.85874, 240, 95, 25)
    zp6 = Zoneplate("MYZONER", "zp6", zpz, -4.85874, 240, 95, 25)
    zp7 = Zoneplate("MYZONER", "zp7", zpz, -5.0665680, 250, 100, 25)
    zp8 = Zoneplate("MYZONER", "zp8", zpz, 0, 240, 100, 63.79)

    evmtr = MotorQt("SIM_VBL1610-I10:AMB:ENERGY", name="evmotor")
    # m = Motor('IOC:m106',pos_set=1, collision_support=False)
    # print m.get_name()
    # m.move(-5432, ignore_limits=True)
    # print('HLM', m.m.high_limit)
    # print('LLM', m.low_limit)
    dets = [det1, det2, evmtr]  # just one in this case, but it could be more than one
    RE(
        scan(dets, evmtr, 260, 360, 10)  # scan motor1 from 260 to 360
    )  # ...both in 10 steps
    # RE(scan(dets,
    #         zp2, 260, 360,  # scan motor1 from 260 to 360
    #         evmtr, 260, 360,  # scan motor1 from 260 to 360
    #         10))  # ...both in 10 steps

    # app.exec_()
