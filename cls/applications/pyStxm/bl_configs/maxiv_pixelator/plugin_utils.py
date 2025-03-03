import os
from PyQt5 import uic

from cls.utils.log import get_module_logger

from cls.scanning.paramLineEdit import intLineEditParamObj, dblLineEditParamObj
from cls.stylesheets import get_style


_logger = get_module_logger(__name__)
########################################################################
########################################################################
#### plugin UI utils
########################################################################
########################################################################

PREC = 3

def connect_scan_req_detail_flds_to_validator(self):
    """
    connect_param_flds_to_validator(): This functions purpose is to take all of the
    QLineEdit fields of a scan param plugin and add to them an object that connects
    the field to an appropriate QValidator that will manage that the values entered
    into each field abide by certain rules, they are limited to a value between the
    llm and hlm values, as well the object handles changeing the background color of each field
    as it is being edited and after a valid value has been recorded when teh enter key
    is pressed. If a valid value has been entered and the return key has been pressed
    the object emits the 'valid_returnPressed' signal which in turn will call the associated
    callback that will recalc all of the other fields in the roi

    : param: self is the scan_req detail widget
    : param: scan_req_widget is the actual instanciated scan req details UI form
    :returns: None
    """



    # the following added to support zmq dcs servers Fall 2024
    if hasattr(self.scan_req_wdg, "precisionFld"):
        fld = getattr(self.scan_req_wdg, "precisionFld")
        fld.dpo = dblLineEditParamObj("precisionFld", 0.0, 10000.0, PREC, parent=fld)
        fld.dpo.valid_returnPressed.connect(lambda: update_scan_req_data(self))

    if hasattr(self.scan_req_wdg, "defocusDiamFld"):
        fld = getattr(self.scan_req_wdg, "defocusDiamFld")
        fld.dpo = dblLineEditParamObj("defocusDiamFld", 0.0, 10000.0, PREC, parent=fld)
        fld.dpo.valid_returnPressed.connect(lambda: update_scan_req_data(self))

    if hasattr(self.scan_req_wdg, "accelDistFld"):
        fld = getattr(self.scan_req_wdg, "accelDistFld")
        fld.dpo = dblLineEditParamObj("accelDistFld", 0.0, 10000.0, PREC, parent=fld)
        fld.dpo.valid_returnPressed.connect(lambda: update_scan_req_data(self))

    if hasattr(self.scan_req_wdg, "tileDelayFld"):
        fld = getattr(self.scan_req_wdg, "tileDelayFld")
        fld.dpo = dblLineEditParamObj("tileDelayFld", 0.0, 10000.0, PREC, parent=fld)
        fld.dpo.valid_returnPressed.connect(lambda: update_scan_req_data(self))

    if hasattr(self.scan_req_wdg, "lineDelayFld"):
        fld = getattr(self.scan_req_wdg, "lineDelayFld")
        fld.dpo = dblLineEditParamObj("lineDelayFld", 0.0, 10000.0, PREC, parent=fld)
        fld.dpo.valid_returnPressed.connect(lambda: update_scan_req_data(self))

    if hasattr(self.scan_req_wdg, "pointDelayFld"):
        fld = getattr(self.scan_req_wdg, "pointDelayFld")
        fld.dpo = dblLineEditParamObj("pointDelayFld", 0.0, 10000.0, PREC, parent=fld)
        fld.dpo.valid_returnPressed.connect(lambda: update_scan_req_data(self))

