"""
Created on Jan 4, 2019

@author: bergr
"""
import numpy as np

from cls.data_io.nxstxm.stxm_types import scan_types
from cls.data_io.nxstxm.device_names import *
from cls.data_io.nxstxm.utils import dct_get
from cls.data_io.nxstxm.roi_dict_defs import *

# from cls.data_io.nxstxm.nxstxm_utils import (make_signal, _dataset, _string_attr, _group, make_1d_array, \
#                                           get_nx_standard_epu_mode, get_nx_standard_epu_harmonic_new, translate_pol_id_to_stokes_vector, \
#                                           readin_base_classes, make_NXclass, remove_unused_NXsensor_fields)

from cls.data_io.nxstxm.nxstxm_utils import _dataset, _string_attr, make_1d_array
import cls.data_io.nxstxm.nx_key_defs as nxkd

MARK_DATA = False


#     parent.modify_focus_ctrl_str_attrs(cntrl_nxgrp, doc)
#     parent.modify_focus_ctrl_data_grps(cntrl_nxgrp, doc)


def modify_focus_ctrl_data_grps(parent, nxgrp, doc, scan_type):
    """

    :param nxgrp:
    :param doc:
    :return:
    """
    resize_data = False
    rois = parent.get_rois_from_current_md(doc["run_start"])
    x_src = parent.get_devname(dct_get(rois, SPDB_XPOSITIONER))
    x_posnr_nm = parent.fix_posner_nm(dct_get(rois, SPDB_XPOSITIONER))
    # x_posnr_src = rois['X']['SRC']
    y_src = parent.get_devname(dct_get(rois, SPDB_YPOSITIONER))
    y_posnr_nm = parent.fix_posner_nm(dct_get(rois, SPDB_YPOSITIONER))
    # y_posnr_src = rois['Y']['SRC']
    uid = parent.get_current_uid()
    zz_src = parent.get_devname(dct_get(rois, SPDB_ZZPOSITIONER))
    zz_posnr_nm = parent.fix_posner_nm(dct_get(rois, SPDB_ZZPOSITIONER))

    xnpoints = int(dct_get(rois, SPDB_XNPOINTS))
    ynpoints = int(dct_get(rois, SPDB_YNPOINTS))
    znpoints = dct_get(rois, SPDB_ZZNPOINTS)
    ttlpnts = xnpoints * znpoints
    if x_src not in parent._data["primary"].keys():
        # use the canned setpoints
        xdata = np.array(dct_get(rois, SPDB_XSETPOINTS), dtype=np.float32)
        ydata = np.array(dct_get(rois, SPDB_YSETPOINTS), dtype=np.float32)
        zzdata = np.array(dct_get(rois, SPDB_ZZSETPOINTS), dtype=np.float32)
    else:
        prim_data_lst = parent.get_primary_all_data(x_src)
        if len(prim_data_lst) < ttlpnts:
            resize_data = True
            # scan was aborted so use setpoint data here
            xdata = np.array(dct_get(rois, SPDB_XSETPOINTS), dtype=np.float32)
            ydata = np.array(dct_get(rois, SPDB_YSETPOINTS), dtype=np.float32)
            zzdata = np.array(dct_get(rois, SPDB_ZZSETPOINTS), dtype=np.float32)
        else:
            # use actual data
            # xdata is teh first xnpoints
            xdata = np.array(
                parent.get_primary_all_data(x_src)[0:xnpoints],
                dtype=np.float32,
            )
            # ydata is every ynpoint
            ydata = np.array(
                parent.get_primary_all_data(y_src)[0::znpoints],
                dtype=np.float32,
            )
            zzdata = np.array(
                parent._data["primary"][zz_src][uid]["data"][0::ynpoints],
                dtype=np.float32,
            )

    line_position = list(range(0, xnpoints))

    _dataset(nxgrp, "line_position", line_position, "NX_FLOAT")

    _dataset(nxgrp, y_posnr_nm, ydata, "NX_FLOAT")
    _dataset(nxgrp, x_posnr_nm, xdata, "NX_FLOAT")
    _dataset(nxgrp, zz_posnr_nm, zzdata, "NX_FLOAT")

    # this should be an array the same shape as the 'data' group in NXdata filled with the storagering current
    # ring_cur_signame = parent.get_devname("DNM_RING_CURRENT")
    # if ring_cur_signame not in parent._data.keys():
    #     # use the baseline start/stop values and create a sequence from start to stop
    #     strt, stp = parent._data["baseline"][ring_cur_signame][uid]["data"]
    #     sr_data = np.linspace(strt, stp, ttlpnts, endpoint=True)
    # else:
    #     sr_data = np.array(
    #         parent._data["baseline"][ring_cur_signame][uid]["data"], dtype=np.float32
    #     )
    #     if resize_data:
    #         sr_data = np.resize(sr_data, (ttlpnts,))
    #
    # _dataset(nxgrp, "data", np.reshape(sr_data, (znpoints, xnpoints)), "NX_NUMBER")

    _sr_data = parent.get_baseline_all_data("DNM_BASELINE_RING_CURRENT")
    sr_data = np.linspace(_sr_data[0], _sr_data[1], ttlpnts)
    _dataset(nxgrp, "data", np.reshape(sr_data, (znpoints, xnpoints)), "NX_NUMBER")
    _string_attr(nxgrp, "axes", [zz_posnr_nm, "line_position"])


