import time as ttime
import numpy as np
import copy
from PyQt5 import QtCore
import ophyd
from ophyd import Component as Cpt, EpicsSignal, EpicsSignalRO, DeviceStatus

# from ophyd.device import (Device)
from ophyd.signal import Signal
from ophyd.flyers import MonitorFlyerMixin
from cls.plotWidgets.utils import *
from bcm.devices import report_fields
from bcm.devices.ophyd import BaseDAQmxOphydDev, BaseSimDAQmxOphydDev
from cls.types.stxmTypes import scan_types, detector_types
from cls.utils.log import get_module_logger
from bcm.devices.ophyd.base_detector import BaseDeviceSignals, BaseDetectorDev
from cls.utils.hash_utils import gen_unique_id_from_string

from bcm.devices.ophyd.qt.data_emitters import QtDataEmitter

_logger = get_module_logger(__name__)

DATA_OFFSET = 2

# class QtDataEmitterSignals(QtCore.QObject):
#     new_plot_data = QtCore.pyqtSignal(object)  # emits a standard plotter dict
#
#     def __init__(self, epoch="run", **kwargs):
#         super(QtDataEmitterSignals, self).__init__()

# class BaseDeviceSignals(QtCore.QObject):
#     """
#     The base signals provided in the API for scans, this class provides the following signals to every sscan record
#
#     :signal changed: The detectordevice has read a new value
#
#     :returns: None
#
#     """
#
#     # changed = QtCore.pyqtSignal(object)  # dct
#     # sig_do_read = QtCore.pyqtSignal()
#     # sig_do_event_emit = QtCore.pyqtSignal()
#     new_plot_data = QtCore.pyqtSignal(object)
#
#     def __init__(self, parent=None):
#         """
#         __init__(): description
#
#         :param parent=None: parent=None description
#         :type parent=None: parent=None type
#
#         :returns: None
#         """
#         QtCore.QObject.__init__(self, parent)
#
# class BaseDetectorDev:
#
#     def __init__(self, **kwargs):
#         super(BaseDetectorDev, self).__init__()
#         self.det_id = None
#         self.p_num_points = 1
#         self.p_num_rows = None
#         self._pnts_per_row = None
#         self._cb_id = None
#         self._scan_type = None
#         # self.mode = 0
#         self._scale_val = 1.0
#         self._det_type = detector_types.POINT  # or LINE or 2D
#         self._plot_dct = make_counter_to_plotter_com_dct()
#
#     def configure(self):
#         """
#         to be implemented by inheriting class
#         :return:
#         """
#         pass
#
#     # def set_mode(self, val):
#     #     self.mode = val
#
#     def set_det_type(self, det_type="POINT"):
#         if det_type.find("POINT") > -1:
#             self._det_type = detector_types.POINT
#         elif det_type.find("LINE_FLYER") > -1:
#             self._det_type = detector_types.LINE_FLYER
#         elif det_type.find("LINE") > -1:
#             self._det_type = detector_types.LINE
#         elif det_type.find("TWO_D") > -1:
#             self._det_type = detector_types.TWO_D
#         else:
#             print(
#                 "set_det_type: Unknown Detector type [%s], needs to be a string of detector_type"
#                 % det_type
#             )
#
#     def get_det_type(self):
#         return self._det_type
#
#     def is_point_det(self):
#         if self._det_type is detector_types(detector_types.POINT):
#             return True
#         else:
#             return False
#
#     def is_line_det(self):
#         if self._det_type is detector_types(detector_types.LINE):
#             return True
#         else:
#             return False
#
#     def is_line_flyer_det(self):
#         if self._det_type is detector_types(detector_types.LINE_FLYER):
#             return True
#         else:
#             return False
#
#     def is_2D_det(self):
#         if self._det_type is detector_types(detector_types.TWO_D):
#             return True
#         else:
#             return False
#
#     def set_num_points(self, val):
#         self.p_num_points = int(val)
#
#     def set_num_rows(self, val):
#         self.p_num_rows = int(val)
#
#     def set_points_per_row(self, val):
#         self._pnts_per_row = int(val)
#
#     def set_scan_type(self, _stype):
#         self._scan_type = _stype


