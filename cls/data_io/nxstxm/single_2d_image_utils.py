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
from cls.data_io.nxstxm.nxstxm_utils import _dataset, _string_attr, make_1d_array

import cls.data_io.nxstxm.nx_key_defs as nxkd


MARK_DATA = False


#     parent.modify_2posner_ctrl_str_attrs(cntrl_nxgrp, doc)
#     parent.modify_2posner_ctrl_data_grps(cntrl_nxgrp, doc)


def modify_2posner_ctrl_data_grps(parent, nxgrp, doc, scan_type):
    """

    :param nxgrp:
    :param doc:
    :return:
    """
    #resize_data = False
    rois = parent.get_rois_from_current_md(doc["run_start"])
    x_src = parent.get_devname(rois[SPDB_X][POSITIONER])
    x_posnr_nm = parent.fix_posner_nm(rois[SPDB_X][POSITIONER])
    # x_posnr_src = rois[SPDB_X]['SRC']
    y_src = parent.get_devname(rois[SPDB_Y][POSITIONER])
    y_posnr_nm = parent.fix_posner_nm(rois[SPDB_Y][POSITIONER])
    # y_posnr_src = rois[SPDB_Y]['SRC']
    uid = parent.get_current_uid()

    xnpoints = int(rois[SPDB_X][NPOINTS])
    ynpoints = int(rois[SPDB_Y][NPOINTS])
    ttlpnts = xnpoints * ynpoints
    #prim_data_lst = parent.get_primary_all_data(x_src)
    #if len(prim_data_lst) < ttlpnts:
    if x_src not in parent._data["primary"].keys():
        #resize_data = True
        # scan was aborted so use setpoint data here
        xdata = np.array(rois[SPDB_X][SETPOINTS], dtype=np.float32)
        ydata = np.array(rois[SPDB_Y][SETPOINTS], dtype=np.float32)
    else:
        # use actual data
        # xdata is teh first xnpoints
        xdata = np.array(
            parent.get_primary_all_data(x_src)[0:xnpoints], dtype=np.float32
        )
        # ydata is every ynpoint
        ydata = np.array(
            parent.get_primary_all_data(y_src)[0::ynpoints], dtype=np.float32
        )

    _dataset(nxgrp, y_posnr_nm, ydata, "NX_FLOAT")
    _dataset(nxgrp, x_posnr_nm, xdata, "NX_FLOAT")

    # this should be an array the same shape as the 'data' group in NXdata filled with the storagering current
    sr_data = None
    ring_cur_signame = parent._cur_scan_md[parent._cur_uid]['ring_current_nm']
    if ring_cur_signame in parent._data["baseline"].keys():
        rois = parent.get_rois_from_current_md(doc["run_start"])
        # use the baseline start/stop values and create a sequence from start to stop
        # strt, stp = self._data['baseline'][ring_cur_signame][uid]['data']
        strt, stp = parent.get_baseline_all_data(ring_cur_signame)
        sr_data = np.linspace(strt, stp, rois["X"][NPOINTS], dtype=np.float32)
    else:
        sr_data = np.array(
            parent._data["primary"][ring_cur_signame]["data"], dtype=np.float32
        )
    #if resize_data:
    #    sr_data = np.resize(sr_data, (ttlpnts,))
    if sr_data is not None:
        sr_data = np.resize(sr_data, (ttlpnts,))
        _dataset(nxgrp, "data", np.reshape(sr_data, (ynpoints, xnpoints)), "NX_NUMBER")

    modify_2posner_ctrl_str_attrs(parent, nxgrp, doc)


def modify_2posner_ctrl_str_attrs(parent, nxgrp, doc):
    """

    :param nxgrp:
    :param doc:
    :return:
    """
    rois = parent.get_rois_from_current_md(doc["run_start"])
    x_posnr_nm = parent.fix_posner_nm(rois[SPDB_X][POSITIONER])
    y_posnr_nm = parent.fix_posner_nm(rois[SPDB_Y][POSITIONER])

    _string_attr(nxgrp, "axes", [y_posnr_nm, x_posnr_nm])


