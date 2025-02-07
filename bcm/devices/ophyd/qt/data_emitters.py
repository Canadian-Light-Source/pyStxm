import json

from PyQt5 import QtCore
import numpy as np
import copy

# import itertools
from collections import deque
from bluesky.callbacks.core import CallbackBase, get_obj_fields
from cls.plotWidgets.utils import *
from cls.utils.hash_utils import gen_unique_id_from_string
from cls.plotWidgets.utils import gen_complete_spec_chan_name
from bcm.devices.ophyd.sis3820_scalar import sis3820_remove_row_change_extra_point

SIMULATE = False


class QtDataEmitterSignals(QtCore.QObject):
    new_data = QtCore.pyqtSignal(object)
    final_data = QtCore.pyqtSignal(object)
    new_plot_data = QtCore.pyqtSignal(object)  # emits a standard plotter dict

    def __init__(self, epoch="run", **kwargs):
        super(QtDataEmitterSignals, self).__init__()


class QtDataEmitter(CallbackBase):
    def __init__(self, epoch="run", **kwargs):
        super(QtDataEmitter, self).__init__()
        self._q_sigs = QtDataEmitterSignals()
        self.new_data = self._q_sigs.new_data
        self.final_data = self._q_sigs.final_data
        self.new_plot_data = self._q_sigs.new_plot_data
        self._plot_dct = make_counter_to_plotter_com_dct()




class BaseQtSpectraDataEmitter(QtDataEmitter):
    def __init__(self, det_id, det_nm, y=None, x=None, epoch="run", **kwargs):
        super(BaseQtSpectraDataEmitter, self).__init__(None)
        self.det_id = det_id
        self.det = det_nm #gen_unique_id_from_string(cntr)
        self._start_doc = None
        self._stop_doc = None
        self._events = deque()
        self._descriptors = deque()
        self._scan_type = None
        # self._sp_id_lst = []
        self._spid_seq_map = {}
        # self._ttl_sequence_points = 0
        # self._num_spids = 0

        if x is not None:
            self.x, *others = get_obj_fields([x])
        else:
            self.x = "seq_num"

        if y is not None:
            self.y, *others = get_obj_fields([y])
        else:
            self.y = "seq_num"

        if "scan_type" in kwargs.keys():
            self._scan_type = kwargs["scan_type"]

        if "spid_seq_map" in kwargs.keys():
            self._spid_seq_map = kwargs["spid_seq_map"]

        self._epoch_offset = None  # used if x == 'time'
        self._epoch = epoch

    def start(self, doc):
        # print('MyDataEmitter: start')
        self.x_data, self.y_data = [], []

        self._start_doc = doc
        super().start(doc)

    def descriptor(self, doc):
        # print('MyDataEmitter: descriptor')
        self._descriptors.append(doc)
        super().descriptor(doc)

    def event(self, doc):
        # print('MyDataEmitter: event: ')
        self._events.append(doc)
        super().event(doc)

    def update_caches(self, x, y):
        self.y_data.append(y)
        self.x_data.append(x)

    def stop(self, doc):
        # print('MyDataEmitter: stop')
        self._stop_doc = doc
        super().stop(doc)

    def reset(self):
        # print('MyDataEmitter: reset')
        self._spid_seq_map = {}
        self._start_doc = None
        self._stop_doc = None
        self._events.clear()
        self._descriptors.clear()


class BaseQtImageDataEmitter(QtDataEmitter):
    def __init__(self, det_id, det_nm, y=None, x=None, epoch="run", **kwargs):
        super(BaseQtImageDataEmitter, self).__init__(None)
        self.det_id = det_id
        self.det = det_nm
        self._start_doc = None
        self._stop_doc = None
        self._events = deque()
        self._descriptors = deque()
        self._scan_type = None
        self._bi_dir = False
        if "scan_type" in kwargs.keys():
            self._scan_type = kwargs["scan_type"]
        if "bi_dir" in kwargs.keys():
            self._bi_dir = kwargs["bi_dir"]

        if x is not None:
            self.x, *others = get_obj_fields([x])
        else:
            self.x = "seq_num"

        if y is not None:
            self.y, *others = get_obj_fields([y])
        else:
            self.y = "seq_num"

        self._epoch_offset = None  # used if x == 'time'
        self._epoch = epoch

    def start(self, doc):
        # print('BaseQtImageDataEmitter: start')
        self.x_data, self.y_data = [], []
        self._start_doc = doc
        super().start(doc)

    def descriptor(self, doc):
        # print('BaseQtImageDataEmitter: descriptor')
        self._descriptors.append(doc)
        super().descriptor(doc)

    def event(self, doc):
        # print('BaseQtImageDataEmitter: event: ')
        self._events.append(doc)
        super().event(doc)

    def update_caches(self, x, y):
        self.y_data.append(y)
        self.x_data.append(x)

    def stop(self, doc):
        # print('BaseQtImageDataEmitter: stop')
        self._stop_doc = doc
        super().stop(doc)

    def reset(self):
        # print('BaseQtImageDataEmitter: reset')
        self._start_doc = None
        self._stop_doc = None
        self._events.clear()
        self._descriptors.clear()


