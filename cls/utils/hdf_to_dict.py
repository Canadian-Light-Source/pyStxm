import pprint
import os
import time
import h5py
import numpy as np
import simplejson as json

from cls.types.stxmTypes import (
    scan_types,
)
from cls.utils.list_utils import merge_to_one_list
from cls.utils.dict_utils import dct_get
from cls.utils.roi_dict_defs import *
from cls.utils.fileUtils import get_file_path_as_parts

def hdf5_to_dict_with_attributes(hdf5_group):
    """
    Recursively walks through an HDF5 group and returns its structure as a dictionary,
    including group and dataset attributes, with special handling for the 'doc' attribute.

    :param hdf5_group: An h5py.Group or h5py.File object representing the HDF5 group.
    :return: A dictionary representing the HDF5 tree structure with attributes.
    """
    tree = {"_attrs_": dict(hdf5_group.attrs)}  # Process group attributes
    for key, item in hdf5_group.items():
        if isinstance(item, h5py.Group):  # If it's a group, recurse
            #print(str(item))
            if str(item).find('scan_request') > -1:
                continue
            tree[key] = hdf5_to_dict_with_attributes(item)
        elif isinstance(item, h5py.Dataset):  # If it's a dataset, store its shape, dtype, and attributes
            tree[key] = {
                "type": "dataset",
                "shape": item.shape,
                "dtype": str(item.dtype),
                "_data_": item[()],
                "_attrs_": dict(item.attrs)  # Process dataset attributes
            }
    return tree

def get_roi_from_data_array(dat_array):
    npts_x = npts_y = npts_e = 0
    if dat_array.ndim == 1:
        npts_x, = dat_array.shape
        npts_y = 1
    elif dat_array.ndim == 2:
        npts_y, npts_x = dat_array.shape
    elif dat_array.ndim == 3:
        npts_e, npts_y, npts_x = dat_array.shape

    cntr = (dat_array[0] + dat_array[-1]) * 0.5
    rng = dat_array[-1] - dat_array[0]
    step = dat_array[1] - dat_array[0]


total_items = 0
total_time = 0


def decode_if_bytes(value):

    try:
        if isinstance(value, bytes):
            return value.decode('utf-8', errors='replace')
        elif isinstance(value, np.ndarray):
            if value.dtype.kind == 'S':  # String-like dtype
                return np.char.decode(value, 'utf-8', errors='replace').tolist()
            return value.tolist()
        elif isinstance(value, list):
            return list(map(decode_if_bytes, value))  # Use map for better performance
    except Exception:
        return str(value)
    return value

def get_default_entry_name(file_dct):
    """
    file_dct is the top level dict for the h5 file
    """
    if 'default' in file_dct.keys():
        return file_dct['default']
def get_default_entry(file_dct):
    """
    file_dct is the top level dict for the h5 file
    """
    if 'default' in file_dct['__attrs__'].keys():
        return file_dct[file_dct['__attrs__']['default']]

def get_default_entry_signal_name(file_dct):
    """
    file_dct is the top level dict for the h5 file
    """
    e_dct = get_default_entry(file_dct)
    if 'default' in e_dct['_attrs_'].keys():
        return e_dct['_attrs_']['default']

def get_default_entry_signal(file_dct):
    """
    file_dct is the top level dict for the h5 file
    """
    e_dct = get_default_entry(file_dct)
    sig_nm = get_default_entry_signal_name(file_dct)
    if sig_nm in e_dct.keys():
        data_nm = e_dct[sig_nm]['_attrs_']['signal']
        return e_dct[sig_nm][data_nm]

def get_default_entry_nxdata_group(file_dct):
    """
    file_dct is the top level dict for the h5 file
    """
    e_dct = get_default_entry(file_dct)
    sig_nm = get_default_entry_signal_name(file_dct)
    if sig_nm in e_dct.keys():
        data_nm = e_dct[sig_nm]['_attrs_']['signal']
        return sig_nm, e_dct[sig_nm]

def get_default_entry_nxinstrument_group(file_dct):
    """
    file_dct is the top level dict for the h5 file
    """
    e_dct = get_default_entry(file_dct)
    return e_dct['instrument']

