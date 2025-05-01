"""
Created on May 1, 2025

@author: bergr
"""
import os
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import uic

from cls.appWidgets.basePreference import BasePreference
from cls.applications.pyStxm.main_obj_init import MAIN_OBJ
from cls.stylesheets import get_style
from cls.utils.log import get_module_logger
from cls.utils.dict_utils import dct_get, dct_put

uiDir = os.path.join(os.path.dirname(os.path.abspath(__file__)))

_logger = get_module_logger(__name__)


class BaseDetectorDetailDialog(QtWidgets.QDialog):
    def __init__(self, name, det, args={}, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.name = name
        self.setModal(True)
        self.titleLbl = QtWidgets.QLabel(name)
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.titleLbl)
        self.qssheet = get_style()
        self.setStyleSheet(self.qssheet)

        self.setLayout(layout)

        self.dct = {}
        self.dct["name"] = name
        self.dct["det_dev"] = det
        self.dct["args"] = args

        self.sections = {}
        self.add_section("ENABLED", False)
        self.define_sections()

    def add_section(self, section, val=None):
        """
        a convienience function that preppends the name of the detector onto the section name
        :return:
        """
        # only if the section does NOT already exist do we create and assign it
        if section not in list(self.sections.keys()):
            self.sections[section] = val

    def get_section(self, section):
        """
        self explanatory
        :param section:
        :return: value of section if it exists
        """
        val = None
        if section in list(self.sections.keys()):
            val = self.sections[section]
        else:
            _logger.error("section for this detector does not exist [%s]" % section)
        return val

    def get_sections(self):
        """
        return all sections that have been defined
        :return:
        """
        return self.sections

    def define_sections(self):
        """
        here sections means the details for this detector, these section names are used as keys into a settings
        dict kept in the DEFAULTS module for reload and recording, so basically any setting preference that you
        want to retain should have a section name
        to be implemented by inheriting class
        :return:
        """
        pass

    def get_cfg(self):
        """
        get all of the devices configuration params here and put into dct
        """
        return self.dct


class APD_DetailDialog(BaseDetectorDetailDialog):
    def __init__(self, name, det, args={}, parent=None):
        super(APD_DetailDialog, self).__init__(name, det)

    def define_sections(self):
        """
        the particular settings we want to track for this detector
        :return:
        """
        self.add_section("device", "Dev3")
        self.add_section("counter", "ctr1")
        self.add_section("src_term", "PFI1")
        self.add_section("src_clk", "PFI2")


class PMT_DetailDialog(BaseDetectorDetailDialog):
    def __init__(self, name, det, args={}, parent=None):
        super(PMT_DetailDialog, self).__init__(name, det)

    def define_sections(self):
        """
        the particular settings we want to track for this detector
        :return:
        """
        self.add_section("device", "Dev4")
        self.add_section("counter", "ctr2")
        self.add_section("src_term", "PFI0")
        self.add_section("src_clk", "PFI12")


class DAQMX_DetailDialog(BaseDetectorDetailDialog):
    def __init__(self, name, det, args={}, parent=None):
        super(DAQMX_DetailDialog, self).__init__(name, det)

    def define_sections(self):
        """
        the particular settings we want to track for this detector
        :return:
        """
        self.add_section("device", "Dev3")
        self.add_section("port", "0")
        self.add_section("line", "4")


class EPICS_DetailDialog(BaseDetectorDetailDialog):
    def __init__(self, name, det, args={}, parent=None):
        super(EPICS_DetailDialog, self).__init__(name, det)

    def define_sections(self):
        """
        the particular settings we want to track for this detector
        :return:
        """
        self.add_section("ver", "R3.14.12.4")
        self.add_section("host_arch", "win32-x86_debug")


def make_detail_detector_form(name, det):
    if name.find("PMT") > -1:
        ddf = PMT_DetailDialog(name, det)

    elif name.find("APD") > -1:
        ddf = APD_DetailDialog(name, det)

    elif name.find("StorageRingCurrent") > -1:
        ddf = EPICS_DetailDialog(name, det)

    else:
        #_logger.info("Detector [%s] has no supported detail form" % name)
        ddf = None

    return ddf


