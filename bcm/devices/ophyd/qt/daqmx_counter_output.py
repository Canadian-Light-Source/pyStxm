import time as ttime
import numpy as np

from PyQt5 import QtCore, QtWidgets
import time
import ophyd
from ophyd import Component as Cpt, EpicsSignal, EpicsSignalRO, DeviceStatus

from cls.utils.enum_utils import Enum
from cls.utils.dict_utils import dct_get, dct_put
from cls.scan_engine.bluesky.bluesky_defs import bs_dev_modes

from bcm.devices.ophyd import BaseDAQmxOphydDev
from bcm.devices import report_fields
from cls.utils.log import get_module_logger


_logger = get_module_logger(__name__)

trig_types = Enum(
    "DAQmx_Val_None",
    "DAQmx_Val_AnlgEdge",
    "DAQmx_Val_AnlgWin",
    "DAQmx_Val_DigEdge",
    "DAQmx_Val_DigPattern",
    "SOFT_TRIGGER",
)

trig_src_types = Enum("NORMAL_PXP", "NORMAL_LXL", "E712")


class GateDevice(ophyd.Device):
    run = Cpt(EpicsSignal, "Run", kind="omitted")

    def __init__(self, prefix, name):
        super(GateDevice, self).__init__(prefix, name=name)

    def stage(self):
        st = super().trigger()
        self.run.put(1)
        #st._finished = True
        _logger.debug("GateDevice: stage: st.set_finished()")
        st.set_finished()
        return st

    def unstage(self):
        st = super().trigger()
        self.run.put(0)
        #st._finished = True
        _logger.debug("GateDevice: unstage: st.set_finished()")
        st.set_finished()
        return st


