"""
Created on Jan 4, 2019

@author: bergr
"""

import numpy as np

from cls.data_io.nxstxm.stxm_types import two_posner_scans
from cls.data_io.nxstxm.device_names import *
from cls.data_io.nxstxm.roi_dict_defs import *
from cls.data_io.nxstxm.nxstxm_utils import _dataset, _string_attr, make_1d_array
from cls.data_io.nxstxm.utils import dct_get

import cls.data_io.nxstxm.nx_key_defs as nxkd


def modify_spectra_ctrl_data_grps(parent, nxgrp, doc, scan_type):
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

    modify_spectra_ctrl_str_attrs(parent, nxgrp, doc)


def modify_spectra_ctrl_str_attrs(parent, nxgrp, doc):
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


def modify_spectra_nxdata_group(parent, data_nxgrp, doc, scan_type):
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
    y_src = parent.get_devname(rois[SPDB_Y][POSITIONER])
    y_posnr_nm = parent.fix_posner_nm(rois[SPDB_Y][POSITIONER])
    evs = dct_get(parent._wdg_com, SPDB_SINGLE_LST_EV_ROIS)
    num_ev_points = len(evs)

    xnpoints = int(rois[SPDB_X][NPOINTS])
    ynpoints = int(rois[SPDB_Y][NPOINTS])
    ttlpnts = xnpoints * num_ev_points
    uid = parent.get_current_uid()
    # primary_det_nm = parent.get_primary_det_nm(uid)
    det_nm = parent.get_nxgrp_det_name(data_nxgrp)
    det_data = np.array(parent.get_primary_all_data(det_nm), dtype=np.float32)
    if det_nm.find("RING_CURRENT") > -1:
        #hack
        det_data = det_data[0 :: len(parent._sp_id_lst)]
    else:
        det_data = det_data.flatten()
    rows = 1
    (cols,) = det_data.shape

    if (rows * cols) < ttlpnts:
        # scn had been aborted
        resize_data = True
        # scan was aborted so use setpoint data here
        xdata = np.array(xnpoints, dtype=np.float32)
        ydata = np.array(rois[SPDB_Y][SETPOINTS], dtype=np.float32)
    else:
        if x_src not in parent._data["primary"].keys():
            xdata = make_1d_array(ttlpnts, rois[SPDB_X][SETPOINTS])
            ydata = make_1d_array(ttlpnts, rois[SPDB_Y][SETPOINTS])
        else:
            # use actual data
            # xdata is teh first xnpoints
            # xdata = np.array(parent._data['primary'][x_src][uid]['data'][0:xnpoints], dtype=np.float32)
            xdata = make_1d_array(ttlpnts, parent.get_sample_x_data("start"))
            # ydata is every ynpoint
            # ydata = np.array(parent._data['primary'][y_src][uid]['data'][0::ynpoints], dtype=np.float32)
            ydata = make_1d_array(ttlpnts, parent.get_sample_y_data("start"))

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
    # _dataset(data_nxgrp, 'data', prim_data_arr, 'NX_NUMBER')
    _dset = _dataset(data_nxgrp, "data", det_data, "NX_NUMBER")
    _string_attr(_dset, "signal", "1")

    # det_nm = parent.get_primary_det_nm(doc['run_start'])
    #
    # #need to find out how many energy points we need to make space for
    # det_data = np.array(parent._data['primary'][det_nm][uid]['data'], dtype=np.float32)
    #
    # #js_str = parent._cur_scan_md[doc['run_start']]['wdg_com']
    # #wdg_com = json.loads(js_str)
    # evs = parent._wdg_com['SINGLE_LST']['EV_ROIS']
    # num_ev_points = len(evs)
    # #rows, cols = det_data.shape
    # #init_dat_arr = np.zeros((num_ev_points, rows, cols), dtype=np.float32)
    # init_dat_arr = np.empty((num_ev_points, rows, cols), dtype=np.float32)
    # init_dat_arr[:] = np.NAN
    #
    # init_dat_arr[0] = det_data
    # _dataset(data_nxgrp, 'data', data, 'NX_NUMBER')


def modify_spectra_instrument_group(parent, inst_nxgrp, doc, scan_type):
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
    xnpoints = int(rois[SPDB_X][NPOINTS])
    ynpoints = int(rois[SPDB_Y][NPOINTS])
    evs = dct_get(parent._wdg_com, SPDB_SINGLE_LST_EV_ROIS)
    num_ev_points = len(evs)
    ttlpnts = xnpoints * num_ev_points

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

    # if (scan_type in two_posner_scans):
    # xnpoints = int(rois[SPDB_X][NPOINTS])
    # ynpoints = int(rois[SPDB_Y][NPOINTS])
    # ttlpnts = xnpoints * ynpoints

    x_src = parent.get_devname(rois[SPDB_X][POSITIONER])
    x_posnr_nm = parent.fix_posner_nm(rois[SPDB_X][POSITIONER])
    y_src = parent.get_devname(rois[SPDB_Y][POSITIONER])
    y_posnr_nm = parent.fix_posner_nm(rois[SPDB_Y][POSITIONER])

    # xdata is teh first xnpoints
    if x_src not in parent._data["primary"].keys():
        xdata = np.array(rois[SPDB_X][SETPOINTS], dtype=np.float32)
        ydata = np.array(rois[SPDB_Y][SETPOINTS], dtype=np.float32)
    else:
        xdata = parent._data["primary"][x_src]["data"][0:xnpoints]
        # ydata is every ynpoint
        ydata = parent._data["primary"][y_src]["data"][0::ynpoints]

    parent.make_detector(
        inst_nxgrp, y_posnr_nm, np.tile(ydata, ynpoints), dwell, ttlpnts, units="um"
    )
    parent.make_detector(
        inst_nxgrp, x_posnr_nm, np.tile(xdata, xnpoints), dwell, ttlpnts, units="um"
    )