class BaseCounterInputDevice(BaseDAQmxOphydDev, BaseDetectorDev):
    run = Cpt(EpicsSignal, "Run", kind="omitted")
    row_mode = Cpt(EpicsSignal, "RowMode", kind="config")
    points_per_row = Cpt(EpicsSignal, "PointsPerRow", kind="config")
    device_select = Cpt(EpicsSignal, "DeviceSelect", kind="config")
    counter_select = Cpt(EpicsSignal, "CounterSelect", kind="config")
    signal_src_pin_select = Cpt(EpicsSignal, "SignalSrcPinSelect", kind="config")
    initial_count = Cpt(EpicsSignal, "InitialCount", kind="config")
    count_dir = Cpt(EpicsSignal, "CountDir", kind="config")
    max_points = Cpt(EpicsSignal, "MaxPoints", kind="config")
    sample_mode = Cpt(EpicsSignal, "SampleMode", kind="config")
    signal_src_clock_select = Cpt(EpicsSignal, "SignalSrcClockSelect", kind="config")
    sampling_rate = Cpt(EpicsSignal, "SamplingRate", kind="config")
    edge_select = Cpt(EpicsSignal, "EdgeSelect", kind="config")
    retriggerable = Cpt(EpicsSignal, "Retriggerable", kind="config")
    trig_type = Cpt(EpicsSignal, "TriggerType", kind="config")
    trig_src_select = Cpt(EpicsSignal, "TrigSrcSelect", kind="config")
    row_num_rbv = Cpt(EpicsSignalRO, "RowNum_RBV", kind="omitted")
    point_num_rbv = Cpt(EpicsSignalRO, "PointNum_RBV", kind="omitted")
    read_counts = Cpt(EpicsSignal, "ReadCounts", kind="omitted")
    point_dwell = Cpt(EpicsSignal, "PointDwell", kind="config")
    run_rbv = Cpt(EpicsSignalRO, "Run_RBV", kind="omitted")


    def __init__(self, prefix, name, **kwargs):
        super(BaseCounterInputDevice, self).__init__(prefix, name=name)
        #self.det_id = gen_unique_id_from_string(name)
        self.cntr = 0
        # to allow Qt Signals to be emitted
        self._sigs = BaseDeviceSignals()
        #make a signal attribute for this counter input dev
        self.new_plot_data = self._sigs.new_plot_data

        if "scan_type" in kwargs.keys():
            self._scan_type = kwargs["scan_type"]

        if "scale_val" in kwargs.keys():
            self._scale_val = kwargs["scale_val"]

        #report_fields(self)

    def set_dwell(self, dwell):
        self.point_dwell.put(dwell)

    def set_points_per_row(self, val):
        self._pnts_per_row = val
        self.points_per_row.put(val)

    def get_name(self):
        return self.name

    # def get_position(self):
    #     return 0

    def set_num_points(self, val):
        self.p_num_points = int(val)
        self.max_points.put(self.p_num_points)

    def stage(self):
        # should this be calling st = super().stage()?
        st = super().stage()
        # self.cntr = 0
        # self.run.put(1)
        return st

    def unstage(self):
        # should this be calling st = super().unstage()?
        st = super().unstage()
        self.run.put(0)
        return st

    def trigger(self):
        # should this be calling st = super().trigger()?
        st = DeviceStatus(self)
        self.read_counts.put(1, callback=st._finished)
        return st

    def read(self):
        # print('TestDetectorDevice: read called')
        # return(self.single_value_rbv.get())
        self.cntr += 1

        # return {self.name + '_single_value_rbv': {'value': self.single_value_rbv.get(),
        #                     'cntr': self.cntr, 'timestamp': ttime.time()}}
        d ={
            self.name: {
                "value": self.single_value_rbv.get() * self._scale_val,
                "cntr": self.cntr,
                "timestamp": ttime.time(),
            }
        }
        # print(f"[{self.name}]=",d)
        return d

    def describe(self):
        # print('TestDetectorDevice: describe called')
        res = super().describe()
        # here the key is the name + _<EpicsSignal name> but I want this to be only 'name'
        d = res
        k = list(res.keys())[0]
        d[self.name] = res.pop(k)
        # d[self.name + '_single_value_rbv'] = res.pop(k)
        for key in d:
            d[key]["units"] = "counts"
        return d


class PointDetectorDevice(BaseCounterInputDevice, BaseDetectorDev):
    # by adding this as 'hinted' it will be added to the name in the base class describe() function
    single_value_rbv = Cpt(EpicsSignalRO, "SingleValue_RBV", kind="hinted")

    def __init__(self, prefix, name, scale_val=1.0):
        super(PointDetectorDevice, self).__init__(
            prefix, name=name, scale_val=scale_val
        )
        self.mode = 0  # 0 == point, 1 == line
        self.set_det_type("POINT")

    def enable_on_change_sub(self):
        print(f"enable_on_change_sub: single_value_rbv [{self.name}]")
        self._cb_id = self.single_value_rbv.subscribe(self.on_change)

    def disable_on_change_sub(self):
        print(f"disable_on_change_sub: single_value_rbv [{self.name}]")
        self.single_value_rbv.unsubscribe(self._cb_id)

    def report(self):
        """return a dict that reresents all of the settings for this device"""
        print("name = %s, type = %s" % (str(self.__class__), self.name))

    def configure(self):
        # self.do_point_config(scan_types.SAMPLE_POINT_SPECTRUM, 2.0, 1, 1)
        self.do_point_config(self._scan_type, 2.0, 1, 1, self._pnts_per_row)

    def stage(self):
        # if (self.mode is 0):
        #     self.do_point_config(scan_types.SAMPLE_POINT_SPECTRUM, 2.0, 1, 1)
        # else:
        #     pass
        # should this be calling st = super().stage()?
        #self.enable_on_change_sub()
        st = super().stage()
        self.configure()
        self.cntr = 0
        self.run.put(1)
        return st


    def unstage(self):
        #self.disable_on_change_sub()
        st = super().unstage()
        return st

    def on_change(self, **kwargs):
        """
        note this is not used currently but it is here for consistancy
        {'old_value': 2.0,
        'value': 4.0,
        'timestamp': 1549577201.36433,
        'sub_type': 'value',
        'obj':
            EpicsSignalRO(read_pv='uhvCI:counter:SingleValue_RBV',
                name='noisy_det_single_value_rbv',
                parent='noisy_det',
                value=4.0,
                timestamp=1549577201.36433,
                pv_kw={},
                auto_monitor=False,
                string=False)
        }

        :param kwargs:
        :return:
        """
        print('PointDetectorDevice: on_change')
        self.new_plot_data.emit(kwargs)
        # print(kwargs)

    def do_point_config(self, scan_type, dwell, numE, numX, points_per_row=None):
        # trig_src_pfi = 4
        # self.trig_src_select.put(trig_src_pfi)  # /PFI 4  this will need to be part of a configuration at some point
        # self.signal_src_clock_select.put(12)  # /PFI 12
        self.trig_src_select.put(
            self.trig_src_pfi
        )  # /PFI 4  set by the caller prior to executing a scan

        self.trig_type.put(3)  # Digital_EDge
        self.sample_mode.put(2)  # DAQmx_HWTimedSinglePoint
        # self.max_points.put(roi['X'][NPOINTS]) #X points
        self.max_points.put(
            2
        )  # X points, so that the waveform returns <row> <point> <value> <pad>
        self.row_mode.put(1)  # 1 point
        self.retriggerable.put(True)

        if scan_type == scan_types.SAMPLE_POINT_SPECTRUM:
            self.points_per_row.put(numE)  # EV point spectra
        else:
            if points_per_row:
                self.points_per_row.put(points_per_row)
            else:
                self.points_per_row.put(numX)  # X points

    # def describe(self):
    #     #print('PointDetectorDevice: describe called')
    #     res = super().describe()
    #     for key in res:
    #         res[key]['units'] = "counts"
    #         res[key]['shape'] = '[%d,]' % len(res[key]['data'])
    #     return res

