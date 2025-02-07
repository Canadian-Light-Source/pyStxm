from PyQt5 import QtCore, QtGui, QtWidgets
from cls.applications.pyStxm.widgets.scan_table_view.baseScanTable import *

from cls.applications.pyStxm.widgets.scan_table_view.evScanTableModel import (
    EnergyScanTableModel,
)
from cls.utils.str_utils import isfloat, isint


class EnergyScanTableView(BaseScanTableView):
    def __init__(self, scanList=[], single_dwell=False, parent=None):
        """
        __init__(): description

        :param scanList=[]: scanList=[] description
        :type scanList=[]: scanList=[] type

        :param parent=None: parent=None description
        :type parent=None: parent=None type

        :returns: None
        """
        # setup the header for the top of the table
        hdrList = [
            "ID",
            "Start",
            "End",
            "Range\n(eV)",
            "#Points",
            "Step\n(eV)",
            "Dwell\n(ms)",
        ]
        self.hdrValidators = [(isint, int),  # ID
                              (isfloat, float),  # Start
                              (isfloat, float), # End
                              (isfloat, float), # Range
                              (isint, int), # Points
                              (isfloat, float), # Step
                              (isfloat, float)] # Dwell
        # self.func_list = ['ev_id', 'center', 'range', 'step','Npoints', 'dwell', 'pol1', 'pol2', 'off1', 'off2', 'xmcd']
        super(EnergyScanTableView, self).__init__(
            hdrList, scanList, EnergyScanTableModel, parent
        )
        #self.setStyleSheet(EV_SS)
        self.setObjectName("EnergyScanTableView")
        self.evNum = 0
        self.single_dwell = single_dwell

        # self.init_model()
        # self.set_model_id_start_val(EV_CNTR)
        # self.table_view.horizontalHeader().setSectionResizeMode(QtGui.QHeaderView.ResizeToContents)
        #self.scan_changed.connect(self.on_scan_changed)

    def set_model_validators(self):
        """
        sets teh validators for the model fields
        """
        self.tablemodel.set_validators(self.hdrValidators)

    def init_model(self):
        """
        init_model(): description

        :returns: None
        """
        self.tablemodel = EnergyScanTableModel(self.hdrList, self.scans, self, single_dwell=self.single_dwell, parent=self)
        self.set_model_column_defaults()

    def set_model_column_defaults(self):
        """
        set_model_column_defaults(): description

        :returns: None
        """
        self.tablemodel.set_col_readonly(0)

    def set_roi_is_valid(self, index: int, *, valid: bool):
        self.tablemodel.set_row_field_state(index, START, valid=valid)
        self.tablemodel.set_row_field_state(index, STOP, valid=valid)

    def modify_scan(self, scan_id, newscan, do_step_npts=False):
        """
        modify_scan(): description

        :param scan_id: scan_id description
        :type scan_id: scan_id type

        :param newscan: newscan description
        :type newscan: newscan type

        :param do_step_npts=False: do_step_npts=False description
        :type do_step_npts=False: do_step_npts=False type

        :returns: None
        """
        """ """
        scan = self.tablemodel.get_scan(scan_id)
        if scan is not None:
            self.tablemodel.modify_data(scan_id, newscan, do_step_npts)
