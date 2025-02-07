import pathlib
import pprint
import numpy as np

from cls.data_io.stxm_data_io import STXMDataIo
from cls.utils.dirlist import get_files_with_extension
from cls.types.stxmTypes import scan_types
from cls.utils.json_utils import dict_to_json, json_to_file, file_to_json, json_to_dict

from cls.data_io.tests.plot_fit import fit_and_plot


def get_dwell_from_entry(entry_dct):
    sp_keys = list(entry_dct['WDG_COM']['SPATIAL_ROIS'].keys())
    return entry_dct['WDG_COM']['SPATIAL_ROIS'][sp_keys[0]]['EV_ROIS'][0]['DWELL']
    # return entry_dct['WDG_COM']['SINGLE_LST']['DWELL'][0]


def get_scan_range_from_entry(entry_dct, axis='X'):
    sp_keys = list(entry_dct['WDG_COM']['SPATIAL_ROIS'].keys())
    return entry_dct['WDG_COM']['SPATIAL_ROIS'][sp_keys[0]][axis]['RANGE']
    # return entry_dct['WDG_COM']['SINGLE_LST']['SP_ROIS'][0][axis]['RANGE']


def get_num_points_from_entry(entry_dct, axis='X'):
    sp_keys = list(entry_dct['WDG_COM']['SPATIAL_ROIS'].keys())
    return int(entry_dct['WDG_COM']['SPATIAL_ROIS'][sp_keys[0]][axis]['NPOINTS'])
    # return entry_dct['WDG_COM']['SINGLE_LST']['SP_ROIS'][0][axis]['NPOINTS']


def get_filename_from_spdb(sp_db):
    """
    Turn the start and stop time delta into (total seconds, hours:minutes:seconds)
    'END_TIME': b'2023-07-05T11:24:01',
    'START_TIME': b'2023-07-05T11:22:53',

    'ACTIVE_DATA_OBJ': {'CFG': {'CUR_EV_IDX': None,
       'CUR_SAMPLE_POS': None,
       'CUR_SEQ_NUM': None,
       'CUR_SPATIAL_ROI_IDX': None,
       'DATA_DIR': 'G:\\SM\\test_data\\guest\\0705',
       'DATA_EXT': 'hdf5',
       'DATA_FILE_NAME': 'C230705001.hdf5',
       'DATA_IMG_IDX': 0,
       'DATA_STATUS': 'NOT_FINISHED',
       'DATA_THUMB_NAME': 'C230705001',
       'PREFIX': 'C230705001',
       'PTYCHO_CAM_DATA_DIR': '',
       'ROI': None,
       'SCAN_TYPE': None,
       'STACK_DIR': '',
       'THUMB_EXT': 'jpg',
       'UNIQUEID': None,
       'WDG_COM': None},
      'DATA': {'POINTS': None, 'SSCANS': {}},
      'DEVICES': None,
      'END_TIME': b'2023-07-05T11:24:01',
      'START_TIME': b'2023-07-05T11:22:53',
      'VERSION': b'1.0'}

    Parameters
    ----------
    sp_db
    axis

    Returns
    -------

    """

    ado = sp_db['ACTIVE_DATA_OBJ']
    return ado['CFG']['DATA_DIR'] + "\\" + ado['CFG']['DATA_FILE_NAME']


def get_scan_type(entry_dct):
    spatial_keys = list(entry_dct['WDG_COM']['SPATIAL_ROIS'].keys())
    key = spatial_keys[0]
    scan_type_enum = entry_dct['WDG_COM']['SPATIAL_ROIS'][key]['SCAN_PLUGIN']['SCAN_TYPE']
    return scan_types[scan_type_enum]


def make_scan_time_dct(data_io, entry_dct):
    """
    a convienience function to create a 'standard' dict for use by thumb widgets
    :param data_io:
    :param entry_dct:
    :return:
    """
    sp_db = data_io.get_first_sp_db_from_entry(entry_dct)
    ttl_scan_seconds = data_io.get_elapsed_time_from_sp_db(sp_db, axis='X')

    dct = {}
    dct['dwell'] = get_dwell_from_entry(entry_dct)
    dct["ttl_scan_seconds"] = ttl_scan_seconds
    dct['scan_type'] = get_scan_type(entry_dct)
    dct['scan_range_x'] = get_scan_range_from_entry(entry_dct, axis='X')
    dct['num points_x'] = get_num_points_from_entry(entry_dct, axis='X')
    dct['scan_range_y'] = get_scan_range_from_entry(entry_dct, axis='Y')
    dct['num points_y'] = get_num_points_from_entry(entry_dct, axis='Y')
    dct["fpath"] = get_filename_from_spdb(sp_db)
    dct['param_hash'] = hash(f"{dct['scan_type']}:{dct['dwell']}:{dct['num points_x']}:{dct['num points_y']}")
    dct['unique_hash'] = hash(
        f"{dct['fpath']}:{dct['scan_type']}:{dct['dwell']}:{dct['num points_x']}:{dct['num points_y']}")
    # dct["entries"] = entry_dct
    # print(f"Total scan time = {ttl_scan_seconds} seconds")
    print(f"Processed: {dct['fpath']}")
    return dct