def modify_base_2d_nxdata_group(parent, data_nxgrp, doc, scan_type):
    """

    :param entry_nxgrp:
    :param cntr_nm:
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
    uid = parent.get_current_uid()
    xnpoints = int(rois[SPDB_X][NPOINTS])
    ynpoints = int(rois[SPDB_Y][NPOINTS])
    ttlpnts = xnpoints * ynpoints
    # prim_data_lst = parent.get_primary_all_data(x_src)

    #if len(prim_data_lst) < ttlpnts:
    if x_src not in parent._data["primary"].keys():
        #resize_data = True
        # scan was aborted so use setpoint data here
        xdata = np.array(rois[SPDB_X][SETPOINTS], dtype=np.float32)
        ydata = np.array(rois[SPDB_Y][SETPOINTS], dtype=np.float32)
    else:
        # use actual data
        # xdata is teh first xnpoints
        xdata = np.array(
            parent.get_primary_all_data(x_src)[0:xnpoints], dtype=np.float32
        )
        # ydata is every ynpoint
        ydata = np.array(
            parent.get_primary_all_data(y_src)[0::ynpoints], dtype=np.float32
        )

    _dataset(data_nxgrp, y_posnr_nm, ydata, "NX_FLOAT")
    _dataset(data_nxgrp, x_posnr_nm, xdata, "NX_FLOAT")

    _string_attr(data_nxgrp, "axes", [y_posnr_nm, x_posnr_nm])
    _string_attr(data_nxgrp, "signal", "data")

    # det_nm = parent.get_primary_det_nm(doc['run_start'])
    det_nm = parent.get_nxgrp_det_name(data_nxgrp)

    three_d_scans = [
        scan_types.DETECTOR_IMAGE,
        scan_types.OSA_IMAGE,
        scan_types.OSA_FOCUS,
        scan_types.SAMPLE_FOCUS,
        scan_types.SAMPLE_IMAGE_STACK,
        scan_types.COARSE_IMAGE,
        scan_types.COARSE_GONI,
        scan_types.TOMOGRAPHY,
    ]
    if scan_types(scan_type) in three_d_scans:
        # det_data = np.array(parent._data['primary'][det_nm]['data'], dtype=np.float32).reshape((1, ynpoints, xnpoints))
        # if det_nm not in parent._data["primary"].keys():
        #     # must be a flyer scan, only one detector in primary stream
        #     det_data = np.array(
        #         parent._data["baseline"][det_nm][uid]["data"][0], dtype=np.float32
        #     )
        # else:
        #     # det name is in primary data stream
        #     resize_data = False
        #     det_data = np.array(
        #         parent.get_primary_all_data(det_nm), dtype=np.float32
        #     )
        resize_data = False
        det_data = np.array(parent.get_primary_all_data(det_nm), dtype=np.float32)

        # if resize_data:
        #     det_data = parent.fix_aborted_data(det_data, ttlpnts)
        det_data = parent.fix_aborted_data(det_data, ttlpnts)

        #for a line by line scan the data here (if say RING_CURRENT) we will only have 1 value per row, so we need to duplicate the single value for the entire row
        cols = 0
        if det_data.ndim == 1:
            rws, = det_data.shape
        else:
            rws,cols = det_data.shape

        if rws == ynpoints and cols != xnpoints:
            #need to concatenate
            det_data = np.concatenate((det_data, np.tile(det_data, xnpoints-1)))
            det_data = np.reshape(det_data, (ynpoints, xnpoints))
        else:
            det_data = np.reshape(det_data, (1, ynpoints, xnpoints))

        if MARK_DATA:
            # put a black box in corner
            c = int(xnpoints / 3)
            r = int(xnpoints / 3)
            for n in range(r):
                det_data[0, n, 0:c] = 0

    else:
        # det_data = np.array(parent._data['primary'][det_nm]['data'], dtype=np.float32).reshape((ynpoints, xnpoints))
        if det_nm not in parent._data["primary"].keys():
            det_data = np.array(
                parent._data["baseline"][det_nm][uid]["data"][0], dtype=np.float32
            )
        else:
            det_data = np.array(
                parent.get_primary_all_data(det_nm), dtype=np.float32
            )

    _dset = _dataset(data_nxgrp, "data", det_data, "NX_NUMBER")
    _string_attr(_dset, "signal", "1")


def modify_base_2d_instrument_group(parent, inst_nxgrp, doc, scan_type):
    """

    :param nxgrp:
    :param doc:
    :param scan_type:
    :return:
    """
    rois = parent.get_rois_from_current_md(doc["run_start"])
    dwell = parent._cur_scan_md[doc["run_start"]]["dwell"] * 0.001
    # det_nm = parent.get_primary_det_nm(doc['run_start'])
    scan_type = parent.get_stxm_scan_type(doc["run_start"])
    uid = parent.get_current_uid()
    ttlpnts = int(rois[SPDB_X][NPOINTS] * rois[SPDB_Y][NPOINTS])

    # det_data = np.array(parent._data['primary'][det_nm][uid]['data'])  # .reshape((ynpoints, xnpoints))
    # parent.make_detector(inst_nxgrp, parent._detector_names, det_data, dwell, ttlpnts, units='counts')

    sample_x_data = make_1d_array(ttlpnts, parent.get_sample_x_data("start"))
    sample_y_data = make_1d_array(ttlpnts, parent.get_sample_y_data("start"))
    parent.make_detector(
        inst_nxgrp, nxkd.SAMPLE_X, sample_x_data, dwell, ttlpnts, units="um"
    )
    parent.make_detector(
        inst_nxgrp, nxkd.SAMPLE_Y, sample_y_data, dwell, ttlpnts, units="um"
    )

    if scan_type in two_posner_scans:
        xnpoints = int(rois[SPDB_X][NPOINTS])
        ynpoints = int(rois[SPDB_Y][NPOINTS])
        ttlpnts = int(rois[SPDB_X][NPOINTS] * rois[SPDB_Y][NPOINTS])

        x_src = parent.get_devname(rois[SPDB_X][POSITIONER])
        x_posnr_nm = parent.fix_posner_nm(rois[SPDB_X][POSITIONER])
        y_src = parent.get_devname(rois[SPDB_Y][POSITIONER])
        y_posnr_nm = parent.fix_posner_nm(rois[SPDB_Y][POSITIONER])

        # xdata is the first xnpoints

        #check to see if this is a flyer?
        if x_src not in parent._data["primary"].keys():
            # look slike it so only det in primary is flyer det so use setpoints
            xdata = np.array(rois[SPDB_X][SETPOINTS], dtype=np.float32)
            ydata = np.array(rois[SPDB_Y][SETPOINTS], dtype=np.float32)
        else:
            xdata = parent.get_primary_all_data(x_src)[0:xnpoints]
            # ydata is every ynpoint
            ydata = parent.get_primary_all_data(y_src)[0::ynpoints]

        parent.make_detector(
            inst_nxgrp, y_posnr_nm, np.tile(ydata, ynpoints), dwell, ttlpnts, units="um"
        )
        parent.make_detector(
            inst_nxgrp, x_posnr_nm, np.tile(xdata, xnpoints), dwell, ttlpnts, units="um"
        )