class SpecDataEmitter(BaseQtSpectraDataEmitter):
    def __init__(self, det, x=None, epoch="run", **kwargs):
        super(SpecDataEmitter, self).__init__(det, x=x, epoch=epoch, **kwargs)
        self.det = det

    def event(self, doc):
        """Unpack data from the event and call self.update().
        {'descriptor': '4731a9d3-caf4-4e55-b26d-2d01b82accd9',
         'time': 1546888660.8272438,
         'data': {'det1': 5.0,
          'det2': 1.764993805169191,
          'mtr_x': -500.0,
          'mtr_x_user_setpoint': -500.0},
         'timestamps': {'det1': 1546888660.7001529,
          'det2': 1546888660.7001529,
          'mtr_x': 1546884667.758824,
          'mtr_x_user_setpoint': 1546888660.21448},
         'seq_num': 1,
         'uid': 'b389da0f-540f-427e-89bf-bd7c501ee717',
         'filled': {}}
        """
        # This outer try/except block is needed because multiple event
        # streams will be emitted by the RunEngine and not all event
        # streams will have the keys we want.
        # print('SpecDataEmitter: event: ')
        try:
            # This inner try/except block handles seq_num and time, which could
            # be keys in the data or accessing the standard entries in every
            # event.
            try:
                # dct = dict(doc)
                # print(doc['data'].keys())
                if self.det in doc["data"].keys():
                    new_y = doc["data"][self.det]
                    # if(self.x not in doc['data'].keys()):
                    if self.x not in doc["data"].keys():
                        # new_x = doc['data'][self.x]
                        new_x = self._spid_seq_map[doc["seq_num"]][1]
                    else:
                        new_x = doc["seq_num"]
                    # _sp_id = self._sp_id_lst
                    _sp_id = self._spid_seq_map[doc["seq_num"]][0]
                else:
                    new_y = doc["data"][self.y]
                    # _sp_id = self._sp_id_lst
                    _sp_id = self._spid_seq_map[doc["seq_num"]][0]

            except KeyError:
                # print('SpecDataEmitter: KeyError: ')
                if self.x in ("time", "seq_num"):
                    new_x = doc[self.x]
                else:
                    raise

        except KeyError:
            # wrong event stream, skip it
            # print('SpecDataEmitter: KeyError: ')
            return

        # Special-case 'time' to plot against against experiment epoch, not
        # UNIX epoch.
        if self.x == "time" and self._epoch == "run":
            new_x -= self._epoch_offset

        self.update_caches(new_x, new_y)
        # print('SpecDataEmitter: emit x=%f y=%f' % (new_x, new_y))
        # self.new_data.emit(dct)
        self.new_data.emit((new_x, new_y))
        self._plot_dct[CNTR2PLOT_ROW] = 0
        self._plot_dct[CNTR2PLOT_SP_ID] = _sp_id
        self._plot_dct[CNTR2PLOT_COL] = new_x
        self._plot_dct[CNTR2PLOT_VAL] = new_y
        self._plot_dct[CNTR2PLOT_SCAN_TYPE] = self._scan_type
        self.new_plot_data.emit(self._plot_dct)

        # self.update_plot()
        super().event(doc)

    def update_caches(self, x, y):
        self.y_data.append(y)
        self.x_data.append(x)