class BaseOphydGate(BaseDAQmxOphydDev):
    """
    This class represents a counter output task that generates a pulse train used to gate other
    counter tasks, this it is stored here in the counter module
    """

    run = Cpt(EpicsSignal, ":Run", kind="omitted")
    dwell = Cpt(EpicsSignal, ":Dwell", kind="omitted")
    max_points = Cpt(EpicsSignal, ":MaxPoints", kind="omitted")
    duty_cycle = Cpt(EpicsSignal, ":DutyCycle", kind="omitted")
    trig_type = Cpt(EpicsSignal, ":TriggerType", kind="omitted")
    trig_delay = Cpt(EpicsSignal, ":TriggerDelay", kind="omitted")
    retrig = Cpt(EpicsSignal, ":Retriggerable", kind="omitted")
    device_select = Cpt(EpicsSignal, ":DeviceSelect", kind="omitted")
    counter_select = Cpt(EpicsSignal, ":CounterSelect", kind="omitted")
    sample_mode = Cpt(EpicsSignal, ":SampleMode", kind="omitted")
    output_idle_state = Cpt(EpicsSignal, ":OutputIdleState", kind="omitted")
    clock_src_select = Cpt(EpicsSignal, ":ClockSrcSelect", kind="omitted")
    retriggerable = Cpt(EpicsSignal, ":Retriggerable", kind="omitted")
    trigger_type = Cpt(EpicsSignal, ":TriggerType", kind="omitted")
    trig_src_select = Cpt(EpicsSignal, ":TrigSrcSelect", kind="omitted")
    edge_select = Cpt(EpicsSignal, ":EdgeSelect", kind="omitted")
    trigger_delay = Cpt(EpicsSignal, ":TriggerDelay", kind="omitted")
    soft_trigger = Cpt(EpicsSignal, ":SoftTrigger", kind="omitted")
    run_rbv = Cpt(EpicsSignal, ":Run_RBV", kind="omitted")

    def __init__(self, prefix, name, **kwargs):
        super(BaseOphydGate, self).__init__(prefix, name=name, **kwargs)
        self.p_dwell = 2.0
        self.p_duty_cycle = 0.5
        self.p_num_points = 1
        self.run_rbv.subscribe(self.on_running)
        self.trig = None

        self.isRunning = 0
        # time.sleep(0.4)
        self.stop()
        report_fields(self)

    def report_fields(self):
        """
        an interface that will printout all the pv fields used by this class
        """

        for k, v in self._sig_attrs.items():
            if v.suffix[0] == ".":
                if self.prefix[-1] == ":":
                    _pvname = self.prefix[0:-1] + v.suffix
                else:
                    _pvname = self.prefix + v.suffix
            print("%s" % (_pvname))

    # self.configure()
    def get_name(self):
        return self.prefix + ":Run"

    def on_running(self, **kwargs):
        # rawData = kwargs['value']
        # print 'BaseGate: on_running' , kwargs
        self.isRunning = kwargs["value"]

    # def on_running(self, val):
    #     # print 'BaseGate: on_running' , kwargs
    #     self.isRunning = val

    # def wait_till_stopped(self, proc_qt_msgs=True):
    #     while self.isRunning:
    #         time.sleep(0.1)
    #         if proc_qt_msgs:
    #             QtWidgets.QApplication.processEvents()
    #
    # def wait_till_running(self, proc_qt_msgs=True):
    #     while not self.isRunning:
    #         time.sleep(0.1)
    #         if proc_qt_msgs:
    #             QtWidgets.QApplication.processEvents()
    #
    # def wait_till_running_polling(self, proc_qt_msgs=True):
    #     idx = 0
    #     while not self.run_rbv.get() and (idx < 10):
    #         time.sleep(0.1)
    #         if proc_qt_msgs:
    #             QtWidgets.QApplication.processEvents()
    #         idx += 1

    def stop(self):
        if self.run.connected:
            self.run.put(0)
        # self.isRunning = 0

    def configure(self, num_points=1, dwell=2.0, duty=0.5, soft_trig=False, trig_delay=0.0):

        self.trig_src_select.put(self.trig_src_pfi)
        self.clock_src_select.put(self.src_clock_pfi)
        self.ctr_src_pfi.put(self.counter_select)

        self.p_dwell = dwell
        self.p_duty_cycle = duty
        self.p_num_points = num_points

        self.max_points.put(self.p_num_points)
        self.dwell.put(self.p_dwell)
        self.duty_cycle.put(self.p_duty_cycle)
        self.trig_delay.put(trig_delay)

        if self.trig is not None:
            self.trig_type.put(trig_types.SOFT_TRIGGER)
        else:
            self.trig_type.put(trig_types.DAQMX_VAL_DIGEDGE)

    def get_report(self):
        """return a dict that reresents all of the settings for this device"""
        dct = {}
        dct_put(dct, "dwell", self.dwell.get())
        dct_put(dct, "max_points", self.max_points.get())
        dct_put(dct, "duty_cycle", self.duty_cycle.get())
        dct_put(dct, "trig_type", self.trig_type.get())
        dct_put(dct, "trig_delay", self.trig_delay.get())
        dct_put(dct, "retrig", self.retrig.get())
        dct_put(dct, "device_select", self.device_select.get())
        dct_put(dct, "counter_select", self.counter_select.get())
        dct_put(dct, "sample_mode", self.sample_mode.get())
        dct_put(dct, "output_idle_state", self.output_idle_state.get())
        dct_put(dct, "clock_src_select", self.clock_src_select.get())
        dct_put(dct, "retriggerable", self.retriggerable.get())
        dct_put(dct, "trigger_type", self.trigger_type.get())
        dct_put(dct, "trig_src_select", self.trig_src_select.get())
        dct_put(dct, "edge_select", self.edge_select.get())
        dct_put(dct, "trigger_delay", self.trigger_delay.get())
        return dct

    def load_defaults(self):
        self.duty_cycle.set(0.5)
        self.max_points(1)
        self.retrig.set(0)

    def open(self):
        self.start()

    def start(self):
        self.run.put(1)

    # self.isRunning = 1

    def do_trigger(self):
        if self.trig is not None:
            self.trig.put(1)

    def set_dwell(self, val):
        self.dwell.put(val)