def make_event_doc_dict(det_nm, seq_num, data):
    """
    doc.keys()
        Out[1]: dict_keys(['descriptor', 'time', 'data', 'timestamps', 'seq_num', 'uid', 'filled'])
        doc['data']['DNM_LINE_DET_waveform_rbv'] = array()
    """
    dct = {}
    dct['seq_num'] = seq_num
    dct['data'][det_nm] = data
    return(dct)


class LineDetectorDevice(BaseCounterInputDevice, BaseDetectorDev):
    """
    This Device simply connects to the line detector and sets up a subscription such that when the line changes
    it emits the data on its changed signal so that a plotter can plot it, the data acquisition is done on the
     flyer device
    """

    waveform_rbv = Cpt(EpicsSignalRO, "Waveform_RBV", kind="hinted", auto_monitor=True)

    def __init__(self, prefix, name):
        super(LineDetectorDevice, self).__init__(prefix, name=name)
        self.set_det_type("LINE")
        self._default_sub = "acq_done"
        self.rawData = None

    def enable_on_change_sub(self):
        self._cb_id = self.waveform_rbv.subscribe(self.on_waveform_changed)

    def disable_on_change_sub(self):
        #self.waveform_rbv.clear_sub(self.on_change)
        self.waveform_rbv.unsubscribe(self._cb_id)
        self._cb_id = None

    def report(self):
        """return a dict that reresents all of the settings for this device"""
        print("name = %s, type = %s" % (str(self.__class__), self.name))

    def configure(self, npoints, scan_type):
        self.set_num_points(npoints)
        self.set_scan_type(scan_type)
        self.do_line_config()

    def stage(self):
        st = super().stage()
        self.cntr = 0
        self.run.put(1)
        self.enable_on_change_sub()
        return st

    def unstage(self):
        self.disable_on_change_sub()
        super().unstage()

    def do_line_config(self):
        xnpoints = self.p_num_points + 2
        self.trig_src_select.put(self.trig_src_pfi)  # /PFI 3  connect PFI3 to the interferometer "pixelclock" wire
        self.trig_type.put(3)  # DAQmx_Val_DigPattern
        self.signal_src_clock_select.put(self.ci_clk_src_gate_pfi)  # /PFI 12
        self.sample_mode.put(0)  # DAQmx_Val_FiniteSamps
        self.max_points.put(xnpoints)  #
        self.row_mode.put(0)  # 0 LINE
        self.points_per_row.put(self.p_num_points)
        self.retriggerable.put(False)

    def do_read(self):
        self.read()

    def trigger(self):
        # base class call to trigger will call set_finished() on the status
        st = super().trigger()
        # st = DeviceStatus(self)
        # _logger.debug("LineDetectorDevice: trigger: st.set_finished()")
        # st.set_finished()
        return st

    #
    def on_waveform_changed(self, *args, **kwargs):
        self.rawData = copy.copy(kwargs["value"])
        #self._sigs.sig_do_read.emit()

    def describe(self):
        desc = dict()
        desc.update(self.waveform_rbv.describe())
        return desc

    def read(self):
        # print('LineDetectorDevice: read called')
        # return(self.waveform_rbv.get())
        self.cntr += 1
        #self.rawData = self.waveform_rbv.get()
        if hasattr(self.rawData, "shape"):
            (num_points,) = self.rawData.shape
            if num_points > 0:
                (row, data) = self.process_scalar_line_data(self.rawData)
                return {
                    self.name + '_waveform_rbv': {
                        "value": data,
                        "cntr": self.cntr,
                        "timestamp": ttime.time(),
                        "row": int(row),
                    }
                }
        return {
            self.name: {
                "value": 0,
                "cntr": self.cntr,
                "timestamp": ttime.time(),
                "row": int(0),
            }
        }

    def process_scalar_line_data(self, data):
        """stores raw scalar data of increasing counts"""

        arr = np.array(data)

        row = int(arr[0])
        # slice values are absolute array locations
        arr2 = arr[DATA_OFFSET : self.p_num_points + (2*DATA_OFFSET)]
        arr3 = self.line_as_ediff(arr2, len(arr2))

        return (row, arr3)

    def line_as_ediff(self, arr, npoints, even=True, reverse=False):
        if even:
            # this one adds a zero to the end of the array keeping teh priginal size  dat = np.ediff1d(arr, to_end=np.array([0])).clip([0,])
            dat = np.ediff1d(arr).clip(
                [
                    0,
                ]
            )
            if reverse:
                dat = dat[::-1]
            # dat = np.roll(dat,1)
        else:
            # dat = np.ediff1d(arr, to_end=np.array([0])).clip([0,])
            dat = np.ediff1d(arr).clip(
                [
                    0,
                ]
            )
        return dat[:self.p_num_points]




