import math
import time

import numpy as np
from ophyd.device import Component as Cpt
from ophyd.signal import EpicsSignal, EpicsSignalRO
from PyQt5 import QtCore, QtWidgets

from bcm.devices.zmq.motor import ZMQMotor

from cls.utils.log import get_module_logger
from cls.utils.roi_dict_defs import *


_logger = get_module_logger(__name__)

MAX_PIEZO_RANGE = 250.0
# MAX_DELTA_FINE_RANGE_UM = MAX_PIEZO_RANGE / 2.0
# MIN_INTERFER_RESET_RANGE_UM = MAX_DELTA_FINE_RANGE_UM / 4.0
MAX_DELTA_POS_CHNG_UM = 1000
MAX_FINE_SCAN_VELO = 10000
MAX_COARSE_SCAN_VELO = 2500
E712_MID_RANGE_VOLTS = 50
MAX_COARSE_MOTOR_VELO = 3500

MAX_DELTA_OFF_CENTER = 20 #um, if the current position is less than this value away from setpoint then skip moving coarse motor

class sample_abstract_motor(ZMQMotor):
    """
    NOTE: this is not a scanable motor class, it is meant to be used to setup a scan by configuring the triggers
    Represents an abstract motor that connects to a defined set of PV's of an Abstract positioner
    (Coarse Stepper Motor and Fine piezo motor combined), this implementation is particular to the Abstract Epics motor
    driver developed at teh CLS specifically for the STXM,
        mode - in teh driver there are 7 "modes" that determine how the driver controls the steppers and piezo's
        scan_start - is the position that a scan will start from, this position includes the acceleration distance
        scan_stop  - is teh position that a scan will use to stop at, this position includes the decceleration distance
        marker_start - is the position that the driver will trigger a digital out that is used to start the pulse train generation
        marker_stop - is the position that the pulse train generation will stop
        set_marker - will set the trigger position, is typically used to set a position that will not trigger when motor returns to scan_start
        atz_set_coarse_pos - a function that AutoZero's the piezo stage then sets its position to the current coarse stage position value
    """
    #proc_msgs = pyqtSignal()
    # mode = Cpt(EpicsSignal, ":Mode", kind="omitted")
    # scan_start = Cpt(EpicsSignal, ":ScanStart", kind="omitted")
    # scan_stop = Cpt(EpicsSignal, ":ScanStop", kind="omitted")
    # marker_start = Cpt(EpicsSignal, ":MarkerStart", kind="omitted")
    # marker_stop = Cpt(EpicsSignal, ":MarkerStop", kind="omitted")
    # set_marker = Cpt(EpicsSignal, ":SetMarker", kind="omitted")
    # atz_set_coarse_pos = Cpt(EpicsSignal, ":AtzSetCoarsePos", kind="omitted")
    # set_coarse_pos = Cpt(EpicsSignal, ":SetCoarsePos", kind="omitted")

    def __init__(self, signal_name, **kwargs):
        kwargs['ignore_msta'] = True
        ZMQMotor.__init__(self, signal_name, **kwargs)

        self.MODE_NORMAL = 0
        self.MODE_LINE_UNIDIR = 1
        self.MODE_LINE_BIDIR = 2
        self.MODE_POINT = 3
        self.MODE_COARSE = 4
        self.MODE_SCAN_START = 5
        self.MODE_MOVETO_SET_CPOS = 6

        self.marker_start_pos = 0
        self.POWER_OFF = 0
        self.POWER_ON = 1

        self._coarse_mtr: ZMQMotor = None
        self._fine_mtr: ZMQMotor = None
        self.mtr_busy = False
        self.pos = None
        self.prev_velo = None
        self.finish_move_timer = QtCore.QTimer()
        self.finish_move_timer.setSingleShot(True)
        self.finish_move_timer.timeout.connect(self.finish_abs_move)

        self._max_coarse_range: float = 10000.  # sane default, may be overridden
        self._max_fine_range: float = MAX_PIEZO_RANGE  # sane default, may be overridden
    #     self._coarse_scanable_range = 10
    #     self._fine_scanable_range = 10
    #     # default of 10um, note this is different than the low and high soft limits, those
    #     # are set by the coarse motors for an e712 motor because it needs to be able to use setpoint values that are
    #     # in the range of the coarse motor, scanable range is the actual physical range of the piezo stage and will
    #     # come from the max_fine_x and max_fine_y declarations in the bealmline config file
    #
    # def set_scanable_ranges(self, coarse: float, fine: float) -> None:
    #     self._coarse_scanable_range = coarse
    #     self._fine_scanable_range = fine

    def check_scan_limits(self, start: float, stop: float, coarse_only: bool = False) -> bool:
        """
        check the start stop values against current soft limits
        return False if beyond else True if they are reachable

        check_coarse_only is included for API support and not used
        """
        can_got_to_target = super().check_scan_limits(start, stop, coarse_only)

        if can_got_to_target:
            # check fine stage
            fine_in_rel_range = math.fabs(stop - start) < self.max_fine_range
            return fine_in_rel_range or coarse_only
        else:
            return False

    @property
    def max_fine_range(self) -> float:
        """Maximum travel range for fine piezo motor; in microns (um)"""
        return self._max_fine_range

    @property
    def max_delta_fine_range(self) -> float:
        """Maximum travel range, relative from center, for fine piezo motor; in microns (um)"""
        return self.max_fine_range / 2.0

    @property
    def min_interfer_reset_range(self) -> float:
        """Minimum difference threshold to trigger a reset of the interferometer; in microns (um)"""
        return self.max_delta_fine_range / 4.0

    def do_autozero(self):
        """
        make E712 channel perform and autozero procedure, this will leave the channel at 50V
        """
        pass


    def move(self, pos, wait=True, **kwargs):
        """
        override the lower level epics motor as this class is now providing the functionality
        that used to be provided by the Abstract Motor Driver (removed in Fall of 2022)
        """
        self.move_to_position(pos)

    def set_piezo_power_off(self):
        """ convienience function to set the power off"""
        #print("set_piezo_power_off[%s] turning power off" % self._fine_mtr.name)
        #self._fine_mtr.servo_power.put(self.POWER_OFF)
        pass

    def set_piezo_power_on(self):
        """ convienience function to set the power on"""
        #print("set_piezo_power_on[%s] turning power on" % self._fine_mtr.name)
        #self._fine_mtr.servo_power.put(self.POWER_ON)
        pass

    def set_coarse_fine_mtrs(self, coarse: ZMQMotor, fine: ZMQMotor):
        '''
        coarse is an instance of the coarse Epics motor as is fine
        '''
        self._coarse_mtr = coarse
        self._fine_mtr = fine

        #synchronize the softlimits to those of the coarse motor
        llm = self._coarse_mtr.get_low_limit()
        hlm = self._coarse_mtr.get_high_limit()
        self.set_low_limit(llm)
        self._fine_mtr.set_low_limit(llm)
        self.set_high_limit(hlm)
        self._fine_mtr.set_high_limit(hlm)

    def get_coarse_mtr(self):
        """
        return instance of the coarse motor
        """
        return(self._coarse_mtr)

    def get_fine_mtr(self):
        """
        return instance of the coarse motor
        """
        return(self._fine_mtr)

    def set_coarse_fine_ranges(self, coarse: float, fine: float):
        if coarse:
            self._max_coarse_range = coarse
        if fine:
            self._max_fine_range = fine

    def on_status_changed(self, stat):
        #print(stat)
        pass

    def calc_scan_range(self, roi):
        """
        take an roi dict and return min max of the range
        """
        min = roi[START]
        max = roi[STOP]
        return(min, max)

    def is_fine_in_range(self, roi):
        """
        This function makes the assumption that the abstract motor is at the center of the previous scan
        given a roi dict determine if the fine motor is currently in range to perform the scan given in the roi
        """
        nr_cntr = self.is_fine_already_near_center(roi[CENTER])
        smin_in_range = False
        smax_in_range = False
        smin, smax = self.calc_scan_range(roi)
        fbk = float(self._fine_mtr.user_readback.get())
        # now calc max range from current center
        cmin = fbk - self.max_delta_fine_range
        cmax = fbk + self.max_delta_fine_range
        #if it is then check to see if the scan range will work
        if smin > cmin:
            smin_in_range = True
        if smax < cmax:
            smax_in_range = True
        return smin_in_range and smax_in_range

    def check_scan_limits(self, start: float, stop: float, coarse_only: bool = False) -> bool:
        # the fine piezo stage will have a small relative range,
        # but we may move the coarse stepper stage to compensate
        fine_in_rel_range = math.fabs(stop - start) < self.max_fine_range
        return (fine_in_rel_range or coarse_only) and self._coarse_mtr.check_scan_limits(start, stop)

    def move_fine_to_coarse_fbk_pos(self):
        """
        we are exploiting the idea that the fine motors center opf voltage and physical ranges is set
        to where the coarse motors position is, so this function essentially allows caller scan plugins to reset
        the fine motor to the center of its voltage and physical ranges
        """
        # fbk_pos = self._coarse_mtr.user_readback.get()
        # self._fine_mtr.servo_power.put(1)
        # self._fine_mtr.move(fbk_pos)
        pass

    def is_fine_already_near_center(self, center):
        """
        check to see if the fine motor is already near the given center of position, and near the middle of its voltage range
        """
        # pos_chk = self.do_position_check(self._fine_mtr, center)
        # volt_chk = self.do_voltage_check()
        # return pos_chk and volt_chk
        pass

    def do_position_check(self, mtr: ZMQMotor, setpoint: float):
        """
        take a motor and check to see if its feedback position is within a deadband of the setpoint
        """
        fbk = float(mtr.user_readback.get())
        threshold = 5.0
        return  math.fabs(fbk - setpoint) <= threshold

    def do_voltage_check(self):
        """
        take a fine (piezo) motor and check to see if its current voltage is within +-10 volts of mid range (50)
        if it is return True else False
        """
        # volt_fbk = float(self._fine_mtr.output_volt_rbv.get())
        # threshold = 10.0
        # return math.fabs(E712_MID_RANGE_VOLTS - volt_fbk) <= threshold
        pass

    def do_interferometer_check(self):
        """
        look at the feedbacks of the coarse and fine motors and decide if the interferometers should be reset
        function ALWAYS returns with piezo power off
        """
        pass

    def move_to_scan_start(self, start=0.0, stop=0.0, npts=1, dwell=1.0, start_in_center=False, line_scan=True):
        """
        control both the fine and the coarse motors to move to the scan start position
        also calc and set the velocity

        start_in_center: if the scan is going to be a fine scan then we want the coarse motors to go to the center of the scan
                            as the piezo's are going to do all the moving and they need to be in the center of their ranges
        """
        pass

    def move_coarse_to_scan_start(self, start=0.0, stop=0.0, npts=1, dwell=1.0, start_in_center=False, line_scan=True):
        """
        control both the fine and the coarse motors to move to the scan start position
        also calc and set the velocity

        start_in_center: if the scan is going to be a fine scan then we want the coarse motors to go to the center of the scan
                            as the piezo's are going to do all the moving and they need to be in the center of their ranges
        """
        pass

    def motor_on_a_limit(self, mtr):
        """
        an status exception is thrown if the motor is already on a limit and you try to move into it

        This should be the DCS servers issue to check so just return that it is not on a limit
        """
        return False


    def move_to_position(self, pos, do_interfer_reset=False):
        """
        the DCS server handles the coordinated control of the abstract positioner so just send the setpoint
        """
        self.set('user_setpoint', pos)


    def finish_abs_move(self):
        """
        a signal handler that will finish teh abs move, basically turn on servo and push final position

        handled by the DCS server
        """
        pass

    def is_within_deadband(self, mtr, pos, deadband=1.0):
        """
        checks to see if current motor position is within deadband, if so return true else false
        """
        fbk = mtr.get_position()
        abs_delta = math.fabs(pos - fbk)
        return abs_delta <= deadband

    def move_coarse_to_position(self, pos, do_interfer_reset=False):
        """
        control both the fine and the coarse motors to move to the given position, checking the range from the current position
        to see if it is a fine move or a coarse move

        handled by the DCS server
        """
        pass

    def reset_interferometers(self, arg=0):
        """
        NOTE: This will cause BOTH axis to set their positions to the coarse motors for X and Y respectively
        todo:
        the DCS server may or may not offer this capability so might be implemented in the future
        """
        # _logger.info("Resetting the Interferometers")
        pass

    def reset_interferometer_with_atz(self, arg=0):
        """
        NOTE: this is per axis,
        this will cause the fine stage to execute an autozero  (which will put it into the center of its
        physical and voltage ranges, then set the position of the fine stage to be the same as the coarse stage
        todo:
        the DCS server may or may not offer this capability so might be implemented in the future
        """
        #self.atz_set_coarse_pos.put(1)
        pass

    def set_mode(self, mode):
        """
        put the mode value to the PV
        :param mode:
        :return:
        """
        self.mode.put(mode)

    def config_start_stop(
        self, start=0.0, stop=0.0, npts=1, accRange=0.0, deccRange=1.0, line=True
    ):
        """
        config_samplex_start_stop(): description

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

        todo:
        the DCS server may or may not offer this capability so might be implemented in the future
        """
        pass

    def enable_marker_position(self, en):
        '''
        this assumes that all other markers have already been set and this function
        is called as part of a line by line scan to essentially enable and disable the triggering

        todo:
        the DCS server may or may not offer this capability so might be implemented in the future
        '''
        pass

