import time
import datetime
import copy
from PyQt5 import QtCore
import simplejson as json
import numpy as np

from ophyd.flyers import MonitorFlyerMixin
from ophyd import Component as Cpt, EpicsSignal, Device, EpicsSignalRO
from ophyd.status import DeviceStatus, SubscriptionStatus

from bcm.devices.ophyd.base_detector import BaseDeviceSignals, BaseDetectorDev
from cls.plotWidgets.utils import *
from cls.types.stxmTypes import scan_types, detector_types
from cls.utils.log import get_module_logger
from cls.utils.prog_dict_utils import make_progress_dict, set_prog_dict

_logger = get_module_logger(__name__)

SIS3820_EXTRA_PNTS = 1

class CST(datetime.tzinfo):
    def utcoffset(self, dt):
        return datetime.timedelta(hours=-6)

    def dst(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return "Saskatchewan Canada"


class SIS3820ScalarDevice(Device, MonitorFlyerMixin, BaseDetectorDev):
    run = Cpt(EpicsSignal, "mcs:startScan", kind="omitted", put_complete=True)
    stop_scan = Cpt(EpicsSignal, "mcs:stopScan", kind="omitted", put_complete=True)
    dwell = Cpt(EpicsSignal, "mcs:delay", kind="omitted", put_complete=True)
    num_acqs = Cpt(EpicsSignal, "mcs:nscan", kind="omitted")
    num_en_chans = Cpt(EpicsSignal, "mcs:numEnabled", kind="omitted")
    input_mode = Cpt(EpicsSignal, "mcs:inputMode", kind="omitted")
    output_mode = Cpt(EpicsSignal, "mcs:outputMode", kind="omitted")
    trigger_source = Cpt(EpicsSignal, "mcs:triggerSource", kind="omitted")
    mode = Cpt(EpicsSignal, "mcs:mode", kind="omitted")
    source = Cpt(EpicsSignal, "mcs:source", kind="omitted")
    lne_channel = Cpt(EpicsSignal, "mcs:LNEchannel", kind="omitted")
    preset_val1 = Cpt(EpicsSignal, "mcs:presetVal1", kind="omitted")
    preset_val2 = Cpt(EpicsSignal, "mcs:presetVal2", kind="omitted")
    preset_chan2 = Cpt(EpicsSignal, "mcs:presetChan2", kind="omitted")
    show_rate = Cpt(EpicsSignal, "mcs:showRate", kind="omitted")
    sub_bkgrnd = Cpt(EpicsSignal, "mcs:subBackground", kind="omitted")
    continuous = Cpt(EpicsSignal, "mcs:continuous", kind="omitted")
    reset = Cpt(EpicsSignal, "mcs:reset", kind="omitted")
    invert_input = Cpt(EpicsSignal, "mcs:invertInput", kind="omitted")
    invert_output = Cpt(EpicsSignal, "mcs:invertOutput", kind="omitted")
    user_led = Cpt(EpicsSignal, "mcs:userLED", kind="omitted")
    num_acqs_per_trig = Cpt(EpicsSignal, "mcs:scanCount", kind="omitted")
    num_acqs_per_trig_fbk = Cpt(EpicsSignal, "mcs:curCount", kind="omitted")
    ch_00_enable = Cpt(EpicsSignal, "mcs00:enable", kind="omitted")
    ch_01_enable = Cpt(EpicsSignal, "mcs01:enable", kind="omitted")
    ch_02_enable = Cpt(EpicsSignal, "mcs02:enable", kind="omitted")
    ch_03_enable = Cpt(EpicsSignal, "mcs03:enable", kind="omitted")
    ch_04_enable = Cpt(EpicsSignal, "mcs04:enable", kind="omitted")
    ch_05_enable = Cpt(EpicsSignal, "mcs05:enable", kind="omitted")
    ch_06_enable = Cpt(EpicsSignal, "mcs06:enable", kind="omitted")
    ch_07_enable = Cpt(EpicsSignal, "mcs07:enable", kind="omitted")
    ch_08_enable = Cpt(EpicsSignal, "mcs08:enable", kind="omitted")
    ch_09_enable = Cpt(EpicsSignal, "mcs09:enable", kind="omitted")
    ch_10_enable = Cpt(EpicsSignal, "mcs10:enable", kind="omitted")
    ch_11_enable = Cpt(EpicsSignal, "mcs11:enable", kind="omitted")
    ch_12_enable = Cpt(EpicsSignal, "mcs12:enable", kind="omitted")
    ch_13_enable = Cpt(EpicsSignal, "mcs13:enable", kind="omitted")
    ch_14_enable = Cpt(EpicsSignal, "mcs14:enable", kind="omitted")
    ch_15_enable = Cpt(EpicsSignal, "mcs15:enable", kind="omitted")
    ch_16_enable = Cpt(EpicsSignal, "mcs16:enable", kind="omitted")
    ch_17_enable = Cpt(EpicsSignal, "mcs17:enable", kind="omitted")
    ch_18_enable = Cpt(EpicsSignal, "mcs18:enable", kind="omitted")
    ch_19_enable = Cpt(EpicsSignal, "mcs19:enable", kind="omitted")
    ch_20_enable = Cpt(EpicsSignal, "mcs20:enable", kind="omitted")
    ch_21_enable = Cpt(EpicsSignal, "mcs21:enable", kind="omitted")
    ch_22_enable = Cpt(EpicsSignal, "mcs22:enable", kind="omitted")
    ch_23_enable = Cpt(EpicsSignal, "mcs23:enable", kind="omitted")
    ch_24_enable = Cpt(EpicsSignal, "mcs24:enable", kind="omitted")
    ch_25_enable = Cpt(EpicsSignal, "mcs25:enable", kind="omitted")
    ch_26_enable = Cpt(EpicsSignal, "mcs26:enable", kind="omitted")
    ch_27_enable = Cpt(EpicsSignal, "mcs27:enable", kind="omitted")
    ch_28_enable = Cpt(EpicsSignal, "mcs28:enable", kind="omitted")
    ch_29_enable = Cpt(EpicsSignal, "mcs29:enable", kind="omitted")
    ch_30_enable = Cpt(EpicsSignal, "mcs30:enable", kind="omitted")
    ch_31_enable = Cpt(EpicsSignal, "mcs31:enable", kind="omitted")
    ch_00_fbk = Cpt(EpicsSignal, "mcs00:fbk", kind="omitted")
    ch_01_fbk = Cpt(EpicsSignal, "mcs01:fbk", kind="omitted")
    ch_02_fbk = Cpt(EpicsSignal, "mcs02:fbk", kind="omitted")
    ch_03_fbk = Cpt(EpicsSignal, "mcs03:fbk", kind="omitted")
    ch_04_fbk = Cpt(EpicsSignal, "mcs04:fbk", kind="omitted")
    ch_05_fbk = Cpt(EpicsSignal, "mcs05:fbk", kind="omitted")
    ch_06_fbk = Cpt(EpicsSignal, "mcs06:fbk", kind="omitted")
    ch_07_fbk = Cpt(EpicsSignal, "mcs07:fbk", kind="omitted")
    ch_08_fbk = Cpt(EpicsSignal, "mcs08:fbk", kind="omitted")
    ch_09_fbk = Cpt(EpicsSignal, "mcs09:fbk", kind="omitted")
    ch_10_fbk = Cpt(EpicsSignal, "mcs10:fbk", kind="omitted")
    ch_11_fbk = Cpt(EpicsSignal, "mcs11:fbk", kind="omitted")
    ch_12_fbk = Cpt(EpicsSignal, "mcs12:fbk", kind="omitted")
    ch_13_fbk = Cpt(EpicsSignal, "mcs13:fbk", kind="omitted")
    ch_14_fbk = Cpt(EpicsSignal, "mcs14:fbk", kind="omitted")
    ch_15_fbk = Cpt(EpicsSignal, "mcs15:fbk", kind="omitted")
    ch_16_fbk = Cpt(EpicsSignal, "mcs16:fbk", kind="omitted")
    ch_17_fbk = Cpt(EpicsSignal, "mcs17:fbk", kind="omitted")
    ch_18_fbk = Cpt(EpicsSignal, "mcs18:fbk", kind="omitted")
    ch_19_fbk = Cpt(EpicsSignal, "mcs19:fbk", kind="omitted")
    ch_20_fbk = Cpt(EpicsSignal, "mcs20:fbk", kind="omitted")
    ch_21_fbk = Cpt(EpicsSignal, "mcs21:fbk", kind="omitted")
    ch_22_fbk = Cpt(EpicsSignal, "mcs22:fbk", kind="omitted")
    ch_23_fbk = Cpt(EpicsSignal, "mcs23:fbk", kind="omitted")
    ch_24_fbk = Cpt(EpicsSignal, "mcs24:fbk", kind="omitted")
    ch_25_fbk = Cpt(EpicsSignal, "mcs25:fbk", kind="omitted")
    ch_26_fbk = Cpt(EpicsSignal, "mcs26:fbk", kind="omitted")
    ch_27_fbk = Cpt(EpicsSignal, "mcs27:fbk", kind="omitted")
    ch_28_fbk = Cpt(EpicsSignal, "mcs28:fbk", kind="omitted")
    ch_29_fbk = Cpt(EpicsSignal, "mcs29:fbk", kind="omitted")
    ch_30_fbk = Cpt(EpicsSignal, "mcs30:fbk", kind="omitted")
    ch_31_fbk = Cpt(EpicsSignal, "mcs31:fbk", kind="omitted")
    waveform_rbv = Cpt(EpicsSignalRO, "mcs:scan", kind="omitted")

    def __init__(self, prefix, name):
        super(SIS3820ScalarDevice, self).__init__(prefix, name=name)
        self.sigs = BaseDeviceSignals()
        self.new_plot_data = self.sigs.new_plot_data
        self.stream_name = "primary"
        #self.name = name
        self._process_wavefrom_cb = False
        self.row = 0
        self.col = 0
        self.num_rows = 0
        self.num_cols = 0
        self.rawData = None
        self.twoD_data = None
        self.is_staged = False
        self.is_pxp_scan = True
        self.is_spec_scan = False
        self.is_e712_wvgen_scan = False
        self.return_2D_data = False #added for ptycho because all of inner positioners data is collected as it comes in and only read out after an iteration of the inner positioner
        self._prog_dct = make_progress_dict(sp_id=0, percent=0, cur_img_idx=0)

        #flags to remove the points in the line of data that correspond to that scans row change point that should be disgarded
        # a scan should call set_row_change_index_point() before scanning
        self.remove_first_point = False
        self.remove_last_point = False
        self.ignore_even_data_points = False
        self.fix_first_point = False
        self.enable_progress_emit = False

        self.enabled_channels = {}
        self.enabled_channels_lst = []
        self.channel_names = []
        self._cb_ids = []
        self.sp_ids = []

        self.seq_map = {}

        self.spec_spid = None
        self.generate_channel_names()
        self._det_type = detector_types.POINT  # or LINE or 2D
        self._plot_dct = make_counter_to_plotter_com_dct()
        self.update_channel_map()
        self.init_indexs()
        #setup waveform subscription
        self._cb_ids.append(self.waveform_rbv.subscribe(self.on_waveform_changed))

    def calc_cur_progress(self, row, col):
        """
        calculate the current progress, 0-100% oer image
        """
        percent = (row/self.num_rows) * 100.0
        return(percent)

    def set_sequence_map(self, map):
        """
        from a scan plan set teh sequence map so that a progress dict can be emitted if desired
        by using the information from the current sequence and the map to determine the precentage of
        current progress
        """
        self.seq_map = map

    def set_spatial_ids(self, spid_lst):
        """
        load a list of spatial ids so that channel names can be generated properly for spec scans
        """
        self.sp_ids = spid_lst

    def set_spid(self, spid):
        """
        when performing a spectra scan the channel name must include the spatial id of the
        current point so it is set here
        """
        self.spec_spid = spid

    def enable_data_read_for_spectra(self, en):
        """
        enable/disable a flag that will affect how the data is read (the channels names will have the spatial id added)
        for spectra scans
        """
        self.is_spec_scan = en

    def enable_data_read_for_ptychography(self, en):
        """
        enable/disable what data is passed when the read() is called.
        added for ptycho because all of inner positioners data is collected as it comes in and only read out after an iteration of the inner positioner
        """
        self.return_2D_data = en

    def set_row_change_index_points(self, remove_first_point=False,remove_last_point=False,ignore_even_data_points=False,fix_first_point=False):
        """
        a function to be called by the parent scan that sets up which flags need to be set to properly process the line of data
        for a particular scan, not all scans trigger the same that is why this is needed
        """
        # the first point in the line of channel data occurred during row change
        self.remove_first_point = remove_first_point
        # the last point in the line of channel data occurred during row change
        self.remove_last_point = remove_last_point
        # because the E712 cannot reposnd fast enough when the dwell times are set less than 25 ms
        # extra settle time must be added, when this is the case teh triggers the E712 generates will be
        # 2 times what the number of points are and we throw away every even point [0,2,4,6,8...]
        # this is a flag to indicate we are expecting that must ch data and need to ignore the even values
        # of the channels data
        self.ignore_even_data_points = ignore_even_data_points
        #for some software triggered scans the first pixel will contain the last counts value
        self.fix_first_point = fix_first_point

    def abort_scan(self):
        """
        interrupt the SIS3820 in the middle of a scan and ask it to stop
        """
        self.stop_scan.put(1)

    def get_all_channel_names(self):
        """
        a convienience function to return the names of all the sis3820 channels,
        primarily used to tell the parent UI what names to populate a detector selection form with
        """
        return(self.channel_names)

    def kickoff(self):
        # base class call to kickoff will call set_finished() on the status
        self.twoD_data = None
        #_logger.info(f"kickoff: self.twoD_data = None ")
        st = super().kickoff() #this sets the parents _acquiring attr to True

        def check_value(*, old_value, value, **kwargs):
            "Return True when the acquisition is complete, False otherwise."
            return (old_value == 0 and value == 1)

        status = SubscriptionStatus(self.run, check_value)

        self.run.put(1)


        #return st
        return status

    # def complete(self):
    #     # base class call to complete will call set_finished() on the status
    #     #st = super().complete()
    #
    #     def check_value(*, old_value, value, **kwargs):
    #         "Return True when the acquisition is complete, False otherwise."
    #         return (old_value == 1 and value == 0)
    #
    #     status = SubscriptionStatus(self.run, check_value)
    #     #self.run.set(0)
    #     return status
    #     #return st

    def is_running(self):
        run = self.run.get()
        if run:
            return(True)
        else:
            return(False)

    def set_dwell(self, dwell):
        """
        a function used by higher level scans to set the dwell
        """
        self.dwell.put(dwell)

    def setup_for_hdw_triggered(self):
        '''
        configure SIS3820 for hardware trigger
        '''
        self.input_mode.put(1) # 1
        self.output_mode.put(0) # 0
        self.trigger_source.put(1) # hardware
        self.source.put(0) # clocking source is internal [Clock, External, Channel, Preset, VME]
        self.mode.put(0) # MCS
        self.lne_channel.put(0)
        self.preset_val1.put(0)
        self.preset_val2.put(0)
        self.preset_chan2.put(0)
        self.show_rate.put(0)
        self.sub_bkgrnd.put(0)
        self.continuous.put(0)
        self.reset.put(0)
        self.invert_input.put(0)
        self.invert_output.put(0)
        self.user_led.put(0)
        self.is_e712_wvgen_scan = False
        #self.flush_monitors()
        self.enable_on_change_sub()

    def flush_monitors(self):
        """
        for some reason the driver will post a couple monitors when run is toggled on and off
        and a scan has previously run, so here before we start to subscribe to the monitors
        toggle the run pv
        """
        for i in range(4):
            self.run.put(1)
            self.run.put(0)

    def setup_for_ntrigs_per_line(self):
        """
        The settings you need
        for the scaler should be as follows
            dwell = 0
            nscan = points in a line + 1
            scanCount = lines * nscan
            Input mode = Mode 1
            Operational Mode = MCS
            Trigger source = Hardware
            Source = External
        """
        self.dwell.put(0.0)
        self.input_mode.put(1)  # 1
        self.output_mode.put(0)  # 0
        self.trigger_source.put(1)  # hardware
        self.source.put(1) # clocking source is internal [Clock, External, Channel, Preset, VME]
        self.mode.put(0)  # MCS
        self.source.put(1)  # External
        self.lne_channel.put(0)
        self.preset_val1.put(0)
        self.preset_val2.put(0)
        self.preset_chan2.put(0)
        self.show_rate.put(0)
        self.sub_bkgrnd.put(0)
        self.continuous.put(0)
        self.reset.put(0)
        self.invert_input.put(0)
        self.invert_output.put(0)
        self.user_led.put(0)
        self.is_e712_wvgen_scan = True
        #self.flush_monitors()

        #initiate callback subscription here it will be cleared during unstage()
        self.enable_on_change_sub()


    def setup_for_software_triggered(self):
        '''
        configure SIS3820 to read a point when RUN is started for dwell time
        '''
        self.input_mode.put(0) # 0
        self.output_mode.put(0) # 0
        self.trigger_source.put(0) # Software
        self.source.put(0)  # clocking source is internal [Clock, External, Channel, Preset, VME]
        self.mode.put(0) # MCS
        self.source.put(0) # clock
        self.lne_channel.put(0)
        self.preset_val1.put(0)
        self.preset_val2.put(0)
        self.preset_chan2.put(0)
        self.show_rate.put(0)
        self.sub_bkgrnd.put(0)
        self.continuous.put(0)
        self.reset.put(0)
        self.invert_input.put(0)
        self.invert_output.put(0)
        self.user_led.put(0)
        self.is_e712_wvgen_scan = False
        #ensure subscription is disabled
        self.disable_on_change_sub()
        #self.flush_monitors()


    def enable_on_change_sub(self):
        #print("enable_on_change_sub: self._process_wavefrom_cb = True")
        self._process_wavefrom_cb = True
        # self.disable_on_change_sub()
        # print("enable_on_change_sub: self._cb_ids.append(self.waveform_rbv.subscribe(self.on_waveform_changed))")
        # self._cb_ids.append(self.waveform_rbv.subscribe(self.on_waveform_changed))
        # #self._cb_ids.append(self.on_waveform_changed)

    def disable_on_change_sub(self):
        #print("disable_on_change_sub: self._process_wavefrom_cb = False")
        self._process_wavefrom_cb = False
        #self.waveform_rbv.clear_sub(self.on_waveform_changed)
        # print("disable_on_change_sub: self.waveform_rbv.unsubscribe_all()")
        # #self.waveform_rbv.unsubscribe_all()
        # for cb_id in self._cb_ids:
        #     self.waveform_rbv.unsubscribe(cb_id)

        #self.waveform_rbv._read_pv.clear_callbacks()
        # for cbid in self._cb_ids:
        #     self.waveform_rbv.unsubscribe(cbid)
        #
        #     self._cb_ids.remove(cbid)

    def on_waveform_changed(self, *args, **kwargs):
        if self.is_staged:
            if self._process_wavefrom_cb:
                self.rawData = copy.copy(kwargs["value"])
                self.process_sis3820_data(kwargs)


    def process_sis3820_data(self, kwargs):
        """
        kwargs is an EPICS dict used for callbacks
        """

        do_emit = False
        data_dct = {}
        #ch_id_lst, ch_nm_lst, en_chan_fbk_attrs = self.get_enabled_chans()
        #num_chans = len(ch_nm_lst)
        #self.enabled_channels_lst.append({"chan_nm": ch_nm, "chan_num": i})
        num_chans = len(self.enabled_channels_lst)
        arr = kwargs['value']

        if type(arr) == np.ndarray:

            # skip total array length number
            arr = arr[1:]
            _cols, = arr.shape
            if _cols < self.num_cols:
                #ignore
                return
            #take a slice of data array to pull out all values of each channel
            for ch_num in range(num_chans):
                #chan_nm = ch_nm_lst[ch_num]
                chan_nm = self.enabled_channels_lst[ch_num]["chan_nm"]
                _num = ch_num + 1
                # numpy slicing start:stop:step to get each channels data
                dat = arr[_num-1::num_chans]
                fix_first_point = False
                if self.row == 0:
                    fix_first_point = True

                # if self.ignore_even_data_points:
                #     remove_last = False
                # else:
                #     remove_last = True
                #
                # remove_first = False

                #stripped_dat = sis3820_remove_row_change_extra_point(dat, ignore_even_data_points=self.ignore_even_data_points, fix_first_point=fix_first_point, remove_first=remove_first, remove_last=remove_last)
                stripped_dat = sis3820_remove_row_change_extra_point(dat,
                                    ignore_even_data_points=self.ignore_even_data_points,
                                    fix_first_point=fix_first_point,
                                    remove_first=self.remove_first_point,
                                    remove_last=self.remove_last_point)

                # if ch_num == 0:
                #     print(f"sis3820_scalar.py: process_sis3820_data: chan 0 data: raw", dat)
                #     print(f"sis3820_scalar.py: process_sis3820_data: chan 0 data: STRIPPED", stripped_dat)
                #     print()
                # print(dat.shape)
                # print(stripped_dat.shape)
                if self.is_spec_scan:
                    #generate the correct channel name with spid
                    chan_nm = gen_complete_spec_chan_name(chan_nm, self.spec_spid)
                data_dct[chan_nm] = stripped_dat

            row_chan_dct = {}
            row_chan_dct[self.row] = data_dct
            # keep this data for collect to process
            if self.twoD_data is None:
                _logger.debug(f"twoD_data should not be None here")
                self.twoD_data = {}

            self.twoD_data[self.row] = data_dct

            if self.enable_progress_emit:
                percent = self.calc_cur_progress(self.row, self.col)
                img_num = self.seq_map[self.seq_cntr]["img_num"]
                ev_idx = self.seq_map[self.seq_cntr]["ev_idx"]
                pol_idx = self.seq_map[self.seq_cntr]["pol_idx"]

                set_prog_dict(self._prog_dct, sp_id=0, percent=percent, cur_img_idx=img_num, ev_idx=ev_idx,
                              pol_idx=pol_idx)
                plot_dct = make_counter_to_plotter_com_dct(self.row, self.col, data_dct, is_point=self.is_pxp_scan, prog_dct=self._prog_dct)
                self.seq_cntr += 1

            else:
                plot_dct = make_counter_to_plotter_com_dct(self.row, self.col, data_dct, is_point=self.is_pxp_scan, prog_dct={})

            self.new_plot_data.emit(plot_dct)

            self.increment_indexes()

    def set_config(self, rows, cols, is_pxp_scan=False, is_e712_wg_scan=False, pxp_single_trig=False):
        self.abort_scan()
        self.init_indexs()
        self.seq_cntr = 0
        self.num_rows = rows
        self.num_cols = cols
        self.is_pxp_scan = is_pxp_scan
        if is_pxp_scan and not is_e712_wg_scan:
            self.enable_progress_emit = False
            #all point by point scans, det, osa etc
            self.ignore_even_data_points = False
            self.num_acqs.put(1)
            # make it 2 counts as first in buffer is always huge and inaccurate
            #self.num_acqs_per_trig.put(2)
            self.num_acqs_per_trig.put(1)
        elif pxp_single_trig:
            self.enable_progress_emit = True
            self.num_cols = 0  # this forces self.row to increment each iteration of the sequence when self.increment_indexes
            # point scan by Ptychography
            self.ignore_even_data_points = False
            cols = cols + SIS3820_EXTRA_PNTS
            self.num_acqs.put(cols)
            self.num_acqs_per_trig.put(rows * cols)

        elif is_pxp_scan and is_e712_wg_scan:
            self.enable_progress_emit = True
            self.num_cols = 0 #this forces self.row to increment each iteration of the sequence when self.increment_indexes
            # point scan
            self.ignore_even_data_points = True
            cols = (cols * 2)# + SIS3820_EXTRA_PNTS
            self.num_acqs.put(cols)
            self.num_acqs_per_trig.put(rows * cols)

        elif not is_pxp_scan and is_e712_wg_scan:
            self.enable_progress_emit = True
            #line scan
            #cols = cols + SIS3820_EXTRA_PNTS
            self.ignore_even_data_points = False
            cols = cols + SIS3820_EXTRA_PNTS
            self.num_acqs.put(cols)
            self.num_acqs_per_trig.put(rows * cols)
        else:
            self.enable_progress_emit = False
            #coarseImage scan
            self.ignore_even_data_points = False
            self.num_acqs.put(cols + SIS3820_EXTRA_PNTS)
            #self.num_acqs_per_trig.put(rows + SIS3820_EXTRA_PNTS)
            #need the num acqs per trig to be same a num acqs so that an entire line is emitted
            self.num_acqs_per_trig.put(cols + SIS3820_EXTRA_PNTS)

    def generate_channel_names(self):
        """
        one place to generate the names that will be used in code and emitted to connected signals
        """
        self.channel_names = []
        for i in range(0,32):
            nm = f"{self.name}_CHAN_{str(i).zfill(2)}"
            # strip the DNM_ if it exists
            nm = nm.replace("DNM_", "")
            # if self.is_spec_scan and len(self.sp_ids) > 0:
            #     for sp_id in self.sp_ids:
            #         #generate the correct channel name with spid
            #         self.channel_names.append(gen_complete_spec_chan_name(nm, sp_id))
            # else:
            #     nm = f"{self.name}_CHAN_{str(i).zfill(2)}"
            #     self.channel_names.append(nm)
            nm = f"{self.name}_CHAN_{str(i).zfill(2)}"
            self.channel_names.append(nm)

    def update_channel_map(self):
        '''
        check to see which channels are enabled so that the channel ID can be emitted along with the data
        remember that the data in the array is in the order of enabled channels
        '''
        #self.generate_channel_names()
        self.enabled_channels = {}
        self.enabled_channels_lst = []
        data_order_idx = 0
        # from 0 - 31
        for i in range(0,32):
            attr_ch_nm = f"ch_{str(i).zfill(2)}_enable"
            #ch_nm = f"{self.name}_CHAN_{str(i).zfill(2)}"
            ch_nm = self.channel_names[i]
            attr = getattr(self, attr_ch_nm)
            val = attr.get()
            fbk_attr_ch_nm = f"ch_{str(i).zfill(2)}_fbk"
            fbk_attr = getattr(self, fbk_attr_ch_nm)

            if val > 0:
                # dict indexed by the index into the data array and holds the actual channel number (0-31)
                # so for example the first data array value is from channel 15 if
                # self.enabled_channels[0] = {'chan_num': 15}
                self.enabled_channels[data_order_idx] = {"chan_nm": ch_nm, "chan_num": i, "fbk_attr": fbk_attr}
                self.enabled_channels_lst.append({"chan_nm": ch_nm, "chan_num": i})
                data_order_idx = data_order_idx + 1

    def disable_all_channels(self):
        """
        this is called by parent that is passing in a list of channels that the user has selected
        given a list of channels to enable walk the list and call put on each,

        """
        # disable all channels not in list
        for i in range(0,32):
            attr_ch_nm = f"ch_{str(i).zfill(2)}_enable"
            attr = getattr(self, attr_ch_nm)
            if attr:
                #disable it
                attr.put(0)

    def is_chan_enabled(self, chan_name):
        """
        given a channel name return if it is currently enabled or not in EPICS
        """
        chan = self.get_chan_num_from_name(chan_name)
        attr_ch_nm = f"ch_{str(chan).zfill(2)}_enable"
        attr = getattr(self, attr_ch_nm)
        en = attr.get()
        if en:
            return(True)
        else:
            return(False)

    def enable_channel(self, chan_name, en):
        """
        this is called by parent that is passing in a channel name that the user has selected
        """
        chan = self.get_chan_num_from_name(chan_name)
        if chan > -1 and chan < 32:
            attr_ch_nm = f"ch_{str(chan).zfill(2)}_enable"
            attr = getattr(self, attr_ch_nm)
            if attr:
                # enable or disable it
                attr.put(en)

    def get_chan_num_from_name(self, nm):
        nm = nm.replace("DNM_","")
        chan = int(nm.replace('SIS3820_CHAN_',''))
        return(chan)

    def get_enabled_chans(self, update_map=True):
        '''
        return a list of channel numbers that are enabled
        '''
        if update_map:
            self.update_channel_map()
        ch_id_lst = []
        ch_nm_lst = []
        ch_fbk_lst = []
        for idx, ch_dct in self.enabled_channels.items():
            ch_id_lst.append(ch_dct['chan_num'])
            ch_nm_lst.append(ch_dct['chan_nm'])
            ch_fbk_lst.append(ch_dct['fbk_attr'])
        return(ch_id_lst, ch_nm_lst, ch_fbk_lst)

    def report(self):
        print("name = %s, type = %s" % (str(self.__class__), self.name))

    def init_indexs(self):
        '''
        initialize the different row and column indexes
        '''
        self.row = 0
        self.col = 0
        # self.num_rows = 0
        # self.num_cols = 0
        # self.seq_cntr = 0

    def increment_indexes(self):
        '''
        increment the different indexes based on a pxp scan or lxl
        '''
        #self.seq_cntr += 1
        if self.is_pxp_scan:
            if (self.col + 1) > self.num_cols:
                # start a new row
                self.col = 0
                self.row = self.row + 1
            else:
                self.col = self.col + 1
        else:
            # is lxl
            self.row = self.row + 1

    # def trigger(self):
    #     #self.update_channel_map()
    #     st = super().trigger()
    #     return st

    # def trigger(self):
    #     """
    #     this one works most of the time
    #     """
    #     if self.is_pxp_scan:
    #         self.run.put(1)
    #     # def check_value(*, old_value, value, **kwargs):
    #     #     "Return True when the acquisition is complete, False otherwise."
    #     #     return (old_value == 1 and value == 0)
    #     #
    #     # status = SubscriptionStatus(self.run, check_value)
    #     #self.run.set(0)
    #     st = super().trigger()
    #     return st

    def trigger(self):
        """
        this one works most of the time, but testing check_value
        """
        if not self.is_pxp_scan:
            #print("SIS3820: trigger: not self.is_pxp_scan")
            st = super().trigger()
            return(st)

        def check_value(*, old_value, value, **kwargs):
            "Return True when the acquisition is complete, False otherwise."
            return (old_value == 1 and value == 0)

        status = SubscriptionStatus(self.run, check_value)
        if self.is_pxp_scan:
            #print("sis3820_scalar: trigger: self.is_pxp_scan: calling run(1)")
            self.run.put(1)

        return status


    # def trigger(self):
    #     def check_value(*, old_value, value, **kwargs):
    #         print("SIS3820: check_value before if")
    #         #"Mark status as finished when the acquisition is complete."
    #         if old_value == 1 and value == 0:
    #             print("SIS3820: calling status.set_finished()")
    #             status.set_finished()
    #             # Clear the subscription.
    #             self.run.clear_sub(check_value)
    #
    #     status = DeviceStatus(self.run)
    #     self.run.subscribe(check_value)
    #     self.run.set(1)
    #     print("SIS3820: setting run to 1, returning status")
    #     return status

    # def trigger(self):
    #     def check_value(*, old_value, value, **kwargs):
    #         "Return True when the run is complete, False otherwise."
    #         return (old_value == 1 and value == 0)
    #
    #     status = SubscriptionStatus(self.run, check_value)
    #     self.run.set(1)
    #     return status

    # def complete(self):
    #     def check_value(*, old_value, value, **kwargs):
    #         #"Return True when the run is complete, False otherwise."
    #         return (old_value == 1 and value == 0)
    #
    #     status = SubscriptionStatus(self.run, check_value)
    #     #self.run.set(1)
    #     return status


    def stage(self):
        st = super().stage()
        self.update_channel_map()
        #self.enable_on_change_sub()
        self.is_staged = True
        return st

    def unstage(self):
        # make sure
        #self.disable_on_change_sub()
        self.abort_scan()
        self.is_staged = False
        st = super().unstage()
        self.run.put(0)
        #st._finished = True

        return st

    def describe(self):
        desc = dict()
        en_chan_nums, en_chan_nms, en_chan_fbk_attrs = self.get_enabled_chans()
        if self.is_pxp_scan:
            desc = {}
            desc[self.name + '_waveform_rbv'] = {}
            desc[self.name + '_waveform_rbv']["shape"] = [self.num_rows, self.num_cols]
            desc[self.name + '_waveform_rbv']["dtype"] = "number"
            desc[self.name + '_waveform_rbv']["source"] = "PVNAME"
            desc[self.name + '_waveform_rbv']["chan_nms"] = en_chan_nms
            desc[self.name + '_waveform_rbv']["chan_nums"] = en_chan_nums
            desc[self.name + '_waveform_rbv']["chan_dct"] = {}
            desc[self.name + '_waveform_rbv']["col"] = ""
            desc[self.name + '_waveform_rbv']["row"] = ""
            desc[self.name + '_waveform_rbv']["sis3820_extra_pnts"] = SIS3820_EXTRA_PNTS

        else:
            desc.update(self.waveform_rbv.describe())
            #desc[self.name + '_waveform_rbv'] = {}
            desc[self.name + '_waveform_rbv']["shape"] = [self.num_rows, self.num_cols]
            desc[self.name + '_waveform_rbv']["dtype"] = "number"
            desc[self.name + '_waveform_rbv']["source"] = "PVNAME"
            desc[self.name + '_waveform_rbv']["chan_nms"] = en_chan_nms
            desc[self.name + '_waveform_rbv']["chan_nums"] = en_chan_nums
            desc[self.name + '_waveform_rbv']["chan_dct"] = {}
            desc[self.name + '_waveform_rbv']["col"] = ""
            desc[self.name + '_waveform_rbv']["row"] = ""
            desc[self.name + '_waveform_rbv']["sis3820_extra_pnts"] = SIS3820_EXTRA_PNTS
            # desc[self.name + '_waveform_rbv']["timestamp"] = ""
        return desc

    def get_read_chan_dict(self):
        """
        walk all enabled channels reading the values and return in a dict
        """
        dct = {}
        en_chan_nums, en_chan_nms, en_chan_fbk_attrs = self.get_enabled_chans(update_map=False)
        for i in range(len(en_chan_nums)):
            ch_nm = en_chan_nms[i]
            if self.is_spec_scan:
                # generate the correct channel name with spid
                ch_nm = gen_complete_spec_chan_name(ch_nm, self.spec_spid)
            fbk_attr = en_chan_fbk_attrs[i]
            val = np.array([fbk_attr.get()])
            dct[ch_nm] = val
        return dct

    def read(self):
        '''
        if the current scan is lxl then I need to have an
        '''
        # print('SIS3820ScalarDevice: read called')
        # return(self.waveform_rbv.get())

        if self.is_pxp_scan:
            # {'DNM_SIS3820_waveform_rbv': {'value': {'DNM_SIS3820_CHAN_00': array([8005]), 'DNM_SIS3820_CHAN_15': array([5119])}, 'timestamp': 1694195834.472079}}
            dct = {
                self.name + '_waveform_rbv': {'value': self.get_read_chan_dict(), "timestamp": time.time()
                                              }
            }

        else:
            #line data
            self.rawData = self.waveform_rbv.get()
            # note the first data point in the array returned is the number of enabled channels
            if hasattr(self.rawData, "shape"):
                _nsamples, = self.rawData.shape
                en_chan_nums, en_chan_nms, en_chan_fbk_attrs = self.get_enabled_chans(update_map=False)
                num_chans = len(en_chan_nums)
                if _nsamples == 0:
                    dct = {
                        self.name + '_waveform_rbv': {
                            "value": [0],
                            "timestamp": time.time(),
                            "chan_nms": en_chan_nms,
                            "chan_nums": en_chan_nums,
                            "chan_dct": {},
                            "col": int(self.col),
                            "row": int(self.row),

                        }
                    }
                    return(dct)
                #print("self.rawdata.shape", self.rawData.shape)
                data = self.rawData[1:]
                if self.return_2D_data:
                    #self.twoD_data contains a dictionary using the row number as the key to a dictionary whose
                    # keys are the channel names and values are 1 rows worth of points
                    dct = {}
                    # append each rows data to that channels total data
                    for row_num, data_dct in self.twoD_data.items():
                        for k in data_dct.keys():
                            if k not in dct.keys():
                                dct[k] = []
                            dct[k] += list(data_dct[k])

                    #return a dict of channels with 1D data
                    _data = dct
                else:
                    _data = self.read_process_sis3820_data(data)

                dct = {
                    self.name + '_waveform_rbv': {
                        "value": _data,
                        "timestamp": time.time(),
                        # "chan_dct": self.read_process_sis3820_data(data),
                    }
                }

        self.increment_indexes()
        # print(dct)
        return(dct)
    # def read(self):
    #     '''
    #     if the current scan is lxl then I need to have an
    #     '''
    #     # print('SIS3820ScalarDevice: read called')
    #     # return(self.waveform_rbv.get())
    #
    #
    #     #line data
    #     self.rawData = self.waveform_rbv.get()
    #     # note the first data point in the array returned is the number of enabled channels
    #     if hasattr(self.rawData, "shape"):
    #         _nsamples, = self.rawData.shape
    #         en_chan_nums, en_chan_nms, en_chan_fbk_attrs = self.get_enabled_chans()
    #         num_chans = len(en_chan_nums)
    #         if _nsamples == 0:
    #             dct = {
    #                 self.name + '_waveform_rbv': {
    #                     "value": [0],
    #                     "timestamp": time.time(),
    #                     "chan_nms": en_chan_nms,
    #                     "chan_nums": en_chan_nums,
    #                     "chan_dct": {},
    #                     "col": int(self.col),
    #                     "row": int(self.row),
    #
    #                 }
    #             }
    #             return(dct)
    #         #print("self.rawdata.shape", self.rawData.shape)
    #         data = self.rawData[1:]
    #         if self.return_2D_data:
    #             #self.twoD_data contains a dictionary using the row number as the key to a dictionary whose
    #             # keys are the channel names and values are 1 rows worth of points
    #             dct = {}
    #             # append each rows data to that channels total data
    #             for row_num, data_dct in self.twoD_data.items():
    #                 for k in data_dct.keys():
    #                     if k not in dct.keys():
    #                         dct[k] = []
    #                     dct[k] += list(data_dct[k])
    #
    #             #return a dict of channels with 1D data
    #             _data = dct
    #         else:
    #             _data = self.read_process_sis3820_data(data)
    #
    #         dct = {
    #             self.name + '_waveform_rbv': {
    #                 "value": _data,
    #                 "timestamp": time.time(),
    #                 # "chan_dct": self.read_process_sis3820_data(data),
    #             }
    #         }
    #
    #         self.increment_indexes()
    #         return(dct)



    def read_process_sis3820_data(self, arr):
        """
        arr is a numpy array of the 1D data of all channels into a channel dictionary
        { "chan name 1": data,
        "chan name 2": data}
        and return it
        """

        do_emit = False
        data_dct = {}
        ch_id_lst, ch_nm_lst, en_chan_fbk_attrs = self.get_enabled_chans(update_map=False)
        num_chans = len(ch_nm_lst)
        #print("read_process_sis3820_data:")

        if type(arr) == np.ndarray:
            # skip total array length number
            arr_cols, = arr.shape
            if (not self.is_pxp_scan) and (arr_cols < self.num_cols):
                #ignore
                return
            #take a slice of data array to pull out all values of each channel
            for ch_num in range(num_chans):
                _chan_nm = ch_nm_lst[ch_num]
                _num = ch_num + 1
                # numpy slicing start:stop:step
                dat = arr[_num-1::num_chans]
                stripped_dat = sis3820_remove_row_change_extra_point(dat,
                                                                     ignore_even_data_points=self.ignore_even_data_points,
                                                                     fix_first_point=self.fix_first_point,
                                                                     remove_first=self.remove_first_point,
                                                                     remove_last=self.remove_last_point)
                #set chan_nm
                chan_nm = _chan_nm
                #print(dat.shape)
                if self.is_spec_scan:
                    #generate the correct channel name with spid
                    chan_nm = gen_complete_spec_chan_name(_chan_nm, self.spec_spid)

                #print(f"SIS3820: read() channel name to {chan_nm}")
                data_dct[chan_nm] = stripped_dat

        return(data_dct)


    def describe_collect(self):
        """Describe details for the flyer collect() method"""
        desc = dict()
        desc.update(self.waveform_rbv.describe())
        k = list(desc.keys())[0]
        desc[k]['shape'] = (self.row*self.col,)
        d = {self.stream_name: desc}
        # print('describe_collect: ', d)
        return d

    def complete(self):
        # base class call to complete will call set_finished() on the status
        # if self.is_e712_wvgen_scan:
        #     self.disable_on_change_sub()

        st = super().complete()
        return st

    def merge_row_data_into_2d(self):
        """
        walk all of the rows of indiv chan data of all enabled channels and create a 2D array/list of each channels rows of data
        """
        dct = {}
        if self.twoD_data:
            for row, d in self.twoD_data.items():
                for k in d.keys():
                    if k not in dct.keys():
                        dct[k] = []
                    dct[k].append(d[k])
            # ret_dct = {}
            # for k in dct.keys():
            #     ret_dct[k] = np.array(dct[k], dtype=np.int)
            # return(ret_dct)
        return(dct)

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
                    time=time.time(),
                    timestamps={attr: data["timestamp"]},
                    #data={attr: data['value']},
                    data={attr: self.merge_row_data_into_2d()},
                )
                self.twoD_data = None
                #_logger.info(f"collect: self.twoD_data = None ")
                yield d