def get_stxm_scan_type(dgrp):
    """

    """
    if isinstance(dgrp['stxm_scan_type']['__data__'], list):
        return dgrp['stxm_scan_type']['__data__'][0]
    else:
        return dgrp['stxm_scan_type']['__data__']

def get_pystxm_scan_type_from_file_dct(file_dct):
    """
    given a file_dct retrieve the standard enum integer value of the scan type from the first spatial roi
    """
    entry_nm = get_default_entry_name(file_dct)
    sp_id = list(file_dct[entry_nm][WDG_COM][SPATIAL_ROIS].keys())[0]
    _scan_type = dct_get(file_dct[entry_nm][WDG_COM][SPATIAL_ROIS][sp_id], SPDB_SCAN_PLUGIN_TYPE)
    return _scan_type


def get_first_sp_db_from_file_dct(file_dct):
    """
    given a file_dct retrieve the first spatial database
    """
    entry_nm = get_default_entry_name(file_dct)
    sp_id = list(file_dct[entry_nm][WDG_COM][SPATIAL_ROIS].keys())[0]
    sp_db = file_dct[entry_nm][WDG_COM][SPATIAL_ROIS][sp_id]
    return sp_db

def get_pystxm_standard_scan_type_from_string(scan_type_str):
    """
    returns the correct scan_type from enumerated types
       the scan type was read from the stxm_scan_type dataset from the NXdata group of the data file
        and we want to convert it to using the stxm scan_types
        scan_types = Enum(
            "detector_image",
            "osa_image",
            "osa_focus",
            "sample_focus",
            "sample_point_spectrum",
            "sample_line_spectrum",
            "sample_image",
            "sample_image_stack",
            "generic_scan",
            "coarse_image",
            "coarse_goni",
            "tomography",
            "pattern_gen",
            "ptychography",
            "two_variable_image"
        )
    """
    # scan_type_str = get_stxm_scan_type(file_dct)
    if scan_type_str == "detector image":
        return scan_types.DETECTOR_IMAGE
    if scan_type_str == "osa image":
        return scan_types.OSA_IMAGE
    if scan_type_str == "osa focus":
        return scan_types.OSA_FOCUS
    if scan_type_str == "sample focus":
        return scan_types.SAMPLE_FOCUS
    if scan_type_str == "sample point spectrum":
        return scan_types.SAMPLE_POINT_SPECTRUM
    if scan_type_str == "sample line spectrum":
        return scan_types.SAMPLE_LINE_SPECTRUM
    if scan_type_str == "sample image":
        return scan_types.SAMPLE_IMAGE
    if scan_type_str == "sample image stack":
        return scan_types.SAMPLE_IMAGE_STACK
    if scan_type_str == "generic scan":
        return scan_types.GENERIC_SCAN
    if scan_type_str == "coarse image":
        return scan_types.COARSE_IMAGE
    if scan_type_str == "coarse goni":
        return scan_types.COARSE_GONI
    if scan_type_str == "tomography":
        return scan_types.TOMOGRAPHY
    if scan_type_str == "pattern gen":
        return scan_types.PATTERN_GEN
    if scan_type_str == "ptychography":
        return scan_types.PTYCHOGRAPHY
    if scan_type_str == "two variable image":
        return scan_types.TWO_VARIABLE_IMAGE

def get_times(entry_dct, data_grp):
    """

    """
    #dgrp_nm, dgrp = get_default_entry_nxdata_group(file_dct)
    #def_entry = get_default_entry(file_dct)
    start_time = entry_dct['start_time']['__data__']
    end_time = entry_dct['end_time']['__data__']
    count_time = data_grp['count_time']['__data__'][0]
    return start_time, end_time, count_time

def get_polarization(data_dgr):
    """

    """
    dct = {}
    # dgrp_nm, dgrp = get_default_entry_nxdata_group(file_dct)
    for k in data_dgr.keys():
        if k.find('epu_polarization') > -1:
            dct[k] = data_dgr[k]['__data__'][0]
        elif k.find('epu_offset') > -1:
            dct[k] = data_dgr[k]['__data__'][0]
        elif k.find('polar') > -1:
            dct[k] = data_dgr[k]['__data__'][0]
    return dct


