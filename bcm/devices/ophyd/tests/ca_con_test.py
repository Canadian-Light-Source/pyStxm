import epics
import time

# def __on_connect(self, pvname=None, chid=None, conn=True):
#     "callback for connection events"
#     # occassionally chid is still None (ie if a second PV is created
#     # while __on_connect is still pending for the first one.)
#     # Just return here, and connection will happen later

from ophyd import Device, EpicsSignal, EpicsSignalRO
from ophyd import Component as Cpt
from ophyd.utils import set_and_wait
from cls.utils.log import (
    get_module_logger,
    log_to_qt,
    log_to_console,
    log_to_qt_and_to_file,
)
_logger = get_module_logger(__name__)


class BasicConnection(Device):
    # ai0_rbv = Cpt(EpicsSignal, 'ai0_RBV')
    # load_cmd = Cpt(EpicsSignal, 'Cmd:Load-Cmd.PROC')
    # unload_cmd = Cpt(EpicsSignal, 'Cmd:Unload-Cmd.PROC')
    # execute_cmd = Cpt(EpicsSignal, 'Cmd:Exec-Cmd')
    ai0_rbv = Cpt(EpicsSignalRO, 'ai0_RBV')

class BasicCoDevice(Device):
    run = Cpt(EpicsSignal, ":Run", kind="omitted")
    device_select = Cpt(EpicsSignal, ":DeviceSelect", kind="config")
    counter_select = Cpt(EpicsSignal, ":CounterSelect", kind="config")
    #initial_count = Cpt(EpicsSignal, ":InitialCount", kind="config")
    #count_dir = Cpt(EpicsSignal, ":CountDir", kind="config")
    max_points = Cpt(EpicsSignal, ":MaxPoints", kind="config")
    sample_mode = Cpt(EpicsSignal, ":SampleMode", kind="config")
    #signal_src_clock_select = Cpt(EpicsSignal, ":SignalSrcClockSelect", kind="config")
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

class BaseCounterInputDevice(Device):
    run = Cpt(EpicsSignal, ":Run", kind="omitted")
    row_mode = Cpt(EpicsSignal, ":RowMode", kind="config")
    points_per_row = Cpt(EpicsSignal, ":PointsPerRow", kind="config")
    device_select = Cpt(EpicsSignal, ":DeviceSelect", kind="config")
    counter_select = Cpt(EpicsSignal, ":CounterSelect", kind="config")
    signal_src_pin_select = Cpt(EpicsSignal, ":SignalSrcPinSelect", kind="config")
    initial_count = Cpt(EpicsSignal, ":InitialCount", kind="config")
    count_dir = Cpt(EpicsSignal, ":CountDir", kind="config")
    max_points = Cpt(EpicsSignal, ":MaxPoints", kind="config")
    sample_mode = Cpt(EpicsSignal, ":SampleMode", kind="config")
    signal_src_clock_select = Cpt(EpicsSignal, ":SignalSrcClockSelect", kind="config")
    sampling_rate = Cpt(EpicsSignal, ":SamplingRate", kind="config")
    edge_select = Cpt(EpicsSignal, ":EdgeSelect", kind="config")
    retriggerable = Cpt(EpicsSignal, ":Retriggerable", kind="config")
    trig_type = Cpt(EpicsSignal, ":TriggerType", kind="config")
    trig_src_select = Cpt(EpicsSignal, ":TrigSrcSelect", kind="config")
    row_num_rbv = Cpt(EpicsSignalRO, ":RowNum_RBV", kind="omitted")
    point_num_rbv = Cpt(EpicsSignalRO, ":PointNum_RBV", kind="omitted")
    read_counts = Cpt(EpicsSignal, ":ReadCounts", kind="omitted")
    point_dwell = Cpt(EpicsSignal, ":PointDwell", kind="config")
    #single_value_rbv = Cpt(EpicsSignalRO, ":SingleValue_RBV", kind="hinted")
    run_rbv = Cpt(EpicsSignalRO, ":Run_RBV", kind="omitted")
    # waveform_rbv = Cpt(EpicsSignalRO, 'Waveform_RBV', kind='hinted')

my_robot = BasicConnection('TB_ASTXM:Ai:', name='my_basicConnection', read_attrs=['ai0_rbv'])
co_dev = BasicCoDevice('TB_ASTXM:Co:gate', name='my_basic_co_dev')
ci_dev = BaseCounterInputDevice('TB_ASTXM:Ci:counter', name='my_basic_ci_dev')

#pv = epics.PV("TB_ASTXM:Ai:ai0_RBV", verbose=True)#, connection_callback=)
# while True:
#     print(my_robot.ai0_rbv.get())
#     time.sleep(0.5)
def do_con_test(dev):
    try:
        attr_keys = list(dev._sig_attrs.keys())
        for a in attr_keys:
            attr = getattr(dev, a)
            _logger.info(f"{attr.name} = {attr.get()}")
    except:
        _logger.error("Trying to read the signals from {dev.name} caused an exception")
        exit()
log_to_console()
i = 0
while True:
    do_con_test(co_dev)
    do_con_test(ci_dev)
    i = i + 1
    _logger.info(i)