class LineDetectorFlyerDevice(MonitorFlyerMixin, BaseCounterInputDevice, BaseDetectorDev):
    waveform_rbv = Cpt(EpicsSignalRO, "Waveform_RBV", kind="hinted", auto_monitor=False)

    def __init__(self, *args, stream_names=None, **kwargs):
        if stream_names is not None:
            s_keys = list(stream_names.keys())
            strm_nm = stream_names[s_keys[0]]
        else:
            strm_nm = "primary"

        super().__init__(*args, **kwargs)
        self.new_plot_data = self._sigs.new_plot_data
        self.stream_name = strm_nm
        # Feb 6 2023 self.set_det_type("LINE")
        self.set_det_type("LINE_FLYER")
        self.set_num_points(1)
        self.set_num_rows(0)
        self._cntr = 0
        self._is_point = False
        self._2D_data = 0
        self.prev_2D_data = 0
        self._cb_id = None
        self._lines_collected = []
        self._line_data = None


    def enable_on_change_sub(self):
        self._cb_id = self.waveform_rbv.subscribe(self.on_changed)

    def disable_on_change_sub(self):
        #self.waveform_rbv.clear_sub(self.on_change)
        self.waveform_rbv.unsubscribe(self._cb_id)
        self._cb_id = None

    def init_internal_data(self):
        self._2D_data = 0
        self.set_num_rows(0)

    def _do_event_emit(self):
        dct = make_event_doc_dict(self.name + '_waveform_rbv', self._cntr, self._line_data)
        # emit an event type document for this
        self.new_event.emit(dct)

    def on_changed(self, **kwargs):
        """
        CB to record new line of data into 2D array, and also to emit that line of data via the new_plot_data signal
        I am notsure why but I am getting 2 calls to thois callback from a single subscription, so until I have time to figure
        it out just make sure only 1 line is emitted per image
        """
        self._cntr = self._cntr + 1
        #print(kwargs)
        if self.p_num_rows > 0:
            # if rows are currently None then this is a startup CB
            # the row indicator is the first value in array, the current column is the second followed by the line data
            row = int(kwargs['value'][0])
            if row <= len(self._lines_collected):
                if row not in self._lines_collected:
                    self._line_data = kwargs['value']
                    row, data = self.process_scalar_line_data(kwargs['value'])
                    self._plot_dct[CNTR2PLOT_DETID] = self.det_id
                    self._plot_dct[CNTR2PLOT_ROW] = int(row)
                    self._plot_dct[CNTR2PLOT_COL] = 0
                    self._plot_dct[CNTR2PLOT_VAL] = data
                    self._plot_dct[CNTR2PLOT_IS_POINT] = False
                    self.new_plot_data.emit(self._plot_dct)

                    # print(f"LineDetectorFlyerDevice: on_changed: {self.name} saving row [{row}] to self._2D_data[] of len [{len(data)}]")
                    self._2D_data[row] = data
                    self._lines_collected.append(row)

    def report(self):
        """return a dict that reresents all of the settings for this device"""
        print("name = %s, type = %s" % (str(self.__class__), self.name))

    def configure_for_scan(self, npoints, scan_type):
        self.set_num_points(npoints)
        self.set_scan_type(scan_type)
        self._is_point = False
        self._cntr = 0
        self.do_line_config()

        #init 2D data
        cols = self.p_num_points
        rows = self.p_num_rows
        if rows == 0:
            _logger.error("Scan plan needs to initialize the number of rows for this flyer with a call to set_num_rows() before calling configure on this device")
            return
        self._init_2D_data()

    def kickoff(self):
        # base class call to kickoff will call set_finished() on the status
        st = super().kickoff() #this sets the parents _acquiring attr to True
        self.enable_on_change_sub()
        return st

    def complete(self):
        # base class call to complete will call set_finished() on the status
        st = super().complete()
        return st

    def stage(self):
        self.run.put(1)

    def unstage(self):
        # base class call to unstage will call set_finished() on the status
        st = super().unstage()
        self.run.put(0)
        self.disable_on_change_sub()
        return st

    def _init_2D_data(self):
        self._lines_collected = []
        cols = self.p_num_points
        rows = self.p_num_rows
        del (self._2D_data)
        self._2D_data = np.zeros((rows,cols), dtype=np.int)

    def do_line_config(self):
        xnpoints = self.p_num_points + 2

        self.trig_src_select.put(self.trig_src_pfi)
        self.trig_type.put(3)  # DAQmx_Val_DigPattern
        #self.signal_src_clock_select.put(12)  # /PFI 12
        self.signal_src_clock_select.put(self.ci_clk_src_gate_pfi)  # /PFI 12

        self.sample_mode.put(0)  # DAQmx_Val_FiniteSamps
        self.max_points.put(xnpoints)  #
        self.row_mode.put(0)  # 0 LINE
        self.points_per_row.put(self.p_num_points)
        self.retriggerable.put(False)

    def do_point_config(self):
        """a convienience function to have a single place to configure the devices to acquire a line of points
        while scanning using the E712's wave form generator
        """
        NUM_FOR_EDIFF = 2
        xnpoints = self.p_num_points  # + NUM_FOR_EDIFF

        # self.configure(dwell, num_points=xnpoints, row_mode='Line')  # , row_mode='LINE')
        self.trig_src_select.put(self.trig_src_pfi)  # /PFI 3  connect PFI3 to the interferometer "pixelclock" wire

        # counter.trig_type.put(3)  # DAQmx_Val_DigPattern
        self.trig_type.put(6)  # Pause Trigger
        self.signal_src_clock_select.put(3)  # /PFI 3 this is connected to the E712 OUT1

        self.sample_mode.put(1)  # DAQmx_Val_ContSamps
        if self._scan_type == scan_types.SAMPLE_LINE_SPECTRUM:
            # dont need the extra points
            self.max_points.put(self.p_num_points + 1)  #
        else:
            self.max_points.put(xnpoints)  #
        self.row_mode.put(0)  # 0 LINE
        self.points_per_row.put(self.p_num_points)
        self.retriggerable.put(False)

        if self._scan_type == scan_types.SAMPLE_POINT_SPECTRUM:
            # self.points_per_row.put(numE)  # EV point spectra
            self.points_per_row.put(self.p_num_points)  # EV point spectra
        else:
            self.points_per_row.put(self.p_num_points)  # X points

    def process_scalar_line_data(self, data):
        """stores raw scalar data of increasing counts"""
        (npts,) = data.shape
        num_points = npts - DATA_OFFSET - DATA_OFFSET + 1
        arr = np.array(data)
        row = int(arr[0])
        arr2 = arr[DATA_OFFSET : num_points + DATA_OFFSET]
        arr3 = self.line_as_ediff(arr2, len(arr2))
        return (row, arr3)

    def line_as_ediff(self, arr, npoints, even=True, reverse=False):
        if even:
            # this one adds a zero to the end of the array keeping teh priginal size  dat = np.ediff1d(arr, to_end=np.array([0])).clip([0,])
            dat = np.ediff1d(arr).clip(
                [
                    0,
                ]
            )
            if reverse:
                dat = dat[::-1]
            # dat = np.roll(dat,1)
        else:
            # dat = np.ediff1d(arr, to_end=np.array([0])).clip([0,])
            dat = np.ediff1d(arr).clip(
                [
                    0,
                ]
            )
        return dat

    def describe(self):
        # print('TestDetectorDevice: describe called')
        res = super().describe()
        # here the key is the name + _<EpicsSignal name> but I want this to be only 'name'
        d = res
        k = list(res.keys())[0]
        d[self.name] = res.pop(k)
        # d[self.name + '_single_value_rbv'] = res.pop(k)
        for key in d:
            d[key]["units"] = "counts"
        return d

    def read(self):
        """
        read() returns the complete 2D data
        """
        # print('TestDetectorDevice: read called')
        # return(self.single_value_rbv.get())
        # return {self.name + '_single_value_rbv': {'value': self.single_value_rbv.get(),
        #                     'cntr': self.cntr, 'timestamp': ttime.time()}}
        # return {
        #     self.name: {
        #     #'waveform_rbv': {
        #         "value": self.waveform_rbv.get(),
        #         "timestamp": ttime.time(),
        #     }
        # }
        rd = dict()
        rd.update(self.waveform_rbv.read())
        k = list(rd.keys())[0]
        if type(self._2D_data) == int:
            self._init_2D_data()
        rd[k]['value'] = copy.copy(self._2D_data)
        rd[k]['shape'] = self._2D_data.shape
        return(rd)

    def describe_collect(self):
        """Describe details for the flyer collect() method"""
        desc = dict()
        desc.update(self.waveform_rbv.describe())
        k = list(desc.keys())[0]
        if type(self._2D_data) == int:
            #array not initialized yet
            desc[k]['shape'] = (0,1)
        else:
            desc[k]['shape'] = self._2D_data.shape
        d = {self.stream_name: desc}
        # print('describe_collect: ', d)
        return d



    def collect(self):
        """Retrieve all collected data, must return exact same keys as layed out in describe_collect()

        {'line_det_strm': {
            'line_det_waveform_rbv': {
                   'source': 'PV:uhvCI:counter:Waveform_RBV',
                   'dtype': 'array',
                   'shape': [104],
                   'units': None,
                   'lower_ctrl_limit': None,
                   'upper_ctrl_limit': None},
            }
        }
        """
        if self._acquiring:
            raise RuntimeError(
                "Acquisition still in progress. Call complete()" " first."
            )

        self._collected_data = self.read()
        collected = self._collected_data
        self._collected_data = None

        if self._pivot:
            for attr, data in collected.items():
                name = getattr(self, attr).name
                for ts, value in zip(data["timestamp"], data["value"]):
                    d = dict(
                        time=ts,
                        timestamps={name: ts},
                        data={name: value},
                    )
                    # print('collect: ', d)
                    yield d

        else:
            for attr, data in collected.items():
                d = dict(
                    time=ttime.time(),
                    timestamps={attr: data["timestamp"]},
                    data={attr: data['value']},
                )
                yield d