class BaseCounterOutputDevice(BaseDAQmxOphydDev):
    run = Cpt(EpicsSignal, ":Run", kind="omitted")
    device_select = Cpt(EpicsSignal, ":DeviceSelect", kind="config")
    counter_select = Cpt(EpicsSignal, ":CounterSelect", kind="config")
    max_points = Cpt(EpicsSignal, ":MaxPoints", kind="config")
    sample_mode = Cpt(EpicsSignal, ":SampleMode", kind="config")
    signal_src_clock_select = Cpt(EpicsSignal, ":SignalSrcClockSelect", kind="config")
    edge_select = Cpt(EpicsSignal, ":EdgeSelect", kind="config")
    retriggerable = Cpt(EpicsSignal, ":Retriggerable", kind="config")
    trig_type = Cpt(EpicsSignal, ":TriggerType", kind="config")
    trig_src_select = Cpt(EpicsSignal, ":TrigSrcSelect", kind="config")
    dwell = Cpt(EpicsSignal, ":Dwell", kind="config")
    duty_cycle = Cpt(EpicsSignal, ":DutyCycle", kind="config")
    output_idle_state = Cpt(EpicsSignal, ":OutputIdleState", kind="config")
    clock_src_select = Cpt(EpicsSignal, ":ClockSrcSelect", kind="config")
    trigger_delay = Cpt(EpicsSignal, ":TriggerDelay", kind="config")
    soft_trigger = Cpt(EpicsSignal, ":SoftTrigger", kind="config")
    run_rbv = Cpt(EpicsSignalRO, ":Run_RBV", kind="omitted")

    # self.runningcb_idx = self.add_callback('Run_RBV', self.on_running)

    def __init__(self, prefix, name):
        super(BaseCounterOutputDevice, self).__init__(prefix, name=name)
        self.name = name
        self.cntr = 0
        self.p_dwell = 1.0
        self.p_duty_cycle = 0.5
        self.p_num_points = 1
        self.p_trig_src = 4
        self.trig = None
        self.mode = bs_dev_modes.NORMAL_PXP  # 0 == point, 1 == line
        report_fields(self)

    def get_name(self):
        return self.name

    def report(self):
        print("\tname = %s, type = %s" % (str(self.__class__), self.name))

    def set_trig_src(self, src=trig_src_types.NORMAL_PXP):
        # assert src in trig_src_types._dict.keys(), "src must be of type trig_src_types"
        # if(src in trig_src_types._dict.keys()):
        #     if(src is trig_src_types.NORMAL_PXP):
        #         self.p_trig_src = 4
        #     elif(src is trig_src_types.NORMAL_LXL):
        #         self.p_trig_src = 3
        #     elif(src is trig_src_types.E712):
        #         self.p_trig_src = 3
        # self.trig_src_select.put(self.p_trig_src)

        self.trig_src_select.put(self.trig_src_pfi)

    def set_mode(self, val):
        self.mode = val

    def set_dwell(self, val):
        self.p_dwell = val
        self.dwell.put(val)

    def set_duty_cycle(self, val):
        self.p_duty_cycle = val
        self.duty_cycle.put(val)

    def set_num_points(self, val):
        self.p_num_points = val
        self.max_points.put(self.p_num_points)

    def stage(self):
        _logger.debug("BaseCounterOutputDevice: stage: super().stage()")
        super().stage()
        _logger.debug("BaseCounterOutputDevice: stage: self.run.put(1)")
        self.run.put(1)
        _logger.debug("BaseCounterOutputDevice: stage: st = DeviceStatus(self)")
        st = DeviceStatus(self)
        #print("BaseCounterOutputDevice: stage: st._finished = True")
        #st._finished = True
        _logger.debug("BaseCounterOutputDevice: stage: st.set_finished()")
        st.set_finished()
        _logger.debug("BaseCounterOutputDevice: stage: return st")
        return st

    def unstage(self):
        _logger.debug("BaseCounterOutputDevice: unstage: super().unstage()")
        super().unstage()
        _logger.debug("BaseCounterOutputDevice: unstage: self.run.put(0)")
        self.run.put(0)
        _logger.debug("BaseCounterOutputDevice: unstage: st = DeviceStatus(self)")
        st = DeviceStatus(self)
        #print("BaseCounterOutputDevice: unstage: st._finished = True")
        #st._finished = True
        _logger.debug("BaseCounterOutputDevice: unstage: st.set_finished()")
        st.set_finished()
        _logger.debug("BaseCounterOutputDevice: unstage: return st")
        return st

    def trigger(self):
        st = DeviceStatus(self)
        self.read_counts.put(1, callback=st._finished)
        return st

    def read(self):
        # print('TestDetectorDevice: read called')
        # return(self.single_value_rbv.get())
        self.cntr += 1

        return {
            self.name
            + "_single_value_rbv": {
                "value": self.single_value_rbv.get(),
                "cntr": self.cntr,
                "timestamp": ttime.time(),
            }
        }

    def describe(self):
        # print('TestDetectorDevice: describe called')
        res = super().describe()
        for key in res:
            res[key]["units"] = "counts"
        return res

    # def configure(self, num_points=1, dwell=2.0, duty=0.5, soft_trig=False, trig_delay=0.0):
    def configure(self, soft_trig=False, trig_delay=0.0):
        # self.p_dwell = dwell
        # self.p_duty_cycle = duty
        # self.p_num_points = num_points
        if self.mode is bs_dev_modes.NORMAL_PXP:
            self.max_points.put(self.p_num_points)
        else:
            self.max_points.put(self.p_num_points + 2)
        self.dwell.put(self.p_dwell)
        self.duty_cycle.put(self.p_duty_cycle)
        self.trig_delay.put(trig_delay)

        if self.trig is not None:
            self.trig_type.put(trig_types.SOFT_TRIGGER)
        else:
            self.trig_type.put(trig_types.DAQMX_VAL_DIGEDGE)

    def load_defaults(self):
        self.set_duty_cycle(0.5)
        self.set_num_points(1)
        self.retrig.set(0)

    def open(self):
        self.start()

    def start(self):
        self.run.put(1)

    # self.isRunning = 1

    def do_trigger(self):
        if self.trig is not None:
            self.trig.put(1)