class LineDataEmitter(BaseQtSpectraDataEmitter):
    def __init__(self, y, x=None, epoch="run", **kwargs):
        super(LineDataEmitter, self).__init__(y, x=x, epoch=epoch, **kwargs)

    def event(self, doc):
        """Unpack data from the event and call self.update().
        {'descriptor': '4731a9d3-caf4-4e55-b26d-2d01b82accd9',
         'time': 1546888660.8272438,
         'data': {'det1': 5.0,
          'det2': 1.764993805169191,
          'mtr_x': -500.0,
          'mtr_x_user_setpoint': -500.0},
         'timestamps': {'det1': 1546888660.7001529,
          'det2': 1546888660.7001529,
          'mtr_x': 1546884667.758824,
          'mtr_x_user_setpoint': 1546888660.21448},
         'seq_num': 1,
         'uid': 'b389da0f-540f-427e-89bf-bd7c501ee717',
         'filled': {}}
        """
        # This outer try/except block is needed because multiple event
        # streams will be emitted by the RunEngine and not all event
        # streams will have the keys we want.
        # print('LineDataEmitter: event: ', doc)
        #
        # try:
        #     # This inner try/except block handles seq_num and time, which could
        #     # be keys in the data or accessing the standard entries in every
        #     # event.
        #     try:
        #         #dct = dict(doc)
        #         # print(doc['data'].keys())
        #         new_x = doc['data'][self.x]
        #     except KeyError:
        #         # print('SpecDataEmitter: KeyError: ')
        #         if self.x in ('time', 'seq_num'):
        #             new_x = doc[self.x]
        #         else:
        #             raise
        #     new_y = doc['data'][self.y]
        # except KeyError:
        #     # wrong event stream, skip it
        #     # print('SpecDataEmitter: KeyError: ')
        #     return
        #
        # # Special-case 'time' to plot against against experiment epoch, not
        # # UNIX epoch.
        # if self.x == 'time' and self._epoch == 'run':
        #     new_x -= self._epoch_offset
        #
        # self.update_caches(new_x, new_y)
        # print('SpecDataEmitter: emit x=%f y=%f' % (new_x, new_y))
        # # self.new_data.emit(dct)
        # self.new_data.emit((new_x, new_y))
        # # self.update_plot()
        super().event(doc)

    def update_caches(self, x, y):
        self.y_data.append(y)
        self.x_data.append(x)


#######################################################################################
def indices_array_generic(m, n):
    r0 = np.arange(m)  # Or r0,r1 = np.ogrid[:m,:n], out[:,:,0] = r0
    r1 = np.arange(n)
    out = np.empty((m, n, 2), dtype=int)
    out[:, :, 0] = r0[:, None]
    out[:, :, 1] = r1
    return out


def gen_seq_num_to_x_y_dict(rows, cols, bi_dir=False):
    nd = indices_array_generic(rows, cols)
    idx = 0
    if bi_dir:
        for idx in list(range(rows)):
            if (idx % 2) > 0:
                # odd
                arr = nd[idx]
                up_arr = np.flipud(arr)
                nd[idx] = up_arr
    aaa = np.reshape(nd, (rows * cols, 2))
    enum = [i for i, _ in enumerate(aaa)]
    x = zip(enum, aaa)
    dct = dict(x)
    return dct


