"""
Created on Jan 4, 2019

@author: bergr
"""

# Suitcase subpackages should follow strict naming and interface conventions.
# The public API must include Serializer and should include export if it is
# intended to be user-facing. They should accept the parameters sketched here,
# but may also accept additional required or optional keyword arguments, as
# needed.
import json
import os
import sys
import event_model
from pathlib import Path
import h5py
import nexpy
import numpy as np
import time
import datetime
from time import localtime
import copy

import suitcase.utils


from cls.data_io.nxstxm.utils import *
from cls.data_io.nxstxm.device_names import *
from cls.data_io.nxstxm.stxm_types import (
    scan_types,
    single_entry_scans,
    single_2d_scans,
    single_image_scans,
    stack_type_scans,
    spectra_type_scans,
    line_spec_scans,
    focus_scans,
    sample_image_filetypes,
    IS_PXP,
    IS_LXL
)

from cls.data_io.nxstxm.nxstxm_utils import (
    _dataset,
    _string_attr,
    _group,
    make_1d_array,
    get_nx_standard_epu_mode,
    get_nx_standard_epu_harmonic_new,
    translate_pol_id_to_stokes_vector,
    readin_base_classes,
    make_NXclass,
    remove_unused_NXsensor_fields,
)

from cls.data_io.nxstxm.generic_scan_utils import (
    modify_generic_scan_nxdata_group,
    modify_generic_scan_ctrl_data_grps,
    modify_generic_scan_instrument_group,
)
from cls.data_io.nxstxm.single_2d_image_utils import (
    modify_base_2d_nxdata_group,
    modify_2posner_ctrl_data_grps,
    modify_base_2d_instrument_group,
)
from cls.data_io.nxstxm.focus_image_utils import (
    modify_focus_nxdata_group,
    modify_focus_ctrl_data_grps,
    modify_focus_instrument_group,
)
from cls.data_io.nxstxm.single_image_utils import (
    modify_single_image_nxdata_group,
    modify_single_image_ctrl_data_grps,
    modify_single_image_instrument_group,
)

from cls.data_io.nxstxm.stack_image_utils import (
    modify_stack_nxdata_group,
    modify_stack_ctrl_data_grps,
)
from cls.data_io.nxstxm.spectra_utils import (
    modify_spectra_nxdata_group,
    modify_spectra_ctrl_data_grps,
    modify_spectra_instrument_group,
)

from cls.data_io.nxstxm.linespec_utils import (
    modify_line_spectra_nxdata_group,
    modify_line_spectra_ctrl_data_grps,
    modify_line_spectra_instrument_group,
)

import cls.data_io.nxstxm.nx_key_defs as nxkd
from cls.data_io.nxstxm.utils import find_path_to_key

from ._version import get_versions

_logger = get_module_logger(__name__)

__version__ = get_versions()["version"]
del get_versions


def msec_to_sec(ms):
    return ms * 0.001


