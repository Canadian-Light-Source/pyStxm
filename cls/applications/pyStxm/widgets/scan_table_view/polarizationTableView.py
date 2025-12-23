"""
Created on Nov 16, 2016

@author: bergr
"""
from PyQt5 import QtCore, QtGui, QtWidgets

from cls.applications.pyStxm.widgets.scan_table_view.baseScanTable import *

from cls.applications.pyStxm.widgets.scan_table_view.polarizationTableModel import (
    PolarizationTableModel,
)
from cls.applications.pyStxm.widgets.scan_table_view.polarizationCmboBoxDelegate import (
    PolComboBoxDelegate,
    POLARIZATION_COLUMN,
)
from cls.utils.str_utils import isfloat, isint


class PolarizationTableView(BaseScanTableView):

    # changed = QtCore.pyqtSignal()

    def __init__(self, scanList=[], parent=None):
        """
        __init__(): description

        :param scanList=[]: scanList=[] description
        :type scanList=[]: scanList=[] type

        :param parent=None: parent=None description
        :type parent=None: parent=None type

        :returns: None
        """
        # setup the header for the top of the table
        hdrList = ["ID", "Polarization", "Offset", "Linear Angle"]
        # self.func_list = ['pol_id', 'polarity', 'offset','linearAngle']
        self.hdrValidators = [(isint, int),  # ID
                              (isint, int),  # Polarization
                              (isfloat, float), # Offset
                              (isfloat, float) ] # Linear Angle

        super(PolarizationTableView, self).__init__(
            hdrList, scanList, PolarizationTableModel, parent
        )
        #self.setStyleSheet(POL_SS)
        self.setObjectName("PolarizationTableView")
        self.xyNum = 0
        # self.set_model_id_start_val(POL_CNTR)
        self.setItemDelegateForColumn(POLARIZATION_COLUMN, PolComboBoxDelegate(self))

        self.setMaximumHeight(100)
        # Set the resize policy
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.setSizePolicy(size_policy)
        # Restrict the height to 100
        self.setFixedHeight(100)

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
        self.tablemodel = PolarizationTableModel(self.hdrList, self.scans, self)
        self.set_model_column_defaults()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        header = self.horizontalHeader()
        header.setSectionResizeMode(POLARIZATION_COLUMN, QtWidgets.QHeaderView.Fixed)
        header.resizeSection(POLARIZATION_COLUMN, 100)

    def get_polarity_combobox(self):
        """
        get_polarity_combobox(): description

        :returns: None
        """
        cbox = QtWidgets.QComboBox()
        # the values that need to be pushed out for these are (in order)
        #             [-1, 0, 1]
        cbox.addItems(["Circ Left", "Circ Right", "Linear"])
        return cbox

    def set_model_column_defaults(self):
        """
        set_model_column_defaults(): description

        :returns: None
        """
        self.tablemodel.set_col_readonly(0)

    #        for i in range(1,len(self.hdrList)):
    #                self.horizontalHeader().setSectionResizeMode(i, QtWidgets.QHeaderView.Stretch)

    def update_table(self):
        """
        update_table(): description

        :returns: None
        """
        if self.tablemodel is not None:
            for row in range(0, self.tablemodel.rowCount()):
                # table_view.openPersistentEditor(table_model.index(row, 0))
                self.openPersistentEditor(
                    self.tablemodel.index(row, POLARIZATION_COLUMN)
                )

    def set_offset_is_valid(self, index: int, *, valid: bool):
        self.tablemodel.set_row_field_state(index, OFF, valid=valid)

    def set_angle_is_valid(self, index: int, *, valid: bool):
        self.tablemodel.set_row_field_state(index, ANGLE, valid=valid)

    def add_scan(self, scan, scan_id):
        """
        add_scan(): description

        :param scan: scan description
        :type scan: scan type

        :param scan_id: scan_id description
        :type scan_id: scan_id type

        :returns: None
        """
        """ add a scan to the current model that is owned by scan_id"""
        success = False
        if self.switch_models(self.model_id):
            # scan[SPDB_ID_VAL] = self.model_id_start_val + self.get_num_scans()
            scan[SPDB_ID_VAL] = scan_id
            success = self.tablemodel.add_scan(scan)
            self._cur_selected_scan = scan
            self.select_row(scan[SPDB_ID_VAL])
            self.set_model_column_defaults()
            success = True

        self.update_table()

        return success