class SIM_ReadbackSignal(Signal):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._metadata.update(
            connected=True,
            write_access=False,
        )

    def get(self):
        self._readback = self.parent.sim_state['readback']
        return self._readback

    def describe(self):
        res = super().describe()
        # There should be only one key here, but for the sake of
        # generality....
        for k in res:
            res[k]['precision'] = self.parent.precision
        return res

    @property
    def timestamp(self):
        '''Timestamp of the readback value'''
        return self.parent.sim_state['readback_ts']

    def put(self, value, *, timestamp=None, force=False):
        raise ReadOnlyError("The signal {} is readonly.".format(self.name))

    def set(self, value, *, timestamp=None, force=False):
        raise ReadOnlyError("The signal {} is readonly.".format(self.name))


class SimDetectorDevice(BaseSimDAQmxOphydDev, BaseDeviceSignals, BaseDetectorDev):
    def __init__(self, prefix, name):
        super(SimDetectorDevice, self).__init__(prefix, name=name)
        #self.det_id = gen_unique_id_from_string(name)
        self._det_type = detector_types.POINT
        self.cntr = 0
        # to allow Qt Signals to be emitted
        self._sigs = BaseDeviceSignals()
        self.new_plot_data = self._sigs.new_plot_data
        self.set_num_points(1)
        self.set_num_rows(0)
        self._scan_type = None
        self._pnts_per_row = None
        self.mode = 0
        self._scale_val = 1.0
        self._dwell = 1.0
        self._lines_collected = []


    def set_dwell(self, dwell):
        self._dwell = dwell