def get_sp_db_dct_from_file_dict(file_dct):
    """
    make sp-dbs for each default axis and also return the stxm_scan_type in the dict

    """
    dct = {}
    entry_dct = get_default_entry(file_dct)
    # set default entry name
    dct['default'] = file_dct['__attrs__']['default']
    # set default nxdata name
    dgrp_nm = entry_dct['__attrs__']['default']
    dgrp = entry_dct[dgrp_nm]
    sig_nm = entry_dct[dgrp_nm]['__attrs__']['signal']

    dct['nxdata'] = {dgrp_nm: np.array(entry_dct[dgrp_nm][sig_nm]['__data__'])}
    dct['nxdata_nm'] = dgrp_nm
    dct['nxsignal_nm'] = sig_nm
    dct['energy'] = np.array(dgrp['energy']['__data__'])
    dct['polarization'] = get_polarization_offset_angle_from_instrument(entry_dct)
    dct['start_time'], dct['end_time'], dct['count_time'] = get_times(entry_dct, dgrp)

    scan_type_str = get_stxm_scan_type(dgrp)
    if scan_type_str == 'generic scan':
        # Pixelator saves Two Variable scans as generic scan
        # check the dimensions of the data
        cntr = list(dct['nxdata'].keys())[0]
        if dct['nxdata'][cntr].ndim > 1:
            scan_type_str = 'two variable image'

    dct['stxm_scan_type'] = scan_type_str
    dct['pystxm_enum_scan_type'] = get_pystxm_standard_scan_type_from_string(dct['stxm_scan_type'])
    directory, filename, suffix = get_file_path_as_parts(file_dct['__attrs__']['file_name'])
    dct['file_path'] = file_dct['__attrs__']['file_name']
    dct['directory'] = directory
    dct['file_name'] = filename + suffix

    axis_names = list(dgrp['__attrs__']['axes'])
    if dct['pystxm_enum_scan_type'] == scan_types.SAMPLE_POINT_SPECTRUM:
        #Sample Point, make sure it includes sample_x and sample_y, SLS currently doesnt have these in axes list only energy
        if 'sample_x' not in axis_names:
            if 'sample_x' in dgrp.keys():
                axis_names.append('sample_x')
        if 'sample_y' not in axis_names:
            if 'sample_y' in dgrp.keys():
                axis_names.append('sample_y')

    dct['axis_names'] = axis_names
    # for each axis create an sp_db
    for ax_nm in axis_names:
        ax_data = dgrp[ax_nm]['__data__']
        dct[ax_nm] = np.array(ax_data)

    #print(f"finished: get_sp_db_from_entry_dict: keys={list(dct.keys())}")
    return dct