class DetectorItem(QtWidgets.QWidget):
    update_setting = QtCore.pyqtSignal(object)

    def __init__(self, name, det, details_wdg, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.name = name
        # self.dcs_name = det.get_name()
        #self.dcs_name = det.name
        self.det = det
        if hasattr(det, 'dcs_name'):
            self.dcs_name = det.dcs_name
        else:
            self.dcs_name = det.prefix

        if details_wdg is not None:
            self.det_cfg = details_wdg.get_cfg()

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        self.detailsWdg = details_wdg
        self.detailsBtn = QtWidgets.QToolButton()
        self.detailsBtn.setToolTip("Config " + name + " details")
        # self.radioBtn = QtWidgets.QRadioButton(name)
        self.chkBox = QtWidgets.QCheckBox(name)
        if hasattr(det, "prefix"):
            self.chkBox.setToolTip(det.prefix)
        elif hasattr(det, "signal"):
            self.chkBox.setToolTip(det.signal.name)
        else:
            self.chkBox.setToolTip(self.name)

        self.chkBox.setStyleSheet("QCheckBox:checked{background-color: rgb(114, 148, 240); color:rgb(0,0,0);}")

        # COMMENTED OUT FOR NOW Feb 21 2023 layout.addWidget(self.detailsBtn)
        # layout.addWidget(self.radioBtn)
        layout.addWidget(self.chkBox)

        self.detailsBtn.clicked.connect(self.on_show_details)
        # self.radioBtn.clicked.connect(self.on_radio_clicked)
        self.chkBox.clicked.connect(self.on_checkbox_clicked)

        if hasattr(self.det, "is_chan_enabled"):
            en = self.det.is_chan_enabled(self.name)
            self.is_checked = en
        else:
            #default is disabled
            self.is_checked = False
        self.set_checked(self.is_checked)
        self.setLayout(layout)

    def update_bg_color(self, chkd):
        if chkd:
            #self.chkBox.setStyleSheet("background-color: black")
            self.chkBox.setStyleSheet("QLabel{ color: black};")
        else:
            #self.chkBox.setStyleSheet("background-color: black");
            self.chkBox.setStyleSheet("QLabel{ color: white};")

    def set_checked(self, chkd):
        self.chkBox.setChecked(chkd)
        #self.update_bg_color(chkd)

    def get_checked(self):
        ret = self.chkBox.isChecked()
        return ret

    def get_wdg_sections(self):
        dct = {}
        if self.detailsWdg is not None:
            dct[self.detailsWdg.name] = self.detailsWdg.get_sections()
        return dct

    def on_show_details(self):
        if self.detailsWdg is not None:
            self.detailsWdg.show()

    def on_checkbox_clicked(self, chkd):
        self.is_checked = chkd
        dct = {}
        det = None
        if hasattr(self.det, "enable_channel"):
            det = self.det

        if chkd:
            dct[self.name] = {"ENABLED": True}
            if det:
                det.enable_channel(self.name, 1)
        else:
            dct[self.name] = {"ENABLED": False}
            if det:
                det.enable_channel(self.name, 0)
        #self.update_bg_color(chkd)
        self.update_setting.emit(dct)

    def is_checked(self):
        return self.get_checked()

    def get_name(self):
        return self.name

    def get_dcs_name(self):
        return self.dcs_name


class DetectorsPanel(BasePreference):
    def __init__(self, name="DetectorsPanel", parent=None, sel_changed_cb=None):
        super(DetectorsPanel, self).__init__(name, parent)
        self.sel_changed_cb = sel_changed_cb
        vbox = QtWidgets.QVBoxLayout()
        self.setLayout(vbox)
        grpBox = QtWidgets.QGroupBox(" Detectors ")
        self.widgetList = []
        self.qssheet = get_style()
        glayout = QtWidgets.QGridLayout()
        glayout.setContentsMargins(2, 2, 2, 2)
        det_lst = MAIN_OBJ.get_device_list(detectors=True)
        num_dets = len(det_lst) + 2
        rows = int(num_dets / 2)
        positions = [(i, j) for i in range(rows) for j in range(2)]
        i = 0
        for detname in det_lst:
            if detname.find('SIS3820')>-1:
                #detame is a channel of main device DNM_SIS3820 so pull that as the device
                det = MAIN_OBJ.device('DNM_SIS3820')
            else:
                det = MAIN_OBJ.device(detname)
            # a sim device will return None
            if det:
                ddf = make_detail_detector_form(detname, det)
                widget = DetectorItem(detname, det, ddf)
                widget.update_setting.connect(self.on_update_setting)
                widget.setStyleSheet(self.qssheet)
                self.widgetList.append(widget)
                glayout.addWidget(widget, positions[i][0], positions[i][1])
            i = i + 1
        grpBox.setLayout(glayout)
        spacer = QtWidgets.QSpacerItem(
            1, 1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        vbox.addWidget(grpBox)
        vbox.addItem(spacer)
        self.setStyleSheet(self.qssheet)
        self.init_sections()

        # init from saved
        self.reload()

    def reload(self):
        """
        load settings saved in the DEFAULTS module
        :return:
        """
        for w in self.widgetList:
            _scts = w.get_wdg_sections()
            det_name = w.get_name()
            if det_name in _scts.keys():
                for _sect in list(_scts[det_name].keys()):
                    if _sect == "ENABLED":
                        val = self.get_section("%s.ENABLED" % (det_name))
                        w.set_checked(val)

    #
    def init_sections(self):
        """
        define all of the preferences for
        :return:
        """
        for w in self.widgetList:
            _scts = w.get_wdg_sections()
            det_name = w.get_name()
            if det_name in _scts.keys():
                for _sect in list(_scts[det_name].keys()):
                    self.add_section(
                        "%s.%s" % (det_name, _sect), _scts[det_name][_sect]
                    )

    def on_update_setting(self, dct):
        det_name = list(dct.keys())[0]
        # self.set_section(
        #     "%s.ENABLED" % (det_name), dct_get(dct, "%s.ENABLED" % det_name)
        # )
        # print(f"on_update_setting {self.get_selected_detectors()}")
        if self.sel_changed_cb:
           self.sel_changed_cb(self.get_selected_detectors())

    def get_selected_detectors(self, scan_class=None):
        """
        walk all of the detectors and record which ones are checked
        """
        #get the scan classes ddefault detector and make sure that it shows as selected
        # dflt_det = scan_class.default_detector_nm
        lst = []
        for d_item in self.widgetList:
            if d_item.get_checked():
                dct = {}
                dct["name"] = d_item.get_name()
                dct["dcs_name"] = d_item.get_dcs_name()
                lst.append(d_item.get_name())
        return lst

    def update_pref_dct(self):
        """
        When called, compile all preferences for the pref widget into the self.pef_dct and return it
        to be mplemented by inheriting class
        :return: updated self.pref_dct
        """
        pass

    def load_defaults(self):
        """

        :return:
        """


if __name__ == "__main__":
    import sys

    # motorCfgObj = StxmMotorConfig(r'C:\controls\py2.7\Beamlines\sm\stxm_control\StxmDir\Microscope Configuration\Motor.cfg')
    app = QtWidgets.QApplication(sys.argv)

    # log_to_qt()
    motorPanel = DetectorsPanel()
    motorPanel.show()
    sys.exit(app.exec_())
