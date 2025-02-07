"""
Created on Jan 4, 2019

@author: bergr
"""

import numpy as np

from cls.data_io.nxstxm.stxm_types import scan_types, two_posner_scans
from cls.data_io.nxstxm.device_names import *

# from cls.data_io.nxstxm.utils import dct_get, dct_put
from cls.data_io.nxstxm.roi_dict_defs import *

# from cls.data_io.nxstxm.nxstxm_utils import (make_signal, _dataset, _string_attr, _group, make_1d_array, \
#                                           get_nx_standard_epu_mode, get_nx_standard_epu_harmonic_new, translate_pol_id_to_stokes_vector, \
#                                           readin_base_classes, make_NXclass, remove_unused_NXsensor_fields)

from cls.data_io.nxstxm.nxstxm_utils import _dataset, _string_attr

import cls.data_io.nxstxm.nx_key_defs as nxkd


def modify_stack_ctrl_data_grps(parent, nxgrp, doc, scan_type):
    """
    :param parent:
    :param nxgrp:
    :param doc:
    :param scan_type:
    :return:
    """
    resize_data = False
    rois = parent.get_rois_from_current_md(doc["run_start"])
    x_src = parent.get_devname(rois[SPDB_X][POSITIONER])
    x_posnr_nm = parent.fix_posner_nm(rois[SPDB_X][POSITIONER])
    y_src = parent.get_devname(rois[SPDB_Y][POSITIONER])
    y_posnr_nm = parent.fix_posner_nm(rois[SPDB_Y][POSITIONER])

    xnpoints = int(rois[SPDB_X][NPOINTS])
    ynpoints = int(rois[SPDB_Y][NPOINTS])
    evs = parent._wdg_com["SINGLE_LST"]["EV_ROIS"]
    num_ev_points = len(evs)

    ttlpnts = num_ev_points * xnpoints * ynpoints

    resize_data = True
    # scan was aborted so use setpoint data here
    xdata = np.array(rois[SPDB_X][SETPOINTS], dtype=np.float32)
    ydata = np.array(rois[SPDB_Y][SETPOINTS], dtype=np.float32)

    # _dataset(nxgrp, y_posnr_nm, ydata, 'NX_FLOAT')
    # _dataset(nxgrp, x_posnr_nm, xdata, 'NX_FLOAT')
    # if there were already sample_x and y created by the default constructors then delete them and recreate with the right data
    if nxkd.SAMPLE_Y in nxgrp.keys():
        del nxgrp[nxkd.SAMPLE_X]
        del nxgrp[nxkd.SAMPLE_Y]

    # these names (sample_x, sample_y) are hardcoded into the nxstxm definition
    _dataset(nxgrp, nxkd.SAMPLE_Y, ydata, "NX_FLOAT")
    _dataset(nxgrp, nxkd.SAMPLE_X, xdata, "NX_FLOAT")

    # this should be an array the same shape as the 'data' group in NXdata filled with the storagering current
    _sr_data = parent.get_baseline_all_data("DNM_BASELINE_RING_CURRENT")
    sr_data = np.linspace(_sr_data[0], _sr_data[1], ttlpnts)

    _dataset(
        nxgrp,
        "data",
        np.reshape(sr_data, (num_ev_points, ynpoints, xnpoints)),
        "NX_NUMBER",
    )

    modify_stack_ctrl_str_attrs(parent, nxgrp, doc)


def modify_stack_ctrl_str_attrs(parent, nxgrp, doc):
    """
    :param parent:
    :param nxgrp:
    :param doc:
    :return:
    """
    rois = parent.get_rois_from_current_md(doc["run_start"])
    x_posnr_nm = parent.fix_posner_nm(rois[SPDB_X][POSITIONER])
    y_posnr_nm = parent.fix_posner_nm(rois[SPDB_Y][POSITIONER])

    _string_attr(nxgrp, "axes", [y_posnr_nm, x_posnr_nm])