class ImageDataEmitter(BaseQtImageDataEmitter):
    def __init__(self, det_id, det_nm, y=None, x=None, epoch="run", **kwargs):
        super(ImageDataEmitter, self).__init__(det_id, det_nm, y=y, x=x, epoch=epoch, **kwargs)
        self.det_data = []
        self.rows = 0
        self.cols = 0
        self.x_idx = 0
        self.y_idx = 0
        self.img_idx = 0  # linespec scans can be made up of multiple images (ev regions) side by side in a single scan
        self.factor_list = []
        self._seq_dct = None

    def update_idxs(self, seq_num):
        """
        The doc only contains a single sequence number so generate row column indexs
        The sequence number is used as an index into teh sequence_map dict which is constructed like this:
            {<seq num (int)>: {'img_num': <img_num> (int), 'row': <row_num> (int), 'col': <column_num> (int)},
            ...
            }

        :param seq_num:
        :return:
        """
        if seq_num in self._seq_dct.keys():
            self.img_idx = self._seq_dct[seq_num]["img_num"]
            # self.y_idx = self._seq_dct[seq_num][self.img_idx][0]
            self.y_idx = self._seq_dct[seq_num]["row"]
            # self.x_idx = self._seq_dct[seq_num][self.img_idx][1]
            #self.x_idx = self._seq_dct[seq_num]["col"]
            self.x_idx = self._seq_dct[seq_num]["col"] - 1
        else:
            # increment x
            if seq_num != 1:
                self.x_idx += 1

    def set_row_col(self, rows, cols, seq_dct=None):
        """
        if seq_dct is None then generate a new sequence dictionary map, otherwise install teh one that is passed in
        :param rows:
        :param cols:
        :param seq_dct:
        :return:
        """
        self.rows = int(rows)
        self.cols = int(cols)
        # self.gen_factor_list(cols)
        if seq_dct is None:
            self._seq_dct = gen_seq_num_to_x_y_dict(
                self.rows, self.cols, bi_dir=self._bi_dir
            )
        else:
            self._seq_dct = seq_dct

    def start(self, doc):
        # print('ImageDataEmitter: start')
        if self._seq_dct is None:
            print("ERROR: First set the number of rows and columns!")
            return
        self.x_data, self.y_data, self.det_data = [], [], []
        self.x_idx = 0
        self.y_idx = 0
        self._start_doc = doc
        super().start(doc)

    def event(self, doc):
        """Unpack data from the event and call self.update().
        """
        # This outer try/except block is needed because multiple event
        # streams will be emitted by the RunEngine and not all event
        # streams will have the keys we want.        new_det = None
        #print(doc)
        new_x = None
        new_y = None
        try:
            # This inner try/except block handles seq_num and time, which could
            # be keys in the data or accessing the standard entries in every
            # event.
            try:
                # print(doc)
                # make sure the index is zero based
                seq_num = doc["seq_num"] - 1

                self.update_idxs(seq_num)
                # print(self.det)
                # print(doc['data'].keys())

                klst = list(doc["data"].keys())
                res = [i for i in klst if self.det in i]
                # if(self.det in doc['data'].keys()):
                if len(res) > 0:
                    if SIMULATE:
                        new_det = np.random.randint(65535)
                    else:
                        #new_det = doc["data"][self.det]
                        new_det = doc["data"][klst[0]]

                    new_x = self.x_idx
                    new_y = self.y_idx
                    # print('ImageDataEmitter: event: seq_num[%d] [%d, %d, %d]' % (seq_num, self.x_idx, self.y_idx, new_det))
                else:
                    return
            except KeyError:
                print("ImageDataEmitter: KeyError: ")
                if self.x in ("time", "seq_num"):
                    new_x = doc[self.x]
                else:
                    raise
            # new_y = doc['data'][self.y]
        except KeyError:
            # wrong event stream, skip it
            # print('ImageDataEmitter: KeyError: ')
            return

        do_emit = False
        if type(new_det) in [int, float]:
            do_emit = True
        elif type(new_det) == np.ndarray and new_det.any():
            do_emit = True
        if do_emit:
            self.update_caches(new_x, new_y, new_det)
            # print('ImageDataEmitter: emit x=%f y=%f' % (new_x, new_y))
            # self.new_data.emit(dct)
            #self.new_data.emit((new_x, new_y, new_det))
            self._plot_dct[CNTR2PLOT_DETID] = self.det_id
            self._plot_dct[CNTR2PLOT_ROW] = int(new_y)
            self._plot_dct[CNTR2PLOT_COL] = int(new_x)
            self._plot_dct[CNTR2PLOT_VAL] = new_det
            self._plot_dct[CNTR2PLOT_IS_LINE] = True
            self._plot_dct[CNTR2PLOT_IS_POINT] = False

            self.new_plot_data.emit(self._plot_dct)
            # self.update_plot()
        super().event(doc)

    def update_caches(self, x, y, det):
        self.y_data.append(y)
        self.x_data.append(x)
        self.det_data.append(det)

    def stop(self, doc):
        # print('ImageDataEmitter: stop')
        self._stop_doc = doc
        self.emit_data()
        super().stop(doc)

    def emit_data(self):
        dct = {}
        dct["x_data"] = self.x_data
        dct["y_data"] = self.y_data
        dct["det_data"] = self.det_data
        self.final_data.emit(dct)
        # print('emitting data')