def init_scan_req_member_vars(self):
    """
    any pixelator scan that wants to use these params needs the member vars
    """
    self.scan_req_wdg = uic.loadUi(os.path.join(os.path.dirname(__file__), "scan_req_details.ui"))
    self.scan_req_wdg.setMinimumWidth(600)
    self.scan_req_wdg.setMinimumHeight(400)

    self.precision_val = 0.0
    self.defocus_diam_val = 0.0
    self.accel_dist_val = 0.0
    self.tile_delay_val = 0.0
    self.line_delay_val = 0.0
    self.point_delay_val = 0.0
    self.defocus_enabled = 0.0
    self.adapt_pos_precision_enabled = 0.0

    if hasattr(self, 'scanReqDetailsBtn'):
        self.scanReqDetailsBtn.clicked.connect(lambda: show_scan_request_details(self))

        self.get_scan_request = lambda: get_scan_request_dct(self)
        ss = get_style()
        self.scan_req_wdg.setStyleSheet(ss)

        self.scan_req_wdg.autoDefocusChkBox.clicked.connect(lambda: on_auto_defocus_clicked(self, self.scan_req_wdg.autoDefocusChkBox.isChecked()))
        self.scan_req_wdg.adaptPosPrecChkBox.clicked.connect(lambda: on_adapt_prec_clicked(self, self.scan_req_wdg.adaptPosPrecChkBox.isChecked()))
        self.scan_req_wdg.closeBtn.clicked.connect(lambda: on_close_button(self))
    else:
        self.get_scan_request = lambda: get_empty_scan_request_dct(self)

    #create default dict that plugins can use to force default values
    dct = {}
    dct['adapt_precision'] = None
    dct['auto_defocus'] = None
    dct['y_axis_fast'] = None
    dct['meander'] = None
    dct['tiling'] = None
    dct['prec_field'] = None
    dct['defocus_diam_field'] = None
    dct['accel_dist'] = None
    dct['tile_delay'] = None
    dct['line_delay'] = None
    dct['point_delay'] = None
    dct['line_repeat'] = None
    dct['polarization'] = None
    # assign it to plugin
    self.default_scan_rec_setting_dct = dct

def set_scan_rec_default(self, attr: str, val):
    if attr not in self.default_scan_rec_setting_dct.keys():
        _logger.error(f'attr [{attr}] is not a valid scan request default')
    else:
        self.default_scan_rec_setting_dct[attr] = val

        #now set the UI to this value
        if attr == 'tiling':
            set_check_box(self, 'tiling', val)
        elif attr == 'adapt_precision':
            set_check_box(self, 'adaptPosPrec', val)
        elif attr == 'auto_defocus':
            set_check_box(self, 'autoDefocus', val)
        elif attr == 'y_axis_fast':
            set_check_box(self, 'yAxisFast', val)
        elif attr == 'meander':
            set_check_box(self, 'meander', val)
        elif attr == 'prec_field':
            set_field(self, 'precision', val)
        elif attr == 'defocus_diam_field':
            set_field(self, 'defocusDiam', val)
        elif attr == 'accel_dist':
            set_field(self, 'accelDist', val)
        elif attr == 'tile_delay':
            set_field(self, 'tileDelay', val)
        elif attr == 'line_delay':
            set_field(self, 'lineDelay', val)
        elif attr == 'point_delay':
            set_field(self, 'pointDelay', val)
        elif attr == 'line_repeat':
            set_spin_box(self, 'lineRep', val)
        elif attr == 'polarization':
            # not sure this one can be overridden
            pass

def set_check_box(self, name, val):

    if hasattr(self.scan_req_wdg, f'{name}ChkBox'):
        a = getattr(self.scan_req_wdg, f'{name}ChkBox')
        a.setChecked(val)

def set_field(self, name, val):

    if hasattr(self.scan_req_wdg, f'{name}Fld'):
        a = getattr(self.scan_req_wdg, f'{name}Fld')
        a.setText(f"{val:.2f}")

def set_spin_box(self, name, val):

    if hasattr(self.scan_req_wdg, f'{name}SpinBox'):
        a = getattr(self.scan_req_wdg, f'{name}SpinBox')
        a.setValue(val)

def on_close_button(self):
    """
    when the ok bnutton is pressed
    """
    update_scan_req_data(self)
    self.scan_req_wdg.hide()