def modify_focus_nxdata_group(parent, data_nxgrp, doc, scan_type):
    """

    :param entry_nxgrp:
    :param cntr_nm:
    :param doc:
    :param scan_type:
    :return:
    """
    resize_data = False

    rois = parent.get_rois_from_current_md(doc["run_start"])
    x_src = parent.get_devname(dct_get(rois, SPDB_XPOSITIONER))
    x_posnr_nm = parent.fix_posner_nm(dct_get(rois, SPDB_XPOSITIONER))
    y_src = parent.get_devname(dct_get(rois, SPDB_YPOSITIONER))
    y_posnr_nm = parent.fix_posner_nm(dct_get(rois, SPDB_YPOSITIONER))
    zz_src = parent.get_devname(dct_get(rois, SPDB_ZZPOSITIONER))
    zz_posnr_nm = parent.fix_posner_nm(dct_get(rois, SPDB_ZZPOSITIONER))
    uid = parent.get_current_uid()
    det_nm = parent.get_nxgrp_det_name(data_nxgrp)
    det_stream = parent._det_strm_map[det_nm]
    #prim_data_arr = np.array(parent._data[det_stream][det_nm][uid]["data"])
    #prim_data_arr = parent.get_primary_all_data(det_nm)

    xnpoints = int(dct_get(rois, SPDB_XNPOINTS))
    ynpoints = int(dct_get(rois, SPDB_YNPOINTS))
    zznpoints = dct_get(rois, SPDB_ZZNPOINTS)
    ttlpnts = xnpoints * zznpoints

    if x_src not in parent._data["primary"].keys():
        # use the canned setpoints
        xdata = np.array(dct_get(rois, SPDB_XSETPOINTS), dtype=np.float32)
        ydata = np.array(dct_get(rois, SPDB_YSETPOINTS), dtype=np.float32)
        zzdata = np.array(dct_get(rois, SPDB_ZZSETPOINTS), dtype=np.float32)
    else:
        prim_data_lst = parent.get_primary_all_data(x_src)
        if len(prim_data_lst) < ttlpnts:
            resize_data = True
            # scan was aborted so use setpoint data here
            xdata = np.array(dct_get(rois, SPDB_XSETPOINTS), dtype=np.float32)
            ydata = np.array(dct_get(rois, SPDB_YSETPOINTS), dtype=np.float32)
            zzdata = np.array(dct_get(rois, SPDB_ZZSETPOINTS), dtype=np.float32)
        else:
            # use actual data
            # xdata is teh first xnpoints
            xdata = np.array(
                parent.get_primary_all_data(x_src)[0:xnpoints],
                dtype=np.float32,
            )
            # ydata is every ynpoint
            ydata = np.array(
                parent.get_primary_all_data(y_src)[0::zznpoints],
                dtype=np.float32,
            )
            zzdata = np.array(
                parent._data["primary"][zz_src][uid]["data"][0::ynpoints],
                dtype=np.float32,
            )

    line_position = list(range(0, xnpoints))

    _dataset(data_nxgrp, "line_position", line_position, "NX_FLOAT")

    _dataset(data_nxgrp, y_posnr_nm, ydata, "NX_FLOAT")
    _dataset(data_nxgrp, x_posnr_nm, xdata, "NX_FLOAT")
    _dataset(data_nxgrp, zz_posnr_nm, zzdata, "NX_FLOAT")

    _string_attr(data_nxgrp, "axes", [zz_posnr_nm, "line_position"])
    _string_attr(data_nxgrp, "signal", "data")

    three_d_scans = [scan_types.OSA_FOCUS, scan_types.SAMPLE_FOCUS]

    #check first dimension of list is line length, check if detector returned enough, if it didnt then interpolate
    prim_arr = np.array(parent.get_primary_all_data(det_nm), dtype=np.float32)
    #prim_arr = np.array(prim_data_arr)
    if prim_arr.ndim  == 1:
        resize_data = True

    elif prim_arr.ndim  == 2:
        rows, cols = prim_arr.shape
        if cols < xnpoints:
            resize_data = True

    if scan_types(scan_type) in three_d_scans:
        det_data = prim_arr
        if resize_data:
            #    det_data = parent.fix_aborted_data(det_data, ttlpnts)
            det_data = np.reshape(det_data, (zznpoints, xnpoints))

    else:
        #RUSS Apr 12 2023 det_data = np.array(parent.get_primary_all_data(det_nm), dtype=np.float32)
        det_data = prim_arr

    _dset = _dataset(data_nxgrp, "data", det_data, "NX_NUMBER")
    _string_attr(_dset, "signal", "1")