class SIS3820ImageDataEmitter(BaseQtImageDataEmitter):
    def __init__(self, det_id, det_nm, y=None, x=None, det_dev=None, is_pxp=True, epoch="run", **kwargs):
        super(SIS3820ImageDataEmitter, self).__init__(det_id, det_nm, y=y, x=x, epoch=epoch, **kwargs)
        self.det_data = []
        self.det_dev = det_dev
        self.is_pxp = is_pxp
        self.rows = 0
        self.cols = 0
        self.x_idx = -1
        self.y_idx = 0
        self.img_idx = 0  # linespec scans can be made up of multiple images (ev regions) side by side in a single scan
        self.factor_list = []
        self._seq_dct = None
        self.ch_id_lst = []
        self.ch_nm_lst = []
        self._acquired_rows = []
        self.skip_first_datapoint = False
        self.md = {}
        if self.det_dev:
            self.ch_id_lst, self.ch_nm_lst, fbk_attrs = self.det_dev.get_enabled_chans()

    def update_idxs(self, seq_num):
        """
        The doc only contains a single sequence number so generate row column indexs
        The sequence number is used as an index into teh sequence_map dict which is constructed like this:
            {<seq num (int)>: {'img_num': <img_num> (int), 'row': <row_num> (int), 'col': <column_num> (int)},
            ...
            }

        :param seq_num:
        :return:
        """
        if seq_num in self._seq_dct.keys():
            self.img_idx = self._seq_dct[seq_num]["img_num"]
            # self.y_idx = self._seq_dct[seq_num][self.img_idx][0]
            self.y_idx = self._seq_dct[seq_num]["row"]
            # self.x_idx = self._seq_dct[seq_num][self.img_idx][1]
            # if self.is_pxp:
            #     #skip first datapoint because 3820 produces return to row point which we dont want
            #     self.x_idx = self._seq_dct[seq_num]["col"] - 1
            self.x_idx = self._seq_dct[seq_num]["col"]
        else:
            # increment x
            if seq_num != 1:
                self.x_idx += 1

    def set_row_col(self, rows, cols, seq_dct=None):
        """
        if seq_dct is None then generate a new sequence dictionary map, otherwise install teh one that is passed in
        :param rows:
        :param cols:
        :param seq_dct:
        :return:
        """
        self.rows = int(rows)
        self.cols = int(cols)
        # self.gen_factor_list(cols)
        if seq_dct is None:
            self._seq_dct = gen_seq_num_to_x_y_dict(
                self.rows, self.cols, bi_dir=self._bi_dir
            )
        else:
            self._seq_dct = seq_dct

    def start(self, doc):
        # print('ImageDataEmitter: start')
        if self._seq_dct is None:
            print("ERROR: First set the number of rows and columns!")
            return
        self.x_data, self.y_data, self.det_data = [], [], []
        self.md = json.loads(doc['metadata'])
        self.md['sis3820_data_map'] = copy.copy(self.det_dev.enabled_channels_lst)
        self.x_idx = 0
        self.y_idx = 0
        self._acquired_rows = []
        self._start_doc = doc
        super().start(doc)

    def process_sis3820_data(self, doc):
        """
        ('event', {'descriptor': '3b9f225b-9f74-4ae1-a468-c347bb7e5cff', 'uid': '9e7561cc-9231-4d6d-afae-1190a7ee0cbd', 'time': 1676490522.2321472, 'seq_num': 50, 'data': {'SIS3820_waveform_rbv': [0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044]}, 'timestamps': {'SIS3820_waveform_rbv': 1676490522.2321472}, 'filled': {}, '_name': 'Event'})
        """
        data_dct = {}
        data_map = self.md['sis3820_data_map']
        num_chans = len(self.md['sis3820_data_map'])
        seq_num = doc['seq_num']
        self.skip_first_datapoint = False
        d_keys = list(doc['data'].keys())
        if self.y_idx not in self._acquired_rows:
            self._acquired_rows.append(self.y_idx)

        for k in d_keys:
            if k.find('SIS3820') > -1:
                data_arr = doc['data'][k]
                #take a slice of data array to pull out all values of each channel
                for ch_num in range(num_chans):
                    ch_dct = data_map[ch_num]
                    _num = ch_num + 1
                    # numpy slicing start:stop:step for each enabled channel
                    dat = data_arr[_num-1::num_chans]
                    fix_first_point = False
                    if not self.is_pxp:
                        fix_first_point = True

                    stripped_dat = sis3820_remove_row_change_extra_point(dat, ignore_even_data_points=False, fix_first_point=fix_first_point, remove_first=False, remove_last=False)
                    # if ch_num == 0:
                    #     print(f"data_emitters.py: process_sis3820_data(doc): chan 0 data: raw", dat)
                    #     print(f"data_emitters.py: process_sis3820_data(doc): chan 0 data: STRIPPED", stripped_dat)
                    #     print()
                    # print(dat.shape)
                    # print(stripped_dat.shape)

                    data_dct[ch_dct['chan_nm']] = stripped_dat

        if self.skip_first_datapoint:
            data_dct = None
        return(data_dct)
        #pprint.pprint(data_dct)

    def event(self, doc):
        """Unpack data from the event and call self.update().
        """
        # This outer try/except block is needed because multiple event
        # streams will be emitted by the RunEngine and not all event
        # streams will have the keys we want.        new_det = None
        #print(doc)
        new_x = None
        new_y = None
        try:
            # This inner try/except block handles seq_num and time, which could
            # be keys in the data or accessing the standard entries in every
            # event.
            try:
                # print(doc)
                # make sure the index is zero based
                seq_num = doc["seq_num"] - 1

                # self.update_idxs(seq_num)
                # print(self.det)
                # print(doc['data'].keys())

                klst = list(doc["data"].keys())
                res = [i for i in klst if self.det in i]
                # if(self.det in doc['data'].keys()):
                if len(res) > 0:
                    if SIMULATE:
                        new_det = np.random.randint(65535)
                    else:
                        #new_det = doc["data"][self.det]
                        new_det = doc["data"][klst[0]]
                    if new_det == None:
                        return
                    if len(new_det) == 1:
                        if new_det[0] == 0:
                            # looks like a line reset array
                            print("SIS3820ImageDataEmitter: event: looks like a line reset array")
                            return
                    self.update_idxs(seq_num)
                    new_x = self.x_idx
                    new_y = self.y_idx
                    # print('SIS3820ImageDataEmitter: event: seq_num[%d] [%d, %d, %d]' % (seq_num, self.x_idx, self.y_idx, new_det))
                else:
                    return

            except KeyError:
                print("SIS3820ImageDataEmitter: KeyError: ")
                if self.x in ("time", "seq_num"):
                    new_x = doc[self.x]
                else:
                    raise
            # new_y = doc['data'][self.y]
        except KeyError:
            # wrong event stream, skip it
            # print('SIS3820ImageDataEmitter: KeyError: ')
            return

        do_emit = False
        if type(new_det) in [int, float]:
            do_emit = True
        elif type(new_det) == dict:
            do_emit = True
        elif type(new_det) == np.ndarray and new_det.any():
            do_emit = True
        if do_emit:
            #new_det = self.process_sis3820_data(doc)
            if new_det:
                self.update_caches(new_x, new_y, new_det)
                # print('SIS3820ImageDataEmitter: emit x=%f y=%f' % (new_x, new_y))
                # self.new_data.emit(dct)
                #self.new_data.emit((new_x, new_y, new_det))
                self._plot_dct[CNTR2PLOT_DETID] = self.det_id
                self._plot_dct[CNTR2PLOT_ROW] = int(new_y)
                self._plot_dct[CNTR2PLOT_COL] = int(new_x)
                self._plot_dct[CNTR2PLOT_VAL] = new_det
                self._plot_dct[CNTR2PLOT_IS_LINE] = True
                self._plot_dct[CNTR2PLOT_IS_POINT] = False
                #print(f"SIS3820ImageDataEmitter: event:: col = {self._plot_dct[CNTR2PLOT_COL]} row = {self._plot_dct[CNTR2PLOT_ROW]} = {new_det}")
                self.new_plot_data.emit(self._plot_dct)
            # self.update_plot()
        super().event(doc)

    def update_caches(self, x, y, det):
        self.y_data.append(y)
        self.x_data.append(x)
        self.det_data.append(det)

    def stop(self, doc):
        # print('ImageDataEmitter: stop')
        self._stop_doc = doc
        self.emit_data()
        super().stop(doc)

    def emit_data(self):
        dct = {}
        dct["x_data"] = self.x_data
        dct["y_data"] = self.y_data
        dct["det_data"] = self.det_data
        self.final_data.emit(dct)
        # print('emitting data')

