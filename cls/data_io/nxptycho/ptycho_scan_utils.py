"""
Created on Jan 4, 2019

@author: bergr
"""
import h5py

import numpy as np

from cls.data_io.nxptycho.stxm_types import scan_types, two_posner_scans
from cls.data_io.nxptycho.device_names import *

# from cls.data_io.nxstxm.utils import dct_get, dct_put
from cls.data_io.nxptycho.roi_dict_defs import *

# from cls.data_io.nxstxm.nxstxm_utils import (make_signal, _dataset, _string_attr, _group, make_1d_array, \
#                                           get_nx_standard_epu_mode, get_nx_standard_epu_harmonic_new, translate_pol_id_to_stokes_vector, \
#                                           readin_base_classes, make_NXclass, remove_unused_NXsensor_fields)

from cls.data_io.nxptycho.nxptycho_utils import _dataset, _string_attr, make_1d_array
import cls.data_io.nxptycho.nx_key_defs as nxkd


def modify_ptycho_ctrl_data_grps(parent, nxgrp, doc, scan_type):
    """
    :param parent:
    :param nxgrp:
    :param doc:
    :param scan_type:
    :return:
    """
    resize_data = False
    uid = parent.get_current_uid()
    rois = parent.get_rois_from_current_md(doc["run_start"])
    x_src = parent.get_devname(rois[SPDB_X][POSITIONER])
    x_posnr_nm = parent.fix_posner_nm(rois[SPDB_X][POSITIONER])
    y_src = parent.get_devname(rois[SPDB_Y][POSITIONER])
    y_posnr_nm = parent.fix_posner_nm(rois[SPDB_Y][POSITIONER])

    xnpoints = int(rois[SPDB_X]["NPOINTS"])
    ynpoints = int(rois[SPDB_Y]["NPOINTS"])
    evs = parent._wdg_com["SINGLE_LST"]["EV_ROIS"]
    num_ev_points = len(evs)

    ttlpnts = num_ev_points * xnpoints * ynpoints

    if x_src not in parent._data["primary"].keys():
        # resize_data = True
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

    # if there were already sample_x and y created by the default constructors then delete them and recreate with the right data
    if nxkd.SAMPLE_Y in nxgrp.keys():
        del nxgrp[nxkd.SAMPLE_X]
        del nxgrp[nxkd.SAMPLE_Y]

    # these names (sample_x, sample_y) are hardcoded into the nxstxm definition
    _dataset(nxgrp, nxkd.SAMPLE_Y, ydata, "NX_FLOAT")
    _dataset(nxgrp, nxkd.SAMPLE_X, xdata, "NX_FLOAT")

    _sr_data = parent.get_baseline_all_data("DNM_BASELINE_RING_CURRENT")
    sr_data = np.linspace(_sr_data[0], _sr_data[1], ttlpnts)

    _dataset(
        nxgrp,
        "data",
        np.reshape(sr_data, (num_ev_points, ynpoints, xnpoints)),
        "NX_NUMBER",
    )

    modify_ptycho_ctrl_str_attrs(parent, nxgrp, doc)


def modify_ptycho_ctrl_str_attrs(parent, nxgrp, doc):
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