def print_scan_time_dct(s_dct, i):
    print(f"[{i}] took {dct['ttl_scan_seconds']} seconds")


def process_scans(crs_images_dct):
    for crs_parm, lst in crs_images_dct.items():
        i = 0
        for sct_dct in lst:
            print_scan_time_dct(sct_dct, i)


def build_database(path):
    # path = r'G:/SM/test_data/guest'
    fpaths = get_files_with_extension(path, ext=".hdf5", skip_lst=[])

    dct = {}
    dct['scan_type'] = {}

    for fpath in fpaths:
        p = pathlib.Path(fpath)
        fname = p.name
        data_dir = p.as_posix().replace(fname, "")
        dataio = STXMDataIo(data_dir, fname.replace(".hdf5", ""))
        base_dct = dataio.load()
        if base_dct:
            if 'default' in list(base_dct.keys()):
                ekey = base_dct['default']
                edct = base_dct[ekey]
                fdct = make_scan_time_dct(dataio, edct)
                if fdct['scan_type'] not in dct['scan_type'].keys():
                    dct['scan_type'][fdct['scan_type']] = {}

                # add this scan hashed by its params to the scan_types list
                if fdct['param_hash'] not in dct['scan_type'][fdct['scan_type']].keys():
                    dct['scan_type'][fdct['scan_type']][fdct['param_hash']] = []

                dct['scan_type'][fdct['scan_type']][fdct['param_hash']].append(fdct)
            else:
                pprint.pprint(base_dct)
        else:
            print(f"something wrong with this file [{fname}")

    return dct


if __name__ == '__main__':
    import os

    path = r'2024/guest/2024_05'
    db_path = path + "/time_dct.js"
    num_sd_to_remove = 2

    # kload it instead
    if os.path.exists(db_path):
        js = file_to_json(path + "\\time_dct.js")
        dct = json_to_dict(js)
    else:
        # build it
        dct = build_database(path)
        js = dict_to_json(dct)
        json_to_file(db_path, js)

    # pprint.pprint(dct)
    styp_keys = dct["scan_type"].keys()

    for st in styp_keys:
        # dct['scan_type'][ 'coarse_image'][4459244325424181265].keys()
        print(f"Processing ['{st}']")
        # now walk each param set
        for hsh, hdct_lst in dct["scan_type"][st].items():
            sdct = hdct_lst[0]
            # dct['dwell'] = get_dwell_from_entry(entry_dct)
            # dct["ttl_scan_seconds"] = ttl_scan_seconds
            # dct['scan_type'] = get_scan_type(entry_dct)
            # dct['scan_range_x'] = get_scan_range_from_entry(entry_dct, axis='X')
            # dct['num points_x'] = get_num_points_from_entry(entry_dct, axis='X')
            # dct['scan_range_y'] = get_scan_range_from_entry(entry_dct, axis='Y')
            # dct['num points_y'] = get_num_points_from_entry(entry_dct, axis='Y')
            title = f"\t[{st}] Params: {sdct['dwell']} ms dwell and {sdct['num points_x']}x{sdct['num points_y']} points"
            print(title)
            i = 0
            avg_sec = 0
            arr_lst = []
            for h in hdct_lst:
                print(f"\t\t{h['fpath']} took {h['ttl_scan_seconds']} seconds")
                # avg_sec += h['ttl_scan_seconds']
                arr_lst.append(h['ttl_scan_seconds'])
                i += 1

            elements = np.array(arr_lst)
            mean = np.mean(elements, axis=0)
            sd = np.std(elements, axis=0)
            print(f"\t\t\tWith Mean {mean} -> Removing outliers +/- {sd:.2f} ({num_sd_to_remove}*sdev) ")
            final_list = [x for x in arr_lst if (x > mean - num_sd_to_remove * sd)]
            final_list = [x for x in final_list if (x < mean + num_sd_to_remove * sd)]
            i = 0
            avg_sec = 0
            for v in final_list:
                avg_sec += v
                i += 1

            if i == 0:
                i = 1
            print(f"\t\t\tscans for param {hsh} to avg of {avg_sec / i:.2f} seconds")
            print()
            if len(final_list) > 10:
                data_x = list(range(len(final_list)))
                data_y = final_list
                degree_of_fit = 5  # 1 so its linear
                fit_and_plot(data_x, data_y, degree_of_fit, title, do_plot=True)