def get_default_data_from_hdf5_file(file_path):
    """
    get the default data from a datafile as fast as possible
    from an hdf5 file

    # start_time = time.time()
        sp_db = create_spdb_wdgcom_from_file_dct(file_dct)
        # end_time = time.time()  # Get the timestamp after execution
        # elapsed_time = end_time - start_time
        #print(f"Took: Elapsed Time: {elapsed_time:.6f} seconds to run create_spdb_wdgcom_from_file_dct [{filename}]")

    """
    if os.path.exists(file_path):
        # start_time = time.time()
        with (h5py.File(file_path, 'r') as h5_file):
            #hdf5_dict = traverse_h5_group(h5_file)
            dct = {}
            ekey = list(h5_file.keys())[0]
            if h5_file[ekey].attrs['NX_class'] == b'NXentry':
                entry_dct = h5_file[ekey]
                # set default entry name
                dct['default'] = ekey
                #find NXdata
                entry_grp = h5_file[ekey]
                ekeys = list(entry_grp.keys())
                for k in ekeys:
                    if 'NX_class' in entry_grp[k].attrs.keys():
                        if entry_grp[k].attrs['NX_class'] == b'NXdata':
                            # set default nxdata name
                            dgrp_nm = k
                            dgrp = entry_grp[k]
                            sig_nm = dgrp.attrs['signal'].decode('utf8')

                            dct['nxdata'] = {dgrp_nm: np.array(dgrp[sig_nm])}
                            dct['nxdata_nm'] = dgrp_nm
                            dct['nxsignal_nm'] = sig_nm
                            dct['energy'] = np.array(dgrp['energy'])

                            dct['start_time'] = decode_if_bytes(entry_grp['start_time'][()])
                            dct['end_time'] = decode_if_bytes(entry_grp['end_time'][()])
                            dct['count_time'] = dgrp['count_time'][()]
                            stype = decode_if_bytes(dgrp['stxm_scan_type'][()])
                            dct['stxm_scan_type'] = stype[0] if isinstance(stype, list) else stype

                            dct['pystxm_enum_scan_type'] = get_pystxm_standard_scan_type_from_string(dct['stxm_scan_type'])
                            dct['file_name'] = file_path

                            axis_names = decode_if_bytes(list(dgrp.attrs['axes']))
                            if dct['pystxm_enum_scan_type'] == scan_types.SAMPLE_POINT_SPECTRUM:
                                #Sample Point, make sure it includes sample_x and sample_y, SLS currently doesnt have these in axes list only energy
                                if 'sample_x' not in axis_names:
                                    if 'sample_x' in dgrp.keys():
                                        axis_names.append('sample_x')
                                if 'sample_y' not in axis_names:
                                    if 'sample_y' in dgrp.keys():
                                        axis_names.append('sample_y')

                            dct['axis_names'] = axis_names
                            # for each axis create an sp_db
                            for ax_nm in axis_names:
                                dct[ax_nm] = dgrp[ax_nm][()]

                        elif entry_grp[k].attrs['NX_class'] == b'NXinstrument':
                            dgrp_nm = k
                            dgrp = h5_file[ekey][k]
                            dct['polarization'] = get_polarization_offset_angle_from_instrument_hdf_group(dgrp)
                            dct['source'] = decode_if_bytes(dgrp['source']['name'][()])[0]

                        elif entry_grp[k].attrs['NX_class'] == b'NXcollection':
                            if 'scan_request' in entry_grp[k].keys():
                                dct['scan_request'] = json.loads(decode_if_bytes(entry_grp[k]['scan_request']['scan_request'][()])[0])

        #end_time = time.time()
        #elapsed_time = end_time - start_time
        #print(f"get_default_data_from_hdf5_file: Took: Elapsed Time: {elapsed_time:.6f} seconds to run create_spdb_wdgcom_from_file_dct [{filename}]")
        return dct



def get_energy_setpoints(sp_db):
    """
    use the default attribute to return the energy setpoints
    """
    _setpoints = []
    for e_roi in sp_db[EV_ROIS]:
        _setpoints.append(e_roi[SETPOINTS])

    _setpoints = merge_to_one_list(_setpoints)
    return _setpoints

def get_polarization_offset_angle_from_instrument(entry_dct):
    # check to see if polarizatiomn is included in the file, return None if not
    # if epu_polarization
    dgrp_nm = entry_dct['__attrs__']['default']
    data_grp = entry_dct[dgrp_nm]
    pol_dct = {}
    pol_exists = False
    for k in data_grp.keys():
        if k.find('polariz') > -1:
            pol_exists = True
            break
    if pol_exists:
        pol_dct = get_polarization(data_grp)
        inst_dct = entry_dct['instrument'] # get_default_entry_nxinstrument_group(data_grp)
        #offset = inst_dct['epu']['gap_offset']
        if 'epu' in inst_dct.keys():
            pol_dct['epu_angle'] = inst_dct['epu']['linear_inclined_angle']['__data__'][0]
        else:
            pol_dct['epu_angle'] = 0.0
    return pol_dct

def get_polarization_offset_angle_from_instrument_hdf_group(grp):
    # check to see if polarizatiomn is included in the file, return None if not

    pol_dct = {}
    pol_exists = False
    for k in grp.keys():
        if k.find('polariz') > -1:
            pol_exists = True
            break
    if pol_exists:
        pol_dct = get_polarization(grp)
        # inst_dct = entry_dct['instrument'] # get_default_entry_nxinstrument_group(data_grp)
        #offset = inst_dct['epu']['gap_offset']
        if 'epu' in inst_dct.keys():
            pol_dct['epu_angle'] = inst_dct['epu']['linear_inclined_angle']['__data__'][0]
        else:
            pol_dct['epu_angle'] = 0.0
    return pol_dct