class GateDevice(BaseCounterOutputDevice):
    def __init__(self, prefix, name):
        super(GateDevice, self).__init__(prefix, name=name)

    def stage(self):
        if self.mode is bs_dev_modes.NORMAL_PXP:
            self.do_point_config()
        else:
            self.do_line_config()
        self.cntr = 0
        self.run.put(1)
        st = super().stage()
        return st

    def unstage(self):
        st = super().unstage()
        return st

    def configure(
        self, num_points=1, dwell=1.0, duty=0.5, soft_trig=False, trig_delay=0.0
    ):

        self.max_points.put(num_points)
        self.dwell.put(dwell)
        self.duty_cycle.put(duty)
        self.trigger_delay.put(trig_delay)

        if self.trig is not None:
            self.trig_type.put(trig_types.SOFT_TRIGGER)
        else:
            self.trig_type.put(trig_types.DAQMX_VAL_DIGEDGE)

    def do_point_config(self):
        """a convienience function to have a single place to configure the devices to acquire single points"""

        self.set_num_points(1)
        self.set_duty_cycle(0.9999)
        # trig_src_pfi = 4
        self.configure(1, dwell=self.p_dwell, duty=0.999, trig_delay=0.0)
        # self.trig_src_select.put(self.p_trig_src)  # /PFI 4  this will need to be part of a configuration at some point
        self.trig_src_select.put(self.trig_src_pfi)
        self.retriggerable.put(1)

    def do_line_config(self):
        """a convienience function to have a single place to configure the devices to acquire single points"""

        # trig_src_pfi = 3
        xnpoints = self.p_num_points + 2
        self.configure(num_points=xnpoints, dwell=self.p_dwell, duty=0.5)
        # self.trig_src_select.put(self.p_trig_src)  # /PFI 3  connect PFI4 to the interferometer "pixelclock" wire
        self.sample_mode.put(0)  # DAQmx_Val_FiniteSamps
        # self.trig_src_select.put(self.p_trig_src)  # /PFI 3  connect PFI4 to the interferometer "pixelclock" wire
        self.trig_src_select.put(self.trig_src_pfi)
