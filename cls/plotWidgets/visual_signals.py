from PyQt5 import QtWidgets, QtCore

from cls.utils.colors import ColorsObject

MAX_SIGNALS = 50


class VisualSignalsClass(QtCore.QObject):
    """
    This class is so that a single instance of state for the selected ROI's and detector signals can exist
    and used between several widgets to keep plot colors and names unique
    """
    roi_id_updated = QtCore.pyqtSignal(int)
    def __init__(self):
        super(VisualSignalsClass, self).__init__()
        self._roi_shapes = {}
        self._det_sigs = {}
        self.signals = {}
        self._roi_cntr = 0
        self._detsig_cntr = 0
        self.colors = ColorsObject()
        self.plot_boundaries = {'xmin':None, 'xmax':None, 'ymin':None,'ymax':None}
        # self.create_base_signals()

    def set_plot_boundaries(self, xmin, ymin, xmax, ymax):
        """
        in order for the roi polygon coordinates to work in during integration they have to be normalized to
        pixels
        """
        self.plot_boundaries['xmin'] = xmin
        self.plot_boundaries['xmax'] = xmax
        self.plot_boundaries['ymin'] = ymin
        self.plot_boundaries['ymax'] = ymax

    def get_plot_boundaries(self):
        """
        return the dict
        """
        return self.plot_boundaries

    def get_next_roi_id(self):
        self._roi_cntr += 1
        return self._roi_cntr

    def get_current_roi_id(self):
        return self._roi_cntr

    def reset_roi_cntr(self):
        self._roi_cntr = 0
        self.colors.reset_color_map()

    def create_base_signals(self):
        for i in range(MAX_SIGNALS):
            self._roi_shapes[i] = self.gen_sig_dct(i)
            self._det_sigs[i] = self.gen_sig_dct(i)
            # self.signals[i] = self.gen_sig_dct(i)

    def add_signal(self, sig_dct={}):
        """
        sig_dct should be a dict of dicts
        4: {'name': 'ROI_4 [tab:cyan]',
              'color': '#17becf',
              'points': [],
              'checked': False}}
        """
        keys = list(sig_dct.keys())
        if keys:
            key = keys[0]
            dct = sig_dct[key]
            nm = dct["name"]
            if nm.find("ROI") > -1:
                #get member attr for roi_shapes
                _dct = self._roi_shapes
            else:
                # get member attr for det_sigs
                _dct = self._det_sigs
            # nm = dct['name']
            # clr = dct['color']
            # points = dct['points']
            # checked = dct['checked']
            _dct.update(sig_dct)

    def set_signal_checkstate(self, sig_nm, chk):
        """
        toggle a signals checkstate
        """
        dct = self.get_signal(sig_nm)
        if len(dct) > 0:
            dct["checked"] = chk

    def get_signal(self, sig_nm):
        """
        return the signal from either of the dicts
        """
        for id, dct in self._roi_shapes.items():
            if dct["name"] == sig_nm:
                return dct

        for id, dct in self._det_sigs.items():
            if dct["name"] == sig_nm:
                return dct

    def get_parent_dct(self, sig_nm):
        """
        find which dict this signal is in and return the dict
        """
        for id, dct in self._roi_shapes.items():
            if dct["name"] == sig_nm:
                return (self._roi_shapes, id)

        for id, dct in self._det_sigs.items():
            if dct["name"] == sig_nm:
                return (self._det_sigs, id)
        return None, None

    def del_signal(self, sig_nm):
        p_dct, sig_id = self.get_parent_dct(sig_nm)
        if p_dct is not None:
            if len(p_dct) > 0:
                if sig_id is not None:
                    p_dct.pop(sig_id)

        if len(self._roi_shapes) == 0:
            self.reset_roi_cntr()

        self.roi_id_updated.emit(self._roi_cntr)

    def get_max_num_signals(self):
        return MAX_SIGNALS

    def get_all_signals(self):
        self.signals = {}
        for id, dct in self._roi_shapes.items():
            # if dct['checked']:
            self.signals.update({id: dct})

        for id, dct in self._det_sigs.items():
            # if dct['checked']:
            self.signals.update({id: dct})

        return self.signals

    def get_all_rois(self):
        rois = {}
        for id, dct in self._roi_shapes.items():
            rois.update({id: dct})

        return rois

    def get_roi_colors(self):
        clrs = {}
        rois = self.get_all_rois()
        for id, r_dct in rois.items():
            clrs[id] = r_dct['color']
        return clrs

    def get_all_detectors(self):
        dets = {}
        for id, dct in self._det_sigs.items():
            dets.update({id: dct})

        return dets

    def get_num_rois(self):
        num_rois = len(self._roi_shapes)
        return num_rois

    def get_roi_ids(self):
        ids = []
        for id, dct in self._roi_shapes.items():
            ids.append(id)
        return ids

    def clear_all(self):
        self.clear_rois()
        self.clear_dets()
        self.signals = {}
        self.colors.reset_color_map()


    def clear_dets(self):
        self._det_sigs = {}
        self._detsig_cntr = 0

    def clear_rois(self):
        self._roi_shapes = {}
        self._roi_cntr = 0
        self.reset_roi_cntr()

    def add_roi_shape(self, dct):
        self._roi_shapes.update(dct)

    def set_det_signals(self, dct):
        self._det_sigs = dct

    def gen_sig_dct(
        self, sig_id, title="SIG_", color="#FFFFFF", points=[], checked=True, shape=None
    ):
        dct = {}
        dct["name"] = title
        dct["color"] = color
        #dct["points"] = points
        dct["points"] = tuples_list = [(points[i], points[i + 1]) for i in range(0, len(points), 2)]
        dct["checked"] = checked
        dct["shape"] = shape
        return {sig_id: dct}