#
class sample_motor(ZMQMotor):
    """
    Represents an motor that is typically a piezo motor, either a sample fine stage or a zoneplate X/Y stage
    """

    # mode = Cpt(EpicsSignal, ":Mode", kind="omitted")
    # scan_start = Cpt(EpicsSignal, ":ScanStart", kind="omitted")
    # scan_stop = Cpt(EpicsSignal, ":ScanStop", kind="omitted")
    # marker_start = Cpt(EpicsSignal, ":MarkerStart", kind="omitted")
    # marker_stop = Cpt(EpicsSignal, ":MarkerStop", kind="omitted")
    # set_marker = Cpt(EpicsSignal, ":SetMarker", kind="omitted")
    # auto_zero = Cpt(EpicsSignal, ":AutoZero", kind="omitted")
    # servo_power = Cpt(EpicsSignal, ":ServoPower", kind="omitted")
    # servo_power_rbv = Cpt(EpicsSignalRO, ":ServoPower_RBV", kind="omitted")
    # output_volt_rbv = Cpt(EpicsSignalRO, ":OutputVolt_RBV", kind="omitted")

    def __init__(self, signal_name, **kwargs):
        # if signal_name.endswith('.'):
        #     signal_name = signal_name[:-1]
        ZMQMotor.__init__(self, signal_name, **kwargs)

        self.MODE_NORMAL = 0
        self.MODE_LINE_UNIDIR = 1
        self.MODE_LINE_BIDIR = 2
        self.MODE_POINT = 3
        self.MODE_COARSE = 4
        self.MODE_SCAN_START = 5
        self.MODE_MOVETO_SET_CPOS = 6

        self.POWER_OFF = 0
        self.POWER_ON = 1
        self.scanable_range = 10

        # default of 10um, note this is different than the low and high soft limits, those
        # are set by the coarse motors for an e712 motor because it needs to be able to use setpoint values that are
        # in the range of the coarse motor, scanable range is the actual physical range of the piezo stage and will
        # come from the max_fine_x and max_fine_y declarations in the bealmline config file

    def set_max_scanable_range(self, rng: float) -> None:
        self.scanable_range = rng

    def set_power(self, val):
        """
        turn on or off teh power to the stage
        :param val:
        :return:
        """
        # self.servo_power.put(val)
        pass

    def set_mode(self, mode):
        """
        put the mode value to the PV
        :param mode:
        :return:
        """
        self.mode.put(mode)

    def config_start_stop(
        self, start=0.0, stop=0.0, npts=1, accRange=0.0, deccRange=1.0, line=True
    ):
        """
        todo:
        the DCS server may or may not offer this capability so might be implemented in the future

        """
        pass