class CST(datetime.tzinfo):
    def utcoffset(self, dt):
        return datetime.timedelta(hours=-6)

    def dst(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return "Saskatchewan Canada"


def make_timestamp_now():
    """
    create a ISO 8601 formatted time string for the current time and return it
    """
    t = datetime.datetime.now(tz=CST()).isoformat()
    return t


def finish_export(data_dir, file_prefix, uid):
    """
    This was moved into its own function so that if multiple entrys had been created in the same file they
    would have been done so in a tmp file, were done now so rename it to the final filename
    :param file_prefix:
    :return:
    """
    # tmp_fname = os.path.join(data_dir, '%s.hdf5.tmp' % file_prefix)
    try:
        tmp_fname = os.path.join(data_dir, f"{uid}-{file_prefix}")
        final_fname = tmp_fname.replace(".tmp", "")
        final_fname = f"{final_fname.replace(f'{uid}-', '')}.hdf5"
        os.rename(tmp_fname, final_fname)
        print(f"nxstxm: finished exporting {final_fname}")
        _logger.info(f"nxstxm: finished exporting {final_fname}")
    except:
        _logger.info("finish_export: no file to rename")
        print("finish_export: no file to rename")


def test_can_do_tmp_file(data_dir, file_prefix):
    """
    see if we are going to have trouble creating this file later when scan is done
    :param data_dir:
    :param file_prefix:
    :return:
    """
    fname = os.path.join(data_dir, "%s.hdf5.tmp" % file_prefix)
    nf = None
    try:
        nf = h5py.File(fname, "a")
        nf.close()
        os.remove(fname)
        return True
    except:
        _logger.info("Looks like there already was a file[%s]" % fname)
        if nf is not None:
            nf.close()
        if os.path.exists(fname + ".err"):
            # removing previous failed file
            os.remove(fname + ".err")
        os.rename(fname, fname + ".err")
        return False


def export(gen, directory, file_prefix="{uid}-", **kwargs):
    """
    Export a stream of documents to nxstxm_baseline.

    .. note::

        This can alternatively be used to write data to generic buffers rather
        than creating files on disk. See the documentation for the
        ``directory`` parameter below.

    Parameters
    ----------
    gen : generator
        expected to yield ``(name, document)`` pairs

    directory : string, Path or Manager.
        For basic uses, this should be the path to the output directory given
        as a string or Path object. Use an empty string ``''`` to place files
        in the current working directory.

        In advanced applications, this may direct the serialized output to a
        memory buffer, network socket, or other writable buffer. It should be
        an instance of ``suitcase.utils.MemoryBufferManager`` and
        ``suitcase.utils.MultiFileManager`` or any object implementing that
        inferface. See the suitcase documentation at
        https://nsls-ii.github.io/suitcase for details.

    file_prefix : str, optional
        The first part of the filename of the generated output files. This
        string may include templates as in ``{proposal_id}-{sample_name}-``,
        which are populated from the RunStart document. The default value is
        ``{uid}-`` which is guaranteed to be present and unique. A more
        descriptive value depends on the application and is therefore left to
        the user.

    **kwargs : kwargs
        Keyword arugments to be passed through to the underlying I/O library.

    Returns
    -------
    artifacts : dict
        dict mapping the 'labels' to lists of file names (or, in general,
        whatever resources are produced by the Manager)

    Examples
    --------

    Generate files with unique-identifer names in the current directory.

    >>> export(gen, '')

    Generate files with more readable metadata in the file names.

    >>> export(gen, '', '{plan_name}-{motors}-')

    Include the experiment's start time formatted as YY-MM-DD_HH-MM.

    >>> export(gen, '', '{time:%%Y-%%m-%%d_%%H:%%M}-')

    Place the files in a different directory, such as on a mounted USB stick.

    >>> export(gen, '/path/to/my_usb_stick')
    """
    with Serializer(directory, file_prefix, **kwargs) as serializer:
        for item in gen:
            # print('ITEM:', item)
            serializer(*item)
    return serializer.artifacts


class Serializer(event_model.DocumentRouter):
    """
    Serialize a stream of documents to nxstxm_baseline.

    .. note::

        This can alternatively be used to write data to generic buffers rather
        than creating files on disk. See the documentation for the
        ``directory`` parameter below.

    Parameters
    ----------
    directory : string, Path, or Manager
        For basic uses, this should be the path to the output directory given
        as a string or Path object. Use an empty string ``''`` to place files
        in the current working directory.

        In advanced applications, this may direct the serialized output to a
        memory buffer, network socket, or other writable buffer. It should be
        an instance of ``suitcase.utils.MemoryBufferManager`` and
        ``suitcase.utils.MultiFileManager`` or any object implementing that
        inferface. See the suitcase documentation at
        https://nsls-ii.github.io/suitcase for details.

    file_prefix : str, optional
        The first part of the filename of the generated output files. This
        string may include templates as in ``{proposal_id}-{sample_name}-``,
        which are populated from the RunStart document. The default value is
        ``{uid}-`` which is guaranteed to be present and unique. A more
        descriptive value depends on the application and is therefore left to
        the user.

    **kwargs : kwargs
        Keyword arugments to be passed through to the underlying I/O library.

    Attributes
    ----------
    artifacts
        dict mapping the 'labels' to lists of file names (or, in general,
        whatever resources are produced by the Manager)
    """

    def __init__(self, directory, file_prefix="{}-", **kwargs):

        self._file_prefix = "{}-" + file_prefix
        self._kwargs = kwargs
        if isinstance(directory, (str, Path)):
            # Ensure directory exists
            dir_path = Path(directory)
            dir_path.mkdir(parents=True, exist_ok=True)
            self._directory = dir_path  # normalize to Path
            self._manager = suitcase.utils.MultiFileManager(self._directory)
        else:
            self._directory = directory  # a Manager-like object
            self._manager = directory

        self._templated_file_prefix = file_prefix  # set when we get a 'start' document
        self._streamnames = {}  # maps descriptor uids to stream_names
        self._img_idx_map_dct = {}
        self._primary_det_nm = None
        self._detector_names = None
        self._det_strm_map = {}
        self._file_time_str = make_timestamp_now()
        self._cur_scan_md = {}
        self._processed_sp_ids = []
        self._cur_sp_id = None
        self._data = {}
        self._start_found = False
        self._nf = None


    @property
    def artifacts(self):
        # The 'artifacts' are the manager's way to exposing to the user a
        # way to get at the resources that were created. For
        # `MultiFileManager`, the artifacts are filenames.  For
        # `MemoryBuffersManager`, the artifacts are the buffer objects
        # themselves. The Serializer, in turn, exposes that to the user here.
        #
        # This must be a property, not a plain attribute, because the
        # manager's `artifacts` attribute is also a property, and we must
        # access it anew each time to be sure to get the latest contents.
        return self._manager.artifacts

    def close(self):
        """
        Close all of the resources (e.g. files) allocated.
        """
        self._manager.close()

    # These methods enable the Serializer to be used as a context manager:
    #
    # with Serializer(...) as serializer:
    #     ...
    #
    # which always calls close() on exit from the with block.

    def __enter__(self):
        return self

    def __exit__(self, *exception_details):
        self.close()

    def start(self, doc):
        """Extracts `start` document information for formatting file_prefix.

        This method checks that only one `start` document is seen and formats
        `file_prefix` based on the contents of the `start` document.
            START: [entry1]

            Run Start
            =========
            host            : myNotebook
            plan_name       : exec_e712_wavgen
            plan_type       : generator
            scan_id         : 1
            scan_title      : entry1
            time            : 1552057991.7095182
            uid             : f66a3e61-dcbb-4975-9fc8-c38a0255fb1b
            user            : bergr

        Parameters:
        -----------
        doc : dict
            RunStart document
        """
        start_time = localtime(doc["time"])
        self._start_time_str = time.strftime("%Y-%m-%dT%H:%M:%S", start_time)

        # grab the meta data that was entered into the md var in the scan plan
        _metadata_dct = json.loads(doc["metadata"])
        self._cur_scan_md[doc["uid"]] = copy.copy(_metadata_dct)
        # for k in _metadata_dct.keys():
        #     self._cur_scan_md[doc['uid']][k] = _metadata_dct[k]

        for k in self._kwargs.keys():
            self._cur_scan_md[doc["uid"]][k] = self._kwargs[k]

        if "first_uid" not in self._kwargs.keys():
            # assume there is only one scan uid and set it here
            self._cur_scan_md[doc["uid"]]["first_uid"] = doc["uid"]
        if "last_uid" not in self._kwargs.keys():
            # assume there is only one scan uid and set it here
            self._cur_scan_md[doc["uid"]]["last_uid"] = doc["uid"]

        self._img_idx_map_dct = json.loads(_metadata_dct["img_idx_map"])
        self._sequence_map = json.loads(_metadata_dct["sequence_map"])
        if "sis3820_data_map" in _metadata_dct.keys():
            self._sis3820_data_map = json.loads(_metadata_dct["sis3820_data_map"])
        else:
            self._sis3820_data_map = [{}]
        #self._detector_names = _metadata_dct["primary_det"]
        self._default_det = _metadata_dct["default_det"]
        self._sp_id_lst = _metadata_dct["sp_id_lst"]
        self._cur_sp_id = self._sp_id_lst[0]
        self._cur_uid = doc["uid"]
        self._wdg_com = json.loads(self._cur_scan_md[self._cur_uid]['wdg_com'])
        self._scan_type = _metadata_dct["scan_type"]
        self._scan_subtype = self.get_scan_subtype()

        # assign the member vars
        self._e_idx = self._img_idx_map_dct["e_idx"]
        self._entry_nm = self._img_idx_map_dct["entry"]
        self._pol_idx = self._img_idx_map_dct["pol_idx"]
        self._sp_id = self._img_idx_map_dct["sp_id"]
        self._sp_idx = self._img_idx_map_dct["sp_idx"]
        self._tmp_fname = os.path.join(
            self._directory,
            self._file_prefix.format(self._cur_scan_md[doc["uid"]]["first_uid"]),
        )
        self._sample_rotation_angle = self._cur_scan_md[doc["uid"]]["rotation_angle"]

        js_str = self._cur_scan_md[doc["uid"]]["wdg_com"]
        #self._wdg_com = json.loads(js_str)

        # self._data_shape = self.get_data_shape()


        if self._start_found:
            raise RuntimeError(
                "The serializer in suitcase.nxstxm expects documents from one "
                "run only. Two `start` documents where sent to it"
            )
        else:
            self._start_found = True

    def get_scan_subtype(self):
        sp_ids = list(self._wdg_com['SPATIAL_ROIS'].keys())
        #use the first one as they should all be the same
        subtype = -1
        if len(sp_ids) > 0:
            subtype = self._wdg_com['SPATIAL_ROIS'][sp_ids[0]]['SCAN_PLUGIN']['SCAN_SUBTYPE']
        return subtype

    # def get_data_shape(self):
    #     """
    #     based on the scan parameters and scan type return the shape of the data,
    #     this should really be done at scan config time and passed in with the metadata
    #     """
    #     # get teh scan params based on scan type
    #     sp_roi = self._wdg_com['SINGLE_LST']['SP_ROIS'][0]
    #     #self._scan_type
    #     # single_2d_scans
    #     # focus_scans
    #     # multi_entry_scans
    #     shp = []
    #     if self._scan_type in (single_2d_scans or focus_scans or multi_entry_scans):
    #         shp = self.get_2D_image_data_shape(sp_roi)
    #
    #     #other scans here
    #
    #     return shp


    def get_2D_image_data_shape(self, sp_roi):
        """
        for scan types 6,
        """
        npts_x = sp_roi['X']['NPOINTS']
        npts_y = sp_roi['Y']['NPOINTS']
        npts_ev = sp_roi['EV_NPOINTS']
        return (npts_ev, npts_x, npts_y)





        #determine the shape of the data

        #return it as a list

    def return_initialized_data(self, shp):
        """
        take the desired shape of final data and create an array of nan's and return that array as a single dimensional list
        IS_PXP scan data will be 1D arrays, if LXL they will be multi D arrays
        """

        if len(shp) == 1:
            init_dat = np.full((shp[0]), np.nan)
        elif len(shp) == 2:
            if self._scan_subtype == IS_PXP:
                init_dat = np.full((shp[0] * shp[1]), np.nan)
            else:
                init_dat = np.full((shp[0] , shp[1]), np.nan)
        elif len(shp) == 3:
            if self._scan_subtype == IS_PXP:
                init_dat = np.full((shp[0] * shp[1] * shp[2]), np.nan)
            else:
                init_dat = np.full((shp[0], shp[1], shp[2]), np.nan)
        else:
            #most likely this is a baseline stream detector so give it 2 values for start and stop values
            init_dat = np.full((2), np.nan)

        #init_dat[:] = np.nan
        # init_dat[:] = -1

        return list(init_dat)

    # Custom function to add two elements, treating NaN as 0
    def add_with_nan_handling(self, x, y):
        """
        for use in elemental wise addition of two lists
        """
        if type(x) == list:
            if len(x) > 1:
                if np.isnan(np.array(x)).any():
                    x = np.nan_to_num(x, nan=0)
                    x = x.tolist()
        else:
            if np.isnan(x):
                x = 0

        if type(y) == list:
            if len(y) > 1:
                if np.isnan(np.array(y)).any():
                    y = np.nan_to_num(y, nan=0)
                    y = y.tolist()
        else:
            if np.isnan(y):
                y = 0
        return x + y

    def add_arrays(self, A_nans, B_nums):
        """
        A is the full size array of nans
        B is the array of actual data complete or not

        returns A padded with nan's if the complete data was not available
        """
        # Example arrays
        #A_nans = np.full(15, np.nan)  # array of 15 NaNs
        #B_nums = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])  # array of 11 integers
        num_B, = np.array(B_nums).shape
        A_nans = np.array(A_nans)

        # # Create a mask to identify NaN values in A
        # mask_15 = np.isnan(A_nans)

        # Overwrite NaN values in A with corresponding elements from B
        # A[mask_15] = B_nums[:mask_15.sum()]
        A_nans[:num_B] = B_nums[:num_B]
        #A_nans = np.reshape(A_nans, np.array(B_nums).shape)
        return A_nans

    def get_full_data_shape(self):
        """
        based on the scan type find out what the complete data shape is and return it as a list of values
        This way a complete data array can be initialized with nans then filled in with actual data, and if the data
        is incomplete the data will fill in the nan data array
        """
        sin_lst = self._wdg_com['SINGLE_LST']





    def descriptor(self, doc):
        """Use `descriptor` doc to map stream_names to descriptor uid's.

        This method usess the descriptor document information to map the
        stream_names to descriptor uid's.
        Parameters:
        -----------
        doc : dict
            EventDescriptor document
        """
        strm_name = doc["name"]
        self._data[strm_name] = {}
        num_pnts_shape = [self._cur_scan_md[self._cur_uid]['num_points']]
        for k, v in doc["data_keys"].items():
            if k.find('SIS3820') > -1:
                data_map = self._sis3820_data_map
                num_chans = len(data_map)
                for ch_num in range(num_chans):
                    ch_dct = data_map[ch_num]
                    self._data[strm_name][ch_dct['chan_nm']] = {}
                    self._data[strm_name][ch_dct['chan_nm']][self._cur_uid] = {}
                    self._data[strm_name][ch_dct['chan_nm']][self._cur_uid]["data"] = []
                    self._data[strm_name][ch_dct['chan_nm']][self._cur_uid]["info"] = v
                    # if strm_name.find('primary') > -1:
                    #     self._data[strm_name][ch_dct['chan_nm']][self._cur_uid][
                    #         "data_full_shape"] = self.return_initialized_data(v['shape'])
                    # else:
                    #self._data[strm_name][ch_dct['chan_nm']][self._cur_uid]["data_full_shape"] = self.return_initialized_data(v['shape'])
                    self._data[strm_name][ch_dct['chan_nm']][self._cur_uid]["data_full_shape"] = self.return_initialized_data(num_pnts_shape)
            else:

                self._data[strm_name][k] = {}
                self._data[strm_name][k][self._cur_uid] = {}
                self._data[strm_name][k][self._cur_uid]["data"] = []
                self._data[strm_name][k][self._cur_uid]["info"] = v

                if strm_name.find('primary') > -1:
                    self._data[strm_name][k][self._cur_uid]["data_full_shape"] = self.return_initialized_data(num_pnts_shape)
                else:
                    self._data[strm_name][k][self._cur_uid]["data_full_shape"] = self.return_initialized_data(
                        v['shape'])

        streamname = doc["name"]
        self._streamnames[doc["uid"]] = streamname

    def get_num_unique_channels(self, data_map):
        """
        look at self._sis3820_data_map and return the number of unique channel numbers
        """
        ch_nums = []
        for ch_dct in data_map:
            if ch_dct["chan_num"] not in ch_nums:
                ch_nums.append(ch_dct["chan_num"])
        return len(ch_nums)

    def is_multi_dimensional(self, lst):
        """
        Check if a list is multi-dimensional (contains nested lists).

        Args:
            lst (list): The list to check.

        Returns:
            bool: True if the list is multi-dimensional, False otherwise.
        """
        if not isinstance(lst, list):
            return False

        for item in lst:
            if isinstance(item, list):
                return True

        return False

    def event_page(self, doc):
        """Add event page document information to a ".csv" file.

        This method adds event_page document information to a ".csv" file,
        creating it if nesecary.

        .. warning::

            All non 1D 'tabular' data is explicitly ignored.

        .. note::

            The data in Events might be structured as an Event, an EventPage,
            or a "bulk event" (deprecated). The DocumentRouter base class takes
            care of first transforming the other repsentations into an
            EventPage and then routing them through here, so no further action
            is required in this class. We can assume we will always receive an
            EventPage.

        Parameters:
        -----------
        doc : dict
            EventPage document
        """
        if self._detector_names == None:
            self._detector_names = []
            self._det_strm_map = {}

        seq_num = doc['seq_num'][0] - 1
        strm_name = self._streamnames[doc["descriptor"]]
        strm_name = self._streamnames[doc["descriptor"]]
        for k in doc["data"].keys():
            if k in self._data[strm_name].keys() or k.find('SIS3820') > -1:
                if k.find('SIS3820') > -1:
                    # here create the locations to bust the SIS3820 data out from a single waveform into the individual enabled channels
                    data_map = self._sis3820_data_map
                    num_chans = self.get_num_unique_channels(data_map)
                    data_pkg = doc['data'][k][0]
                    if type(data_pkg) == dict:
                        #flyer LxL or PxP scan, all data stored in single event
                        for k,dat in data_pkg.items():
                            #self._data[strm_name][k][self._cur_uid]["data"].append(np.array(dat))
                            if len(dat) == 1:
                                #dereference this single value instead of appending a list of a single value
                                dat = dat[0]
                            self._data[strm_name][k][self._cur_uid]["data"].append(dat)
                            # init_val = self._data[strm_name][k][self._cur_uid]["data_full_shape"][seq_num]
                            # self._data[strm_name][k][self._cur_uid]["data_full_shape"][seq_num] = self.add_with_nan_handling(init_val, dat[0])

                            if strm_name.find("primary") > -1:
                                if k not in self._detector_names:
                                    self._detector_names.append(k)
                                    self._det_strm_map[k] = strm_name

                else:
                    dat = doc["data"][k][0]
                    self._data[strm_name][k][self._cur_uid]["data"].append(dat)
                    # init_val = self._data[strm_name][k][self._cur_uid]["data_full_shape"][seq_num]
                    # self._data[strm_name][k][self._cur_uid]["data_full_shape"][seq_num] = self.add_with_nan_handling(
                    #     init_val, dat)

                if strm_name.find("primary") > -1:
                    if k not in self._detector_names:
                        self._detector_names.append(k)
                        self._det_strm_map[k] = strm_name

        #result = list(map(add_with_nan_handling, list1, list2))

        event_model.verify_filled(doc)


    def _skip(self, mainstr, skip_list):
        """
        run through list of strings looking to see if the mainstr contains anything in the skip list
        if we find an occurance then return True
        :param mainstr:
        :param skip_list:
        :return:
        """
        ret = False
        for sl in skip_list:
            if mainstr.find(sl) > -1:
                return True

    def create_entry_structure(self, doc, scan_type):
        """
        :param doc:
        :param scan_type:
        :return:
        """

        _logger.info("creating [%s]" % self._entry_nm)
        if scan_types(scan_type) in single_entry_scans:
            self.save_single_entry_scan(doc, scan_type)
        # elif scan_types(scan_type) in spectra_type_scans:
        #     self.save_point_spec_entry_scan(doc, scan_type)
        elif scan_types(scan_type) is scan_types.SAMPLE_POINT_SPECTRUM:
            self.save_point_spec_entry_scan(doc, scan_type)
        else:
            self.save_multi_entry_scan(doc, scan_type)

    def create_file_attrs(self):
        nf = None
        try:
            nf = h5py.File(self._tmp_fname, "a")
            # set attrs foe the file
            _string_attr(nf, nxkd.NXD_HDF_VER, nxkd.HDF5_VER)
            _string_attr(nf, nxkd.NXD_H5PY_VER, h5py.__version__)
            _string_attr(nf, nxkd.NXD_NXPY_VER, nexpy.__version__)
            _string_attr(nf, nxkd.NXD_NX_VER, nxkd.NEXUS_VER)
            _string_attr(nf, nxkd.NXD_FILE_NAME, self._tmp_fname)
            _string_attr(nf, nxkd.NXD_FILE_TIME, self._file_time_str)
            _string_attr(nf, "scan_uid", self.get_current_uid())
            nf.close()

        except:
            _logger.error(
                "create_file_attrs: problem creating file [%s]" % self._tmp_fname
            )

    def save_single_entry_scan(self, doc, scan_type):
        """
        the main function to create the NXstxm file for scans that are NOT point spectra or multi entry
        :param doc:
        :param scan_type:
        :return:
        """
        nf = None
        try:
            nf = self._nf = h5py.File(self._tmp_fname, "a")

            # this entry name comes from metadata setup by scan plan
            entry_nxgrp = _group(nf, self._entry_nm, "NXentry")
            _string_attr(nf, "default", self._entry_nm)

            # # set attrs foe the file
            _dataset(entry_nxgrp, "title", "NeXus sample", "NX_CHAR")
            _dataset(entry_nxgrp, "start_time", self._start_time_str, "NX_DATE_TIME")
            _dataset(entry_nxgrp, "definition", "NXstxm", "NX_CHAR")
            _dataset(entry_nxgrp, "version", "1.0", "NX_CHAR")
            _string_attr(entry_nxgrp, "default", self._default_det)

            self.specific_scan_funcs = self.get_scan_specific_funcs(scan_type)

            # create entry groups
            self.create_collection_group(entry_nxgrp, doc, scan_type)

            ctrl_nxgrp = self.create_base_control_group(entry_nxgrp, doc, scan_type)
            self.specific_scan_funcs["mod_nxctrl"](self, ctrl_nxgrp, doc, scan_type)
            # data_nxgrp = self.create_base_nxdata_group(entry_nxgrp, self._detector_names, doc, scan_type)
            # self.specific_scan_funcs['mod_nxdata'](self, data_nxgrp, doc, scan_type)
            # self._detector_names = list(self._data["primary"].keys())
            data_nxgrps = self.create_base_nxdata_group(
                entry_nxgrp, self._detector_names, doc, scan_type
            )
            for dgrp in data_nxgrps:
                self.specific_scan_funcs["mod_nxdata"](self, dgrp, doc, scan_type)

            inst_nxgrp = self.create_base_instrument_group(entry_nxgrp, doc, scan_type)
            self.specific_scan_funcs["mod_nxinst"](self, inst_nxgrp, doc, scan_type)
            for det_nm in self._detector_names:
                self.create_base_instrument_detector(inst_nxgrp, det_nm, doc)

            self.create_base_sample_group(entry_nxgrp, doc, scan_type)

            nf.close()
        # except:
        #     print("save_single_entry_scan: Unexpected error:", sys.exc_info()[0])
        #     _logger.info("Problem saving file[%s]" % self._tmp_fname)
        #     if nf is not None:
        #         nf.close()
        #     os.rename(self._tmp_fname, self._tmp_fname + ".err")

        except Exception as e:
            print("save_single_entry_scan: Unexpected error:", sys.exc_info()[0])
            _logger.error("Problem saving file[%s]" % self._tmp_fname)
            print("Problem saving file[%s]" % self._tmp_fname)
            exception_type, exception_object, exception_traceback = sys.exc_info()
            filename = exception_traceback.tb_frame.f_code.co_filename
            line_number = exception_traceback.tb_lineno
            print("Exception type: ", exception_type)
            print("File name: ", filename)
            print("Line number: ", line_number)
            if nf is not None:
                nf.close()
            os.rename(self._tmp_fname, self._tmp_fname + ".err")

    def save_multi_entry_scan(self, doc, scan_type):
        """
        Multi entry means that the caller is processing multiple run_uids returned from the run engine, each of which
        is expected to be its own nxstxm entry in a single file
        :param doc:
        :param scan_type:
        :return:
        """
        nf = None
        try:
            nf = self._nf = h5py.File(self._tmp_fname, "a")

            # this entry name comes from metadata setup by scan plan
            # entry_nm = self._cur_scan_md[doc['run_start']]['entry_name']
            entry_nxgrp = _group(nf, self._entry_nm, "NXentry")
            _string_attr(nf, "default", self._entry_nm)

            # set attrs for the file
            _dataset(entry_nxgrp, "title", "NeXus sample", "NX_CHAR")
            _dataset(entry_nxgrp, "start_time", self._start_time_str, "NX_DATE_TIME")
            _dataset(entry_nxgrp, "definition", "NXstxm", "NX_CHAR")
            _dataset(entry_nxgrp, "version", "1.0", "NX_CHAR")
            _string_attr(entry_nxgrp, "default", self._default_det)

            self.specific_scan_funcs = self.get_scan_specific_funcs(scan_type)

            # create entry groups
            self.create_collection_group(entry_nxgrp, doc, scan_type)

            ctrl_nxgrp = self.create_stack_control_group(entry_nxgrp, doc, scan_type)
            self.specific_scan_funcs["mod_nxctrl"](self, ctrl_nxgrp, doc, scan_type)

            # data_nxgrp = self.create_stack_nxdata_group(entry_nxgrp, self._detector_names, doc, scan_type)
            # self.specific_scan_funcs['mod_nxdata'](self, data_nxgrp, doc, scan_type)
            #
            # inst_nxgrp = self.create_base_instrument_group(entry_nxgrp, doc, scan_type)
            # self.specific_scan_funcs['mod_nxinst'](self, inst_nxgrp, doc, scan_type)

            data_nxgrps = self.create_stack_nxdata_group(
                entry_nxgrp, self._detector_names, doc, self._scan_type
            )
            for dgrp in data_nxgrps:
                self.specific_scan_funcs["mod_nxdata"](self, dgrp, doc, scan_type)

            inst_nxgrp = self.create_base_instrument_group(entry_nxgrp, doc, scan_type)
            self.specific_scan_funcs["mod_nxinst"](self, inst_nxgrp, doc, scan_type)
            for det_nm in self._detector_names:
                self.create_base_instrument_detector(inst_nxgrp, det_nm, doc)

            #
            self.create_base_sample_group(entry_nxgrp, doc, scan_type)

            nf.close()
        except:
            print("save_multi_entry_scan: Unexpected error:", sys.exc_info()[0])
            raise
            print("Problem saving file[%s]" % self._tmp_fname)
            _logger.error("Problem saving file[%s]" % self._tmp_fname)
            if nf is not None:
                nf.close()
            os.rename(self._tmp_fname, self._tmp_fname + ".err")

    # def save_point_spec_entry_scan(self, doc, scan_type):
    #     '''
    #     the main function to create the point spectra type NXstxm file
    #     :param doc:
    #     :param scan_type:
    #     :return:
    #     '''
    #     nf = None
    #     try:
    #         self.specific_scan_funcs = self.get_scan_specific_funcs(self._scan_type)
    #         uid = self.get_current_uid()
    #         primary_det_nm = self.get_primary_det_nm(uid)
    #         prim_data_arr = np.array(self._data['primary'][primary_det_nm][uid]['data'])
    #         num_spids = len(self._sp_id_lst)
    #         coll_nxgrp = None
    #         nf = self._nf = h5py.File(self._tmp_fname, 'a')
    #
    #         i = 0
    #         for sp_id in self._sp_id_lst:
    #             self._cur_sp_id = sp_id
    #
    #             #all spid data is in one long array, get this sp_ids data by slicing every nth value
    #             data = prim_data_arr[i::num_spids]
    #
    #             entry_nxgrp = _group(nf, 'entry%s' % sp_id, 'NXentry')
    #
    #             # set attrs for the file
    #             _dataset(entry_nxgrp, 'title', 'NeXus sample', 'NX_CHAR')
    #             _dataset(entry_nxgrp, 'start_time', self._start_time_str, 'NX_DATE_TIME')
    #             _dataset(entry_nxgrp, 'end_time', self._stop_time_str, 'NX_DATE_TIME')
    #             _dataset(entry_nxgrp, 'definition', 'NXstxm', 'NX_CHAR')
    #             _dataset(entry_nxgrp, 'version', '1.0', 'NX_CHAR')
    #
    #             #create entry groups
    #             if (coll_nxgrp is None):
    #                 coll_nxgrp = self.create_collection_group(entry_nxgrp, doc, self._scan_type)
    #             else:
    #                 # just make a copy to recreate it
    #                 nf.copy(coll_nxgrp, entry_nxgrp)
    #
    #             ctrl_nxgrp = self.create_stack_control_group(entry_nxgrp, doc, self._scan_type)
    #             self.specific_scan_funcs['mod_nxctrl'](self, ctrl_nxgrp, doc, self._scan_type)
    #
    #             data_nxgrp = self.create_stack_nxdata_group(entry_nxgrp, self._detector_names, doc, self._scan_type)
    #             self.specific_scan_funcs['mod_nxdata'](self, data_nxgrp, doc, data, self._scan_type)
    #             #modify_spectra_nxdata_group(self, data_nxgrp, doc, data, self._scan_type)
    #
    #             inst_nxgrp = self.create_base_instrument_group(entry_nxgrp, doc, self._scan_type)
    #             self.specific_scan_funcs['mod_nxinst'](self, inst_nxgrp, doc, data, self._scan_type)
    #             #
    #             self.create_base_sample_group(entry_nxgrp, doc, self._scan_type)
    #             i += 1
    #
    #         nf.close()
    #     except:
    #         print("save_point_spec_entry_scan: Unexpected error:", sys.exc_info()[0])
    #         raise
    #         print('Problem saving file[%s]' % self._tmp_fname)
    #         _logger.error('Problem saving file[%s]' % self._tmp_fname)
    #         if(nf is not None):
    #             nf.close()
    #         os.rename(self._tmp_fname, self._tmp_fname + '.err')

    def get_spec_detnames_for_spatial_id(self, sp_id):
        """
        serach _detector_names and return the ones that specify the spatial id
        """
        nms = []
        for nm in self._detector_names:
            if nm.find(f"-spid-{sp_id}") > -1:
                nms.append(nm)
            if nm.find("RING_CURRENT") > -1:
                nms.append(nm)
        return nms


    def save_point_spec_entry_scan(self, doc, scan_type):
        """
        the main function to create the point spectra type NXstxm file
        :param doc:
        :param scan_type:
        :return:
        """
        nf = None
        try:



            self.specific_scan_funcs = self.get_scan_specific_funcs(self._scan_type)
            uid = self.get_current_uid()

            num_spids = len(self._sp_id_lst)
            coll_nxgrp = None
            nf = self._nf = h5py.File(self._tmp_fname, "a")

            i = 0
            self._sp_id_lst.sort()
            set_default_entry = False
            for sp_id in self._sp_id_lst:
                self._cur_sp_id = sp_id

                # all spid data is in one long array, get this sp_ids data by slicing every nth value
                # data = prim_data_arr[i::num_spids]

                entry_nxgrp = _group(nf, "entry%s" % sp_id, "NXentry")
                if not set_default_entry:
                    _string_attr(nf, "default", "entry%s" % sp_id)
                    set_default_entry = True

                # set attrs for the file
                _dataset(entry_nxgrp, "title", "NeXus sample", "NX_CHAR")
                _dataset(
                    entry_nxgrp, "start_time", self._start_time_str, "NX_DATE_TIME"
                )
                _dataset(entry_nxgrp, "definition", "NXstxm", "NX_CHAR")
                _dataset(entry_nxgrp, "version", "1.0", "NX_CHAR")
                #_string_attr(entry_nxgrp, "default", self._default_det)
                self._default_det = self._cur_scan_md[self._cur_uid]["default_entry_detectors"][str(sp_id)]
                _string_attr(entry_nxgrp, "default", self._default_det)

                # create entry groups
                if coll_nxgrp is None:
                    coll_nxgrp = self.create_collection_group(entry_nxgrp, doc, self._scan_type)
                else:
                    # just make a copy to recreate it
                    nf.copy(coll_nxgrp, entry_nxgrp)

                ctrl_nxgrp = self.create_stack_control_group(entry_nxgrp, doc, self._scan_type)
                self.specific_scan_funcs["mod_nxctrl"](self, ctrl_nxgrp, doc, self._scan_type )

                #create a data group for each detector
                spid_detnames = self.get_spec_detnames_for_spatial_id(sp_id)
                #data_nxgrps = self.create_stack_nxdata_group( entry_nxgrp, self._detector_names, doc, self._scan_type )
                data_nxgrps = self.create_stack_nxdata_group(entry_nxgrp, spid_detnames, doc, self._scan_type)
                for dgrp in data_nxgrps:
                    self.specific_scan_funcs["mod_nxdata"](self, dgrp, doc, scan_type)

                inst_nxgrp = self.create_base_instrument_group(
                    entry_nxgrp, doc, scan_type
                )
                self.specific_scan_funcs["mod_nxinst"](self, inst_nxgrp, doc, scan_type)
                for det_nm in spid_detnames:
                    self.create_base_instrument_detector(inst_nxgrp, det_nm, doc)

                #
                self.create_base_sample_group(entry_nxgrp, doc, self._scan_type)
                i += 1

            nf.close()
        except:
            print("save_point_spec_entry_scan: Unexpected error:", sys.exc_info()[0])
            raise
            print("Problem saving file[%s]" % self._tmp_fname)
            _logger.error("Problem saving file[%s]" % self._tmp_fname)
            if nf is not None:
                nf.close()
            os.rename(self._tmp_fname, self._tmp_fname + ".err")

    def get_scan_specific_funcs(self, scan_type):
        """
        using the scan-type that is specified, return a dict of functions that will be used be the data saving
        main routine

                'detector_image', \
				'osa_image', \
				'osa_focus', \
				'sample_focus', \
				'sample_point_spectrum', \
				'sample_line_spectrum', \
				'sample_image', \
				'sample_image_stack', \
				'generic_scan', \
				'coarse_image_scan', \
				'coarse_goni_scan', \
				'tomography_scan' , \
				'pattern_generator_scan'

        :param scan_type:
        :return:
        """

        dct = {}
        if scan_types(scan_type) is scan_types.GENERIC_SCAN:
            dct["mod_nxctrl"] = modify_generic_scan_ctrl_data_grps
            dct["mod_nxdata"] = modify_generic_scan_nxdata_group
            dct["mod_nxinst"] = modify_generic_scan_instrument_group

        elif scan_types(scan_type) in single_2d_scans:
            dct["mod_nxctrl"] = modify_2posner_ctrl_data_grps
            dct["mod_nxdata"] = modify_base_2d_nxdata_group
            dct["mod_nxinst"] = modify_base_2d_instrument_group

        elif scan_types(scan_type) in focus_scans:
            dct["mod_nxctrl"] = modify_focus_ctrl_data_grps
            dct["mod_nxdata"] = modify_focus_nxdata_group
            dct["mod_nxinst"] = modify_focus_instrument_group

        elif scan_types(scan_type) in single_image_scans:
            dct["mod_nxctrl"] = modify_single_image_ctrl_data_grps
            dct["mod_nxdata"] = modify_single_image_nxdata_group
            dct["mod_nxinst"] = modify_single_image_instrument_group

        elif scan_types(scan_type) in stack_type_scans:
            dct["mod_nxctrl"] = modify_stack_ctrl_data_grps
            dct["mod_nxdata"] = modify_stack_nxdata_group
            dct["mod_nxinst"] = modify_single_image_instrument_group

        elif scan_types(scan_type) in spectra_type_scans:
            dct["mod_nxctrl"] = modify_spectra_ctrl_data_grps
            dct["mod_nxdata"] = modify_spectra_nxdata_group
            dct["mod_nxinst"] = modify_spectra_instrument_group

        elif scan_types(scan_type) in line_spec_scans:
            dct["mod_nxdata"] = modify_line_spectra_nxdata_group
            dct["mod_nxctrl"] = modify_line_spectra_ctrl_data_grps
            dct["mod_nxinst"] = modify_line_spectra_instrument_group
        else:
            _logger.error("UNSUPPORTED SCAN_TYPE")

        return dct

    def get_current_uid(self):
        """
        gets the current uid
        :return:
        """
        return self._cur_uid

    def create_collection_group(self, nxgrp, doc, scan_type):
        """
        create an NXcollection group
        :param nxgrp:
        :param doc:
        :param scan_type:
        :return:
        """
        coll_nxgrp = _group(nxgrp, "collection", "NXcollection")
        scan_grp = _group(coll_nxgrp, "scan_request", "NXscanDefinition")
        js_str = self._cur_scan_md[doc["run_start"]]["wdg_com"]
        _dataset(scan_grp, "scan_request", js_str, "NXchar")
        # walk all of the baseline devices and create a MXsensor group entry in collection group
        nx_dct = readin_base_classes("NXsensor")
        for k, dct in self._data["baseline"].items():
            k = k.replace("_val", "")
            self.make_NXsensor(coll_nxgrp, k, dct[self._cur_uid], nx_dct=nx_dct)
        return coll_nxgrp

    def make_NXsensor(self, nxgrp, name, dct, nx_dct=None, modify=False):
        """
        create an signal based on the NXsensor group
        :param nxgrp:
        :param name:
        :param dct:
        :param modify:
        :return:
        """
        # try:
        # if ((not modify) or (nx_dct is None)):
        if nx_dct is None:
            nx_dct = readin_base_classes("NXsensor")

        if not modify:
            tmgrp = make_NXclass(nxgrp, name, "NXsensor", nx_dct["NXsensor"], nxgrp)
        else:
            tmgrp = nxgrp[name]

        # use the value of the signal at end of scan [1], [0] is the start of the scan
        tmgrp["value"][()] = dct["data"][1]
        # strip the 'PV:' off of the source name
        tmgrp["name"][()] = dct["info"]["source"].replace("PV:", "")
        # tmgrp['measurement'][()] = measurement
        tmgrp["short_name"][()] = dct["info"]["object_name"]
        tmgrp["type"][()] = dct["info"]["units"]
        tmgrp["run_control"][
            ()
        ] = 1  # Is data collection controlled or synchronised to this quantity: 1=no

        remove_unused_NXsensor_fields(tmgrp)

    def create_base_instrument_group(self, nxgrp, doc, scan_type):
        """
        create an NXinstrument group
        :param nxgrp:
        :param doc:
        :param scan_type:
        :return:
        """
        inst_nxgrp = _group(nxgrp, "instrument", "NXinstrument")
        self.make_source(inst_nxgrp, doc)
        self.make_monochromator(inst_nxgrp, doc, scan_type=scan_type)
        self.make_zoneplate(inst_nxgrp, doc)

        #epu_pol_src = self.get_devname("DNM_EPU_POLARIZATION", do_warn=False)
        epu_pol_src = "DNM_EPU_POLARIZATION"
        if epu_pol_src:
            # then EPU is supported
            self.make_epu(inst_nxgrp, doc)

        return inst_nxgrp

    def make_detector(self, nxgrp, name, data, dwell, npoints, units="counts"):
        """
        create an NXdetector group
        :param nxgrp:
        :param name:
        :param data:
        :param dwell:
        :param npoints:
        :return:
        """
        grp = _group(nxgrp, name, "NXdetector")
        if data is None:
            _dataset(
                grp, nxkd.NXD_DATA, np.zeros(npoints, dtype=np.float32), "NX_FLOAT"
            )
        else:
            _dataset(grp, nxkd.NXD_DATA, data, "NX_FLOAT")

        _dataset(grp, "count_time", make_1d_array(npoints, dwell), "NX_FLOAT")
        _dataset(grp, "unit", units, "NX_CHAR")

    def make_monochromator(self, nxgrp, doc, modify=False, scan_type=None):
        """
        create a NXmonochromator group
        :param data_dct:
        :param modify:
        :return:
        """
        rois = self.get_rois_from_current_md(doc["run_start"])
        xnpoints = int(dct_get(rois, SPDB_XNPOINTS))
        ynpoints = int(dct_get(rois, SPDB_YNPOINTS))
        zznpoints = dct_get(rois, SPDB_ZZNPOINTS)
        if scan_type is None:
            ttlpnts = xnpoints * ynpoints
        elif scan_types(scan_type) in focus_scans:
            # here Y is zoneplate Z and X is line_position
            ttlpnts = xnpoints * zznpoints
        elif scan_types(scan_type) in [
            scan_types.SAMPLE_LINE_SPECTRUM,
            scan_types.SAMPLE_POINT_SPECTRUM,
        ]:
            evs = dct_get(self._wdg_com, SPDB_SINGLE_LST_EV_ROIS)
            num_ev_points = len(evs)
            ttlpnts = num_ev_points * xnpoints
        elif scan_types(scan_type) is scan_types.GENERIC_SCAN:
            ttlpnts = xnpoints
        else:
            ttlpnts = xnpoints * ynpoints

        #epnts = self.get_baseline_all_data(self.get_devname("DNM_MONO_EV_FBK"))
        epnts = self.get_baseline_all_data("DNM_MONO_EV_FBK")
        # just use the value of energy at start
        epnt = epnts[0]
        e_arr = make_1d_array(ttlpnts, epnt)

        if modify:
            del nxgrp["monochromator"]["energy"]
            grp = nxgrp["monochromator"]
        else:
            grp = _group(nxgrp, "monochromator", "NXmonochromator")

        _dataset(grp, "energy", e_arr, "NX_FLOAT")

    def make_epu(self, nxgrp, doc, modify=False, pol_mode=0):
        """
        The epu polarization is a confusing situation, the implementation of the polarization number is an enumeration
        pol_mode refers to mode in the following definition

        def get_nx_standard_epu_mode(mode):
            Define polarization as either
                cir. right, point of view of source,
                cir. left, point of view of source, or
                linear. If the linear case is selected, there is an additional value in degrees for
                    the angle (number is meaningless if circular is chosen, or may not be filled in, I do not know).

            linear_lst = [2, 3, 4, 5]
            if (mode == 0):
                return (False, 'cir. left, point of view of source')
            elif (mode == 1):
                return (False, 'cir. right, point of view of source')
            elif (mode in linear_lst):
                return (True, 'linear')
            else:
                return (False, 'UNKNOWN')

        """
        rois = self.get_rois_from_current_md(doc["run_start"])
        xnpoints = rois["X"][NPOINTS]
        ynpoints = rois["Y"][NPOINTS]

        #ang = self.get_baseline_all_data(self.get_devname("DNM_EPU_ANGLE"))[0]
        ang = self.get_baseline_all_data("DNM_EPU_ANGLE")[0]
        ang_arr = make_1d_array(xnpoints * ynpoints, ang)
        #epu_gap_offset = self.get_baseline_all_data(self.get_devname("DNM_EPU_OFFSET"))[0]
        epu_gap_offset = self.get_baseline_all_data("DNM_EPU_OFFSET")[0]
        epu_gap_offset_arr = make_1d_array(xnpoints * ynpoints, epu_gap_offset)
        #epu_gap_fbk = self.get_baseline_all_data(self.get_devname("DNM_EPU_GAP"))[0]
        epu_gap_fbk = self.get_baseline_all_data("DNM_EPU_GAP")[0]
        epu_gap_fbk_arr = make_1d_array(xnpoints * ynpoints, epu_gap_fbk)
        epu_harm = int(
            #self.get_baseline_all_data(self.get_devname("DNM_EPU_HARMONIC"))[0]
            self.get_baseline_all_data("DNM_EPU_HARMONIC")[0]
        )
        epu_harm_arr = make_1d_array(xnpoints * ynpoints, epu_harm)

        # also get the stokes parameters for the pol_mode
        stokes = translate_pol_id_to_stokes_vector(pol_mode)

        (use_pol_angle, mode_str) = get_nx_standard_epu_mode(pol_mode)
        if use_pol_angle:
            pol_angle_arr = ang_arr
        else:
            pol_angle_arr = ang_arr

        epu_harmonic = get_nx_standard_epu_harmonic_new(epu_harm)

        if not modify:
            grp = _group(nxgrp, "epu", "NXinsertion_device")
            _dataset(grp, "type", "elliptically polarizing undulator", "NX_CHAR")
            _dataset(grp, "mode", mode_str, "NX_CHAR")
            _dataset(grp, "linear_inclined_angle", pol_angle_arr, "NX_ANGLE")
            _dataset(grp, "gap", epu_gap_fbk_arr, "NX_FLOAT", nx_units="NX_LENGTH")
            _dataset(
                grp, "gap_offset", epu_gap_offset_arr, "NX_FLOAT", nx_units="NX_LENGTH"
            )
            _dataset(grp, "harmonic", epu_harm_arr, "NX_INT", nx_units="NX_UNITLESS")

            _dataset(
                grp,
                "stokes",
                np.tile(stokes, (1, 1)),
                "NX_FLOAT",
                nx_units="NX_UNITLESS",
            )

    def make_zoneplate(self, nxgrp, doc, modify=False):
        """
        The fresnel zoneplate definition, only a subset of standard used because
        I don't not have all the info to populate all fields

        fields:
        central_stop_diameter:NX_FLOAT
                    central_stop_material:NX_CHAR
                  central_stop_thickness:NX_FLOAT
        fabrication:NX_CHAR
                  focus_parameters:NX_FLOAT[]
                  mask_material:NX_CHAR
                  mask_thickness:NX_FLOAT
        outer_diameter:NX_FLOAT
        outermost_zone_width:NX_FLOAT
                  support_membrane_material:NX_CHAR
                  support_membrane_thickness:NX_FLOAT
                  zone_height:NX_FLOAT
                  zone_material:NX_CHAR
                  zone_support_material:NX_CHAR
        """
        zp_def = self.get_stxm_zp_def(doc["run_start"])
        if not modify:
            grp = _group(nxgrp, "zoneplate", "NXfresnel_zone_plate")
            _dataset(grp, "name", "zone plate #%d" % zp_def["zp_idx"], "NX_CHAR")
            _dataset(
                grp, "outer_diameter", zp_def["zpD"], "NX_FLOAT", nx_units="NX_LENGTH"
            )
            _dataset(
                grp,
                "central_stop_diameter",
                zp_def["zpCStop"],
                "NX_FLOAT",
                nx_units="NX_LENGTH",
            )
            _dataset(
                grp,
                "outermost_zone_width",
                zp_def["zpOZone"],
                "NX_FLOAT",
                nx_units="NX_LENGTH",
            )
            _dataset(grp, "fabrication", "etched", "NX_CHAR")

    def make_source(self, nxgrp, doc, modify=False):
        """
        make an NXsource group
        :param nxgrp:
        :param data_dct:
        :param modify:
        :return:
        """
        if not modify:
            _sr_data = self.get_baseline_all_data("DNM_BASELINE_RING_CURRENT")
            rois = self.get_rois_from_current_md(doc["run_start"])
            # ring_cur_signame = self._cur_scan_md[self._cur_uid]['ring_current_nm']
            # if ring_cur_signame in self._data["baseline"].keys():
            #     rois = self.get_rois_from_current_md(doc["run_start"])
            #     # use the baseline start/stop values and create a sequence from start to stop
            #     # strt, stp = self._data['baseline'][ring_cur_signame][uid]['data']
            #     ring_data = self.get_baseline_all_data(ring_cur_signame)
            #     if type(ring_data) == list:
            #         strt = ring_data[0]
            #         stp = ring_data[-1]
            #     elif type(ring_data) == tuple:
            #         strt = ring_data[0]
            #         stp = ring_data[-1]
            #     else:
            #         print("make_source: ring data is not list or tuple")
            #         return
            #     #strt, stp = self.get_baseline_all_data(ring_cur_signame)
            #     sr_data = np.linspace(strt, stp, int(rois["X"][NPOINTS]), dtype=np.float32)
            # else:
            #     sr_data = np.array(
            #         self._data["primary"][ring_cur_signame]["data"], dtype=np.float32
            #     )
            sr_data = np.linspace(_sr_data[0], _sr_data[-1], int(rois["X"][NPOINTS]), dtype=np.float32)

            src_grp = _group(nxgrp, "source", "NXsource")
            _dataset(src_grp, "type", "Synchrotron X-ray Source", "NX_CHAR")
            _dataset(src_grp, "name", "Canadian Lightsource Inc.", "NX_CHAR")
            _dataset(src_grp, "probe", "x-ray", "NX_CHAR")
            _dataset(src_grp, "current", sr_data, "NX_FLOAT", "NX_CURRENT")

        else:
            # nothing to modify
            pass

    def get_devname(self, lu_nm, do_warn=False):
        """
        get the device name using the reverse lookup dict
        :param lu_nm:
        :return:
        """
        md = self._cur_scan_md[self._cur_uid]
        if lu_nm in md["rev_lu_dct"].keys():
            return md["rev_lu_dct"][lu_nm]
        else:
            if do_warn:
                _logger.warn(
                    "nxstxm_primary: get_devname: cannot find [%s] in current scan metadata"
                    % lu_nm
                )
            return lu_nm

    def get_baseline_start_data(self, src_nm):
        """
        the baseline data strem contains 2 values per device one for start and one for stop
        this returns the start value
        check to see if name exists in baseline stream, if not try the DNM_version of the name
        :param src_nm: this is the DNM_ version of the device name, ex: for energy DNM_ENERGY but actual device is BL1610-3-01:ENERGY
        :return:
        """
        dev_nm = self.get_devname(src_nm)
        if dev_nm not in self._data["baseline"].keys():
            #the actual device name doesnt exists so try the DNM_ version of teh name
            dev_nm = src_nm
        return self._data["baseline"][dev_nm][self._cur_uid]["data"][0]

    def get_baseline_stop_data(self, src_nm):
        """
        the baseline data strem contains 2 values per device one for start and one for stop
        this returns the stop value
        :param src_nm:
        :return:
        """
        dev_nm = self.get_devname(src_nm)
        if dev_nm not in self._data["baseline"].keys():
            #the actual device name doesnt exists so try the DNM_ version of teh name
            dev_nm = src_nm
        return self._data["baseline"][dev_nm][self._cur_uid]["data"][1]

    def get_baseline_all_data(self, src_nm):
        """
        the baseline data stream contains 2 values per device one for start and one for stop
        this returns all values
        :param src_nm:
        :return:
        """
        dev_nm = self.get_devname(src_nm)
        if dev_nm not in self._data["baseline"].keys():
            # the actual device name doesnt exists so try the DNM_ version of teh name
            dev_nm = src_nm
        #return self._data["baseline"][dev_nm][self._cur_uid]["data"]
        return self._data["baseline"][dev_nm][self._cur_uid]["data_full_shape"]

    def get_primary_all_data(self, src_nm):
        """
        the primary data stream contains 2 values per device one for start and one for stop
        this returns all values
        :param src_nm:
        :return:
        """
        dev_nm = self.get_devname(src_nm)
        if dev_nm not in self._data["primary"].keys():
            # the actual device name doesnt exists so try the DNM_ version of teh name
            dev_nm = src_nm
        #return self._data["primary"][dev_nm][self._cur_uid]["data"]
        return self._data["primary"][dev_nm][self._cur_uid]["data_full_shape"]

    def get_sample_x_data(self, _type="all"):
        """
        gets data from baseline stream
        _type can be 'all, or 'start', or 'stop'
        :param _type:
        :return:
        """
        #x_src = self.get_devname('DNM_SAMPLE_X')
        x_src = "DNM_SAMPLE_X"
        if _type == "all":
            return self.get_baseline_all_data(x_src)
        elif _type == "start":
            return self.get_baseline_start_data(x_src)
        elif _type == "stop":
            return self.get_baseline_stop_data(x_src)
        else:
            return None

    def get_sample_y_data(self, _type="all"):
        """
        gets data from baseline stream
        _type can be 'all, or 'start', or 'stop'
        :param _type:
        :return:
        """
        #y_src = self.get_devname('DNM_SAMPLE_Y')
        y_src = "DNM_SAMPLE_Y"
        if _type == "all":
            return self.get_baseline_all_data(y_src)
        elif _type == "start":
            return self.get_baseline_start_data(y_src)
        elif _type == "stop":
            return self.get_baseline_stop_data(y_src)
        else:
            return None

    def create_base_control_group(self, entry_nxgrp, doc, scan_type):
        """
        create a standard (non stack) NXcontrol group
        :param entry_nxgrp:
        :param doc:
        :param scan_type:
        :return:
        """
        cntrl_nxgrp = _group(entry_nxgrp, "control", "NXmonitor")
        #ev_src = self.get_devname("DNM_ENERGY")
        ev_src = "DNM_ENERGY"

        # we are not sure if the facility has an EPU
        #epu_pol_src = self.get_devname("DNM_EPU_POLARIZATION", do_warn=False)
        epu_pol_src = "DNM_EPU_POLARIZATION"
        if epu_pol_src:
            # then EPU is supported
            #epu_offset_src = self.get_devname("DNM_EPU_OFFSET")
            epu_offset_src = "DNM_EPU_OFFSET"
            _dataset(
                cntrl_nxgrp,
                nxkd.EPU_OFFSET,
                [self.get_baseline_start_data(epu_offset_src)],
                "NX_FLOAT",
            )
            _dataset(
                cntrl_nxgrp,
                nxkd.EPU_POLARIZATION,
                [self.get_baseline_start_data(epu_pol_src)],
                "NX_FLOAT",
            )

        _dataset(
            cntrl_nxgrp, "energy", [self.get_baseline_start_data(ev_src)], "NX_FLOAT"
        )
        _dataset(
            cntrl_nxgrp, nxkd.SAMPLE_X, self.get_sample_x_data("start"), "NX_FLOAT"
        )
        _dataset(
            cntrl_nxgrp, nxkd.SAMPLE_Y, self.get_sample_y_data("start"), "NX_FLOAT"
        )

        #the group named data will be added by the specific scan type functions called after this one
        _string_attr(cntrl_nxgrp, "signal", "data")
        return cntrl_nxgrp

    def create_stack_control_group(self, entry_nxgrp, doc, scan_type):
        """
            creates a stack NXcontrol group
        :param entry_nxgrp:
        :param doc:
        :param scan_type:
        :return:
        """
        cntrl_nxgrp = _group(entry_nxgrp, "control", "NXmonitor")

        ev_setpoints = self._wdg_com["SINGLE_LST"]["EV_ROIS"]
        _dataset(cntrl_nxgrp, "energy", ev_setpoints, "NX_FLOAT")
        _dataset(
            cntrl_nxgrp, nxkd.SAMPLE_X, self.get_sample_x_data("start"), "NX_FLOAT"
        )
        _dataset(
            cntrl_nxgrp, nxkd.SAMPLE_Y, self.get_sample_y_data("start"), "NX_FLOAT"
        )

        _string_attr(cntrl_nxgrp, "signal", "data")
        return cntrl_nxgrp

    def interpolate_data_from_endpoints(self, arr, npoints):
        """
        given an array use the first and last values and return a linearly interpolated array of npoints between them
        """
        strt = arr[0]
        stp = arr[-1]
        interp_data = np.linspace(strt, stp, npoints, dtype=np.float32)
        return(interp_data)

    def fix_aborted_data(self, data_lst, npoints):
        """
        if the scan was aborted then we have fewer data points than we expected, create a square array the size
        of that we were expecting and copy the datapoints we did get into it
        :param data_lst:
        :param npoints:
        :return:
        """
        zarr = np.zeros(npoints, dtype=np.float32)
        #zarr = np.full(npoints, np.nan)
        darr = np.array(data_lst, dtype=np.float32)
        if darr.ndim == 2:
            # turn 2D into a 1D array
            darr = darr.ravel()
        c = zarr.copy()
        c[:darr.size] = darr
        return c

    def fix_posner_nm(self, nm_str):
        """
        fix the positioner names to replace . with _
        :param nm_str:
        :return:
        """
        l = nm_str.lower()
        l = l.replace(".", "_")
        return l

    def get_rois_from_current_md(self, uid):
        """
        convienience function, get the regions of interest dicts, assumes self._cur_sp_id has been set
        :param uid:
        :return:
        """
        rois = self._cur_scan_md[uid]["rois"][str(self._cur_sp_id)]
        return rois

    def create_base_instrument_detector(self, inst_nxgrp, det_nm, doc):
        """

        :param nxgrp:
        :param doc:
        :param scan_type:
        :return:
        """
        rois = self.get_rois_from_current_md(doc["run_start"])
        dwell = self._cur_scan_md[doc["run_start"]]["dwell"] * 0.001
        scan_type = self.get_stxm_scan_type(doc["run_start"])
        uid = self.get_current_uid()
        det_stream = self._det_strm_map[det_nm]
        ttlpnts = int(rois[SPDB_X][NPOINTS] * rois[SPDB_Y][NPOINTS])
        if scan_type == scan_types.SAMPLE_POINT_SPECTRUM.value:
            # need to slice the 1d array data into num spatial ids
            if det_nm not in self._data[det_stream].keys():
                det_data = np.array(
                    self._data["baseline"][det_nm][uid]["data"][:: len(self._sp_id_lst)]
                )  # .reshape((ynpoints, xnpoints))
            else:
                det_data = np.array(
                    self._data[det_stream][det_nm][uid]["data"][:: len(self._sp_id_lst)]
                )  # .reshape((ynpoints, xnpoints))
        else:
            # take teh entire 1d array
            if det_nm not in self._data[det_stream].keys():
                det_data = np.array(self._data["baseline"][det_nm][uid]["data"])
            else:
                det_data = np.array(self._data[det_stream][det_nm][uid]["data"])
        self.make_detector(inst_nxgrp, det_nm, det_data, dwell, ttlpnts, units="counts")

    def create_base_nxdata_group(self, entry_nxgrp, cntr_nm_lst, doc, scan_type):
        """
        create a standard (non stack) NXdata group, one for each counter name in the counter name list
        :param entry_nxgrp:
        :param cntr_nm:
        :param doc:
        :param scan_type:
        :return:
        """
        dgrps = []
        for cntr_nm in cntr_nm_lst:
            resize_data = False
            data_nxgrp = _group(entry_nxgrp, cntr_nm, "NXdata")
            dgrps.append(data_nxgrp)
            rois = self.get_rois_from_current_md(doc["run_start"])
            xnpoints = int(dct_get(rois, SPDB_XNPOINTS))
            xdata = np.array(dct_get(rois, SPDB_XSETPOINTS), dtype=np.float32)
            ydata = np.array(dct_get(rois, SPDB_YSETPOINTS), dtype=np.float32)
            # make sure dwell is in seconds
            dwell = np.float32(self._cur_scan_md[doc["run_start"]]["dwell"]) * 0.001
            if "SINGLE_LST" not in self._wdg_com.keys():
                spid = list(self._wdg_com["SPATIAL_ROIS"].keys())[0]
                ev_setpoints = []
                for ev_roi in self._wdg_com["SPATIAL_ROIS"][spid]["EV_ROIS"]:
                    ev_setpoints += ev_roi[SETPOINTS]
            else:
                ev_setpoints = self._wdg_com["SINGLE_LST"]["EV_ROIS"]

            num_ev_points = len(ev_setpoints)
            if num_ev_points < 1:
                num_ev_points = 1
            _dataset(
                data_nxgrp,
                "count_time",
                make_1d_array(num_ev_points, dwell),
                "NX_FLOAT",
            )

            #ev_src = self.get_devname("DNM_ENERGY")
            ev_src = "DNM_ENERGY"
            _dataset(
                data_nxgrp, "energy", [self.get_baseline_start_data(ev_src)], "NX_FLOAT"
            )
            _dataset(data_nxgrp, nxkd.SAMPLE_X, xdata, "NX_FLOAT")
            _dataset(data_nxgrp, nxkd.SAMPLE_Y, ydata, "NX_FLOAT")

            # pol_src = self.get_devname(DNM_EPU_POLARIZATION, do_warn=False)
            # if (pol_src):
            #     _dataset(data_nxgrp, 'epu_polarization', self.get_baseline_start_data(pol_src), 'NX_FLOAT')
            #epu_pol_src = self.get_devname("DNM_EPU_POLARIZATION", do_warn=False)
            epu_pol_src = "DNM_EPU_POLARIZATION"
            if epu_pol_src:
                # then EPU is supported
                #epu_offset_src = self.get_devname("DNM_EPU_OFFSET")
                epu_offset_src = "DNM_EPU_OFFSET"
                _dataset(
                    data_nxgrp,
                    nxkd.EPU_OFFSET,
                    [self.get_baseline_start_data(epu_offset_src)],
                    "NX_FLOAT",
                )
                _dataset(
                    data_nxgrp,
                    nxkd.EPU_POLARIZATION,
                    [self.get_baseline_start_data(epu_pol_src)],
                    "NX_FLOAT",
                )

            scan_type_str = self.get_stxm_scan_type_str(doc["run_start"])
            _dataset(data_nxgrp, "stxm_scan_type", scan_type_str, "NX_CHAR")

        return dgrps

    def create_stack_nxdata_group(self, entry_nxgrp, cntr_nm_lst, doc, scan_type):
        """
        create a sample image stack NXdata group
        :param entry_nxgrp:
        :param cntr_nm:
        :param doc:
        :param scan_type:
        :return:
        """
        resize_data = False
        dgrps = []
        for cntr_nm in cntr_nm_lst:
            data_nxgrp = _group(entry_nxgrp, cntr_nm, "NXdata")
            dgrps.append(data_nxgrp)
            # make sure dwell is in seconds
            dwell = np.float32(self._cur_scan_md[doc["run_start"]]["dwell"]) * 0.001
            ev_setpoints = self._wdg_com["SINGLE_LST"]["EV_ROIS"]
            num_ev_points = len(ev_setpoints)
            _dataset(
                data_nxgrp,
                "count_time",
                make_1d_array(num_ev_points, dwell),
                "NX_FLOAT",
            )
            _dataset(data_nxgrp, "energy", ev_setpoints, "NX_FLOAT")
            _dataset(
                data_nxgrp, nxkd.SAMPLE_X, self.get_sample_x_data("start"), "NX_FLOAT"
            )
            _dataset(
                data_nxgrp, nxkd.SAMPLE_Y, self.get_sample_y_data("start"), "NX_FLOAT"
            )

            # pol_src = self.get_devname(DNM_EPU_POLARIZATION, do_warn=False)
            # if (pol_src):
            #     _dataset(data_nxgrp, 'epu_polarization', self.get_baseline_start_data(pol_src), 'NX_FLOAT')
            #epu_pol_src = self.get_devname("DNM_EPU_POLARIZATION", do_warn=False)
            epu_pol_src = "DNM_EPU_POLARIZATION"
            if epu_pol_src:
                # then EPU is supported
                #epu_offset_src = self.get_devname("DNM_EPU_OFFSET")
                epu_offset_src = "DNM_EPU_OFFSET"
                _dataset(
                    data_nxgrp,
                    nxkd.EPU_OFFSET,
                    [self.get_baseline_start_data(epu_offset_src)],
                    "NX_FLOAT",
                )
                _dataset(
                    data_nxgrp,
                    nxkd.EPU_POLARIZATION,
                    [self.get_baseline_start_data(epu_pol_src)],
                    "NX_FLOAT",
                )

            scan_type_str = self.get_stxm_scan_type_str(doc["run_start"])
            _dataset(data_nxgrp, "stxm_scan_type", scan_type_str, "NX_CHAR")

        return dgrps

    def get_stxm_scan_type_str(self, uid):
        """
        get the scant type as a string from the metadata
        :param uid:
        :return:
        """
        scan_type = self._cur_scan_md[uid]["scan_type"]
        if scan_types(scan_type) in sample_image_filetypes:
            s = scan_types(scan_types.SAMPLE_IMAGE).name.replace("_", " ")
        else:
            s = scan_types(scan_type).name.replace("_", " ")
        return s.lower()

    def get_stxm_scan_type(self, uid):
        """
        get the scan type from the metadata
        :param uid:
        :return:
        """
        scan_type = self._cur_scan_md[uid]["scan_type"]
        return scan_type

    def get_stxm_zp_def(self, uid):
        """
        get the zoneplate definition from the metadata
        :param uid:
        :return:
        """
        zp_def = self._cur_scan_md[uid]["zp_def"]
        return zp_def

    def create_base_sample_group(self, entry_nxgrp, doc, scan_type):
        """
            self._sample_rotation_angle is set in 'start' doc and is pulled from the standard metadata dict that was passed in from pyStxm
        :param entry_nxgrp:
        :param doc:
        :param scan_type:
        :return:
        """
        smpl_nxgrp = _group(entry_nxgrp, "sample", "NXsample")
        _dataset(smpl_nxgrp, "rotation_angle", self._sample_rotation_angle, "NX_FLOAT")

    def get_primary_det_nm(self, uid):
        """
        get the primary detector name
        :return:
        """
        if "primary_det" not in self._cur_scan_md[uid].keys():
            _logger.error(
                "get_primary_det_nm: looks like a prefix for the primary detector was not specified in the plan metadata"
            )
            return None

        primary_dets = self._cur_scan_md[uid]["primary_det"]
        for k in self._data["primary"].keys():
            if k.find(primary_det_prefix) > -1:
                return k

        # the plan specified a primary_det in its plan metadata but then didnt include it in the primary data stream
        _logger.error(
            f"get_primary_det_nm: the plan specified a primary_det [{primary_det_prefix}] in its plan metadata but then didnt include it in the primary data stream"
        )
        return None

    def get_nxgrp_det_name(selfself, nxgrp):
        """
        data_nxgrp
        """
        return(nxgrp.name.split("/")[-1])

    def get_primary_stream_detector_names(self, uid):
        """
        convienience function to return the detector prefix specified in the metadata as the primary
        :param uid:
        :return:
        """
        return self._detector_names
        #return self._cur_scan_md[uid]["primary_det"]

    def make_devs(self, nf, dev_dct):
        """
        make a device entry
        :param nf:
        :param dev_dct:
        :return:
        """
        for dev_nm, data in dev_dct.items():
            # info = dev['info']
            _grp = _group(nf, dev_nm, "none")
            _string_attr(_grp, "PVNAME", dev_nm)
            if dev_nm.find("description") == -1:
                _dataset(_grp, "data", data, "number")

    def return_dct_of_this_field_and_val(self, dct, field, val):
        """
        search through dict looking for the keys that has this field and value
        then return key"""
        res = {}
        for k in list(dct.keys()):
            f_keys = list(dct[k]["info"].keys())
            if field in f_keys:
                if val == dct[k]["info"][field]:
                    res[k] = dct[k]
        return res

    def stop(self, doc):
        """Add `stop` document information to the metadata dictionary.
                This method adds the stop document information to the metadata
                dictionary. In addition it also creates the metadata '.json' file and
                exports the metadata dictionary to it.
                Parameters:
                -----------
                doc : dict
                    RunStop document

                    {'run_start': 'f66a3e61-dcbb-4975-9fc8-c38a0255fb1b',
                     'time': 1552058010.90581,
                     'uid': '9aa11d7a-4edd-4c8d-9a7d-b82fcf92fdfb',
                     'exit_status': 'success',
                     'num_events': {'oranges': 101}}

                     scan_types =
                        'detector_image', \
                        'osa_image', \
                        'osa_focus', \
                        'sample_focus', \
                        'sample_point_spectrum', \
                        'sample_line_spectrum', \
                        'sample_image', \
                        'sample_image_stack', \
                        'generic_scan', \
                        'coarse_image_scan', \
                        'coarse_goni_scan', \
                        'tomography_scan', \
                        'pattern_gen_scan'


                """
        # add the stop doc to self._meta.
        try:
            print("suitcase-nxstm: stop", doc)
            if "time" not in doc.keys():
                print("WHATS wrong with this stop doc? leaving")
                return

            scan_type = self._cur_scan_md[doc["run_start"]]["scan_type"]

            dets = {}
            skip_list = ["_units"]
            if "primary" not in list(self._data.keys()):
                # if the scan was aborted/stopped midway there is likely not going to be a primary data stream for the scan
                # iteration that the scan was on, so just skip it so we can save whatever data we have
                print('stop: scan was aborted because no primary datastream exists therefore there is no way to save anything')
                _logger.error('stop: scan was aborted because no primary datastream exists therefore there is no way to save anything')
                return

            if doc["uid"] in self._streamnames.keys():
                streamname = self._streamnames[doc["uid"]]
            else:
                pass

            has_baseline = False
            streams = []
            for k, v in self._streamnames.items():
                streams.append(v)
                if v.find("baseline") > -1:
                    has_baseline = True

            if self._cur_scan_md[doc["run_start"]]["first_uid"] == self._cur_uid:
                if not os.path.exists(self._tmp_fname):
                    self.create_file_attrs()

            #make data final in case the scan was aborted
            for strm_name in streams:
                strm_keys = list(self._data[strm_name].keys())
                for k in strm_keys:
                    shp = self._data[strm_name][k][self._cur_uid]['info']['shape']
                    do_reshape = True
                    if len(shp) == 0:
                        #shp = [self._cur_scan_md[self._cur_uid]['num_points']]
                        do_reshape = False
                    A_nans = self._data[strm_name][k][self._cur_uid]["data_full_shape"]
                    B_nums = self._data[strm_name][k][self._cur_uid]["data"]
                    # data = self.add_arrays(A_nans, B_nums)
                    # if do_reshape:
                    #     data = np.reshape(data, shp)
                    # self._data[strm_name][k][self._cur_uid]["data_full_shape"] = data
                    self._data[strm_name][k][self._cur_uid]["data_full_shape"] = B_nums

            if has_baseline:
                self.create_entry_structure(doc, scan_type=scan_type)
                self._processed_sp_ids.append(self._sp_id)
            else:
                # this is an ev only run so just update the data
                # print('modifying data to an existing entry')
                uid = self.get_current_uid()
                if len(self._detector_names) > 0:
                    for det_nm in self._detector_names:
                        dat_arr = np.array(self._data["primary"][det_nm][uid]["data"])
                        # now place it in correct entry/counter/data
                        self.modify_entry_data(self._entry_nm, det_nm, dat_arr)

            if self._cur_uid == self._cur_scan_md[doc["run_start"]]["last_uid"]:
                stop_time = localtime(doc["time"])
                _stop_time_str = time.strftime("%Y-%m-%dT%H:%M:%S", stop_time)
                nf = h5py.File(self._tmp_fname, "a")
                #make sure that the end_time is set for all entry's
                for ekey in nf.keys():
                    if ekey.find("entry") > -1:
                        _dataset(nf[ekey], "end_time", _stop_time_str, "NX_DATE_TIME")


            # reset scan_type
            self._scan_type = None
            print("suitcase-nxstxm: leaving stop function")

        except:
            print("stop: ERROR")
            _logger.error("Problem modifying data in [%s]" % self._tmp_fname)

    def modify_entry_data(self, entry_nm, det_prfx, data):
        nf = None
        try:
            nf = h5py.File(self._tmp_fname, "a")

            if entry_nm in nf.keys():
                # the entry exists
                egrp = nf[entry_nm]

                if det_prfx in egrp.keys():
                    # the NXdata counter exists
                    cntr_data = egrp[det_prfx]

                    # add the data
                    # print('add the data here for e_idx=%d' % self._e_idx)
                    cntr_data["data"][self._e_idx] = data

                else:
                    _logger.error(
                        "[%s] NXdata group doesnt exist in [%s]" % (det_prfx, entry_nm)
                    )

            else:
                _logger.error(
                    "[%s] NXentry group doesnt exist in file [%s]"
                    % (entry_nm, self._tmp_fname)
                )

            nf.close()

        except:
            _logger.error("Problem modifying data in [%s]" % self._tmp_fname)
            if nf is not None:
                nf.close()
            os.rename(self._tmp_fname, self._tmp_fname + ".err")
