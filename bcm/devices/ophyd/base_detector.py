from PyQt5 import QtCore

from cls.plotWidgets.utils import *
from cls.types.stxmTypes import scan_types, detector_types
from cls.utils.log import get_module_logger


_logger = get_module_logger(__name__)

DATA_OFFSET = 2

class BaseDeviceSignals(QtCore.QObject):
    """
    The base signals provided in the API for scans, this class provides the following signals to every sscan record

    :signal changed: The detectordevice has read a new value

    :returns: None

    """

    # changed = QtCore.pyqtSignal(object)  # dct
    # sig_do_read = QtCore.pyqtSignal()
    # sig_do_event_emit = QtCore.pyqtSignal()
    new_plot_data = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        """
        __init__(): description

        :param parent=None: parent=None description
        :type parent=None: parent=None type

        :returns: None
        """
        QtCore.QObject.__init__(self, parent)


class BaseDetectorDev:

    def __init__(self, **kwargs):
        super(BaseDetectorDev, self).__init__()
        self.det_id = None
        self.p_num_points = 1
        self.p_num_rows = None
        self._pnts_per_row = None
        self._cb_id = None
        self._scan_type = None
        # self.mode = 0
        self._scale_val = 1.0
        self._det_type = detector_types.POINT  # or LINE or 2D
        self._plot_dct = make_counter_to_plotter_com_dct()

    def configure(self):
        """
        to be implemented by inheriting class
        :return:
        """
        pass

    # def set_mode(self, val):
    #     self.mode = val

    def set_det_type(self, det_type="POINT"):
        if det_type.find("POINT") > -1:
            self._det_type = detector_types.POINT
        elif det_type.find("LINE_FLYER") > -1:
            self._det_type = detector_types.LINE_FLYER
        elif det_type.find("LINE") > -1:
            self._det_type = detector_types.LINE
        elif det_type.find("TWO_D") > -1:
            self._det_type = detector_types.TWO_D
        else:
            print(
                "set_det_type: Unknown Detector type [%s], needs to be a string of detector_type"
                % det_type
            )

    def get_det_type(self):
        return self._det_type

    def is_point_det(self):
        if self._det_type is detector_types(detector_types.POINT):
            return True
        else:
            return False

    def is_line_det(self):
        if self._det_type is detector_types(detector_types.LINE):
            return True
        else:
            return False

    def is_line_flyer_det(self):
        if self._det_type is detector_types(detector_types.LINE_FLYER):
            return True
        else:
            return False

    def is_2D_det(self):
        if self._det_type is detector_types(detector_types.TWO_D):
            return True
        else:
            return False

    def set_num_points(self, val):
        self.p_num_points = int(val)

    def set_num_rows(self, val):
        self.p_num_rows = int(val)

    def set_points_per_row(self, val):
        self._pnts_per_row = int(val)

    def set_scan_type(self, _stype):
        self._scan_type = _stype