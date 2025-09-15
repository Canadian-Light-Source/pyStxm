import simplejson as json
import numpy as np
import math

from bcm.devices.epu import convert_wrapper_epu_to_str

from cls.utils.arrays import convert_numpy_to_python
from cls.utils.dict_utils import dct_get
from cls.utils.roi_dict_defs import *
from cls.types.stxmTypes import scan_types, scan_sub_types, image_type_scans, spectra_type_scans

from cls.applications.pyStxm.widgets.dict_based_contact_sheet.utils import get_first_sp_db_from_entry, format_info_text, extract_date_time_from_nx_time


def dict_based_build_image_params(h5_file_dct, energy=None, ev_idx=0, ev_pnt=0, pol_idx=0, stack_idx=None):
    """
    Generate an HTML tooltip string from sp_db_dict data

    :param h5_file_dct: Dictionary containing scan data
    :param energy: Energy value (if None, extracted from data_dct)
    :param pol_idx: Polarization index
    :param ev_idx: Energy vector index
    :param ev_pnt: Energy point index
    :param stack_idx: Stack index (if None, the tooltip will not include stack information

    :return: HTML formatted tooltip string

    """

    sp_db = None
    # Check if it's an entry_dct and extract sp_db
    if 'default' in h5_file_dct and h5_file_dct['default'] in h5_file_dct:
        sp_db = get_first_sp_db_from_entry(h5_file_dct[h5_file_dct['default']])
        _scan_type = dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE)
    if sp_db is None:
        print("ERROR: No SP DB found")
        return
    # Extract counter from default keys
    counter = "counter1"  # default fallback
    if 'default' in h5_file_dct and h5_file_dct['default'] in h5_file_dct:
        entry = h5_file_dct[h5_file_dct['default']]
        if 'default' in entry:
            counter = entry['default']

    focus_scans = [scan_types.OSA_FOCUS, scan_types.SAMPLE_FOCUS]
    spectra_scans = [
        scan_types.SAMPLE_POINT_SPECTRUM,
        scan_types.SAMPLE_LINE_SPECTRUM,
    ]

    stack_scans = [scan_types.SAMPLE_IMAGE_STACK]
    _scan_type = dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE)

    if _scan_type is None:
        # ToDo: after changes to file loading without assumptions about who saved the file the sp_db passed might be
        # an entry_dct, so if type is read as None check to see what the default's say the type is
        # sp_db['entry0']['WDG_COM']['SPATIAL_ROIS']['0']
        sp_db = get_first_sp_db_from_entry(sp_db[sp_db['default']])
        _scan_type = dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE)

        if _scan_type is None:
            return (None, None)
    data = None
    entry_key = h5_file_dct['default']
    entry_dct = h5_file_dct[entry_key]
    sp_db_dct = entry_dct['sp_db_dct']
    data = np.array(sp_db_dct['nxdata'][counter])
    fpath = sp_db_dct['file_path']# .replace("/", "\\")
    all_ev_setpoints = sp_db_dct['energy']

    if data is None:
        if _scan_type is scan_types.SAMPLE_POINT_SPECTRUM:
            data = np.ones((2, 2))
        else:
            return (None, None)

    if data.size == 0:
        if _scan_type is scan_types.SAMPLE_POINT_SPECTRUM:
            data = np.ones((2, 2))
        else:
            return (None, None)

    if data.ndim == 3:
        data = data[0]

    if data.ndim in [1, 2]:
        # # hack
        e_pnt = sp_db[EV_ROIS][ev_idx][SETPOINTS][ev_pnt]
        e_npts = 0
        for e in sp_db[EV_ROIS]:
            if len(e[SETPOINTS]) > 1:
                e_npts += len(e[SETPOINTS])
            else:
                e_npts = 1

        if data.ndim == 1:
            height = 1
            (width,) = data.shape
        else:
            height, width = data.shape

        # s = 'File: %s  \n' %  (fprefix + '.hdf5')
        # if (fpath.find('12162') > -1):
        #    print()

        dct = {}
        dct["file"] = fpath
        dct["scan_type_num"] = dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE)
        dct["scan_type"] = (
                scan_types[dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE)]
                + " "
                + scan_sub_types[dct_get(sp_db, SPDB_SCAN_PLUGIN_SUBTYPE)]
        )
        dct['stxm_scan_type'] = dct_get(sp_db, SPDB_SCAN_PLUGIN_STXM_SCAN_TYPE)
        # this following scan_panel_idx is needed for drag and drop
        # dct["scan_panel_idx"] = dct_get(sp_db, SPDB_SCAN_PLUGIN_PANEL_IDX)
        dct["energy"] = [e_pnt]
        dct["estart"] = sp_db[EV_ROIS][ev_idx][START]
        # if is_folder:
        if len(sp_db[EV_ROIS]) > 1:
            # its a stack folder so show the final energy not just the last in the current region ev_idx
            dct["estop"] = sp_db[EV_ROIS][-1][STOP]
        else:
            dct["estop"] = sp_db[EV_ROIS][ev_idx][STOP]

        dct["e_npnts"] = e_npts

        if stack_idx is not None:
            dct["stack_index"] = stack_idx
        dct["polarization"] = convert_wrapper_epu_to_str(
            sp_db[EV_ROIS][ev_idx][POL_ROIS][pol_idx][POL]
        )
        dct["offset"] = sp_db[EV_ROIS][ev_idx][POL_ROIS][pol_idx][OFF]
        dct["angle"] = sp_db[EV_ROIS][ev_idx][POL_ROIS][pol_idx][ANGLE]
        dct["dwell"] = sp_db[EV_ROIS][ev_idx][DWELL] * 1000.0
        dct['npoints'] = (width, height)

        start_date_str = sp_db[SPDB_ACTIVE_DATA_OBJECT][ADO_START_TIME]
        if isinstance(start_date_str, bytes):
            start_date_str = start_date_str.decode("utf-8")

        end_date_str = sp_db[SPDB_ACTIVE_DATA_OBJECT][ADO_END_TIME]
        if isinstance(end_date_str, bytes):
            end_date_str = end_date_str.decode("utf-8")

        dt0, tm0 = extract_date_time_from_nx_time(start_date_str)
        dt1, tm1 = extract_date_time_from_nx_time(end_date_str)
        dct["date"] = dt0
        dct["start_time"] = tm0
        dct["end_time"] = tm1

        if _scan_type in focus_scans:

            zzcntr = dct_get(sp_db, SPDB_ZZCENTER)
            if zzcntr is None:
                zzcntr = dct_get(sp_db, SPDB_ZCENTER)
            # dct['center'] = (dct_get(sp_db, SPDB_XCENTER), dct_get(sp_db, SPDB_ZZCENTER))
            dct["center"] = (dct_get(sp_db, SPDB_XCENTER), zzcntr)

            zzrng = dct_get(sp_db, SPDB_ZZRANGE)
            if zzrng is None:
                zzrng = dct_get(sp_db, SPDB_ZRANGE)
            dct["range"] = (dct_get(sp_db, SPDB_XRANGE), zzrng)

            zzstep = dct_get(sp_db, SPDB_ZZSTEP)
            if zzstep is None:
                zzstep = dct_get(sp_db, SPDB_ZSTEP)
            dct["step"] = (dct_get(sp_db, SPDB_XSTEP), zzstep)

            zzstrt = dct_get(sp_db, SPDB_ZZSTART)
            if zzstrt is None:
                zzstrt = dct_get(sp_db, SPDB_ZSTART)
            dct["start"] = (dct_get(sp_db, SPDB_XSTART), zzstrt)

            zzstop = dct_get(sp_db, SPDB_ZZSTOP)
            if zzstop is None:
                zzstop = dct_get(sp_db, SPDB_ZSTOP)
            dct["stop"] = (dct_get(sp_db, SPDB_XSTOP), zzstop)

            zzposner = dct_get(sp_db, SPDB_ZZPOSITIONER)
            if zzposner is None:
                zzposner = dct_get(sp_db, SPDB_ZPOSITIONER)
            dct["ypositioner"] = zzposner

            dct["xpositioner"] = dct_get(sp_db, SPDB_XPOSITIONER)

            dct["estop"] = dct_get(sp_db, SPDB_EV_ROIS)[0][STOP]
        else:
            dct["center"] = (
                dct_get(sp_db, SPDB_XCENTER),
                dct_get(sp_db, SPDB_YCENTER),
            )

            dct["range"] = (
                dct_get(sp_db, SPDB_XRANGE),
                dct_get(sp_db, SPDB_YRANGE),
            )

            dct["step"] = (dct_get(sp_db, SPDB_XSTEP), dct_get(sp_db, SPDB_YSTEP))
            dct["estep"] = dct_get(sp_db, SPDB_EV_ROIS)[0][STEP]
            dct["start"] = (
                dct_get(sp_db, SPDB_XSTART),
                dct_get(sp_db, SPDB_YSTART),
            )
            dct["stop"] = (dct_get(sp_db, SPDB_XSTOP), dct_get(sp_db, SPDB_YSTOP))
            dct["xpositioner"] = dct_get(sp_db, SPDB_XPOSITIONER)
            dct["ypositioner"] = dct_get(sp_db, SPDB_YPOSITIONER)

        # if ('GONI' in sp_db.keys()):
        if "GONI" in list(sp_db):
            if dct_get(sp_db, SPDB_GT) is None:
                pass
            if dct_get(sp_db, SPDB_GZCENTER) != None:
                # pass
                dct["goni_z_cntr"] = dct_get(sp_db, SPDB_GZCENTER)
            if dct_get(sp_db, SPDB_GTCENTER) != None:
                dct["goni_theta_cntr"] = dct_get(sp_db, SPDB_GTCENTER)

        jstr = json.dumps(convert_numpy_to_python(dct))

        # construct the tooltip string using html formatting for bold etc
        s = "%s" % format_info_text("File:", dct["file"], start_preformat=True)
        s += "%s %s %s" % (
            format_info_text("Date:", dct["date"], newline=False),
            format_info_text("Started:", dct["start_time"], newline=False),
            format_info_text("Ended:", dct["end_time"]),
        )

        if _scan_type is scan_types.GENERIC_SCAN:
            # add the positioner name
            # s += '%s' % format_info_text('Scan Type:', dct['scan_type'] + ' %s' % dct_get(sp_db, SPDB_XPOSITIONER))
            s += "%s" % format_info_text(
                "Scan Type:", dct["scan_type"], newline=False
            )
            s += " %s" % format_info_text(dct_get(sp_db, SPDB_XPOSITIONER), "")

        else:
            s += "%s" % format_info_text("Scan Type:", dct["scan_type"])

        if (_scan_type in spectra_scans) or (_scan_type in stack_scans and stack_idx is None):
            s += "%s %s %s" % (
                format_info_text(
                    "Energy:",
                    f"[{dct['estart']:.2f} ---> {dct['estop']:.2f}] eV \t",
                    newline=False,
                ),
                format_info_text("#eV Points:", f"{dct['e_npnts']}", newline=False),
                format_info_text("step:", f"{dct['estep']:.2f} ev"),
            )
        else:
            s += "%s" % format_info_text("Energy:", "%.2f eV" % e_pnt)

        if (_scan_type in focus_scans):
            x_start, zpz_start = dct["start"]
            x_stop, zpz_stop = dct["stop"]
            s += '%s' % format_info_text('ZoneplateZ:', '[%.2f ---> %.2f] um' % (zpz_start, zpz_stop))

        _s1 = "%s" % (
            format_info_text(
                "Polarization:",
                "%s"
                % convert_wrapper_epu_to_str(
                    sp_db[EV_ROIS][ev_idx][EPU_POL_PNTS][pol_idx]
                ),
                newline=False,
            )
        )
        _s2 = "%s" % (
            format_info_text(
                "Offset:",
                "%.2f mm" % sp_db[EV_ROIS][ev_idx][EPU_OFF_PNTS][pol_idx],
                newline=False,
            )
        )
        _s3 = "%s" % (
            format_info_text(
                "Angle:", "%.2f deg" % sp_db[EV_ROIS][ev_idx][EPU_ANG_PNTS][pol_idx]
            )
        )
        s += "%s %s %s" % (_s1, _s2, _s3)
        s += "%s" % format_info_text(
            "Dwell:", "%.2f ms" % (sp_db[EV_ROIS][ev_idx][DWELL] )
        )
        s += "%s" % format_info_text("Points:", "%d x %d " % (width, height))

        if dct["center"][0] is None:
            s += "%s" % format_info_text(
                "Center:", "(?, ?) um"
            )
        else:
            s += "%s" % format_info_text(
            "Center:", "(%.2f, %.2f) um" % dct["center"]
            )

        if dct["range"][0] is None:
            s += "%s" % format_info_text(
                "Range:", "(?, ?) um"
            )
        else:
            s += "%s" % format_info_text(
                "Range:", "(%.2f, %.2f) um" % dct["range"]
            )

        if "goni_theta_cntr" in list(dct):

            if dct["step"][0] is None:
                s += "%s" % format_info_text(
                    "StepSize:", "(?, ?) um"
                )
            else:
                s += "%s" % format_info_text(
                    "StepSize:", "(%.3f, %.3f) um" % dct["step"]
                )

            if "goni_z_cntr" in list(dct):
                if dct["goni_z_cntr"][0] is None:
                    s += "%s" % format_info_text(
                        "Goni Z:", "? um"
                    )
                else:
                    s += "%s" % format_info_text(
                        "Goni Z:", "%.3f um" % dct["goni_z_cntr"]
                    )

            s += "%s" % format_info_text(
                "Goni Theta:",
                "%.2f deg" % (dct["goni_theta_cntr"]),
                newline=False,
                end_preformat=True,
            )
        else:
            if dct["step"][0] is None:
                s += "%s" % format_info_text(
                    "StepSize:", "(?, ?) um"
                )
            else:
                s += "%s" % format_info_text(
                    "StepSize:",
                    "(%.3f, %.3f) um" % dct["step"],
                    newline=False,
                    end_preformat=True,
                )

        return (s, jstr)
    else:
        # print 'build_image_params: Unsupported dimensions of data ->[%d]'% data.ndim
        return (None, None)
