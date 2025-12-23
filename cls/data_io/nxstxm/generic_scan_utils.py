"""
Created on Jan 4, 2019

@author: bergr
"""
import numpy as np

from cls.data_io.nxstxm.device_names import *
from cls.data_io.nxstxm.roi_dict_defs import *

# from cls.data_io.nxstxm.nxstxm_utils import (make_signal, _dataset, _string_attr, _group, make_1d_array, \
#                                           get_nx_standard_epu_mode, get_nx_standard_epu_harmonic_new, translate_pol_id_to_stokes_vector, \
#                                           readin_base_classes, make_NXclass, remove_unused_NXsensor_fields)
from cls.data_io.nxstxm.nxstxm_utils import _dataset, _string_attr, make_1d_array
import cls.data_io.nxstxm.nx_key_defs as nxkd


def modify_generic_scan_ctrl_data_grps(parent, nxgrp, doc, scan_type):
    """

    :param nxgrp:
    :param doc:
    :return:
    """
    resize_data = False
    rois = parent.get_rois_from_current_md(doc["run_start"])
    x_src = parent.get_devname(rois[SPDB_X][POSITIONER])
    x_posnr_nm = parent.fix_posner_nm(rois[SPDB_X][POSITIONER]).upper()

    xnpoints = int(rois[SPDB_X][NPOINTS])
    ttlpnts = xnpoints
    uid = parent.get_current_uid()
    prim_data_lst = parent.get_primary_all_data(x_posnr_nm)
    if len(prim_data_lst) < ttlpnts:
        resize_data = True
        # scan was aborted so use setpoint data here
        xdata = np.array(rois[SPDB_X]["SETPOINTS"], dtype=np.float32)
    else:
        # use actual data
        # xdata is teh first xnpoints
        xdata = np.array(
            parent.get_primary_all_data(x_posnr_nm)[0:xnpoints], dtype=np.float32
        )

    _dataset(nxgrp, x_posnr_nm, xdata, "NX_FLOAT")

    modify_generic_scan_ctrl_str_attrs(parent, nxgrp, doc)


def modify_generic_scan_ctrl_str_attrs(parent, nxgrp, doc):
    """

    :param nxgrp:
    :param doc:
    :return:
    """
    rois = parent.get_rois_from_current_md(doc["run_start"])
    x_posnr_nm = parent.fix_posner_nm(rois[SPDB_X][POSITIONER])

    _string_attr(nxgrp, "axes", [x_posnr_nm])


def modify_generic_scan_nxdata_group(parent, data_nxgrp, doc, scan_type):
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
    x_posnr_nm = parent.fix_posner_nm(rois[SPDB_X][POSITIONER]).upper()

    xnpoints = int(rois[SPDB_X][NPOINTS])
    ttlpnts = xnpoints
    det_nm = parent.get_nxgrp_det_name(data_nxgrp)
    prim_data_lst = parent.get_primary_all_data(x_posnr_nm)
    if len(prim_data_lst) < ttlpnts:
        resize_data = True
        # scan was aborted so use setpoint data here
        xdata = np.array(rois[SPDB_X][SETPOINTS], dtype=np.float32)

    else:
        # use actual data
        # xdata is teh first xnpoints
        xdata = np.array(
            parent.get_primary_all_data(x_posnr_nm)[0:xnpoints], dtype=np.float32
        )

    _dataset(data_nxgrp, x_posnr_nm, xdata, "NX_FLOAT")

    _string_attr(data_nxgrp, "axes", [x_posnr_nm])
    _string_attr(data_nxgrp, "signal", "data")

    det_data = np.array(parent.get_primary_all_data(det_nm), dtype=np.float32)
    if det_data.ndim == 2:
        det_data = det_data.flatten()

    _dset = _dataset(data_nxgrp, "data", det_data, "NX_NUMBER")
    _string_attr(_dset, "signal", "1")


def modify_generic_scan_instrument_group(parent, inst_nxgrp, doc, scan_type):
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
    uid = parent.get_current_uid()
    ttlpnts = int(rois[SPDB_X][NPOINTS])

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

    xnpoints = int(rois[SPDB_X][NPOINTS])

    x_src = parent.get_devname(rois[SPDB_X][POSITIONER])
    x_posnr_nm = parent.fix_posner_nm(rois[SPDB_X][POSITIONER]).upper()

    # xdata is teh first xnpoints
    xdata = parent.get_primary_all_data(x_posnr_nm)[0:xnpoints]
    # parent.make_detector(inst_nxgrp, x_posnr_nm, np.tile(xdata, xnpoints), dwell, ttlpnts, units='um')
    parent.make_detector(inst_nxgrp, x_posnr_nm, xdata, dwell, ttlpnts, units="um")