class SIS3820SpecDataEmitter(BaseQtSpectraDataEmitter):

    def __init__(self, det_id, det_nm=None, det_dev=None, epoch="run", **kwargs):
        super(SIS3820SpecDataEmitter, self).__init__(det_id, det_nm, epoch=epoch, **kwargs)
        self.det = det_nm
        self.det_dev = det_dev
        self.x_idx = 0
        self.ch_id_lst = []
        self.ch_nm_lst = []
        self.md = {}
        if self.det_dev:
            self.ch_id_lst, self.ch_nm_lst, fbk_attrs = self.det_dev.get_enabled_chans()

    def start(self, doc):
        # print('ImageDataEmitter: start')
        # if self._seq_dct is None:
        #     print("ERROR: First set the number of rows and columns!")
        #     return
        #self.x_data, self.y_data, self.det_data = [], [], []
        self.md = json.loads(doc['metadata'])
        self.md['sis3820_data_map'] = copy.copy(self.det_dev.enabled_channels_lst)
        self.x_idx = 0
        #self.y_idx = 0
        self._start_doc = doc
        super().start(doc)

    def process_sis3820_data(self, doc, sp_id):
        """
        ('event', {'descriptor': '3b9f225b-9f74-4ae1-a468-c347bb7e5cff', 'uid': '9e7561cc-9231-4d6d-afae-1190a7ee0cbd', 'time': 1676490522.2321472, 'seq_num': 50, 'data': {'SIS3820_waveform_rbv': [0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2043, 0, 0, 0, 0, 0, 0, 0, 2044, 0, 0, 0, 0, 0, 0, 0, 2044]}, 'timestamps': {'SIS3820_waveform_rbv': 1676490522.2321472}, 'filled': {}, '_name': 'Event'})
        """
        data_dct = {}
        #data_map = self.md['sis3820_data_map']
        #num_chans = len(self.md['sis3820_data_map'])
        d_keys = list(doc['data'].keys())
        for k in d_keys:
            if k.find('SIS3820') > -1:
                #data_arr = doc['data'][k]
                chan_dct = doc['data'][k]

                for chan_nm, data in chan_dct.items():
                    if chan_nm.find("-spid-") == -1:
                        # generate the correct channel name with spid
                        chan_nm = gen_complete_spec_chan_name(chan_nm, sp_id)
                    data_dct[chan_nm] = data

        return(data_dct)

    def event(self, doc):
        """Unpack data from the event and call self.update().
        """
        # This outer try/except block is needed because multiple event
        # streams will be emitted by the RunEngine and not all event
        # streams will have the keys we want.
        # print('SpecDataEmitter: event: ')
        try:
            # This inner try/except block handles seq_num and time, which could
            # be keys in the data or accessing the standard entries in every
            # event.
            try:
                data_dct = None
                # make sure the index is zero based
                seq_num = doc["seq_num"] - 1
                det_name = self.det + "_waveform_rbv"
                if det_name in doc["data"].keys():
                    new_y = doc["data"][det_name]
                    if self.x not in doc["data"].keys():
                        new_x = self._spid_seq_map[seq_num][1]
                    else:
                        new_x = doc["seq_num"]
                    _sp_id = self._spid_seq_map[seq_num][0]

                else:
                    return
                    # new_y = doc["data"][self.y]
                    # _sp_id = self._spid_seq_map[doc["seq_num"]][0]

                data_dct = self.process_sis3820_data(doc, _sp_id)

            except Exception as e:
                # print(f'SpecDataEmitter: KeyError: 1: exception = {e}')
                # print(f"self._spid_seq_map={self._spid_seq_map}")
                if self.x in ("time", "seq_num"):
                    new_x = doc[self.x]
                else:
                    raise

        except Exception as e:
            # wrong event stream, skip it
            # print(f'SpecDataEmitter: KeyError: 2 exception = {e}')
            return

        # Special-case 'time' to plot against against experiment epoch, not
        # UNIX epoch.
        if self.x == "time" and self._epoch == "run":
            new_x -= self._epoch_offset

        self.update_caches(new_x, new_y)
        # # print('SpecDataEmitter: emit x=%f y=%f' % (new_x, new_y))
        if data_dct:
            #self._plot_dct[CNTR2PLOT_SP_ID] = _sp_id
            self._plot_dct[CNTR2PLOT_ROW] = 0
            # strip the DNM_ if it exists
            self._plot_dct[CNTR2PLOT_DETID] = self.det.replace("DNM_","")
            self._plot_dct[CNTR2PLOT_COL] = new_x
            self._plot_dct[CNTR2PLOT_VAL] = data_dct
            #self._plot_dct[CNTR2PLOT_SCAN_TYPE] = self._scan_type
            self.new_plot_data.emit(self._plot_dct)

        # self.update_plot()
        super().event(doc)

    def update_caches(self, x, y):
        self.y_data.append(y)
        self.x_data.append(x)