class SimLineDetectorDevice(SimDetectorDevice):
    #waveform_rbv = Cpt(EpicsSignalRO, "Waveform_RBV", kind="hinted", auto_monitor=True)
    sim_waveform_rbv = Cpt(SIM_ReadbackSignal, value=0, kind='hinted')
    def __init__(self, prefix, name):
        super(SimLineDetectorDevice, self).__init__(prefix, name=name)
        self.cntr = 0
        self.precision = 2
        self._scan_type = scan_types.COARSE_IMAGE
        self._default_sub = "acq_done"
        self._plot_dct = make_counter_to_plotter_com_dct()
        self.set_det_type("LINE")


    def report(self):
        """return a dict that reresents all of the settings for this device"""
        print("name = %s, type = %s" % (str(self.__class__), self.name))

    def configure(self, npoints, scan_type):
        pass

    def stage(self):
        # if (self.mode is 0):
        #     self.do_line_config()
        # else:
        #     pass
        res = super().stage()

    def unstage(self):
        self.cntr = 0

    def do_line_config(self):
        pass

    def do_read(self):
        self.read()

    def trigger(self):
        st = DeviceStatus(self)
        st.set_finished()
        return st

    def on_waveform_changed(self, *args, **kwargs):
        pass

    def describe(self):
        return {self.name + '_sim_waveform_rbv': {'source': self.prefix,
                            'dtype': 'array',
                            'shape': [self.p_num_points]}}

    def read(self):
        # print('LineDetectorDevice: read called')
        # return(self.sim_waveform_rbv.get())

        # rawData = self.sim_waveform_rbv.get()
        if self.p_num_points > 0:
            # random line of values between 0 and 500
            (row, data) = (self.cntr, np.random.randint(0, 500, self.p_num_points))
            if row <= len(self._lines_collected):
                if row not in self._lines_collected:
                    self._line_data = data
                    self._plot_dct[CNTR2PLOT_DETID] = self.det_id
                    self._plot_dct[CNTR2PLOT_ROW] = int(row)
                    self._plot_dct[CNTR2PLOT_COL] = 0
                    self._plot_dct[CNTR2PLOT_VAL] = data
                    self._plot_dct[CNTR2PLOT_IS_POINT] = False
                    self.new_plot_data.emit(self._plot_dct)
                    print(f"SimLineDetectorDevice: on_changed: {self.name} saving row [{row}] to self._2D_data[] of len [{len(data)}]")
                    #self._2D_data[row] = data
                    #self._lines_collected.append(row)

            return {
                self.name + '_sim_waveform_rbv': {
                    "value": data,
                    "cntr": self.cntr,
                    "timestamp": ttime.time(),
                    "row": int(row),
                }
            }
        else:
            return {
                self.name + '_sim_waveform_rbv': {
                    "value": 0,
                    "cntr": self.cntr,
                    "timestamp": ttime.time(),
                    "row": int(0),
                }
            }
        self.cntr += 1

    def process_scalar_line_data(self, data):
        """stores raw scalar data of increasing counts"""
        pass

    def line_as_ediff(self, arr, npoints, even=True, reverse=False):
        pass

class SimLineDetectorFlyerDevice(MonitorFlyerMixin, SimDetectorDevice):
    waveform_rbv = Cpt(SIM_ReadbackSignal, value=0, kind='hinted')

    def __init__(self, *args, stream_names=None, **kwargs):

        if stream_names is not None:
            s_keys = list(stream_names.keys())
            self.stream_name = stream_names[s_keys[0]]

        super().__init__(*args, **kwargs)
        self.set_det_type("LINE_FLYER")
        self._2D_data = 0
        self.prev_2D_data = None
        self.row_cntr = 0

    def _init_2D_data(self):
        cols = self.p_num_points
        rows = self.p_num_rows
        self._2D_data = np.zeros((rows,cols), dtype=np.int)

    def kickoff(self):
        # base class call to kickoff will call set_finished() on the status
        st = super().kickoff() #this sets the parents _acquiring attr to True
        self.row_cntr = 0
        self._2D_data = np.random.randint(0, 65535, size=(self.p_num_rows, self.p_num_points))
        return st

    def complete(self):
        # base class call to complete will call set_finished() on the status
        st = super().complete()
        return st

    def read(self):
        """
        read() returns the complete 2D data
        return = {'DNM_LINE_DET_waveform_rbv': {'value': array([503.]),
          'cntr': 1,
          'timestamp': 1670616926.713314,
          'row': 44}}
        """
        self.row_cntr = self.row_cntr + 1
        rd = dict()

        if type(self._2D_data) == np.ndarray:
            shp = self._2D_data.shape
        else:
            shp = (0,1)
        #rd.update(self.waveform_rbv.read())

        nm = self.name + '_waveform_rbv'
        rd[nm] = {'value': self._2D_data,
                  "timestamp": ttime.time(),
                  'shape': shp}

        return(rd)

    def describe(self):
        """
        keys must match those keys returned by a call to read()
        return = {'primary': {'DNM_LINE_DET_FLYER_waveform_rbv': {'source': 'PV:TB_ASTXM:Ci:counter:Waveform_RBV',
           'dtype': 'array',
           'shape': (30, 30),
           'units': '',
           'lower_ctrl_limit': 0.0,
           'upper_ctrl_limit': 10.0,
           'precision': 0}}}
        """
        desc = dict()
        nm = self.name + '_waveform_rbv'
        #desc['primary'] = {nm:
        if type(self._2D_data) == np.ndarray:
            shp = self._2D_data.shape
        else:
            shp = (0,1)

        desc[nm] ={'source': self.prefix,
                  'dtype': 'array',
                  'shape': shp,
                  'units': 'counts',
                  'precision': 0
                 }
        return(desc)

    def describe_collect(self):
        """Describe details for the flyer collect() method"""
        desc = self.describe()
        d = {self.stream_name: desc}
        return d

    def collect(self):
        # collected = self.read()
        # for attr, data in collected.items():
        #     d = dict(
        #         time=ttime.time(),
        #         timestamps={attr: data["timestamp"]},
        #         data={attr: data['value']},
        #     )
        #     yield d
        collected = self.read()
        for attr, data in collected.items():
            d = dict(
                time=ttime.time(),
                timestamps={attr: data["timestamp"]},
                data={attr: self._2D_data},
            )
            yield d


