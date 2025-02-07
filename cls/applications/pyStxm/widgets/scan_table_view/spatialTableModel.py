from typing import Any
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from cls.applications.pyStxm.widgets.scan_table_view.baseScanTable import *
from cls.utils.roi_dict_defs import *
from cls.utils.log import get_module_logger

_logger = get_module_logger(__name__)


class SpatialScanTableModel(BaseScanTableModel):

    scan_changed = QtCore.pyqtSignal(int, object)

    def __init__(
        self, hdrList, datain, parent=None, use_center=True, is_arb_line=False, *args
    ):
        """
        __init__(): description

        :param hdrList: hdrList description
        :type hdrList: hdrList type

        :param datain: datain description
        :type datain: datain type

        :param parent=None: parent=None description
        :type parent=None: parent=None type

        :param *args: *args description
        :type *args: *args type

        :returns: None
        """
        # QtCore.QAbstractTableModel.__init__(self, parent, *args)
        super(SpatialScanTableModel, self).__init__(hdrList, datain, parent, *args)
        # a dict that will use spatial region scan_id's as key to EnergyRegionScanDef's
        self.cur_scan_row = None
        self.scanListData = datain
        #self.editable = False

        # if('CenterX' in hdrList):
        if "CntrX" in hdrList:
            self.column_map = C_SPATIAL_DCT
        else:
            self.column_map = S_SPATIAL_DCT

        self.set_min_rows(0)
        self.set_max_rows(20)

    def data(self, index: QtCore.QModelIndex, role: QtCore.Qt.ItemDataRole):
        """
        override base table model data function
        data(): description

        :param index: index description
        :type index: index type

        :param role: role description
        :type role: role type

        :returns: None
        """
        """ this function gets called once for each Qt.Role """
        row = index.row()
        col = index.column()
        enabled = False

        if not index.isValid():
            print("index is invalid")
            return None

        flags = index.flags()
        if flags & QtCore.Qt.ItemIsEditable:
            enabled = True

        field_valid = self._field_validity_map[row, col]

        if role == QtCore.Qt.DisplayRole:
            validator = self.validators[col][0]
            inst_clss = self.validators[col][1]
            scan = self.scanListData[row]
            prec = 1
            if col == 0:
                value = scan[SPDB_ID_VAL]
            else:
                value = get_val_from_sp_db(self.column_map[col]["hdr"], scan)
                #only allow stepX and stepY to have val dhown in 3 decimal places
                if self.column_map[col]["hdr"].find("STEP") > -1:
                    prec = self.column_map[col]["prec"]
                # cast using the validators class type for this column
                value = inst_clss(value)

            if type(value) is str:
                return value
            if type(value) is float or np.issubdtype(type(value), np.floating):
                return f"{value:.{prec}f}"
            if type(value) in (int, bool) or np.issubdtype(type(value), np.integer):
                return str(value)

        elif role == QtCore.Qt.BackgroundRole:
            if col == 0:
                normal_color = QtCore.Qt.gray
            elif col < 5:
                normal_color = QtCore.Qt.lightGray
            else:
                normal_color = QtCore.Qt.white

            if enabled:
                bg = QtGui.QBrush(normal_color if field_valid else QtCore.Qt.yellow)
            else:
                bg = QtGui.QBrush(QtGui.QColor(220, 220, 220))
            return bg

        elif role == QtCore.Qt.ForegroundRole:
            return QtGui.QBrush(QtCore.Qt.black) if enabled else QtGui.QBrush(QtCore.Qt.black)

        elif role == QtCore.Qt.FontRole:
            fnt = QtGui.QFont()
            fnt.setPointSize(TABLE_FONT_SIZE)
            if col == 0:
                fnt.setBold(True)
            return fnt

        elif role == QtCore.Qt.TextAlignmentRole:
            if col == 0:
                return QtCore.Qt.AlignLeft
            return QtCore.Qt.AlignCenter

        return None

    def setData(self, index: QtCore.QModelIndex, value: Any, role: QtCore.Qt.ItemDataRole, recalc=True, do_signal=True):
        """
        setData(): description

        :param index: index description
        :type index: index type

        :param value: value description
        :type value: value type

        :param role: role description
        :type role: role type

        :param recalc=True: recalc=True description
        :type recalc=True: recalc=True type

        :param do_signal=True: do_signal=True description
        :type do_signal=True: do_signal=True type

        :returns: None
        """
        row = index.row()
        col = index.column()
        ok = True
        if role == QtCore.Qt.EditRole:

            if len(value) == 0:
                # the user didnt enter a value but still
                # if user just hit enter in one of the box's we still want to emit scan_changed
                scan = self.scanListData[row]
                if do_signal:
                    self.scan_changed.emit(row, scan)
                return True

            if col == 0:
                return True
            elif col == 10:
                val = str(value.toString())
                if len(val) < 1:
                    ok = False
            else:
                validator = self.validators[col][0]
                inst_clss = self.validators[col][1]

                if not validator(value):
                    return False

                if len(value) > 0:
                    val = inst_clss(value)
                else:
                    # if user just hit enter in one of the box's we still want to emit scan_changed
                    scan = self.scanListData[row]
                    if do_signal:
                        self.scan_changed.emit(row, scan)
                    return True

            # call the associated setter function for this column (this is setup in the scan definition class
            if ok:
                # only change the value if the user entered a value
                scan = self.scanListData[row]

                # check for a floor or ceiling violation, if there is dont change the value in the model
                floor_lim = self.column_map[col]["floor_val"]
                ceiling_lim = self.column_map[col]["ceiling_val"]

                if not self.is_valid_floor_ceiling_vals(floor_lim, ceiling_lim, val):
                    _logger.error("Value entered is out of range")
                    return False

                roi = get_roi_from_sp_db(self.column_map[col]["hdr"], scan)
                set_field_val_in_sp_db(self.column_map[col]["hdr"], val, scan)
                func = self.column_map[col]["func"]
                # force the row to recalc
                if recalc:
                    # now call the resepctive function to recalc the scan params
                    func(roi)

        if role in (QtCore.Qt.EditRole, QtCore.Qt.DisplayRole):
            # must emit this as part of the framework support for an editable AbstractTableModel
            scan = self.scanListData[row]
            self.dataChanged.emit(index, index)

            if do_signal:
                # print 'EnergyScanTableModel: setData: emitting scan_changed'
                self.scan_changed.emit(row, scan)

        return True

    def modify_data(self, scan_id, newscan, do_step_npts=False):
        """
        modify_data(): description

        :param scan_id: scan_id description
        :type scan_id: scan_id type

        :param newscan: newscan description
        :type newscan: newscan type

        :param do_step_npts=False: do_step_npts=False description
        :type do_step_npts=False: do_step_npts=False type

        :returns: None
        """
        """ tpl = ((startx, starty), (rangex, rangey))"""
        self.replace_scan(scan_id, newscan, do_step_npts)
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