def sis3820_remove_row_change_extra_point(chan_data, ignore_even_data_points=False, fix_first_point=False, remove_first=False, remove_last=False):
    """
    a common function to be called by routines to take an individual channels data
    """
    #set the default
    stripped_chan_dat = chan_data

    #now see if it needs to be modified
    if ignore_even_data_points:
        # remove all the even indexed values
        stripped_chan_dat = chan_data[::2]

    if remove_first:
        # strip the first number
        stripped_chan_dat = chan_data[1:]

    if remove_last:
        # strip last number
        stripped_chan_dat = chan_data[:-1]

    if fix_first_point:
        # the first point of the first line is garbage
        # so copy second point into first
        stripped_chan_dat[0] = stripped_chan_dat[1]

    return stripped_chan_dat



if __name__ == '__main__':
    import sys
    import numpy as np
    from bluesky import RunEngine
    from databroker import Broker
    import bluesky.plan_stubs as bps
    import bluesky.preprocessors as bpp
    from ophyd.sim import det1, det2, det3, motor1, motor2
    from bcm.devices.ophyd.stxm_sample_mtr import e712_sample_motor
    from cls.utils.profile .profile_it import determine_profile_bias_val
    from ophyd import EpicsMotor
    from epics import PV
    import pprint

    def a_scan(dets, motors, rois, num_ev_pnts=4, md={}):

        @bpp.baseline_decorator(motors)
        @bpp.stage_decorator(dets)
        @bpp.run_decorator(md=md)
        def do_scan():
            ACCEL_DISTANCE = 1.0
            #det = dets[0]
            x_roi = rois['x']
            y_roi = rois['y']
            mtr_x = motors[0]
            mtr_y = motors[1]
            sisdev = dets[0]
            # a scan with 10 events
            for y_sp in y_roi['SETPOINTS']:
                yield from bps.mv(sisdev.run, 1)
                yield from bps.mv(mtr_y, y_sp)
                yield from bps.mv(mtr_x, x_roi['STOP'] + ACCEL_DISTANCE)
                yield from bps.mv(mtr_x, x_roi['START'] - ACCEL_DISTANCE)
                yield from bps.trigger_and_read(dets)
        return (yield from do_scan())

    def twoD_raster_pxp_scan(dets, motors, rois, num_ev_pnts=4, md={}):

        @bpp.baseline_decorator(motors)
        @bpp.stage_decorator(dets)
        @bpp.run_decorator(md=md)
        def do_scan():
            ACCEL_DISTANCE = 1.0
            #det = dets[0]
            x_roi = rois['x']
            y_roi = rois['y']
            mtr_x = motors[0]
            mtr_y = motors[1]
            sisdev = dets[0]
            # a scan with 10 events
            for y_sp in y_roi['SETPOINTS']:
                yield from bps.mv(mtr_y, y_sp)
                for x_sp in x_roi['SETPOINTS']:
                    yield from bps.mv(mtr_x, x_sp)
                    #yield from bps.mv(sisdev.run, 1)
                    yield from bps.trigger_and_read(dets)
        return (yield from do_scan())

    def twoD_raster_lxl_scan(dets, motors, rois, num_ev_pnts=4, md={}):

        @bpp.baseline_decorator(motors)
        @bpp.stage_decorator(dets)
        @bpp.run_decorator(md=md)
        def do_scan():
            ACCEL_DISTANCE = 1.0
            #det = dets[0]
            x_roi = rois['x']
            y_roi = rois['y']
            mtr_x = motors[0]
            mtr_y = motors[1]
            sisdev = dets[0]
            scan_velo = mtr_x.velocity.get()
            yield from bps.mv(mtr_x, x_roi['START'], group='BB')
            yield from bps.mv(mtr_y, y_roi['START'], group='BB')
            yield from bps.wait('BB')
            # a scan with 10 events
            for y_sp in y_roi['SETPOINTS']:
                yield from bps.mv(mtr_x.velocity, scan_velo)
                yield from bps.mv(sisdev.run, 1, group='SIS3820')
                #yield from bps.trigger(sisdev)
                yield from bps.mv(mtr_y, y_sp)
                yield from bps.mv(mtr_x, x_roi['STOP'] + ACCEL_DISTANCE, group='BB')
                yield from bps.wait('BB')
                yield from bps.trigger_and_read(dets)
                yield from bps.mv(mtr_x.velocity,2000)
                yield from bps.mv(mtr_x, x_roi['START'] - ACCEL_DISTANCE, group='CC')
                yield from bps.wait('CC')
                #print("bottom of loop")
                

        return (yield from do_scan())


    def twoD_raster_lxl_flyer_scan(dets, motors, rois, num_ev_pnts=4, md={}):

        @bpp.baseline_decorator(motors)
        @bpp.stage_decorator(dets)
        @bpp.run_decorator(md=md)
        def do_scan():
            ACCEL_DISTANCE = 1.0
            # det = dets[0]
            x_roi = rois['x']
            y_roi = rois['y']
            mtr_x = motors[0]
            mtr_y = motors[1]
            sisdev = dets[0]
            scan_velo = mtr_x.velocity.get()
            yield from bps.mv(mtr_x.velocity, 2000)
            yield from bps.mv(mtr_x, x_roi['START'] - ACCEL_DISTANCE, group='CC')
            # a scan with 10 events
            for y_sp in y_roi['SETPOINTS']:
                yield from bps.mv(mtr_x.velocity, scan_velo)
                #yield from bps.mv(sisdev.run, 1, group='SIS3820')
                yield from bps.kickoff(sisdev)
                yield from bps.mv(mtr_y, y_sp)
                yield from bps.mv(mtr_x, x_roi['STOP'] + ACCEL_DISTANCE, group='BB')
                yield from bps.wait('BB')
                #yield from bps.wait('SIS3820')
                #yield from bps.trigger_and_read(dets)
                yield from bps.complete(sisdev)
                yield from bps.collect(sisdev)
                yield from bps.mv(mtr_x.velocity, 2000)
                yield from bps.mv(mtr_x, x_roi['START'] - ACCEL_DISTANCE, group='BB')
                yield from bps.wait('BB')
                #print("bottom of loop")

        return (yield from do_scan())


    def process_sis3820_data(md, doc):
        """
        ('event', {'descriptor': '3b9f225b-9f74-4ae1-a468-c347bb7e5cff', 'uid': '9e7561cc-9231-4d6d-afae-1190a7ee0cbd', 'time': 1676490522.2321472, 'seq_num': 50, 'data': {'SIS3820_waveform_rbv': [0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044]}, 'timestamps': {'SIS3820_waveform_rbv': 1676490522.2321472}, 'filled': {}, '_name': 'Event'})
        """
        data_dct = {}
        data_map = md['data_map']
        num_chans = len(md['data_map'])
        d_keys = list(doc[1]['data'].keys())
        for k in d_keys:
            if k.find('SIS3820') > -1:
                data_lst = doc[1]['data'][k]
                if type(data_lst) == list:
                    arr = np.array(data_lst)
                    #take a slice of data array to pull out all values of each channel
                    for ch_num in range(num_chans):
                        ch_dct = data_map[ch_num]
                        _num = ch_num + 1

                        # numpy slicing start:stop:step
                        dat = arr[_num-1::num_chans]
                        dat = sis3820_remove_row_change_extra_point(self.row, dat, ignore_even_data_points=False)
                        dat = dat[:-1]
                        data_dct[ch_dct['chan_nm']] = dat

            pprint.pprint(data_dct)
    
    def time_test_line_process():
        global sis3820_dev
        sis3820_dev.is_staged = True
        sis3820_dev._process_wavefrom_cb = True
        wv_dat = sis3820_dev.waveform_rbv.get()
        sis3820_dev.on_waveform_changed(None, value=wv_dat)


    def profile_it(bval=None):
        """
        profile_it(): description

        :param func : the function to profile
        :type bval: bias val

        :returns: None
        """
        import profile
        import pstats

        if bval == None:
            bval = determine_profile_bias_val()
        else:
            bval = 3.7343376566234334e-06

        profile.Profile.bias = bval

        profile.run("time_test_line_process()", "sis3820_prof.dat")

        p = pstats.Stats("sis3820_prof.dat")
        p.sort_stats("cumulative").print_stats(100)

    # def qt_plot_handler(plot_dct):
    #     print(plot_dct)
    # from PyQt5.QtWidgets import QApplication
    #
    # app = QApplication([])

    # piezo_mtr = EpicsMotor('PZAC1610-3-I12-40', name="sfx")
    cx_mtr = EpicsMotor("SMTR1610-3-I12-45", name="CoarseX")
    cy_mtr = EpicsMotor("SMTR1610-3-I12-46", name="CoarseY")
    piezo_mtr_x = e712_sample_motor('PZAC1610-3-I12-40', name="sfx")
    piezo_mtr_y = e712_sample_motor('PZAC1610-3-I12-41', name="sfy")


    sis3820_dev = SIS3820ScalarDevice('MCS1610-310-01:', name='SIS3820')
    pprint.pprint(sis3820_dev.describe())
    pprint.pprint(sis3820_dev.read())
    sis3820_dev.enable_on_change_sub()
    profile_it(3.7343376566234334e-06)

    # #sis3820_dev.new_plot_data.connect(qt_plot_handler)
    #
    # #sis3820_dev.setup_for_software_triggered()
    # is_pxp_scan = False
    # coarse = False
    # if coarse:
    #     dwell = 50.0# ms
    #     sis3820_dev.dwell.put(dwell)
    #     rng = 500 # um
    #     hlf_rng = rng * 0.5
    #     start = (-1.0*hlf_rng) - (rng *0.05)
    #     stop = hlf_rng + (rng *0.05)
    #     cols = 50
    #     rows = 50
    #     scan_velo = rng / ((cols * dwell) * 0.001)
    # else:
    #     if is_pxp_scan:
    #         #fine
    #         dwell = 1.0  # ms
    #         sis3820_dev.dwell.put(dwell)
    #         rng = 10  # um
    #         hlf_rng = rng * 0.5
    #         start = (-1.0 * hlf_rng) - (rng * 0.05)
    #         stop = hlf_rng + (rng * 0.05)
    #         cols = 25
    #         rows = 25
    #         scan_velo = 2000
    #     else:
    #         # fine
    #         dwell = 1.0  # ms
    #         sis3820_dev.dwell.put(dwell)
    #         rng = 50  # um
    #         hlf_rng = rng * 0.5
    #         start = (-1.0 * hlf_rng) - (rng * 0.05)
    #         stop = hlf_rng + (rng * 0.05)
    #         cols = 50
    #         rows = 50
    #         scan_velo = rng / ((cols * dwell) * 0.001)
    #
    # piezo_mtr_x.scan_start.put(start)
    # piezo_mtr_x.scan_stop.put(stop)
    # piezo_mtr_x.marker_start.put(-1.0*hlf_rng)
    # piezo_mtr_x.marker_stop.put(hlf_rng)
    # piezo_mtr_x.set_marker.put(-1.0*hlf_rng)
    #
    # sis3820_dev.set_config(rows, cols, is_pxp_scan=is_pxp_scan)
    #
    # x_roi = {'START': start, 'STOP':stop, 'SETPOINTS':np.linspace(start,stop, cols)}
    # y_roi = {'START': start, 'STOP':stop, 'SETPOINTS': np.linspace(start,stop, cols)}
    # # the following produces a 10 event run
    # RE = RunEngine({})
    # db = Broker.named("pystxm_amb_bl10ID1")
    # # Insert all metadata/data captured into db.
    # RE.subscribe(db.insert)
    # dets = [sis3820_dev]
    # # get the start time
    # st = time.time()
    #
    # md = {"scan_type": "test_scan", "data_map": copy.copy(sis3820_dev.enabled_channels_lst)}
    # do_fly = True
    # if rng < 150:
    #     piezo_mtr_x.servo_power.put(1)
    #     piezo_mtr_y.servo_power.put(1)
    #     if is_pxp_scan:
    #         sis3820_dev.setup_for_software_triggered()
    #         x_mtr = piezo_mtr_x
    #         y_mtr = piezo_mtr_y
    #         uid = RE(twoD_raster_pxp_scan(dets, motors=[x_mtr, y_mtr], rois={'x': x_roi, 'y': y_roi},md=md))
    #     else:
    #         #E712 WG controlled scan
    #         sis3820_dev.setup_for_ntrigs_per_line()
    #         x_mtr = piezo_mtr_x
    #         y_mtr = motor2
    #         xx = 0
    #         while xx < 999999:
    #             xx += 1
    #             time.sleep(0.1)
    #
    #         uid = RE(twoD_raster_lxl_flyer_scan(dets, motors=[x_mtr, y_mtr], rois={'x': x_roi, 'y': y_roi},md=md))
    # else:
    #     #line by line with coarse motors
    #     piezo_mtr_x.servo_power.put(0)
    #     piezo_mtr_y.servo_power.put(0)
    #     sis3820_dev.setup_for_hdw_triggered()
    #     cx_mtr.velocity.put(scan_velo)
    #     uid = RE(twoD_raster_lxl_scan(dets, motors=[cx_mtr, cy_mtr], rois={'x': x_roi, 'y': y_roi}, md=md))
    #
    # # get the end time
    # et = time.time()
    # # get the execution time
    # elapsed_time = et - st
    # print('Execution time:', elapsed_time, 'seconds')
    #
    # # db[uid]
    # # header = db[-1]
    # # primary_docs = header.documents(fill=True)
    # # docs = list(primary_docs)
    # # for doc in docs:
    # #     print(doc)
    # #     if doc[0] == 'event':
    # #         data = process_sis3820_data(md, doc)
    #
    # # coarse scan
    # # uid: ('a3449b17-40e2-451a-8c36-d5cf1714dff1',)
    #
    #
    #
    print("Done processing")