class DAQmxCounter(ophyd.Device, BaseDetectorDev):

    def __init__(self, prefix, name, stream_names={"daqmxstrm": "primary"},
                 pxp_trig_src_pfi=None,  # PFI for triggering point by point
                 lxl_trig_src_pfi=None,  # PFI for triggering line by line
                 ci_clk_src_gate_pfi=None,  # PFI for the line gate
                 gate_clk_src_gate_pfi=None,  # PFI for the gate src clock
                 sig_src_term_pfi=None,  # PFI for pmt signal input
                 **kwargs
                 ):

        super().__init__(prefix=prefix, name=name)
        #create isntances of each configuration of the counter
        if "scale_val" in kwargs.keys():
            scale_val = kwargs["scale_val"]
        else:
            scale_val = 1.0
        self._point_dev = PointDetectorDevice(prefix, name, scale_val=scale_val)
        self._line_dev = LineDetectorDevice(prefix, name)
        self._line_flyer_dev = LineDetectorFlyerDevice(prefix, name, stream_names=stream_names)
        self.device = self._point_dev #default

        self._point_dev.trig_src_pfi = pxp_trig_src_pfi  # PFI for triggering point by point
        self._line_dev.trig_src_pfi = lxl_trig_src_pfi  # PFI for triggering line by line
        self._line_flyer_dev.trig_src_pfi = lxl_trig_src_pfi  # PFI for triggering line by line

        self.set_clk_src_gates(ci_clk_src_gate_pfi) # PFI for the line gate
        self.set_gate_clk_src_gate_pfis(gate_clk_src_gate_pfi)  # PFI for the gate src clock
        self.set_sig_src_term_pfis(sig_src_term_pfi) # PFI for pmt signal input

    def set_clk_src_gates(self, pfi):
        """
        set all devs clk_src_gate pfi
        """
        self._point_dev.ci_clk_src_gate_pfi = pfi
        self._line_dev.ci_clk_src_gate_pfi = pfi
        self._line_flyer_dev.ci_clk_src_gate_pfi = pfi

    def set_gate_clk_src_gate_pfis(self, pfi):
        """
        set all devs gate_clk_src_gate pfi
        """
        self._point_dev.gate_clk_src_gate_pfi = pfi
        self._line_dev.gate_clk_src_gate_pfi = pfi
        self._line_flyer_dev.gate_clk_src_gate_pfi = pfi

    def set_sig_src_term_pfis(self, pfi):
        """
        set all devs sig_src_term pfi
        """
        self._point_dev.sig_src_term_pfi = pfi
        self._line_dev.sig_src_term_pfi = pfi
        self._line_flyer_dev.sig_src_term_pfi = pfi

    def get_device_by_type(self, _type=detector_types.POINT):
        if _type == detector_types.POINT:
            dev = self._point_dev
        elif _type == detector_types.LINE:
            dev = self._line_dev
        elif _type == detector_types.LINE_FLYER:
            dev = self._line_flyer_dev
        else:
            _logger.warn(f"No device type given or not supported so returning default PointDetectordevice")
            dev = self._point_dev
        return dev

    # def get_ophyd_device(self):
    #     return self.device