def modify_focus_instrument_group(parent, inst_nxgrp, doc, scan_type):
    """

    :param nxgrp:
    :param doc:
    :param scan_type:
    :return:
    """
    rois = parent.get_rois_from_current_md(doc["run_start"])
    dwell = parent._cur_scan_md[doc["run_start"]]["dwell"] * 0.001
    # det_nm = inst_nxgrp.name.split('/')[-1]
    scan_type = parent.get_stxm_scan_type(doc["run_start"])

    xnpoints = int(dct_get(rois, SPDB_XNPOINTS))
    ynpoints = int(dct_get(rois, SPDB_YNPOINTS))
    zznpoints = dct_get(rois, SPDB_ZZNPOINTS)
    ttlpnts = xnpoints * zznpoints
    uid = parent.get_current_uid()

    # det_data = np.array(parent._data['primary'][det_nm][uid]['data'])  # .reshape((ynpoints, xnpoints))
    # parent.make_detector(inst_nxgrp, det_nm, det_data, dwell, ttlpnts, units='counts')

    sample_x_data = make_1d_array(ttlpnts, parent.get_sample_x_data("start"))
    sample_y_data = make_1d_array(ttlpnts, parent.get_sample_y_data("start"))
    parent.make_detector(
        inst_nxgrp, nxkd.SAMPLE_X, sample_x_data, dwell, ttlpnts, units="um"
    )
    parent.make_detector(
        inst_nxgrp, nxkd.SAMPLE_Y, sample_y_data, dwell, ttlpnts, units="um"
    )

    x_src = parent.get_devname(dct_get(rois, SPDB_XPOSITIONER))
    x_posnr_nm = parent.fix_posner_nm(dct_get(rois, SPDB_XPOSITIONER))
    y_src = parent.get_devname(dct_get(rois, SPDB_YPOSITIONER))
    y_posnr_nm = parent.fix_posner_nm(dct_get(rois, SPDB_YPOSITIONER))
    zz_src = parent.get_devname(dct_get(rois, SPDB_ZZPOSITIONER))
    zz_posnr_nm = parent.fix_posner_nm(dct_get(rois, SPDB_ZZPOSITIONER))

    # xdata is teh first xnpoints

    if x_src not in parent._data["primary"].keys():
        # use the canned setpoints
        xdata = np.array(dct_get(rois, SPDB_XSETPOINTS), dtype=np.float32)
        ydata = np.array(dct_get(rois, SPDB_YSETPOINTS), dtype=np.float32)
        zzdata = np.array(dct_get(rois, SPDB_ZZSETPOINTS), dtype=np.float32)
    else:

        xdata = parent.get_primary_all_data(x_src)[0:xnpoints]
        # ydata is every ynpoint
        ydata = parent.get_primary_all_data(y_src)[0::zznpoints]
        zzdata = parent._data["primary"][zz_src][uid]["data"][0::zznpoints]

    parent.make_detector(
        inst_nxgrp, y_posnr_nm, np.tile(ydata, zznpoints), dwell, ttlpnts, units="um"
    )
    parent.make_detector(
        inst_nxgrp, x_posnr_nm, np.tile(xdata, zznpoints), dwell, ttlpnts, units="um"
    )
    parent.make_detector(
        inst_nxgrp, zz_posnr_nm, np.tile(zzdata, zznpoints), dwell, ttlpnts, units="um"
    )