def modify_ptycho_nxdata_group(parent, data_nxgrp, doc, scan_type):
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

    xnpoints = int(rois[SPDB_X]["NPOINTS"])
    ynpoints = int(rois[SPDB_Y]["NPOINTS"])

    # prim_data_lst = parent._data['primary'][x_src]['data']
    # uid = list(parent._cur_scan_md.keys())[0]
    uid = parent.get_current_uid()
    det_nm = parent.get_nxgrp_det_name(data_nxgrp)
    det_stream = parent._det_strm_map[det_nm]
    #prim_data_arr = np.array(parent._data[det_stream][det_nm][uid]["data"])

    if x_src not in parent._data["primary"].keys():
        # resize_data = True
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

    # regardless of the positioner, these names (sample_x, sample_y) are hardcoded into the nxstxm definition
    # if there were already sample_x and y created by the default constructors then delete them and recreate with the right data
    if nxkd.SAMPLE_Y in data_nxgrp.keys():
        del data_nxgrp[nxkd.SAMPLE_X]
        del data_nxgrp[nxkd.SAMPLE_Y]

    _dataset(data_nxgrp, y_posnr_nm, ydata, "NX_FLOAT")
    _dataset(data_nxgrp, x_posnr_nm, xdata, "NX_FLOAT")

    # _string_attr(data_nxgrp, "axes", ["energy", y_posnr_nm, x_posnr_nm])
    # _string_attr(data_nxgrp, "signal", "data")

    # _string_attr(data_nxgrp, 'axes', [y_posnr_nm, x_posnr_nm])
    _string_attr(data_nxgrp, "axes", ["energy", nxkd.SAMPLE_Y, nxkd.SAMPLE_X])
    _string_attr(data_nxgrp, "signal", "data")

    # det_nm = data_nxgrp.name.split("/")[-1]
    # det_nm = parent.get_primary_det_nm(doc['run_start'])
    # need to find out how many energy points we need to make space for
    # det_data = np.array(parent._data['primary'][det_nm][uid]['data'], dtype=np.float32)

    # js_str = parent._cur_scan_md[doc['run_start']]['wdg_com']
    # wdg_com = json.loads(js_str)
    evs = parent._wdg_com["SINGLE_LST"]["EV_ROIS"]
    num_ev_points = len(evs)
    # rows, cols = det_data.shape
    # init_dat_arr = np.zeros((num_ev_points, rows, cols), dtype=np.float32)
    # init_dat_arr = np.empty((num_ev_points, ynpoints, xnpoints), dtype=np.float32)
    # init_dat_arr[:] = np.NAN
    #all_data = np.array(parent._data[det_stream][det_nm][uid]["data"])

    if det_nm.find(parent._dflt_ptycho_cam) > -1:
        if parent._detdata_is_hdf5:
            #only create the external links of det data is hdf5 (not tiff)
            # this is the default ptycho camera data
            # externa,-addr is where the data is in the detector written files
            external_addr = "/entry/data/data"
            i = 0
            for dct in parent._img_idx_map_dct.items():
                data_nxgrp["data_%d" % i] = h5py.ExternalLink(
                    "%s" % (parent._det_fprfx % i), external_addr
                )
                # root['/entry/'].create_group(f"img{i}")
                # root[f'/entry/img{i}'].attrs['signal'] = 'data'
                # root[f'/entry/img{i}'].attrs['ext_filename'] = f"C230627003_{i:03d}.h5"
                # root[f'/entry/img{i}'].attrs['ext_src_path'] = "/entry/data/data"
                i += 1
    else:
        # all other detectors
        all_data = np.array(parent._data[det_stream][det_nm][uid]["data"])
        _dataset(data_nxgrp, "data", all_data, "NX_NUMBER")

    # init_dat_arr[0] = det_data
    # _dataset(data_nxgrp, 'data', init_dat_arr, 'NX_NUMBER')

    # # link in the signal data
    # local_addr = '/entry/data/counts'
    # external_addr = u"/entry/instrument/detector/counts"
    # f[local_addr] = h5py.ExternalLink(FILE_HDF5_COUNTS, external_addr)
    # nxdata.attrs[u"signal"] = u"counts"
    #
    # # link in the axes data
    # local_addr = u"/entry/data/two_theta"
    # f[local_addr] = h5py.ExternalLink(FILE_HDF5_ANGLES, u"/angles")
    # nxdata.attrs[u"axes"] = u"two_theta"
    # nxdata.attrs[u"two_theta_indices"] = [0, ]
    #
    # local_addr = u"/entry/instrument"
    # f[local_addr] = h5py.ExternalLink(FILE_HDF5_COUNTS, u"/entry/instrument")

    # external_addr = u"/entry/data/data"
    # data_nxgrp['data'] = h5py.ExternalLink(parent._det_fpath, external_addr)


def modify_ptycho_instrument_group(parent, inst_nxgrp, doc, scan_type):
    """

    :param nxgrp:
    :param doc:
    :param scan_type:
    :return:
    """
    rois = parent.get_rois_from_current_md(doc["run_start"])
    dwell = parent._cur_scan_md[doc["run_start"]]["dwell"] * 0.001
    # det_nm = parent.get_primary_det_nm(doc['run_start'])
    # scan_type = parent.get_stxm_scan_type(doc['run_start'])

    ttlpnts = int(rois[SPDB_X][NPOINTS] * rois[SPDB_Y][NPOINTS])
    uid = parent.get_current_uid()
    # det_data = np.array(parent._data['primary'][det_nm][uid]['data'])  # .reshape((ynpoints, xnpoints))
    # parent.make_detector(inst_nxgrp, parent._primary_det_prefix, det_data, dwell, ttl_pnts, units='counts')

    sample_x_data = make_1d_array(ttlpnts, parent.get_sample_x_data("start"))
    sample_y_data = make_1d_array(ttlpnts, parent.get_sample_y_data("start"))
    parent.make_detector(
        inst_nxgrp, nxkd.SAMPLE_X, sample_x_data, dwell, ttlpnts, units="um"
    )
    parent.make_detector(
        inst_nxgrp, nxkd.SAMPLE_Y, sample_y_data, dwell, ttlpnts, units="um"
    )

    xnpoints = int(rois[SPDB_X][NPOINTS])
    ynpoints = int(rois[SPDB_Y][NPOINTS])

    x_src = parent.get_devname(rois[SPDB_X][POSITIONER])
    x_posnr_nm = parent.fix_posner_nm(rois[SPDB_X][POSITIONER])
    y_src = parent.get_devname(rois[SPDB_Y][POSITIONER])
    y_posnr_nm = parent.fix_posner_nm(rois[SPDB_Y][POSITIONER])

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