def update_scan_req_data(self):
    """
    pull the information from the flds and buttons etc from teh scan requsition details forma nd place in member vars
    """
    self.precision_val = float(self.scan_req_wdg.precisionFld.text())
    self.defocus_diam_val = float(self.scan_req_wdg.defocusDiamFld.text())
    self.accel_dist_val = float(self.scan_req_wdg.accelDistFld.text())
    self.tile_delay_val = float(self.scan_req_wdg.tileDelayFld.text())
    self.line_delay_val = float(self.scan_req_wdg.lineDelayFld.text())
    self.point_delay_val = float(self.scan_req_wdg.pointDelayFld.text())

    self.defocus_enabled = self.scan_req_wdg.autoDefocusChkBox.isChecked()
    self.adapt_pos_precision_enabled = self.scan_req_wdg.adaptPosPrecChkBox.isChecked()

def get_scan_request_dct(self):
    """
    based on the plugin's settings create a scan request dictionary that encapsulates all of the
    information needed for the scan engine or dcs server to perform a scan

    To Be implemented by inheriting class

    """
    dct = {}
    dct['adapt_precision'] = True if self.scan_req_wdg.adaptPosPrecChkBox.isChecked() else False
    dct['auto_defocus'] = True if self.scan_req_wdg.autoDefocusChkBox.isChecked() else False
    dct['y_axis_fast'] = True if self.scan_req_wdg.yAxisFastChkBox.isChecked() else False
    dct['meander'] = True if self.scan_req_wdg.meanderChkBox.isChecked() else False
    dct['tiling'] = True if self.scan_req_wdg.tilingChkBox.isChecked() else False
    dct['prec_field'] = float(self.scan_req_wdg.precisionFld.text())
    dct['defocus_diam_field'] = float(self.scan_req_wdg.defocusDiamFld.text())
    dct['accel_dist'] = float(self.scan_req_wdg.accelDistFld.text())
    dct['tile_delay'] = float(self.scan_req_wdg.tileDelayFld.text())
    dct['line_delay'] = float(self.scan_req_wdg.lineDelayFld.text())
    dct['point_delay'] = float(self.scan_req_wdg.pointDelayFld.text())
    dct['line_repeat'] = int(self.scan_req_wdg.lineRepSpinBox.value())
    dct['polarization'] = "" # self.scan_req_wdg.polComboBox.currentText()

    for k, v in self.default_scan_rec_setting_dct.items():
        if v:
            # if the value is not None it was overridden in the plugin constructor to be used as a default value
            dct[k] = v

    return dct

def get_empty_scan_request_dct(self):
    """
    based on the plugin's settings create a scan request dictionary that encapsulates all of the
    information needed for the scan engine or dcs server to perform a scan

    To Be implemented by inheriting class

    """
    dct = {}
    dct['adapt_precision'] = False
    dct['auto_defocus'] = False
    dct['y_axis_fast'] = False
    dct['meander'] = False
    dct['tiling'] = False
    dct['prec_field'] = 0.0
    dct['defocus_diam_field'] = 0.0
    dct['accel_dist'] = 0.0
    dct['tile_delay'] = 0.0
    dct['line_delay'] = 0.0
    dct['point_delay'] = 0.0
    dct['line_repeat'] = 1
    dct['polarization'] = "" # self.scan_req_wdg.polComboBox.currentText()

    return dct

def on_auto_defocus_clicked(self, chkd):
    """
    called when the auto defocus checkbox is clicked
    if Auto is selected then disable the edit field else enable
    """
    if chkd:
        self.scan_req_wdg.defocusDiamFld.setEnabled(False)
    else:
        self.scan_req_wdg.defocusDiamFld.setEnabled(True)

def on_adapt_prec_clicked(self, chkd):
    """
    called when the adapt precision checkbox is clicked
    if Adapt is selected then enable the edit field else disable
    """
    if chkd:
        self.scan_req_wdg.precisionFld.setEnabled(True)
    else:
        self.scan_req_wdg.precisionFld.setEnabled(False)

def show_scan_request_details(self):
    """
    show the scan requistion detail form and extract data on close
    """
    self.scan_req_wdg.show()