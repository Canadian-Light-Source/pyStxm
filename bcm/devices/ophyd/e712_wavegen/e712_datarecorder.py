import os
from PyQt5 import uic, QtWidgets, QtCore, QtGui

from bcm.devices import BaseDevice
from cls.appWidgets.dialogs import setExistingDirectory
from cls.applications.pyStxm import abs_path_to_ini_file
from cls.utils.log import get_module_logger
from cls.utils.cfgparser import ConfigClass
from cls.utils.fileUtils import get_file_path_as_parts

appConfig = ConfigClass(abs_path_to_ini_file)

_logger = get_module_logger(__name__)

MAX_NUM_DATAREC_POINTS = 699050
MIN_DR_RATE = 0.00005


def calc_num_points_required(total_scan_time, rate):
    num_points_required = total_scan_time / (rate * MIN_DR_RATE)
    return num_points_required


def calc_total_scan_time(dwell_sec, nptsX, nptsY):
    tm = (dwell_sec * nptsX) * nptsY
    return tm


def calc_optimal_data_record_rate(total_scan_time):
    """
    calculate the data recorder rate that gives the highest resulition data acquisition given the dwell
    and number of points for the scan, the rate is an integer with 1 being the highest resolution (0.00005 sec per point)

    :param dwell_sec:
    :param nptsX:
    :param nptsY:
    :return (rate, number of points required):
    """
    # total_scan_time = calc_total_scan_time(dwell_sec, nptsX, nptsY)
    # check only up to 80 iterations max
    for i in range(1, 80):
        num_points_required = calc_num_points_required(total_scan_time, i)
        if num_points_required < MAX_NUM_DATAREC_POINTS:
            return (i, num_points_required)
    return (None, None)

def calc_dtr(dwell_ms, desired_pnts_per_dwell, servo_cycle_time):
    """
    given the dwell in ms and the number of points that you would like per dwell
    calculate the Data Recorder Table Rate that would be needed
    """
    dwell_sec = dwell_ms * 0.001
    dwell_pnt_time = dwell_sec/desired_pnts_per_dwell
    dtr = int(round(dwell_pnt_time/ servo_cycle_time))
    return dtr

def calc_datarecpnts_equivelant_wtr_points(ttl_cycle_time, servo_cycle_time, dtr):
    """
    calculate datarecorder equivelant of wavetable rate points
    given... calculate the number of points needed to achieve the same amount
    of wavelength time with the datarecorder
    """
    #wavlength_time_sec = wavtbl_len_pnts * (wavetable_rate * wvform_gen_cycle_time)
    datarec_tbl_pnts = ttl_cycle_time / (dtr * servo_cycle_time)
    return datarec_tbl_pnts