def modify_stack_nxdata_group(parent, data_nxgrp, doc, scan_type):
    """

    :param parent:
    :param data_nxgrp:
    :param doc:
    :param scan_type:
    :return:
    """
    resize_data = False

    rois = parent.get_rois_from_current_md(doc["run_start"])
    x_src = parent.get_devname(rois[SPDB_X][POSITIONER])
    x_posnr_nm = parent.fix_posner_nm(rois[SPDB_X][POSITIONER])
    # x_posnr_src = rois[SPDB_X]['SRC']
    y_src = parent.get_devname(rois[SPDB_Y][POSITIONER])
    y_posnr_nm = parent.fix_posner_nm(rois[SPDB_Y][POSITIONER])
    # y_posnr_src = rois[SPDB_Y]['SRC']

    xnpoints = int(rois[SPDB_X][NPOINTS])
    ynpoints = int(rois[SPDB_Y][NPOINTS])
    ttlpnts = xnpoints * ynpoints
    # prim_data_lst = parent._data['primary'][x_src]['data']
    # uid = list(parent._cur_scan_md.keys())[0]
    uid = parent.get_current_uid()
    # primary_det_nm = parent.get_primary_det_nm(uid)
    # # prim_data_lst = parent._data['primary'][primary_det_nm]['data']
    # prim_data_arr = np.array(parent._data["primary"][primary_det_nm][uid]["data"])

    det_nm = parent.get_nxgrp_det_name(data_nxgrp)
    det_stream = parent._det_strm_map[det_nm]
    prim_data_arr = np.array(parent._data[det_stream][det_nm][uid]["data"])


    if scan_types(scan_type) is scan_types.SAMPLE_POINT_SPECTRUM:
        rows = 1
        (cols,) = prim_data_arr.shape
    else:
        if prim_data_arr.ndim == 2:
            rows, cols = prim_data_arr.shape
        else:
            dud_evidx, rows, cols = prim_data_arr.shape

    if (rows * cols) < ttlpnts:
        # scn had been aborted
        resize_data = True
        # scan was aborted so use setpoint data here
        xdata = np.array(rois[SPDB_X][SETPOINTS], dtype=np.float32)
        ydata = np.array(rois[SPDB_Y][SETPOINTS], dtype=np.float32)
    else:
        if x_src not in parent._data["primary"].keys():
            xdata = np.array(rois[SPDB_X][SETPOINTS], dtype=np.float32)
            ydata = np.array(rois[SPDB_Y][SETPOINTS], dtype=np.float32)
        else:
            # use actual data
            # xdata is teh first xnpoints
            xdata = np.array(
                parent.get_primary_all_data(x_src)[0:xnpoints],
                dtype=np.float32,
            )
            # ydata is every ynpoint
            ydata = np.array(
                parent.get_primary_all_data(y_src)[0::ynpoints],
                dtype=np.float32,
            )

    # _dataset(data_nxgrp, y_posnr_nm, ydata, 'NX_FLOAT')
    # _dataset(data_nxgrp, x_posnr_nm, xdata, 'NX_FLOAT')

    # regardless of the positioner, these names (sample_x, sample_y) are hardcoded into the nxstxm definition
    # if there were already sample_x and y created by the default constructors then delete them and recreate with the right data
    if nxkd.SAMPLE_Y in data_nxgrp.keys():
        del data_nxgrp[nxkd.SAMPLE_X]
        del data_nxgrp[nxkd.SAMPLE_Y]

    _dataset(data_nxgrp, nxkd.SAMPLE_Y, ydata, "NX_FLOAT")
    _dataset(data_nxgrp, nxkd.SAMPLE_X, xdata, "NX_FLOAT")

    # _string_attr(data_nxgrp, 'axes', [y_posnr_nm, x_posnr_nm])
    _string_attr(data_nxgrp, "axes", ["energy", nxkd.SAMPLE_Y, nxkd.SAMPLE_X])
    _string_attr(data_nxgrp, "signal", "data")

    #det_nm = data_nxgrp.name.split("/")[-1]

    # need to find out how many energy points we need to make space for
    #det_data = np.array(parent.get_primary_all_data(det_nm), dtype=np.float32)

    # js_str = parent._cur_scan_md[doc['run_start']]['wdg_com']
    # wdg_com = json.loads(js_str)
    evs = parent._wdg_com["SINGLE_LST"]["EV_ROIS"]
    num_ev_points = len(evs)
    #rows, cols = det_data.shape
    # init_dat_arr = np.zeros((num_ev_points, rows, cols), dtype=np.float32)
    init_dat_arr = np.empty((num_ev_points, rows, cols), dtype=np.float32)
    init_dat_arr[:] = np.NAN

    #init_dat_arr[0] = det_data
    init_dat_arr[0] = prim_data_arr
    # _dataset(data_nxgrp, 'data', init_dat_arr, 'NX_NUMBER')
    _dset = _dataset(data_nxgrp, "data", init_dat_arr, "NX_NUMBER")
    _string_attr(_dset, "signal", "1")