if __name__ == '__main__':
    import numpy as np
    from bluesky import RunEngine
    from databroker import Broker
    import bluesky.plan_stubs as bps
    import bluesky.preprocessors as bpp
    from ophyd.sim import det1, det2, det3, motor1, motor2

    def test_flyer_iface(d):
        # make sure all the following work
        print()
        print(f"------ Det Name: {d.name} ------")
        d.stage()
        if hasattr(d, 'kickoff'):
            d.kickoff()
        print(f"DESCRIBE: {d.describe()}")
        print(f"READ: {d.read()}")
        if hasattr(d, 'complete'):
            d.complete()
        if hasattr(d, 'describe_collect'):
            print(f"DESCRIBE_COLLECT: {d.describe_collect()}")
        if hasattr(d, 'collect'):
            print(f"COLLECT: {d.collect()}")
        d.unstage()

    ACCEL_DISTANCE = 25

    fly_dev_dct = {
        "name": "DNM_LINE_DET_FLYER",
        "class": "LineDetectorFlyerDevice",
        "dcs_nm": "TB_ASTXM:Ci-D1C0:cntr:",
        "con_chk_nm": "Run",
        "stream_names": "primary",
        "monitor_attrs": ["waveform_rbv"],
        "pivot": False,
    }
    line_det_dct = {
        "name": "DNM_LINE_DET",
        "class": "LineDetectorDevice",
        "dcs_nm": "TB_ASTXM:Ci-D1C0:cntr:",
        "name": "DNM_LINE_DET",
        "con_chk_nm": "Run",
    }
    # d = LineDetectorFlyerDevice(
    #     fly_dev_dct["dcs_nm"],
    #     name=fly_dev_dct["name"],
    #     stream_names=fly_dev_dct["stream_names"],
    #     monitor_attrs=fly_dev_dct["monitor_attrs"],
    #     pivot=fly_dev_dct["pivot"],
    # )
    d = LineDetectorDevice(line_det_dct["dcs_nm"], name=line_det_dct["name"])
    dflyer = LineDetectorFlyerDevice(fly_dev_dct["dcs_nm"], name=fly_dev_dct["name"], stream_names= {"line_fly_strm_1": "primary"})

    daqmx_dev1 = DAQmxCounter("TB_ASTXM:Ci-D1C0:cntr:", name='D1_COUNTER_0', stream_names={"line_fly_strm_1": "primary"},
                         pxp_trig_src_pfi= 3,  # PFI for triggering point by point
                         lxl_trig_src_pfi=4,  # PFI for triggering line by line
                        ci_clk_src_gate_pfi= 15,  # PFI for the line gate
                        gate_clk_src_gate_pfi= 8,  # PFI for the gate src clock
                        sig_src_term_pfi= 8,  # PFI for pmt signal input
        )
    daqmx_dev2 = DAQmxCounter("TB_ASTXM:Ci-D2C1:cntr:", name='D2_COUNTER_1', stream_names={"line_fly_strm_2": "primary"},
                              pxp_trig_src_pfi=9,  # PFI for triggering point by point
                              lxl_trig_src_pfi=10,  # PFI for triggering line by line
                              ci_clk_src_gate_pfi=34,  # PFI for the line gate
                              gate_clk_src_gate_pfi=35,  # PFI for the gate src clock
                              sig_src_term_pfi=35,  # PFI for pmt signal input
                              )


    sim_ld1 = SimLineDetectorDevice(
        "TB_ASTXM:Ci:counter1:",
        name='SIM_LINEDET_1'
    )
    sim_ld1.set_num_points(25)

    sim_ld2 = SimLineDetectorDevice(
        "TB_ASTXM:Ci:counter2:",
        name='SIM_LINEDET_2',

    )
    sim_ld1.set_num_points(125)

    sim_lfly_dev1 = SimLineDetectorFlyerDevice(
        "TB_ASTXM:Ci:counter11:",
        name='SIM_FLYERDET_1',
        stream_names={"line_fly_strm_2": "primary"}
    )
    sim_lfly_dev1.set_num_points(10)
    sim_lfly_dev1.set_num_rows(10)

    sim_lfly_dev2 = SimLineDetectorFlyerDevice(
        "TB_ASTXM:Ci:counter12:",
        name='SIM_FLYERDET_2',
        stream_names={"line_fly_strm_3": "primary"}
    )
    dflyer.set_num_points(2)
    dflyer.set_num_points(2)
    sim_lfly_dev1.set_num_points(2)
    sim_lfly_dev1.set_num_rows(2)
    sim_lfly_dev2.set_num_points(2)
    sim_lfly_dev2.set_num_rows(2)


    dets = [dflyer, sim_lfly_dev1, sim_lfly_dev2]
    i = 0
    import time
    while i < 10:
        time.sleep(0.1)
        i = i + 1
    # make sure all the following work
    test_flyer_iface(d)
    test_flyer_iface(dflyer)
    test_flyer_iface(sim_lfly_dev1)
    print("Done")
    # def fly_scan(dets, motors, rois, num_ev_pnts=4, md={"scan_type": "line_flyer_scan"}):
    #
    #     @bpp.baseline_decorator(motors)
    #     @bpp.run_decorator(md=md)
    #     def do_scan():
    #         #det = dets[0]
    #         x_roi = rois['x']
    #         y_roi = rois['y']
    #         mtr_x = motors[0]
    #         mtr_y = motors[1]
    #
    #         # a scan with 10 events
    #         for y_sp in y_roi['SETPOINTS']:
    #             yield from bps.mv(mtr_y, y_sp)
    #             yield from bps.mv(mtr_x, x_roi['STOP'] + ACCEL_DISTANCE)
    #             yield from bps.mv(mtr_x, x_roi['START'] - ACCEL_DISTANCE)
    #             yield from bps.trigger_and_read(dets)
    #     return (yield from do_scan())
    #
    #
    # num_pts = 10
    # x_mtr = motor1
    # y_mtr = motor2
    # x_roi = {'START': -50, 'STOP':50}
    # y_roi = {'SETPOINTS': np.linspace(-50,50,num_pts)}
    # # the following produces a 10 event run
    # RE = RunEngine({})
    # db = Broker.named("pystxm_amb_bl10ID1")
    # # Insert all metadata/data captured into db.
    # RE.subscribe(db.insert)
    # # # dets = [d]
    # # # print(d.describe())
    # # # print(d.read())
    # # d.set_num_points(num_pts)
    # # sim_d1.set_num_points(num_pts)
    # # sim_d2.set_num_points(num_pts)
    # # # print(sim_d1.describe())
    # # # print(sim_d1.read())
    # # # print(sim_d2.read())
    # # d.read()
    # # sim_d1.read()
    # # dets.append(sim_d1)
    # # dets.append(sim_d2)
    # uid = RE(fly_scan(dets, motors=[x_mtr, y_mtr], rois={'x': x_roi, 'y':y_roi}))
    # db[uid]
    # header = db[-1]
    # primary_docs = header.documents(fill=True)
    # docs = list(primary_docs)
    # for doc in docs:
    #     print(doc)