class PI_E712_DataRecorder(QtWidgets.QWidget):

    dr_status = QtCore.pyqtSignal(object)
    change_fld = QtCore.pyqtSignal(object)
    progress_changed = QtCore.pyqtSignal(object)

    def __init__(
        self,
        x_tbl_id=3,
        y_tbl_id=4,
        prefix="IOCE712:",
        e712com=None,
        e712comQ=None,
        parent=None,
    ):
        super(PI_E712_DataRecorder, self).__init__()
        uic.loadUi(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "e712_datarecorder.ui"
            ),
            self,
        )
        self.parent = parent
        self.prefix = prefix

        # self.e712_cmnd_queue = e712comQ
        # self.e712_wv_table_data = e712com
        # self.e712_wv_table_data.data_changed.connect(self.on_e712_com)

        self.dr_chans_enabled_dct = {}
        self.init_dr_widget(
            self.dr_chans_enabled_dct,
            "%sDRTbl_1:en" % self.prefix,
            self.drTblEnChkBox_1,
        )
        self.init_dr_widget(
            self.dr_chans_enabled_dct,
            "%sDRTbl_2:en" % self.prefix,
            self.drTblEnChkBox_2,
        )
        self.init_dr_widget(
            self.dr_chans_enabled_dct,
            "%sDRTbl_3:en" % self.prefix,
            self.drTblEnChkBox_3,
        )
        self.init_dr_widget(
            self.dr_chans_enabled_dct,
            "%sDRTbl_4:en" % self.prefix,
            self.drTblEnChkBox_4,
        )
        self.init_dr_widget(
            self.dr_chans_enabled_dct,
            "%sDRTbl_5:en" % self.prefix,
            self.drTblEnChkBox_5,
        )
        self.init_dr_widget(
            self.dr_chans_enabled_dct,
            "%sDRTbl_6:en" % self.prefix,
            self.drTblEnChkBox_6,
        )
        self.init_dr_widget(
            self.dr_chans_enabled_dct,
            "%sDRTbl_7:en" % self.prefix,
            self.drTblEnChkBox_7,
        )
        self.init_dr_widget(
            self.dr_chans_enabled_dct,
            "%sDRTbl_8:en" % self.prefix,
            self.drTblEnChkBox_8,
        )
        self.init_dr_widget(
            self.dr_chans_enabled_dct,
            "%sDRTbl_9:en" % self.prefix,
            self.drTblEnChkBox_9,
        )
        self.init_dr_widget(
            self.dr_chans_enabled_dct,
            "%sDRTbl_10:en" % self.prefix,
            self.drTblEnChkBox_10,
        )
        self.init_dr_widget(
            self.dr_chans_enabled_dct,
            "%sDRTbl_11:en" % self.prefix,
            self.drTblEnChkBox_11,
        )
        self.init_dr_widget(
            self.dr_chans_enabled_dct,
            "%sDRTbl_12:en" % self.prefix,
            self.drTblEnChkBox_12,
        )
        self.connect_enabled_chkboxs(self.dr_chans_enabled_dct)

        self.dr_chans_src_dct = {}
        self.init_dr_widget(
            self.dr_chans_src_dct,
            "%sDRTbl_1:src" % self.prefix,
            self.drTblSrcComboBox_1,
        )
        self.init_dr_widget(
            self.dr_chans_src_dct,
            "%sDRTbl_2:src" % self.prefix,
            self.drTblSrcComboBox_2,
        )
        self.init_dr_widget(
            self.dr_chans_src_dct,
            "%sDRTbl_3:src" % self.prefix,
            self.drTblSrcComboBox_3,
        )
        self.init_dr_widget(
            self.dr_chans_src_dct,
            "%sDRTbl_4:src" % self.prefix,
            self.drTblSrcComboBox_4,
        )
        self.init_dr_widget(
            self.dr_chans_src_dct,
            "%sDRTbl_5:src" % self.prefix,
            self.drTblSrcComboBox_5,
        )
        self.init_dr_widget(
            self.dr_chans_src_dct,
            "%sDRTbl_6:src" % self.prefix,
            self.drTblSrcComboBox_6,
        )
        self.init_dr_widget(
            self.dr_chans_src_dct,
            "%sDRTbl_7:src" % self.prefix,
            self.drTblSrcComboBox_7,
        )
        self.init_dr_widget(
            self.dr_chans_src_dct,
            "%sDRTbl_8:src" % self.prefix,
            self.drTblSrcComboBox_8,
        )
        self.init_dr_widget(
            self.dr_chans_src_dct,
            "%sDRTbl_9:src" % self.prefix,
            self.drTblSrcComboBox_9,
        )
        self.init_dr_widget(
            self.dr_chans_src_dct,
            "%sDRTbl_10:src" % self.prefix,
            self.drTblSrcComboBox_10,
        )
        self.init_dr_widget(
            self.dr_chans_src_dct,
            "%sDRTbl_11:src" % self.prefix,
            self.drTblSrcComboBox_11,
        )
        self.init_dr_widget(
            self.dr_chans_src_dct,
            "%sDRTbl_12:src" % self.prefix,
            self.drTblSrcComboBox_12,
        )
        self.connect_src_comboboxs(self.dr_chans_src_dct)

        self.dr_options_dct = {}
        self.init_dr_widget(
            self.dr_options_dct,
            "%sDataRecT1Option" % self.prefix,
            self.drTblOptionComboBox_1,
        )
        self.init_dr_widget(
            self.dr_options_dct,
            "%sDataRecT2Option" % self.prefix,
            self.drTblOptionComboBox_2,
        )
        self.init_dr_widget(
            self.dr_options_dct,
            "%sDataRecT3Option" % self.prefix,
            self.drTblOptionComboBox_3,
        )
        self.init_dr_widget(
            self.dr_options_dct,
            "%sDataRecT4Option" % self.prefix,
            self.drTblOptionComboBox_4,
        )
        self.init_dr_widget(
            self.dr_options_dct,
            "%sDataRecT5Option" % self.prefix,
            self.drTblOptionComboBox_5,
        )
        self.init_dr_widget(
            self.dr_options_dct,
            "%sDataRecT6Option" % self.prefix,
            self.drTblOptionComboBox_6,
        )
        self.init_dr_widget(
            self.dr_options_dct,
            "%sDataRecT7Option" % self.prefix,
            self.drTblOptionComboBox_7,
        )
        self.init_dr_widget(
            self.dr_options_dct,
            "%sDataRecT8Option" % self.prefix,
            self.drTblOptionComboBox_8,
        )
        self.init_dr_widget(
            self.dr_options_dct,
            "%sDataRecT9Option" % self.prefix,
            self.drTblOptionComboBox_9,
        )
        self.init_dr_widget(
            self.dr_options_dct,
            "%sDataRecT10Option" % self.prefix,
            self.drTblOptionComboBox_10,
        )
        self.init_dr_widget(
            self.dr_options_dct,
            "%sDataRecT11Option" % self.prefix,
            self.drTblOptionComboBox_11,
        )
        self.init_dr_widget(
            self.dr_options_dct,
            "%sDataRecT12Option" % self.prefix,
            self.drTblOptionComboBox_12,
        )
        self.connect_option_comboboxs(self.dr_options_dct)

        self.dr_trg_src = BaseDevice("%sDataRecTrigSrc" % self.prefix)
        self.trgSrcComboBox.currentIndexChanged.connect(self.on_trg_src_changed)
        self.trgSrcComboBox.setToolTip("%sDataRecTrigSrc" % self.prefix)

        self.dr_get_rec_tbls = BaseDevice("%sGetDataRecTbls" % self.prefix)
        self.drGetDatarecTablesBtn.clicked.connect(self.on_get_rec_tbls_btn)
        self.drGetDatarecTablesBtn.setToolTip("%sGetDataRecTbls" % self.prefix)

        self.dr_start_rec = BaseDevice("%sStartDataRec" % self.prefix)
        self.drStartRecordingBtn.clicked.connect(self.on_start_rec_btn)
        self.drStartRecordingBtn.setToolTip("%sStartDataRec" % self.prefix)

        self.dr_auto_enable_rec = BaseDevice("%sAutoDataRec" % self.prefix)

        self.dr_configure = BaseDevice("%sConfigDataRec" % self.prefix)
        # self.drStartRecordingBtn.clicked.connect(self.on_start_rec_btn)
        # self.drStartRecordingBtn.setToolTip('%sStartDataRec' % self.prefix)

        self.dr_set_rec_tbl_rate = BaseDevice("%sSetRecTblRate" % self.prefix)
        self.drRecRateSpinBox.valueChanged.connect(self.on_rate_changed)
        self.drRecRateSpinBox.setToolTip("%sSetRecTblRate" % self.prefix)

        self.dr_get_rec_tbl_rate = BaseDevice('%sGetRecTblRate' % self.prefix)

        self.dr_get_rec_tbl_rate_in_sec = BaseDevice(
            "%sGetRecTblRateInSec_RBV" % self.prefix, rd_only=True
        )
        # self.dr_get_rec_tbl_rate_in_sec.add_callback(self.on_rec_tbl_rate_changed)
        self.drRateInSecFld.setToolTip("%sGetRecTblRateInSec_RBV" % self.prefix)

        self.dr_get_num_rec_pnts = BaseDevice(
            "%sGetNumRecPoints_RBV" % self.prefix, rd_only=True
        )
        self.dr_get_num_rec_pnts.changed.connect(self.on_num_rec_pnts_changed)
        self.drNumRecPointsFld.setToolTip("%sGetNumRecPoints_RBV" % self.prefix)

        self.dr_get_rec_tbls_sts = BaseDevice(
            "%sGetDataRecTblsSts_RBV" % self.prefix, rd_only=True
        )
        self.dr_get_rec_tbls_sts.changed.connect(self.on_status_changed)
        self.drStatusLbl.setToolTip("%sGetDataRecTblsSts_RBV" % self.prefix)

        self.dr_fpath = BaseDevice("%sDataRecFPath" % self.prefix)
        self.drFPathFld.setToolTip("%sDataRecFPath" % self.prefix)
        self.drFPathFld.returnPressed.connect(self.on_fpath_changed)

        self.dr_progress = BaseDevice(
            "%sGetRecDataProg_RBV" % self.prefix, rd_only=True
        )
        self.dataRecProgBar.setToolTip("%sGetRecDataProg_RBV" % self.prefix)
        # self.dr_progress.add_callback(self.on_prog_pv_changed)
        self.dr_progress.changed.connect(self.on_prog_changed)
        self.selectDirBtn.clicked.connect(self.on_sel_dir)

        #self.autoStartRadioBtn.stateChanged.connect(self.enable_auto_data_recording)

        self.change_fld.connect(self.on_change_fld)



        # self.trgSrcComboBox
        # self.push_all_selections()

    def set_rec_grp(self, widg_num, en, src, option):
        """
        given a set of args set the selection values"""

        self.dr_chans_enabled_dct[f"{self.prefix}DRTbl_{widg_num}:en"]["dev"].put(en)
        self.dr_chans_src_dct[f"{self.prefix}DRTbl_{widg_num}:src"]["dev"].put(src)
        self.dr_options_dct[f"{self.prefix}DataRecT{widg_num}Option"]["dev"].put(option)

    def set_ptycho_defaults(self):
        """
        a convinience function to set the datarecorder up the way we want for ptycho measurements
        """
        self.pntsPerDwellFld.setText(str(25))

        self.trgSrcComboBox.setCurrentIndex(3) #immediate
        self.dr_trg_src.put(3)
        self.autoStartRadioBtn.setChecked(True) #enabled
        self.dr_auto_enable_rec.put(1)

        self.drTblEnChkBox_1.setChecked(True) # enabled
        self.drTblSrcComboBox_1.setCurrentIndex(0) #axis 1, pv is 1 based because that is what is sent to the controller
        self.drTblOptionComboBox_1.setCurrentIndex(1) #current position of axis
        self.set_rec_grp(1, True, 1, 1)

        self.drTblEnChkBox_2.setChecked(True)  # enabled
        self.drTblSrcComboBox_2.setCurrentIndex(1)  # axis 2
        self.drTblOptionComboBox_2.setCurrentIndex(1)
        self.set_rec_grp(2, True, 2, 1)# current position of axis

        self.drTblEnChkBox_3.setChecked(True)  # enabled
        self.drTblSrcComboBox_3.setCurrentIndex(0)  # axis 1
        self.drTblOptionComboBox_3.setCurrentIndex(2)  # position error of axis
        self.set_rec_grp(3, True, 1, 2)

        self.drTblEnChkBox_4.setChecked(True)  # enabled
        self.drTblSrcComboBox_4.setCurrentIndex(1)  # axis 2
        self.drTblOptionComboBox_4.setCurrentIndex(2)  # position error of axis
        self.set_rec_grp(4, True, 2, 2)

        self.drTblEnChkBox_5.setChecked(True)  # enabled
        self.drTblSrcComboBox_5.setCurrentIndex(0)  # axis 1
        self.drTblOptionComboBox_5.setCurrentIndex(15)  # Value of digital out
        self.set_rec_grp(5, True, 1, 15)

        self.drTblEnChkBox_6.setChecked(False)  # disabled
        self.set_rec_grp(6, False, 3, 1)
        self.drTblEnChkBox_7.setChecked(False)  # disabled
        self.set_rec_grp(7, False, 3, 1)
        self.drTblEnChkBox_8.setChecked(False)  # disabled
        self.set_rec_grp(8, False, 3, 1)
        self.drTblEnChkBox_9.setChecked(False)  # disabled
        self.set_rec_grp(9, False, 3, 1)
        self.drTblEnChkBox_10.setChecked(False)  # disabled
        self.set_rec_grp(10, False, 3, 1)
        self.drTblEnChkBox_11.setChecked(False)  # disabled
        self.set_rec_grp(11, False, 3, 1)
        self.drTblEnChkBox_12.setChecked(False)  # disabled
        self.set_rec_grp(12, False, 3, 1)



    def do_configuration(self):
        """
        cause teh data reco configuration to be pushed into the controller
        :return:
        """
        self.dr_configure.put(1)

    def on_prog_pv_changed(self, **kwargs):
        val = kwargs["value"]
        self.progress_changed.emit(val)

    def on_prog_changed(self, val):
        if type(val) is dict:
            val = val["value"]
        # print('e712_datarecorder: on_prog_changed: ')
        # print(val)
        self.dataRecProgBar.setValue(int(val))

    def push_all_selections(self):
        idx = self.trgSrcComboBox.currentIndex()
        self.dr_trg_src.put(idx)
        self.set_enabled_btns()
        self.set_combo_boxs(self.dr_chans_src_dct, is_srcs=True)
        self.set_combo_boxs(self.dr_options_dct)
        self.enable_auto_data_recording(self.autoStartRadioBtn.isChecked())
        self.do_configuration()

    def set_enabled_btns(self):
        dct = self.dr_chans_enabled_dct
        for pv_name in list(dct.keys()):
            widget = dct[pv_name]["wdg"]
            pv = dct[pv_name]["dev"]
            if widget.isChecked():
                pv.put(1)
            else:
                pv.put(0)

    def set_combo_boxs(self, dct, is_srcs=False):
        for pv_name in list(dct.keys()):
            widget = dct[pv_name]["wdg"]
            pv = dct[pv_name]["dev"]
            val = widget.currentIndex()
            if is_srcs:
                # need to make base 1 instead of base 0
                val += 1
            pv.put(val)

    def get_num_chans_enabled(self):
        num_chans = 0
        for k in list(self.dr_chans_enabled_dct.keys()):
            w = self.dr_chans_enabled_dct[k]["wdg"]
            if w.isChecked():
                num_chans += 1
        return num_chans

    def on_sel_dir(self):
        dir = setExistingDirectory(
            "Select Data Directory", init_dir=r"<path_to>\2018\guest"
        )
        self.drFPathFld.setText(str(os.path.join(dir, "000.dat")))

    def set_filename(self, fname):
        """
        a function to set only the file name not the entire path

        so if fname = '002.dat'
        and the current filepath was: r'<path_to>\2018\guest\0717\001.dat'

        this function will set the filepath to r'<path_to>\2018\guest\0717\002.dat'

        :param fname:
        :return:
        """
        fpath = self.drFPathFld.text()
        data_dir, fprefix, fsuffix = get_file_path_as_parts(fpath)
        self.set_filepath(os.path.join(data_dir, fname))

    def get_filepath(self):
        fpath = self.drFPathFld.text()
        data_dir, fprefix, fsuffix = get_file_path_as_parts(fpath)
        return data_dir

    def set_filepath(self, fpath=None):
        """
        a function that can be called be a parent of this widget that passes the absolute file path to
        be used to save the data recorder .dat file
        :param fpath:
        :return:
        """
        if fpath:
            if fpath.find(".hdf5") > -1:
                fpath = fpath.replace(".hdf5", ".dat")
            self.drFPathFld.setText(fpath)
            self.dr_fpath.put(str(fpath))

    def auto_set_datarec_rate(self, total_cycle_time, dwell_ms, wvform_gen_cycle_time, servo_cycle_time, desired_pnts_per_dwell=25):
        # num_chans = self.get_num_chans_enabled()
        #rate, num_pnts_required = calc_optimal_data_record_rate(wavetable_len_pts)
        dtr = calc_dtr(dwell_ms, desired_pnts_per_dwell, servo_cycle_time)
        drectbl_pnts_expected = calc_datarecpnts_equivelant_wtr_points(total_cycle_time, servo_cycle_time, dtr)
        self.on_rate_changed(int(dtr))
        return drectbl_pnts_expected

    def on_fpath_changed(self):
        fpath = self.drFPathFld.text()
        self.dr_fpath.put(str(fpath))

    # def on_status_changed(self, **kwargs):
    #     dct = {}
    #     dct['wdg'] = self.drStatusLbl
    #     if(kwargs['value'] == 0):
    #         dct['val'] = 'READY'
    #         dct['clr'] = 'rgb(166,166,166);'
    #         dct['busy'] = False
    #     else:
    #         dct['val'] = 'SAVING_DATA'
    #         dct['clr'] = 'rgb(244,244,0);'
    #         dct['busy'] = True
    #
    #     self.change_fld.emit(dct)
    #     self.dr_status.emit(dct)

    def on_status_changed(self, val):
        # self.drStatusLbl.setText(str(val))
        dct = {}
        dct["wdg"] = self.drStatusLbl
        if val == 1:
            dct["val"] = "SAVING_DATA"
            dct["clr"] = "rgb(244,244,0);"
            dct["busy"] = True
        else:
            dct["val"] = "READY"
            dct["clr"] = "rgb(166,166,166);"
            dct["busy"] = False

        self.change_fld.emit(dct)
        self.dr_status.emit(dct)

    def on_rec_tbl_rate_changed(self, **kwargs):
        dct = {}
        dct["wdg"] = self.drRateInSecFld
        dct["val"] = str("%.6f" % kwargs["value"])
        self.change_fld.emit(dct)

    # def on_num_rec_pnts_changed(self, **kwargs):
    #     dct = {}
    #     dct['wdg'] = self.drNumRecPointsFld
    #     dct['val'] = str('%d' % kwargs['value'])
    #     self.change_fld.emit(dct)

    def on_num_rec_pnts_changed(self, dct):
        """
        {'old_value': 165749.0, 'value': 166549.0, 'timestamp': 1548530243.190648, 'sub_type': 'value',
        'obj': EpicsSignalRO(read_pv='IOCE712:GetNumRecPoints_RBV', name='IOCE712:GetNumRecPoints_RBV',
            value=166549.0, timestamp=1548530243.190648, pv_kw={}, auto_monitor=True, string=False)}
        :param val:
        :return:
        """
        # print('e712_datarecorder: on_num_rec_pnts_changed')
        # print(val)
        val = dct["value"]
        self.drNumRecPointsFld.setText("%d" % val)

    def on_change_fld(self, dct):
        w = dct["wdg"]
        w.setText(dct["val"])
        if "clr" in list(dct.keys()):
            w.setStyleSheet("color: black; background-color: %s;" % dct["clr"])

    def on_start_rec_btn(self):
        self.dr_start_rec.put(1)

    def on_get_rec_tbls_btn(self):
        fpath = str(self.drFPathFld.text())
        if fpath.find(".dat") > -1:
            self.dr_get_rec_tbls.put(1)
        else:
            print("File path doesnt exist")

    def on_trg_src_changed(self, idx):
        self.dr_trg_src.put(idx)

    def on_rate_changed(self, val):
        self.dr_set_rec_tbl_rate.put(val)

    def init_dr_widget(self, dct, pv_name, widget):
        """
        a convienience function to create a pv and put it and the widget it is connected to into a dict
        :param dct:
        :param pv_name:
        :param widget:
        :return:
        """
        dct[pv_name] = {}
        widget.setToolTip(pv_name)
        dct[pv_name]["wdg"] = widget
        dct[pv_name]["dev"] = BaseDevice(pv_name, write_pv=pv_name)

    def connect_enabled_chkboxs(self, dct):
        """
        take the dict of checkbox widgets and connect them to their handler
        :param dct:
        :return:
        """
        for k in list(dct.keys()):
            w = dct[k]["wdg"]
            w.stateChanged.connect(self.on_enabled_chkbox_changed)

    def enable_auto_data_recording(self, en):
        if en:
            # enable
            self.dr_auto_enable_rec.put(1)
        else:
            # disable
            self.dr_auto_enable_rec.put(0)

    def on_enabled_chkbox_changed(self, state):
        w = self.sender()
        w_dct = self.get_widget_dct(self.dr_chans_enabled_dct, w)
        if state > 0:
            state = 1
        w_dct["dev"].put(state)
        self.push_all_selections()

    def on_src_combobox_changed(self, idx):
        w = self.sender()
        w_dct = self.get_widget_dct(self.dr_chans_src_dct, w)
        # one based
        w_dct["dev"].put(idx + 1)
        self.push_all_selections()

    def on_option_combobox_changed(self, idx):
        w = self.sender()
        w_dct = self.get_widget_dct(self.dr_options_dct, w)
        # zero based
        w_dct["dev"].put(idx)
        self.push_all_selections()

    def get_widget_dct(self, dct, w):
        for k in list(dct.keys()):
            w_dct = dct[k]
            if w_dct["wdg"] == w:
                return w_dct
        print("get_widget: couldnt find widget in the dict")
        return {}

    def connect_src_comboboxs(self, dct):
        """
        take the dict of checkbox widgets and connect them to their handler
        :param dct:
        :return:
        """
        for k in list(dct.keys()):
            w = dct[k]["wdg"]
            w.currentIndexChanged.connect(self.on_src_combobox_changed)

    def connect_option_comboboxs(self, dct):
        """
        take the dict of checkbox widgets and connect them to their handler
        :param dct:
        :return:
        """
        for k in list(dct.keys()):
            w = dct[k]["wdg"]
            w.currentIndexChanged.connect(self.on_option_combobox_changed)

    # def set_filename(self, fname):
    #    self.dr_filename.pu