def add_default_attr(file_path):
    with (h5py.File(file_path, 'a') as hdf5_file):
        hdf5_file.attrs['default'] = 'entry1'
        hdf5_file['entry1'].attrs['default'] = 'counter0'

def hdf5_to_dict(file_path, load_all_data=True):
    """
    Converts an HDF5 file into a nested Python dictionary.

    Args:
        file_path (str): Path to the HDF5 file.

    Returns:
        dict: Nested dictionary representing the HDF5 file structure.
    """
    def extract_attrs(h5_obj):
        """Extract attributes from an HDF5 object into a dictionary."""
        return {decode_if_bytes(k): decode_if_bytes(v) for k, v in h5_obj.attrs.items()}

    def traverse_h5_group(group):
        """Recursively traverse an HDF5 group and convert it to a dictionary."""
        group_dict = {"__attrs__": extract_attrs(group)}
        for key, item in group.items():
            if isinstance(item, h5py.Group):
                # if key in ['instrument','NXmonitor']:
                #     #skip instrument 'NXmonitor'
                #     continue
                group_dict[key] = traverse_h5_group(item)
            elif isinstance(item, h5py.Dataset):
                group_dict[key] = {
                    "__data__": decode_if_bytes(item[()]),
                    "__attrs__": extract_attrs(item),
                }

        return group_dict

    with h5py.File(file_path, 'r') as h5_file:
        hdf5_dict = traverse_h5_group(h5_file)

    # make sure the file name is the final file name not the temporary file name
    hdf5_dict['__attrs__']['file_name'] = file_path

    return hdf5_dict



def go():
    print(f"Profiling hdf5_to_dict()")
    data_dir = r'T:/operations/STXM-data/ASTXM_upgrade_tmp/2024/guest/1231/'
    data_dir = r'T:\operations\STXM-data\ASTXM_upgrade_tmp\2024\guest\2024_05\0516'
    files = dirlist(data_dir, '.hdf5')
    for file_path in files:
        # dct = get_default_data_from_hdf5_file(os.path.join(data_dir, file_path))
        dct = hdf5_to_dict(os.path.join(data_dir, file_path))
        #pprint.pprint(dct)
        #print("done")


if __name__ == "__main__":
    from cls.utils.dirlist import dirlist
    from cls.utils.profiling import profile_it
    # import pprint
    # # Replace 'example.h5' with your HDF5 file path
    # #file_path = r"C:\test_data\0517\A240517035.hdf5"
    # file_path = r'C:\test_data\pixelator\defaulted\Sample_Image_2021-03-16_095.hdf5'
    # files = dirlist(r"C:/test_data/pixelator/defaulted/", ".hdf5")
    # for f in files:
    #     add_default_attr(r"C:/test_data/pixelator/defaulted/" + f)
    # file_path = r'G:\tmpdata\0517\A240517001\A240517001.hdf5'
    # # dct = read_hdf5_nxstxm_file_with_attributes(file_path)
    # # #pprint.pprint(tree_structure)
    # # entry_nm = get_default_entry_name(dct)
    # # # print(get_default_entry(dct))
    # # sig_nm = get_default_entry_signal_name(dct)
    # # # print(get_default_entry_signal(dct))
    # # # print(get_energy_setpoints(dct))
    # # # int_dct = get_default_entry_nxinstrument_group(dct)
    # # # print(get_polarization_offset_angle_from_instrument(dct))
    # # sp_db = get_sp_db_from_entry_dict(dct)
    # # pprint.pprint(sp_db)
    # file_path = r'T:\operations\STXM-data\ASTXM_upgrade_tmp\2024\guest\1231\Sample_Stack_2024-12-31_008.hdf5'
    # # dct = hdf5_to_dict(file_path)
    # data_dir = r'T:/operations/STXM-data/ASTXM_upgrade_tmp/2024/guest/1231/'
    # files = dirlist(r'T:/operations/STXM-data/ASTXM_upgrade_tmp/2024/guest/1231/', '.hdf5')
    # for file_path in files:
    #     #dct = get_default_data_from_hdf5_file(os.path.join(data_dir, file_path))
    #     #dct = hdf5_to_dict(file_path)
    #
    #     pprint.pprint(dct)
    #     print("done")

    profile_it("go", bias_val=1.156238437615624e-06)





