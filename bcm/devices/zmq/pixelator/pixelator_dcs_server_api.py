import time
import os
from PyQt5.QtCore import QTimer
from queue import Queue
import re
import simplejson as json


from bcm.devices.zmq.base_dcs_server_api import BaseDcsServerApi
from bcm.devices.zmq.pixelator.gen_scan_req import GenScanRequestClass
from bcm.devices.zmq.pixelator.scan_reqs.req_substitution import do_substitutions
from bcm.devices.zmq.pixelator.loadfile_reponse import LoadFileResponseClass
from cls.utils.roi_utils import *
from cls.utils.dict_utils import dct_get
from cls.utils.fileUtils import get_file_path_as_parts
from cls.types.stxmTypes import (
    scan_types,
)


from cls.utils.log import get_module_logger
_logger = get_module_logger(__name__)

class ScanStatus(Enum):
    IDLE = 0
    RUNNING = 1
    PAUSED = 2

class SpatialType(Enum):
    image = 0
    line = 1
    point = 2

class ScanType(Enum):
    IMAGE = 0
    POINT_SPEC = 1
    LINE_SPEC = 2


def gen_non_tiled_map(num_blocks, arr_npoints, npoints_x):
    dct = {}
    for block_idx in range(num_blocks):
        dct[block_idx] = gen_non_tiled_map_entry(block_idx, arr_npoints, npoints_x)
    return dct

def gen_non_tiled_map_entry(sdInnerRegionIdx, arr_npoints, npoints_x):
    # npoints_x = Number of pixels each data array represents
    # Calculate the starting pixel index in the 1D image representation
    starting_pixel_index = sdInnerRegionIdx * arr_npoints

    # Calculate the grid locations for all 20 points
    #pixel_positions = []
    pixel_row = (starting_pixel_index + 0) // npoints_x
    pixel_col = (starting_pixel_index + 0) % npoints_x
    return {'row': pixel_row, 'col': pixel_col}



RE_DATA_DIR_PATTERN = r'^\d{4}-\d{2}-\d{2}$'

def gen_loadfile_directory_msg(directory: str, extension: str='.hdf5') -> dict:
    dct = {"directory":f"{directory}",
           "showHidden":1,
           "fileExtension":f"{extension}"
,   }
    return dct

def gen_listDirectory_msg(directory: str, extension: str='.hdf5') -> dict:
    dct = {"directory":f"{directory}",
           "fileExtension": f"{extension}"
,   }
    return dct


def gen_loadfile_msg(directory: str, filename: str) -> dict:
    dct = {
        "directory": f"{directory}"
        , "file": os.path.join(directory, filename)
        , "showHidden": 0
        , "fileExtension": ".hdf5"
        , "directories": [
            ".."
            , "discard"
        ]
        , "files": [
            filename
        ]
        , "pluginNumber": 0
    }
    return dct


class ScanClass(object):
    def __init__(self, *, dcs_server_api=None):
        super().__init__()
        self.dcs_server_api = dcs_server_api
        self.x = {} # x
        self.y = {} # y
        self.z = {} # z
        self.zp = {}  # zp
        self.e = [] # energy regions
        self.p = [] # polarization regions
        self.dwell_ms = 1
        self.num_images = 0
        self.scan_pxp = True # default
        self.status = ScanStatus.IDLE
        self.scan_type_str = 'OSA'
        self.scan_req = {}
        self.spatial_type = "Image"  # Line, Point
        self.wdg_com = {}
        self.wdg_scan_req = {}
        self.sp_roi_dct = {}
        self.sp_ids = None
        self.paused = False

        #pulled from sls_focus.py
        self.tile_shapes = []
        self.scan_shape = None
        self.scan_extent = None
        self.scan_data = None
        self.scan_axis_titles = None
        self.sample_scan_type = ScanType.IMAGE  # default
        # self.scan_data = np.full([10,10],np.nan)
        self.image_buffer = None
        self.tiled_map = {}
        self.non_tiled_map = {}
        self.npoints_rows = 0
        self.npoints_cols = 1
        self.num_inner_regions = 0
        self.num_outer_regions = 0
        self._scan_line_data_cntr = 0
        self.ttl_points_received = 0
        self._total_num_points = 1
        self.cur_col_idx = None
        self.cur_tile_num = 0

    def reset(self):
        """
        reset all member vars to init state
        """

        self.scan_req = {}
        self.x = {}  # x
        self.y = {}  # y
        self.z = {}  # z
        self.zp = {}  # zp
        self.t = {}  # theta
        self.e = []  # energy regions
        self.p = []  # polarization regions
        self.dwell_ms = 1
        self.num_images = 0
        self.scan_pxp = True  # default
        self.status = ScanStatus.IDLE
        self.wdg_scan_req = {}
        self.tile_shapes = []
        self.scan_shape = None
        self.scan_extent = None
        self.scan_data = None
        self.scan_axis_titles = None
        # self.scan_data = np.full([10,10],np.nan)
        self.image_buffer = None
        self.tiling = False
        self.tiled_map = {}
        self.non_tiled_map = {}
        self.npoints_rows = 0
        self.npoints_cols = 1
        self.num_inner_regions = 0
        self.num_outer_regions = 0
        self.ttl_points_received = 0
        self._total_num_points = 1
        self.cur_img_points_received = 0
        self.cur_col_idx = None
        self.cur_tile_num = 0
        self.wdg_com = {}

    def map_app_polarization_to_dcs_polarization(self, pol: str) -> []:
        """
        convert a pyStxm string for polarization to stokes parameters required by Pixelator
        """
        map = {}
        map['circ. left'] = [0,0,-1]
        map['circ. right'] = [0, 0, 1]
        map['linear'] = [1, 0, 0]
        map['eliptical'] = [None, None, None]

        pol_dct = {}
        pol_dct["active"] = 1
        pol_dct["types"] = []
        pol_dct["stokes"] = []

        if pol in map.keys():
            pol_dct["active"] = 1
            pol_dct["types"] = [pol]
            pol_dct["stokes"] = map[pol]

            return pol_dct

        else:
            print(f"Polarization {pol} not supported by Pixelator")
            return None

    def convert_positioner_name(self, posner_nm ):
        """
        this should also convert the pyStxm positioner name ot one pixelator knows
        Parameters
        ----------
        posner_nm

        Returns
        -------

        """

        nm = posner_nm.replace('DNM_','')
        nm = nm.replace('_','')
        return nm

    def map_app_scan_name_to_dcs_scan_name(self, app_scan_name):
        """
        convert the pystxm scan name to one known by pixelator

        NOTE: Pixelator combines Coarse, Fine, Point and Line spec scans into 'Sample'
        Parameters
        ----------
        app_scan_name

        Returns
        -------

        """
        dcs_scan_names = ["Detector", "OSA", "Motor2D", "Focus", "OSA Focus", "Sample"]
        if app_scan_name.find('DETECTOR') > -1:
            return "Detector"
        elif app_scan_name.find('OSA_FOCUS') > -1:
            return "OSA Focus"
        elif app_scan_name.find('OSA') > -1:
            return "OSA"
        elif app_scan_name.find('COARSE_IMAGE') > -1:
            return "Sample"
        elif app_scan_name.find('POSITIONER') > -1:
            return "Motor"
        elif app_scan_name.find('TWO_VARIABLE_SCAN') > -1:
            return "Motor2D"
        elif app_scan_name.find('FOCUS') > -1:
            return "Focus"
        elif app_scan_name.find('SAMPLE') > -1:
            return "Sample"
        elif app_scan_name.find('POINT') > -1:
            return "Sample"
        elif app_scan_name.find('LINE') > -1:
            return "Sample"
        else:
            Exception(f"pixelator_dcs_server_api: map_app_scan_name_to_dcs_scan_name: [{app_scan_name}] not found in map")

    def is_point_spec_scan(self, scan_request):
        """
        it is a point spec if:
            linemode = 'Point by Point'
            SpatialType = 'Point'
            ScanType = 'Sample'
        """
        res = True
        if scan_request["scanType"] not in ['Sample', 'Motor', 'Motor2D']:
            res = False
        if scan_request["spatialType"] not in ['Point', 'Line']:
            res = False
        if scan_request["lineMode"] != 'Point by Point':
            res = False
        return res

    def is_motor_scan(self, scan_request):
        """
        it is a point spec if:
            linemode = 'Point by Point'
            SpatialType = 'Point'
            ScanType = 'Sample'
        """
        res = False
        if scan_request["scanType"] in ['Motor']:
            res = True

        return res

    def is_line_spec_scan(self, scan_request):
        """
        it is a line spec if:
            linemode = 'Point by Point' or 'Constant Velocity
            SpatialType = 'Line'
            ScanType = 'Sample'
        """
        res = True
        if scan_request["scanType"] != 'Sample':
            res = False
        if scan_request["spatialType"] != 'Line':
            res = False
        if scan_request["lineMode"] not in ['Point by Point', 'Constant Velocity']:
            res = False
        return res

    def is_sample_image_scan(self, scan_request):
        """
        it is a line spec if:
            linemode = 'Point by Point' or 'Constant Velocity
            SpatialType = 'Line'
            ScanType = 'Sample'
        """
        res = True
        if scan_request["scanType"] != 'Sample':
            res = False
        if scan_request["spatialType"] not in ['Point', 'Line']:
            res = False
        if scan_request["lineMode"] not in ['Point by Point', 'Constant Velocity']:
            res = False
        return res

    def determine_sample_scan_type(self, scan_request, app_scan_type_str):
        """
        based on the scan request determine what type of pyStxm sample scan it is
        Args:
            scan_request:
            app_scan_type_str:

        Returns:

        """
        if app_scan_type_str in ['POINT', 'POSITIONER']:
            scan_type = ScanType.POINT_SPEC
        elif app_scan_type_str == 'LINE':
            scan_type = ScanType.LINE_SPEC
        elif self.is_point_spec_scan(scan_request):
            scan_type = ScanType.POINT_SPEC
        elif self.is_line_spec_scan(scan_request):
            scan_type = ScanType.LINE_SPEC
        else:
            scan_type = ScanType.IMAGE  # default

        return scan_type

    def init_scan_req(self):
        """
        populate a template for a scan requistion from current data
        assumption is data is set before this function is called
        Returns
        -------

        """
        app_scan_type_str = get_scan_type_str_from_wdg_com(self.wdg_com)
        self.scan_type_str = self.map_app_scan_name_to_dcs_scan_name(app_scan_type_str)
        # if self.scan_pxp:
        #     line_mode = "Point by Point"
        # else:
        #     line_mode = "Constant Velocity"
        scan_req_cls = GenScanRequestClass(self.dcs_server_api.app_to_dcs_devname_map)
        line_mode = self.wdg_scan_req['scan_point_or_line_mode']

        scan_request = scan_req_cls.gen_base_req_structure(self.scan_type_str)

        # set flags to decide what sample scan it is
        self.sample_scan_type = self.determine_sample_scan_type(scan_request, app_scan_type_str)

        if self.scan_type_str == 'Sample':
            # if self.scan_type_str.find('POINT') > -1:
            #     self.spatial_type = "Point"
            # elif self.scan_type_str.find('LINE') > -1:
            #     self.spatial_type = "Line"
            # else:
            #     self.spatial_type = "Image"
            if app_scan_type_str.find('POINT') > -1:
                self.spatial_type = "Point"
            elif app_scan_type_str.find('LINE') > -1:
                self.spatial_type = "Line"
            else:
                self.spatial_type = "Image"
            # Sample scans can be stacks etc so build it
            scan_request["scanType"] = self.scan_type_str
            scan_request["spatialType"] = self.spatial_type
            scan_request["lineMode"] = line_mode



            # # set flags to decide what sample scan it is
            # self.sample_scan_type = self.determine_sample_scan_type(scan_request, app_scan_type_str)

            if self.sample_scan_type in [ScanType.POINT_SPEC, ScanType.LINE_SPEC]:
                #create inner and outer regions for a point and line spec scan
                for e_roi in self.e:
                    scan_request["outerRegions"].append(scan_req_cls.make_base_energy_region(e_roi, self.dcs_server_api.app_to_dcs_devname_map))

                for spid, sp_dct in self.sp_roi_dct.items():
                    scan_request["innerRegions"].append(scan_req_cls.make_point_spatial_region(sp_dct['X'], sp_dct['Y'], self.dcs_server_api.app_to_dcs_devname_map))

                scan_request["displayedAxes"] = scan_req_cls.gen_point_displayed_axis_dicts(["x", "y"], [self.x, self.y],
                                                                         [True, False])  # order matters
                scan_request["nInnerRegions"] = len(self.sp_ids)
                scan_request["nOuterRegions"] = len(scan_request["outerRegions"])
            else:
                # Sample Image
                scan_request["outerRegions"] = scan_req_cls.gen_regions(self.scan_type_str, self.dwell_ms * 0.001, self, is_outer=True)
                scan_request["innerRegions"] = scan_req_cls.gen_regions(self.scan_type_str, self.dwell_ms * 0.001, self, is_outer=False)

                #the following is scan dependant I would think so this will need modification
                scan_request["displayedAxes"] = scan_req_cls.gen_displayed_axis_dicts(["y", "x"], [self.y, self.x],
                                                                     [True, True])  # order matters
                scan_request["nInnerRegions"] = len(self.sp_ids)
                scan_request["nOuterRegions"] = len(self.ev_rois)
        else:
            # pull scan req from a template and do substitutions
            scan_request = do_substitutions(scan_request, self)

        #now finish assignments
        scan_request["meander"] = 1 if self.wdg_scan_req['meander'] else 0
        scan_request["yAxisFast"] = 1 if self.wdg_scan_req['y_axis_fast'] else 0
        scan_request["yAxisFast"] = 1 if self.wdg_scan_req['y_axis_fast'] else 0
        scan_request["osaInFocus"] = 0 #needs to be set proper;y
        scan_request["tiling"] = 1 if self.wdg_scan_req['tiling'] else 0
        scan_request["accelerationDistance"] = self.wdg_scan_req['accel_dist']
        scan_request["tileDelay"] = self.wdg_scan_req['tile_delay']
        scan_request["lineDelay"] = self.wdg_scan_req['line_delay']
        scan_request["pointDelay"] = self.wdg_scan_req['point_delay']
        scan_request["lineRepetition"] = self.wdg_scan_req['line_repeat']
        scan_request["positionPrecision"] = {"precision": self.wdg_scan_req['prec_field']}
        scan_request["defocus"] = {"diameter": self.wdg_scan_req['defocus_diam_field']}
        pol = self.map_app_polarization_to_dcs_polarization(self.wdg_scan_req['polarization'])
        if pol:
            scan_request["polarization"] = pol

        return scan_request

    def intake_scan_status(self, dct):
        """
        Take the dict received from pixelator and assign it to our member variables
        # Part 2: {"current":
            #           {"innerRegion":1,"line":100,"lineRepetition":1,"outerRegion":1,"point":53,"polarization":null,"remainingTime":"00h 22m 46s","time":"00h 02m 01s"},
            #          "scanType":"OSA Scan",
            #          "status":"running",
            #          "total": {"innerRegion":1,"line":100,"lineRepetition":1,"outerRegion":1,"point":100,"polarization":1,"time":"00h 02m 22s"}
            #         }
        Returns
        """
        #print(
        #    f"scanStatus: status={dct['status']} line={dct['current']['line']} point={dct['current']['point']} remainingTime={dct['current']['remainingTime']}")
        if dct['status'].find('running') > -1:
            self.status = ScanStatus.RUNNING
        elif dct['status'].find('paused') > -1:
            self.status = ScanStatus.PAUSED
        elif dct['status'].find('idle') > -1:
            self.status = ScanStatus.IDLE
        else:
            print(f"intake_scan_status: received {dct['status']} so assuming its IDLE")
            self.status = ScanStatus.IDLE


    def intake_scan_started(self, resp):
        """

        """
        self.handle_scanStarted(json.loads(resp[1]))

    def handle_scanLineData(self, data):
        """
        handle the scanLineData response from Pixelator
        Args:
            data:

        Returns:

        """
        dct = {}
        indices = [int(x) for x in data[0].split()]
        dct['outer_idx'] = int(indices[0])
        dct['img_idx'] = int(indices[1])
        dct['tile_num'] = int(indices[2])
        dct['det_chan_idx'] = int(indices[3])
        parts = data[2].split()
        # print(f"handle_scanLineData:  dct {dct}")
        if len(parts) == 2:
            dct['data_shape'] = int(parts[0]), int(parts[1])
        else:
            dct['data_shape'] = int(parts[0]),

        if indices[2] == len(self.tile_shapes):  # when starting a new tile
            self.tile_shapes.append(np.array([0, 0, 0, 0]))  # [Y0, X0, H, W]
            offset_wrap = np.divmod(self.tile_shapes[indices[2] - 1][1] + self.tile_shapes[indices[2] - 1][3], self.scan_shape[-1])
            self.tile_shapes[indices[2]][:2] = [
                self.tile_shapes[indices[2] - 1][0] + self.tile_shapes[indices[2] - 1][2] * offset_wrap[0],
                offset_wrap[1]]
        offset = self.tile_shapes[indices[2]][:2]
        chunk_start = np.array([int(x) for x in data[1].strip("\'b").split()])
        chunk_shape = np.array([int(x) for x in data[2].strip("\'b").split()])
        dct['data'] = np.array([float(x) for x in data[3].strip().strip("\'b[]").split(',')])

        if self.sample_scan_type in [ScanType.POINT_SPEC, ScanType.LINE_SPEC]:
            dct['data_size'] = dct['data_shape'][0]
        else:
            dct['data_size'] = dct['data_shape'][1]

        # if self.is_line_spec_scan(self.scan_req):
        #     dct['row'] = dct['tile_num']
        # else:
        #     dct['row'] = offset[0] + chunk_start[0]

        dct['row'] = offset[0] + chunk_start[0]

        if self.is_point_spec_scan(self.scan_req) or self.is_line_spec_scan(self.scan_req):
            # need to change the img_idx
            dct['col'] = int(indices[1])
            dct['img_idx'] = dct['outer_idx']
        else:
            if len(chunk_start) == 2:
                cstart = chunk_start[1]
                dct['col'] = offset[1] + cstart
        # else:
        #     cstart = dct['img_idx']
        # dct['col'] = offset[1] + cstart
        # print(f"[{self.scan_seq}] scan_data[row={row}, col={col}] = length={len(chunk_values)} {chunk_values}")
        # print(f"handle_scanLineData: row={row} col={col}")
        self.tile_shapes[indices[2]][2:] = np.maximum(self.tile_shapes[indices[2]][2:], chunk_start + chunk_shape)
        return dct

    def intake_scan_line_data(self, resp, selected_det_names):
        """
        resp = '0 0 0 0 ', '0 0 ', '1 25 ', '[20.5650,20.1760,20.5530,20.282...,20.8190,20.0390,20.5670,20.0110,20.9050]
        The scan progress needs to take into account the total number of selected detectors otherwise it will think all
        data is for one detector and give an incorrect progress
        """
        sl_dct = self.handle_scanLineData(resp[1:])

        self.ttl_points_received += sl_dct['data_size']
        self.cur_img_points_received += sl_dct['data_size']

        # calc the progress
        all_scans_progress = int(float((self.ttl_points_received / self._total_num_points) * 100.0)/len(selected_det_names))
        cur_img_progress = int(float((self.cur_img_points_received / (self.npoints_rows * self.npoints_cols)) * 100.0)/len(selected_det_names))
        self._scan_line_data_cntr += 1
        return {'det_name': selected_det_names[sl_dct['det_chan_idx']], 'row': sl_dct['row'], 'col': sl_dct['col'], 'shape': sl_dct['data_shape'],
                'value': sl_dct['data'], 'is_tiled': self.tiling, 'is_partial': True if not self.tiling else False,
                'img_idx': sl_dct['img_idx'],
                "tile_num": sl_dct['tile_num'], "ev_idx": sl_dct['outer_idx'], "prog": cur_img_progress, "pol_idx": sl_dct['tile_num'],
                "total_prog": all_scans_progress}


    def handle_scanStarted(self, scan_request):
        """
        parse the scan request and set the member variables

        Args:
            scan_request:

        Returns:

        """
        #print(scan_request)
        if 'scanType' in scan_request.keys():
            self.scan_running = True
            self.scan_data_is_fresh = True
            self.tiling = True if scan_request['tiling'] == 1 else False
            npoints_x = 0
            npoints_y = 0
            points_dict = {x["trajectories"][0]["positionerName"]: x["nPoints"] for x in scan_request["innerRegions"][0]["axes"]}

            _keys = list(points_dict.keys())
            if self.is_motor_scan(self.scan_req):
                self.npoints_rows = 1 #scan_request["innerRegions"][0]["axes"][0]['nPoints']
                self.npoints_cols = 1

            elif self.is_point_spec_scan(self.scan_req):
                self.npoints_rows = sum(axis['nPoints'] for region in scan_request["outerRegions"] for axis in region["axes"])
                self.npoints_cols = scan_request["innerRegions"][0]["axes"][0]['nPoints']

            elif self.is_line_spec_scan(self.scan_req):
                self.npoints_cols = sum(axis['nPoints'] for region in scan_request["outerRegions"] for axis in region["axes"])
                self.npoints_rows =  scan_request["innerRegions"][0]["axes"][0]['nPoints']
            else:
                if len(_keys) == 2:
                    self.npoints_rows = points_dict[_keys[0]]
                    self.npoints_cols = points_dict[_keys[1]]
                else:
                    self.npoints_rows = points_dict[_keys[0]]
                    if 'axes' in scan_request["outerRegions"][0].keys():
                        self.npoints_cols = scan_request["outerRegions"][0]["axes"][0]['nPoints']
                    else:
                        #likely a motor scan
                        self.npoints_cols = 1

            self.num_inner_regions = scan_request["innerRegions"][0]["axes"][0]['nPoints']

            if 'axes' in scan_request["outerRegions"][0].keys():
                self.num_outer_regions = scan_request["outerRegions"][0]["axes"][0]['nPoints']

            self.num_outer_regions = scan_request['nOuterRegions']

            self._total_num_points = (self.npoints_rows * self.npoints_cols) * self.num_inner_regions * self.num_outer_regions

            extent_dict = {}
            for axis_info in scan_request["innerRegions"][0]["axes"]:
                # print(axis_info)
                if 'length' in axis_info:
                    extent_dict[axis_info["trajectories"][0]["positionerName"]] = [0, axis_info['length']]
                else:
                    if 'center' in axis_info["trajectories"][0].keys():
                        axis_center = axis_info["trajectories"][0]['center']
                    else:
                        axis_center = axis_info["trajectories"][0]['start'] + (axis_info["trajectories"][0]['range'] * 0.5)

                    axis_range = axis_info["trajectories"][0]['range']
                    extent_dict[axis_info["trajectories"][0]["positionerName"]] = [axis_center - .5 * axis_range, axis_center + .5 * axis_range]

            mtr_nm_keys = list(extent_dict.keys())
            if len(mtr_nm_keys) == 2:
                self.scan_shape = [0, 0, points_dict[mtr_nm_keys[0]], points_dict[mtr_nm_keys[1]]]
                self.scan_extent = [extent_dict[mtr_nm_keys[0]][0], extent_dict[mtr_nm_keys[0]][1],
                                    extent_dict[mtr_nm_keys[1]][0], extent_dict[mtr_nm_keys[1]][1]]
                self.scan_axis_titles = [mtr_nm_keys[0], mtr_nm_keys[1]]
            else:
                #self.scan_shape = [0, 0, points_dict[mtr_nm_keys[0]], 0]
                self.scan_shape = [0, 0, 0, points_dict[mtr_nm_keys[0]]]
                self.scan_extent = [extent_dict[mtr_nm_keys[0]][0], extent_dict[mtr_nm_keys[0]][1]]
                self.scan_axis_titles = [mtr_nm_keys[0]]

            self.scan_data = np.full(self.scan_shape[2:], np.nan)

    def convert_scan_request(self, message):
        """
        Takes a wdg_com dict from pyStxm and turns it into a scanRequest sent to Pixelator
        Parameters
        ----------
        scan_request is what gets sent to Pixelator

        Returns
        -------

        """
        # print(message)
        command = message[0]
        self.wdg_com = json.loads(message[1])
        #reset plot counter
        self._scan_line_data_cntr = 0
        self.tiled_map = {}

        self.dwell_ms = get_dwell_from_wdg_com(self.wdg_com)
        self.x = get_axis_roi_from_wdg_com('X', self.wdg_com)
        self.y = get_axis_roi_from_wdg_com('Y', self.wdg_com)
        self.z = get_axis_roi_from_wdg_com('Z', self.wdg_com)
        self.zp = get_axis_roi_from_wdg_com('ZP', self.wdg_com)
        self.e = get_ev_rois_from_wdg_com(self.wdg_com)
        self.p = []  # polarization regions
        #self.scan_pxp = self.x['IS_POINT']
        self.sp_ids = get_sp_ids_from_wdg_com(self.wdg_com)
        self.ev_rois = get_ev_rois_from_wdg_com(self.wdg_com)
        (self.sp_roi_dct, self.sp_ids, sp_id, sp_db) = wdg_to_sp(self.wdg_com)
        # if sp_db['SCAN_PLUGIN']['SCAN_SUBTYPE'] == 0:
        #     self.scan_pxp = True
        # else:
        #     self.scan_pxp = False
        self.scan_pxp = True if dct_get(self.wdg_com, SPDB_SCAN_PLUGIN_SUBTYPE) == 0 else False
        self.wdg_scan_req = self.wdg_com['SCAN_REQUEST']

        # this should be the number of ev npoints * pol npoints
        self.num_images = get_total_ev_pol_npoints_from_ev_rois(self.e)

        self.status = ScanStatus.IDLE
        self.scan_req = self.init_scan_req()
        return self.scan_req



#################################################################################################################
class DcsServerApi(BaseDcsServerApi):

    def __init__(self, parent):
        super().__init__(parent)
        self.devices = {}
        self.scan_class = ScanClass(dcs_server_api=self)

        self.load_file_q = Queue()
        self.load_file_q_poller = QTimer()
        self.load_file_q_poller.timeout.connect(self.process_load_file_queue)
        self.load_file_q_poller.start(750)

        self.busy = False

    def get_server_version_id(self) -> str:
        """
        return the server version id, to be implemented by the inheriting class
        Returns: str
        -------

        """
        return self.parent.server_version

    def get_base_data_dir(self):
        """
        return value from remoteFileSystem dict that we received from Pix controller
        """
        # {'bookmarks': [], 'directory': '/tmp', 'fileExtension': '.hdf5', 'showHidden': 0}
        return self.parent.remote_file_system_info['directory']

    def get_data_file_extension(self):
        """
        return value from remoteFileSystem dict that we received from Pix controller
        """
        # {'bookmarks': [], 'directory': '/tmp', 'fileExtension': '.hdf5', 'showHidden': 0}
        return self.parent.remote_file_system_info['fileExtension']

    def reset_scan_info(self):
        self.scan_class.reset()

    def intake_scan_status(self, dct):
        """
        Take the dict received from pixelator and assign it to our member variables
        # Part 2: {"current":
            #           {"innerRegion":1,"line":100,"lineRepetition":1,"outerRegion":1,"point":53,"polarization":null,"remainingTime":"00h 22m 46s","time":"00h 02m 01s"},
            #          "scanType":"OSA Scan",
            #          "status":"running",
            #          "total": {"innerRegion":1,"line":100,"lineRepetition":1,"outerRegion":1,"point":100,"polarization":1,"time":"00h 02m 22s"}
            #         }

        Returns
        -------
        """
        prog_dct = self.scan_class.intake_scan_status(dct)
        # self.progress.emit(prog_dct)
        # print(f"intake_scan_status: emitting {self.scan_class.status}")
        self.scan_status.emit(self.scan_class.status)

    def intake_scan_started(self, resp):
        dct = self.scan_class.intake_scan_started(resp)
        print(dct)

    def intake_scan_line_data(self, resp):
        """
        resp = '0 0 0 0 ', '0 0 ', '1 25 ', '[20.5650,20.1760,20.5530,20.2820,20.1760,20.0870,20.5080,20.5030,20.4770,20.6060,20.3750,20.1760,20.2540,20.160,20.6820,20.0230,20.110,20.8350,20.6390,20.4680,20.8190,20.0390,20.5670,20.0110,20.9050]
        from messages like below
            ['scanLineData', '0 0 0 0 ', '0 0 ', '1 25 ', '[20.5650,20.1760,20.5530,20.2820,20.1760,20.0870,20.5080,20.5030,20.4770,20.6060,20.3750,20.1760,20.2540,20.160,20.6820,20.0230,20.110,20.8350,20.6390,20.4680,20.8190,20.0390,20.5670,20.0110,20.9050]']
            ['scanLineData', '0 0 0 0 ', '1 0 ', '1 25 ', '[20.940,20.080,20.3650,20.20,20.7250,20.3890,20.2080,20.1390,20.4540,20.8170,20.8690,20.4690,20.5490,20.4280,20.020,20.0970,20.6520,20.5390,20.030,20.5520,20.7720,20.6410,20.1220,20.0420,20.8220]']
            ['scanLineData', '0 0 0 0 ', '2 0 ', '1 25 ', '[20.2660,20.0480,20.70,20.4280,20.2650,20.8170,20.0980,20.3610,20.8350,20.8060,20.4940,20.1120,20.7710,20.3220,20.1030,20.590,20.2160,20.6660,20.6030,20.8620,20.6680,20.8230,20.7090,20.8320,20.2680]']

        """
        dct = self.scan_class.intake_scan_line_data(resp, self.parent.selected_detectors)
        return dct

    def intake_plot_data(self, resp):
        """
        resp = '0 0 0 0 ', '0 0 ', '1 25 ', '[20.5650,20.1760,20.5530,20.2820,20.1760,20.0870,20.5080,20.5030,20.4770,20.6060,20.3750,20.1760,20.2540,20.160,20.6820,20.0230,20.110,20.8350,20.6390,20.4680,20.8190,20.0390,20.5670,20.0110,20.9050]
        from messages like below
            ['scanLineData', '0 0 0 0 ', '0 0 ', '1 25 ', '[20.5650,20.1760,20.5530,20.2820,20.1760,20.0870,20.5080,20.5030,20.4770,20.6060,20.3750,20.1760,20.2540,20.160,20.6820,20.0230,20.110,20.8350,20.6390,20.4680,20.8190,20.0390,20.5670,20.0110,20.9050]']
            ['scanLineData', '0 0 0 0 ', '1 0 ', '1 25 ', '[20.940,20.080,20.3650,20.20,20.7250,20.3890,20.2080,20.1390,20.4540,20.8170,20.8690,20.4690,20.5490,20.4280,20.020,20.0970,20.6520,20.5390,20.030,20.5520,20.7720,20.6410,20.1220,20.0420,20.8220]']
            ['scanLineData', '0 0 0 0 ', '2 0 ', '1 25 ', '[20.2660,20.0480,20.70,20.4280,20.2650,20.8170,20.0980,20.3610,20.8350,20.8060,20.4940,20.1120,20.7710,20.3220,20.1030,20.590,20.2160,20.6660,20.6030,20.8620,20.6680,20.8230,20.7090,20.8320,20.2680]']

        """
        dct = self.scan_class.intake_plot_data(resp)
        return dct

    def process_SUB_rcv_messages(self, resp):
        """
        receives the message that teh dcs server had posted on its PUB socket, figure out what it is and call
        the function that processes it
        Parameters
        ----------
        resp

        Returns
        -------

        """
        #print(f"process_SUB_rcv_messages: {resp}")
        if resp[0].find("recordedChannels") > -1:
            detname_lst = json.loads(resp[1])
            print(
                f"received an update for [recordedChannels]={resp[1]}")
            self.parent.selected_detectors = detname_lst

        elif resp[0].find("chartmode_detector_update") > -1:
            value_dct_lst = json.loads(resp[1])
            for val_dct in value_dct_lst:
                self._update_device_feedback(val_dct["name"], val_dct["value"])

        elif resp[0].find("detectorValues") > -1:
            # print(f"process_SUB_rcv_messages: self.parent.selected_detectors={self.parent.selected_detectors}")
            pass
            # values = json.loads(resp[1])
            # if len(self.parent.selected_detectors) > 0 and (len(self.parent.selected_detectors) == len(values)):
            #     det_vals_zip = zip(self.parent.selected_detectors, values)
            #     # for dcs_devname, val in det_vals_zip:
            #     #     # print(f"det [{dcs_devname}] = {val:.2f}")
            #     #     self._update_device_feedback(dcs_devname, val)
            # else:
            #     self.parent.selected_detectors = [DEFAULT_DETECTOR]
            #     det_vals_zip = zip(self.parent.selected_detectors, values)
            #
            # # for dcs_devname, val in det_vals_zip:
            # #     # print(f"det [{dcs_devname}] = {val:.2f}")
            # #     self._update_device_feedback(dcs_devname, val)
            # #     #print(f"process_SUB_rcv_messages: received an update for [detectorValues]={resp[1]} but I do not know the names of the detectors")

        elif resp[0].find("positionerStatus") > -1:
            # print(f"positionerStatus: resp={resp}")
            #values = json.loads(resp[1])
            values = json.loads(resp[1].replace('NaN', 'null'))
            if len(self.parent.devices['POSITIONERS']) > 0 and (len(self.parent.devices['POSITIONERS']) == len(values)):
                #self.parent.devices['POSITIONERS'], values)
                i = 0
                for app_devname in list(self.parent.devices['POSITIONERS'].keys()):
                    pos = values[i]['position']
                    if pos is None or pos == 'null':
                        pos = -909090.9090909
                    status = values[i]['status']
                    self._update_device_feedback(app_devname, pos, app_devname=app_devname)
                    self._update_device_status(app_devname, status, app_devname=app_devname)
                    # print(f"process_SUB_rcv_messages:positionerStatus: [{app_devname}]  value={pos}")
                    self.parent.devices['POSITIONERS'][app_devname]['position'] = pos
                    self.parent.devices['POSITIONERS'][app_devname]['status'] = status
                    self.devices[app_devname]['position'] = pos
                    self.devices[app_devname]['status'] = status
                    i += 1

        elif resp[0].find("moveStatus") > -1:
            values = json.loads(resp[1])
            print(f"process_SUB_rcv_messages:moveStatus: response: {resp}")

        elif resp[0].find("beamShutterStatus") > -1:
            app_devname = "DNM_SHUTTER"
            value = json.loads(resp[1])
            if value.find("red") > -1:
                val = 0 # closed
                #self.devices[app_devname]['dev'].close()

            else:
                val = 1  # open
                #self.devices[app_devname]['dev'].open()

            self.devices[app_devname]['dev'].update_position(val, False)

        elif resp[0].find("scanStatus") > -1:
            dct = json.loads(resp[1])
            self.intake_scan_status(dct)

        elif resp[0].find("scanLineData") > -1:
            # print(f"process_SUB_rcv_messages: {resp}")
            # pass
            dct = self.intake_scan_line_data(resp)
            if dct['det_name'] in self.parent.selected_detectors:
                # print(f"det [{dcs_devname}] = {val:.2f}")
                self._update_detector_device_feedback(dct)

        elif resp[0].find("scanAborted") > -1:
            print(f"process_SUB_rcv_messages: {resp}")

        elif resp[0].find("scanFinished") > -1:
            # print(f"process_SUB_rcv_messages: {resp}")
            self.scan_class.status = ScanStatus.IDLE
            # print(f"process_SUB_rcv_messages: emitting {self.scan_class.status}")
            self.scan_status.emit(ScanStatus.IDLE)
            self.on_exec_finished(json.loads(resp[1]))



        elif resp[0].find("userStatus") > -1:
            print(f"process_SUB_rcv_messages: {resp}")

        elif resp[0].find("focusType") > -1:
            print(f"process_SUB_rcv_messages: {resp}")

        elif resp[0].find("scanTypeArchive") > -1:
            print(f"process_SUB_rcv_messages: {resp}")

        elif resp[0].find("beamShutterMode") > -1:
            print(f"process_SUB_rcv_messages: {resp}")

        elif resp[0].find("topupMode") > -1:
            print(f"process_SUB_rcv_messages: {resp}")

        elif resp[0].find("topupStatus") > -1:
            print(f"process_SUB_rcv_messages: {resp}")

        elif resp[0].find("scanStarted") > -1:
            # print(f"process_SUB_rcv_messages: {resp}")
            self.intake_scan_started(resp)

        elif resp[0].find("filename") > -1:
            print(f"process_SUB_rcv_messages: {resp}")
            dct = {}
            # make sure that Pixelator didnt send us a name with a suffix
            dct['filename'] = {'name':resp[1], 'dir':resp[2]}
            self.on_msg_to_app(dct)

        elif resp[0].find("focalStatus") > -1:
            print(f"process_SUB_rcv_messages: {resp}")
            # this returns the current A0 value
            # ['focalStatus', '{"maxDOsa":296.4372357791096}']
            dct = json.loads(resp[1])
            app_devname = "DNM_A0"
            self.devices[app_devname]['dev'].update_position(dct['maxDOsa'], False)


        elif resp[0].find("zonePlateDefinition") > -1:
            # print(f"process_SUB_rcv_messages: {resp}")
            dct = json.loads(resp[1])
            self.on_init_beamline_components(dct)
            # self.parent.bl_component_changed.emit('OSAS', self.parent.dcs_server_config['OSAS'])
            # self.parent.bl_component_changed.emit('ZONEPLATES', self.parent.dcs_server_config['ZONEPLATES'])

        elif resp[0].find("positionerDefinition") > -1:
            # walk all positioners and set their definition dicts with set_positioner_dct
            self.parent.positioner_definition = json.loads(resp[1])
            for posner_dct in self.parent.positioner_definition:
                dcs_devname = posner_dct['name']
                if dcs_devname in self.dcs_to_app_devname_map.keys():
                    app_devname = self.dcs_to_app_devname_map[dcs_devname]
                    if app_devname in list(self.parent.devs.keys()):
                        dev = self.parent.devs[app_devname]['dev']
                        dev.set_positioner_dct(posner_dct)
                        # print(f"process_SUB_rcv_messages: positionerDefinition: {app_devname} {posner}")

        elif resp[0].find("scanFileContent") > -1:
            lfr = LoadFileResponseClass(resp[1])
            # Try to clean the string before parsing
            cleaned_json = lfr.pystxm_load.strip()
            if not cleaned_json:
                print("Error: pystxm_load string is empty")
                return

            h5_file_dct = json.loads(cleaned_json)
            # ekey = entry_dct['default']
            # sp_db_dct = entry_dct[ekey]['sp_db_dct']
            self.parent.new_data.emit(h5_file_dct)

        elif resp[0].find('loadFile directory') > -1:
            # reply is the contents of the directory
            dct = json.loads(resp[1])
            print(f"process_SUB_rcv_messages: loadFile directory: {dct}")

        elif parts[0].find('listDirectory') > -1:
            # Handle listDirectory message
            msg_dct = json.loads(parts[1])
            pprint.pprint(msg_dct)

    def get_pystxm_standard_scan_type_from_load_file_response_type(self, scan_type_str):
        """
        returns the correct scan_type from enumerated types
           the scan type was read from the stxm_scan_type dataset from the NXdata group of the data file
            and we want to convert it to using the stxm scan_types
        """
        # scan_type_str = get_stxm_scan_type(file_dct)
        if scan_type_str == "Detector":
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
    
    def connect_to_dcs_server(self, devices_dct: dict) -> bool:
        """
        Connect to the DCS server and sort info returned from dcs server into sections in a dict
        sections include: 'POSITIONERS', 'DETECTORS', 'PRESSURES','TEMPERATURES','PVS'
        Parameters
        ----------
        self

        Returns
        -------

        """
        #self.parent.devices

        reply = self.parent.zmq_dev_server_thread.send_receive(['initialize'])
        print(f"connect_to_dcs_server: received this reply from DCS_SERVER: {reply}")
        # func = cmd_func_map_dct['initialize']
        # # pass self so that the function can pull out data from reply and assign it to local variables
        # func(self, reply)
        if reply[0]['status'] == 'ok':
            self.parent.positioner_definition = reply[1]
            self.parent.detector_definition = reply[2]
            self.parent.oscilloscope_definition = reply[3]
            self.parent.zone_plate_definition = reply[4]
            self.parent.remote_file_system_info = reply[5]
            self.parent.server_version = reply[6]

            self.parent.print_all_devs("positionerDefinition", reply[1])
            self.parent.print_all_devs("detectorDefinition", reply[2])
            self.parent.print_all_devs("oscilloscopeDefinition", self.parent.oscilloscope_definition)
            self.parent.print_all_devs("zonePlateDefinition", reply[4])
            self.on_init_beamline_components(reply[4])
            self.parent.print_all_devs("remoteFileSystemInfo", reply[5])

            for positioner_dct in self.parent.positioner_definition:
                dcs_devname = positioner_dct['name']
                if dcs_devname in self.dcs_to_app_devname_map.keys():
                    app_devname = self.dcs_to_app_devname_map[dcs_devname]
                    if app_devname in list(self.parent.devs.keys()):
                        dev = self.parent.devs[app_devname]['dev']
                        #set device name (the app device name like DNM_PMT etc) and the device dcs_name (Counter0)
                        dev.name = app_devname
                        dev.dcs_name = dcs_devname

                        dev.set_connected(True)
                        dev.set_desc(positioner_dct['description'])

                        #over ride the limits for the fine sample positioners to hack around naming of abstract motor for now
                        if app_devname in ["DNM_SAMPLE_FINE_X", "DNM_SAMPLE_FINE_Y"]:
                            positioner_dct['lowerSoftLimit'] = -7000
                            positioner_dct['upperSoftLimit'] = 7000

                        dev.set_positioner_dct(positioner_dct)

                        if hasattr(dev, 'set_low_limit'):
                            #dev.set_low_limit(positioner_dct['lowerSoftLimit'])
                            dev._low_limit = positioner_dct['lowerSoftLimit']
                        if hasattr(dev, 'set_high_limit'):
                            #dev.set_high_limit(positioner_dct['upperSoftLimit'])
                            dev._high_limit = positioner_dct['upperSoftLimit']



                        if hasattr(dev, 'set_units'):
                            #dev.set_units(positioner_dct['unit'])
                            dev._units = positioner_dct['unit']
                        if hasattr(dev, 'max_velo'):
                            #dev.max_velo.set(positioner_dct['maxVelocity'])
                            dev._max_velo = positioner_dct['maxVelocity']

                        # now record the details passed from pixelator
                        positioner_dct['dev'] = dev
                        self.parent.devs[app_devname]['params'] = positioner_dct

                        positioner_dct['position'] = 99
                        self.parent.devices['POSITIONERS'][app_devname] = positioner_dct
                        self.devices[app_devname] = positioner_dct
                else:
                    print(
                        f"** Pixelator configuration contains device [{dcs_devname}] that does not exist in devs.py file **")
                
            # add DNM_A0 as a device so that its feedback can be updated when Pixelator  sets the ○
            self.devices['DNM_A0'] = {}
            self.devices['DNM_A0']['dev'] = self.parent.devs['DNM_A0']['dev']
            self.devices['DNM_A0']['dev'].set_connected(True)
            
            # WHAT IS THIS CODE DOING ??
            idx = 0
            sel_dets = []
            for det_dct in self.parent.detector_definition:
                #det_name = det_dct['name']
                dcs_det_name = det_dct['name']
                if dcs_det_name not in self.dcs_to_app_devname_map.keys():
                    print(f"** Pixelator configuration contains detector [{dcs_det_name}] that does not exist in devs.py file **")
                    _logger.warn(f"Pixelator configuration contains detector [{dcs_det_name}] that does not exist in devs.py file")
                    continue
                det_name = self.dcs_to_app_devname_map[dcs_det_name]
                selected = False
                # if det_name.find(DEFAULT_DETECTOR) > -1:
                #     reply = self.parent.zmq_dev_server_thread.send_receive(['recordedChannels', json.dumps([det_name])])
                #     if reply[0]['status'] == 'ok':
                #         selected = True

                self.parent.devices['DETECTORS'][det_name] = {'idx':idx, 'unit': det_dct['unit'], 'selected': selected}
                sel_dets.append(det_name)
                idx += 1

            self.parent.selected_detectors = sel_dets
            self.select_detectors(sel_dets)

            #assign some default values to pyStxm devices that do not have a corresponding Pixelator device
            # DNM_FOCAL_LENGTH = Energy * A1
            # DNM_ZP_DEF_A = A1
            appdevs = {'DNM_ENERGY': 650,
                       'DNM_ZP_DEF_A': -11.359,
                       'DNM_A0MAX': 1300,
                       'DNM_FOCAL_LENGTH': 650 * -11.359}
            for app_devname, val in appdevs.items():
                if app_devname in list(self.parent.devs.keys()):
                    dev = self.parent.devs[app_devname]['dev']
                    dev.update_position(val, False)

        return True


    def put(self, put_dct):
        """
        A device setpoint has changed on pyStxm and the put function has been called on the ZMQDevice or ZMQSignal so
        we need to turn this put_dct into the correct message for pixelator

        put_dct: {'command': 'PUT', 'name': 'CoarseX', 'dcs_name': 'CoarseX', 'attr': 'user_setpoint', 'value': 500.0}

        using moveRequest which looking a teh PIxelator MessageQueue code takes 2 arrays?
        // run setPosition for every Positioner
            Json::Value positioners = moveRequestJson.get("positioners", Json::arrayValue);
            Json::Value positions = moveRequestJson.get("positions", Json::arrayValue);

            LOG4CPP_DEBUG_SD()
              << "moveRequest: "
              << "positioners = " << positioners
              << ", positions = " << positions
              << log4cpp::eol;

        Parameters
        ----------
        put_dct

        Returns
        -------

        """
        dcs_devname = put_dct['dcs_name']
        value = put_dct['value']
        attr =  put_dct['attr']

        #only try to put to a pixelator device if it exists on Pixelator

        if dcs_devname not in self.dcs_to_app_devname_map.keys():
            return

        else:
            app_devname = self.dcs_to_app_devname_map[dcs_devname]
            if app_devname not in list(self.parent.devs.keys()):
                return
            dev = self.parent.devs[app_devname]['dev']

        # if dcs_devname.find('Polarization') > -1:
        #     # need to map pyStxm setpoints to Pixelator, valid{Pixelator values are -0.2 to 0.2
        #     # NOTE: these are just test converters!!!!!!!!!!!!!!!!!
        #
        #     reply = self.parent.zmq_dev_server_thread.send_receive(
        #         ['moveRequest', json.dumps({'positioners': [dcs_devname], 'positions': [value]})])
        #
        # elif dcs_devname.find('ZONEPLATE_INOUT') > -1:
        if dcs_devname.find('ZONEPLATE_INOUT') > -1:
            # if it is set to 0 then move the ZonePlate IN, else OUT
            if value == 0:
                reply = self.parent.zmq_dev_server_thread.send_receive(['ZonePlate OUT'])
            else:
                reply = self.parent.zmq_dev_server_thread.send_receive(['ZonePlate IN'])
            dev.update_position(value, False)

        elif dcs_devname.find('OSA_INOUT') > -1:
            # if it is set to 0 then move the OSA IN, else OUT
            if value == 0:
                reply = self.parent.zmq_dev_server_thread.send_receive(['OSA OUT'])
            else:
                reply = self.parent.zmq_dev_server_thread.send_receive(['OSA IN'])
            dev.update_position(value, False)

        elif dcs_devname.find('SAMPLE_OUT') > -1:
            # Move Sample OUT
            reply = self.parent.zmq_dev_server_thread.send_receive(['Sample OUT'])
            dev.update_position(value, False)

        elif dcs_devname.find('RESET_INTERFERS') > -1:
            # Move Sample OUT
            reply = self.parent.zmq_dev_server_thread.send_receive(['resetInterferometer'])
            dev.update_position(value, False)

        elif dcs_devname.find('ALL_MOTORS_OFF') > -1:
            # Move Sample OUT
            reply = self.parent.zmq_dev_server_thread.send_receive(['allMotorsOff'])
            dev.update_position(value, False)

        elif dcs_devname.find('FOCUS_MODE') > -1:
            # ['focusType', '"Static"']
            str_val = dev.ctrl_enum_strs[value]
            reply = self.parent.zmq_dev_server_thread.send_receive(['focusType', json.dumps(str_val)])
            # dev.update_position(value, False)

        elif dcs_devname.find('GATING') > -1:
            # ['topupMode', '"green"']
            str_val = dev.ctrl_enum_strs[value]
            reply = self.parent.zmq_dev_server_thread.send_receive(['topupMode', json.dumps(str_val)])
            # dev.update_position(value, False)

        elif dcs_devname.find('Shutter') > -1:
            # ['beamShutterMode', '"Auto"']
            str_val = dev.ctrl_enum_strs[value]
            reply = self.parent.zmq_dev_server_thread.send_receive(['beamShutterMode', json.dumps(str_val)])
            # dev.update_position(value, False)

        elif attr.find('low_limit_val') > -1:
            # modified positioner definition
            # {
            #     "name": "SampleX"
            #     , "axisName": "SampleX"
            #     , "description": "Fine translation of the sample along the X-axis"
            #     , "unit": "(μm)"
            #     , "velocityUnit": "(μm/ms)"
            #     , "coarsePositioner": "CoarseX"
            #     , "finePositioner": ""
            #     , "hardwareUnitFactor": 1000.0
            #     , "distributionMode": "n"
            #     , "autoOffMode": "Never"
            #     , "positionOffset": 0.0
            #     , "upperSoftLimit": 60000.0
            #     , "lowerSoftLimit": -50000.0
            #     , "maxVelocity": 300.0
            #     , "beamlineControlPosition": 0
            #     , "atPositionCheckInterval": 0.002
            #     , "atPositionCheckTimeout": 10.0
            #     , "destination": 1200.0
            # }
            #
            # send a modified positioner definition
            # ['positionerStatus', '[{"name":"DNM_A0","position":298.0,"status":"ok"}]']
            reply = self.parent.zmq_dev_server_thread.send_receive(
                ['modified positioner definition', json.dumps({"name": dcs_devname, "lowerSoftLimit": value})])

            # if reply[0]['status'] == 'ok':
            #     selected = True
            # else:
            #     print(f"send_scan_request: send modified positioner definition failed, reply={reply}")
        elif attr.find('high_limit_val') > -1:

            reply = self.parent.zmq_dev_server_thread.send_receive(
                ['modified positioner definition', json.dumps({"name": dcs_devname, "upperSoftLimit": value})])

            # if reply[0]['status'] == 'ok':
            #     selected = True
            # else:
            #     print(f"send_scan_request: send modified positioner definition failed, reply={reply}")
        elif attr.find('position_offset') > -1:

            reply = self.parent.zmq_dev_server_thread.send_receive(
                ['modified positioner definition', json.dumps({"name": dcs_devname, "positionOffset": value})])

        elif attr.find('auto_on_off') > -1:

            reply = self.parent.zmq_dev_server_thread.send_receive(
                ['modified positioner definition', json.dumps({"name": dcs_devname, "autoOffMode": value})])

        elif attr.find('loadFile directory') > -1:
            # arg is {"directory":"/tmp/2025-07-14","showHidden":1, "fileExtension":".hdf5"}
            reply = self.parent.zmq_dev_server_thread.send_receive(['loadFile directory', json.dumps(
                {'directory': value, 'showHidden': 1, 'fileExtension': '.hdf5'}
            )])
            # need to emite the reply so that subscribers can use it
            #dev.update_position(value, False)

        elif attr.find('loadFile file') > -1:
            dct = {
                "directory": "/tmp/2025-07-04"
                , "file": "/tmp/2025-07-04/Sample_Image_2025-07-04_001.hdf5"
                , "showHidden": 0
                , "fileExtension": ".hdf5"
                , "directories": [
                    ".."
                    , "discard"
                ]
                , "files": [
                    "Sample_Image_2025-07-04_001.hdf5"
                ]
                , "pluginNumber": 0
            }
            #
            # readMode = 'binary' or 'text'
            # {"filePath": "/tmp/2025-07-14/OSA_2025-07-14_006.hdf5", "readMode": "binary"}
            reply = self.parent.zmq_dev_server_thread.send_receive(['loadFile file', json.dumps(
                dct
            )])

            lfr = LoadFileResponseClass(response_text)
            # Try to clean the string before parsing
            cleaned_json = lfr.pystxm_load.strip()
            if not cleaned_json:
                print("Error: pystxm_load string is empty")
                return

            # Try parsing with error details
            try:
                parsed_data_dct = json.loads(cleaned_json)
                # print(f"Successfully parsed JSON data:")
                # pprint.pprint(parsed_data)
                self.new_data.emit(parsed_data_dct)
                # need to emite the reply so that subscribers can use it
                #dev.update_position(value, False)
            except Exception as e:
                print(f"General error: {str(e)}")

        else:

                reply = self.parent.zmq_dev_server_thread.send_receive(
                    ['moveRequest', json.dumps({'positioners': [dcs_devname], 'positions': [value]})])

        if reply[0]['status'] == 'ok':
            selected = True


    def load_file(self, directory, filename):
        """
        This function calls the DCS server to load a file and then emits the result
        """
        dct = {
            "directory": f"{directory}",
            "file": f"{filename}",
            "showHidden": 0,
            "fileExtension": ".hdf5",
            "directories": ["..", "discard"],
            "files": [f"{filename}"],
             "pluginNumber": 0,
        }
        reply = self.parent.zmq_dev_server_thread.send_receive(['loadFile file', json.dumps(dct)])

        if reply[0]['status'] == 'ok':
            print(f"pixelator_dcs_server_api:load_file: success: loaded file [{filename}] from directory [{directory}]")
        else:
            print(f"pixelator_dcs_server_api:load_file: FAILED: could not load file [{filename}] from directory [{directory}]")
        return

    def load_files(self, directory, filenames):
        """
        This function calls the DCS server to load a file and then emits the result
        """

        files = [f'{directory}{os.path.sep}{filename}' for filename in filenames]

        if len(files) == 0:
            return

        dct = {
            "directory": f"{directory}",
            "file": f"{files[0]}",
            "showHidden": 0,
            "fileExtension": ".hdf5",
            "directories": ["..", "discard"],
            "files": files,
             "pluginNumber": 0,
        }
        reply = self.parent.zmq_dev_server_thread.send_receive(['loadFile files', json.dumps(dct)])

        if reply[0]['status'] == 'ok':
            print(f"pixelator_dcs_server_api:load_files: success: loaded file [{files}] from directory [{directory}]")
        else:
            print(f"pixelator_dcs_server_api:load_files: FAILED: could not load file [{files}] from directory [{directory}]")
        return


    def load_directory(self, directory, extension: str='.hdf5'):
        """
        This function calls the DCS server to load a file and then emits the result
        """
        dct = gen_loadfile_directory_msg(directory, extension=extension)
        reply = self.parent.zmq_dev_server_thread.send_receive(['loadFile directory', json.dumps(dct)])

        if reply[0]['status'] == 'ok':
            # filter out the directories that do not match the date pattern
            strings = reply[1]['directories']
            date_strings = [s for s in strings if re.match(RE_DATA_DIR_PATTERN, s)]
            reply[1]['directories'] = date_strings
            print(f"pixelator_dcs_server_api:load_directory: success: loaded files from directory [{directory}]")
        else:
            print(f"pixelator_dcs_server_api:load_directory: FAILED: could not load files from directory [{directory}]")
        # only return the list of filenames
        return reply[1]['files']

    def request_data_directory_list(self, directory: str, extension: str='.hdf5'):
        """
        querery the DCS server for a list of data directories in the given base directory and return teh list
        """
        dct = gen_listDirectory_msg(directory)
        reply = self.parent.zmq_dev_server_thread.send_receive(['listDirectory', json.dumps(dct)])

        if reply[0]['status'] == 'ok':
            # filter out the directories that do not match the date pattern
            msg_dct = json.loads(reply[1]['message'])
            sub_dir_lst = msg_dct['sub_directories']
            # only return the list of dicts [{"sub_dir": "2025-07-04", "num_h5_files": 5}, ..]
            return sub_dir_lst
        else:
            print(f"pixelator_dcs_server_api:request_data_directory_list: FAILED: could not list sub directoriess from directory [{directory}]")
            return None

    def send_scan_request(self, wdg_com={}):
        """
        take a wdg_com dict from pyStxm and send the Pixelator version to Pixelator
        Parameters
        ----------
        wdg_com

        Returns
        -------

        """
        self.scan_class.reset()
        scan_request = self.scan_class.convert_scan_request(wdg_com)
        # self.send_default_detector_select()
        reply = self.parent.zmq_dev_server_thread.send_receive(
            ['scanRequest', json.dumps(scan_request)])
        if reply[0]['status'] == 'ok':
            self.scan_class.paused = False
        else:
            print(f"send_scan_request: send scanRequest failed, reply={reply}")

    def set_default_detector(self, det_name):
        """
        Set the default detector to be used by Pixelator for scans.
        Name comes from beamline configuration file and is teh DCS detector name, e.g. 'Counter1', 'Counter1', etc.
        """

        self.default_detector = self.app_to_dcs_devname_map.get(det_name, None)
        if self.default_detector is None:
            print(f"set_default_detector: ERROR: could not find DCS detector name for app detector [{det_name}]")
            _logger.error(f"set_default_detector: ERROR: could not find DCS detector name for app detector [{det_name}]")
            return

    def send_default_detector_select(self):
        reply = self.parent.zmq_dev_server_thread.send_receive(['recordedChannels', json.dumps([self.default_detector])])
        if reply[0]['status'] == 'ok':
            print(f'send_default_detector_select: success: selected DEFAULT_DETECTOR[{self.default_detector}]')
        else:
            print(f'send_default_detector_select: FAILED: selected DEFAULT_DETECTOR[{self.default_detector}]')

    def abort_scan(self):

        reply = self.parent.zmq_dev_server_thread.send_receive(['abortScan'])
        if reply[0]['status'] == 'ok':
            self.scan_class.paused = False
        else:
            print(f"send_scan_request: send abort_scan failed, reply={reply}")
        self.scan_class.reset()

    def pause_scan(self):

        reply = self.parent.zmq_dev_server_thread.send_receive(['pauseScan'])
        if reply[0]['status'] == 'ok':
            self.scan_class.paused = True
        else:
            self.scan_class.paused = False
            print(f"send_scan_request: send pause_scan failed, reply={reply}")

    def resume_scan(self):

        reply = self.parent.zmq_dev_server_thread.send_receive(['resumeScan'])
        if reply[0]['status'] == 'ok':
            self.scan_class.paused = False
        else:
            # self.scan_class.paused = False
            print(f"send_scan_request: send resume_scan failed, reply={reply}")


    def on_init_beamline_components(self, components_dct: dict) -> None:
        """
            param: components_dct: a dict that carry the list component params for that component type

            This function initializes the member variable self.beamline_components = {}
            where self.beamline_components ends up something like this =
            {
                'OSAS': {
                    'dOsa': 298.0,
                    'osa_lst': [{'active': 1, 'diameter': 50.0, 'name': 'OSA 50'},
                      {'diameter': 60.0, 'name': 'OSA 60'},
                      {'diameter': 70.0, 'name': 'OSA 70'},
                      {}],
                },
                'ZONEPLATES': [{'NXgeometry': '"Engineering" position of the fresnel zone plate',
                   'active': 1,
                   'b': [0, 6.875],
                   'central_stop_diameter': 75,
                   'central_stop_material': 'Pb',
                   'central_stop_thickness': 500,
                   'fabrication': 'etched',
                   'geometry': {'class': 'NXgeometry',
                    'translation': {'class': 'NXtranslation', 'distances': [0.0, 0.0, -35.0]}},
                   'mask_material': 'mask',
                   'mask_thickness': 400,
                   'name': 'ZonePlate B',
                   'outer_diameter': 240,
                   'outermost_zone_width': 35,
                   'support_membrane_material': 'membrane',
                   'support_membrane_thickness': 300,
                   'zone_height': 200,
                   'zone_material': 'Pt',
                   'zone_support_material': 'air ;)'},
                  {'NXgeometry': '"Engineering" position of the fresnel zone plate',
                   'b': [0, 1.795],
                   'central_stop_diameter': 75,
                   'central_stop_material': 'Pb',
                   'central_stop_thickness': 500,
                   'fabrication': 'etched',
                   'geometry': {'class': 'NXgeometry',
                    'translation': {'class': 'NXtranslation', 'distances': [0.0, 0.0, -35.0]}},
                   'mask_material': 'mask',
                   'mask_thickness': 400,
                   'name': 'ZonePlate A',
                   'outer_diameter': 150,
                   'outermost_zone_width': 15,
                   'support_membrane_material': 'membrane',
                   'support_membrane_thickness': 300,
                   'zone_height': 200,
                   'zone_material': 'Pt',
                   'zone_support_material': 'air ;)'},
                  {'NXgeometry': '"Engineering" position of the fresnel zone plate',
                   'b': [0, 4.821],
                   'central_stop_diameter': 75,
                   'central_stop_material': 'Au',
                   'central_stop_thickness': 500,
                   'fabrication': 'etched',
                   'geometry': {'class': 'NXgeometry',
                    'translation': {'class': 'NXtranslation', 'distances': [0.0, 0.0, -35.0]}},
                   'mask_material': 'mask',
                   'mask_thickness': 400,
                   'name': 'ZonePlate C',
                   'outer_diameter': 240,
                   'outermost_zone_width': 25,
                   'support_membrane_material': 'membrane',
                   'support_membrane_thickness': 300,
                   'zone_height': 200,
                   'zone_material': 'Au',
                   'zone_support_material': 'air ;)'},
                    {}
                ]
            }

        """
        osa_idx = 0
        zp_idx = 0
        for k in components_dct:
            k_upper = k.upper()
            if k_upper.find('OSAS') > -1:
                # load all OSA info
                lst = components_dct[k]
                for _dct in lst:
                    if len(_dct) > 0:
                        _dct['selected'] = False
                        _dct['osa_id'] = osa_idx
                        osa_idx += 1
                        self.parent.dcs_server_config['OSA_DEFS'][_dct['name']] = _dct
                        if 'active' in _dct.keys():
                            active_osa_name = _dct['name']
                            self.parent.dcs_server_config['OSA_DEFS'][active_osa_name]['selected'] = True
            elif k_upper.find('DOSA') > -1:
                # load DOSA (osa_gap) into each OSA info
                val = components_dct[k]
                for k, _dct in self.parent.dcs_server_config['OSA_DEFS'].items():
                    _dct['osa_gap'] = val
            elif k_upper.find('ZONEPLATES') > -1:
                # load all OSA info
                lst = components_dct[k]
                for _dct in lst:
                    if len(_dct) > 0:
                        _dct['selected'] = False
                        _dct['zp_id'] = zp_idx
                        zp_idx += 1
                        self.parent.dcs_server_config['ZP_DEFS'][_dct['name']] = _dct
                        if 'active' in _dct.keys():
                            active_zp_name = _dct['name']
                            self.parent.dcs_server_config['ZP_DEFS'][active_zp_name]['selected'] = True
            else:
                msg = f"UnSupported component type [{k}]"
                _logger.error(msg)
                print(f"on_init_beamline_components: {msg}")

    def get_zoneplate_definitions(self) -> dict:
        """
        Pixelator doesnt take a command to "get" information it will publish information when it changes
        So for now this function will only return the dict found in
        self.parent.dcs_server_config['ZP_DEFS']
        Parameters
        ----------

        Returns: dict of zoneplates configured on the dcs server
        -------

        """
        return self.parent.dcs_server_config['ZP_DEFS']


    def set_zoneplate_definitions(self, zp_defs: dict) -> bool:
        """
        Pixelator combines the OSA and Zoneplate definitions in one multi part message so regardless of sending
        zoneplate defs or osa defs we always send both like this:

        ['zonePlateDefinition', '{"OSAs":[{"active":1,"diameter":50.0,"name":"OSA 50"},{"diameter":60.0,"name":"OSA 60"},{"diameter":70.0,"name":"OSA 70"},{}],"dOsa":298.0,"zonePlates":[{"NXgeometry":"\\"Engineering\\" position of the fresnel zone plate","b":[0,6.8750],"central_stop_diameter":75,"central_stop_material":"Pb","central_stop_thickness":500,"fabrication":"etched","geometry":{"class":"NXgeometry","translation":{"class":"NXtranslation","distances":[0.0,0.0,-35.0]}},"mask_material":"mask","mask_thickness":400,"name":"ZonePlate B","outer_diameter":240,"outermost_zone_width":35,"support_membrane_material":"membrane","support_membrane_thickness":300,"zone_height":200,"zone_material":"Pt","zone_support_material":"air ;)"},{"NXgeometry":"\\"Engineering\\" position of the fresnel zone plate","active":1,"b":[0,1.7950],"central_stop_diameter":75,"central_stop_material":"Pb","central_stop_thickness":500,"fabrication":"etched","geometry":{"class":"NXgeometry","translation":{"class":"NXtranslation","distances":[0.0,0.0,-35.0]}},"mask_material":"mask","mask_thickness":400,"name":"ZonePlate A","outer_diameter":150,"outermost_zone_width":15,"support_membrane_material":"membrane","support_membrane_thickness":300,"zone_height":200,"zone_material":"Pt","zone_support_material":"air ;)"},{"NXgeometry":"\\"Engineering\\" position of the fresnel zone plate","b":[0,4.8210],"central_stop_diameter":75,"central_stop_material":"Au","central_stop_thickness":500,"fabrication":"etched","geometry":{"class":"NXgeometry","translation":{"class":"NXtranslation","distances":[0.0,0.0,-35.0]}},"mask_material":"mask","mask_thickness":400,"name":"ZonePlate C","outer_diameter":240,"outermost_zone_width":25,"support_membrane_material":"membrane","support_membrane_thickness":300,"zone_height":200,"zone_material":"Au","zone_support_material":"air ;)"},{}]}']
        Note all that should be changing from the pyStxm side is which definition is active


        Parameters
        ----------
        name: of the zoneplate
        zp_def: dict of zoneplate details

        Returns: bool True for success False for failed
        -------

        """
        res = False
        #walk through the zp_defs and set the zoneplate 'active': 1 in the pixelator zone_plate_definition dict
        # set all other zoneplates to 'active':0
        for zp_name, zp_dct in zp_defs.items():
            if zp_dct['selected']:
                zp_id = zp_dct['zp_id']
                # set the active
                zp_lst = self.parent.zone_plate_definition['zonePlates']
                for zp_dct in zp_lst:
                    if len(zp_dct) > 0:
                        if zp_dct['zp_id'] == zp_id:
                            zp_dct['active'] = 1
                        else:
                            zp_dct['active'] = 0

        # test = ['modified zonePlate definition', '{"OSAs":[{"diameter":50.0,"name":"OSA 50"},{"active":1,"diameter":60.0,"name":"OSA 60"},{"diameter":70.0,"name":"OSA 70"},{}],"dOsa":298.0,"zonePlates":[{"NXgeometry":"\\"Engineering\\" position of the fresnel zone plate","b":[0,6.8750],"central_stop_diameter":75,"central_stop_material":"Pb","central_stop_thickness":500,"fabrication":"etched","geometry":{"class":"NXgeometry","translation":{"class":"NXtranslation","distances":[0.0,0.0,-35.0]}},"mask_material":"mask","mask_thickness":400,"name":"ZonePlate B","outer_diameter":240,"outermost_zone_width":35,"support_membrane_material":"membrane","support_membrane_thickness":300,"zone_height":200,"zone_material":"Pt","zone_support_material":"air ;)"},{"NXgeometry":"\\"Engineering\\" position of the fresnel zone plate","b":[0,1.7950],"central_stop_diameter":75,"central_stop_material":"Pb","central_stop_thickness":500,"fabrication":"etched","geometry":{"class":"NXgeometry","translation":{"class":"NXtranslation","distances":[0.0,0.0,-35.0]}},"mask_material":"mask","mask_thickness":400,"name":"ZonePlate A","outer_diameter":150,"outermost_zone_width":15,"support_membrane_material":"membrane","support_membrane_thickness":300,"zone_height":200,"zone_material":"Pt","zone_support_material":"air ;)"},{"NXgeometry":"\\"Engineering\\" position of the fresnel zone plate","active":1,"b":[0,4.8210],"central_stop_diameter":75,"central_stop_material":"Au","central_stop_thickness":500,"fabrication":"etched","geometry":{"class":"NXgeometry","translation":{"class":"NXtranslation","distances":[0.0,0.0,-35.0]}},"mask_material":"mask","mask_thickness":400,"name":"ZonePlate C","outer_diameter":240,"outermost_zone_width":25,"support_membrane_material":"membrane","support_membrane_thickness":300,"zone_height":200,"zone_material":"Au","zone_support_material":"air ;)"},{}]}']
        reply = self.parent.zmq_dev_server_thread.send_receive(['modified zonePlate definition',
                                                                json.dumps(self.parent.zone_plate_definition)])
        if reply[0]['status'] == 'ok':
            res = True
        else:
            print(f"send_scan_request: send set_zoneplate_definitions failed, reply={reply}")

        return res

    def set_osa_definitions(self, osa_defs: dict) -> bool:
        """
        Pixelator combines the OSA and Zoneplate definitions in one multi part message so regardless of sending
        zoneplate defs or osa defs we always send both like this:

        ['zonePlateDefinition', '{"OSAs":[{"active":1,"diameter":50.0,"name":"OSA 50"},{"diameter":60.0,"name":"OSA 60"},{"diameter":70.0,"name":"OSA 70"},{}],"dOsa":298.0,"zonePlates":[{"NXgeometry":"\\"Engineering\\" position of the fresnel zone plate","b":[0,6.8750],"central_stop_diameter":75,"central_stop_material":"Pb","central_stop_thickness":500,"fabrication":"etched","geometry":{"class":"NXgeometry","translation":{"class":"NXtranslation","distances":[0.0,0.0,-35.0]}},"mask_material":"mask","mask_thickness":400,"name":"ZonePlate B","outer_diameter":240,"outermost_zone_width":35,"support_membrane_material":"membrane","support_membrane_thickness":300,"zone_height":200,"zone_material":"Pt","zone_support_material":"air ;)"},{"NXgeometry":"\\"Engineering\\" position of the fresnel zone plate","active":1,"b":[0,1.7950],"central_stop_diameter":75,"central_stop_material":"Pb","central_stop_thickness":500,"fabrication":"etched","geometry":{"class":"NXgeometry","translation":{"class":"NXtranslation","distances":[0.0,0.0,-35.0]}},"mask_material":"mask","mask_thickness":400,"name":"ZonePlate A","outer_diameter":150,"outermost_zone_width":15,"support_membrane_material":"membrane","support_membrane_thickness":300,"zone_height":200,"zone_material":"Pt","zone_support_material":"air ;)"},{"NXgeometry":"\\"Engineering\\" position of the fresnel zone plate","b":[0,4.8210],"central_stop_diameter":75,"central_stop_material":"Au","central_stop_thickness":500,"fabrication":"etched","geometry":{"class":"NXgeometry","translation":{"class":"NXtranslation","distances":[0.0,0.0,-35.0]}},"mask_material":"mask","mask_thickness":400,"name":"ZonePlate C","outer_diameter":240,"outermost_zone_width":25,"support_membrane_material":"membrane","support_membrane_thickness":300,"zone_height":200,"zone_material":"Au","zone_support_material":"air ;)"},{}]}']
        Note all that should be changing from the pyStxm side is which definition is active


        Parameters
        ----------
        osadef: dict of zoneplate details

        Returns: bool True for success False for failed
        -------

        """
        res = False
        #walk through the osa_defs and set the osa 'active': 1 in the pixelator zone_plate_definition dict
        # set all other osa's to 'active':0
        for osa_name, osa_dct in osa_defs.items():
            if osa_dct['selected']:
                osa_id = osa_dct['osa_id']
                # set the active
                osa_lst = self.parent.zone_plate_definition['OSAs']
                for osa_dct in osa_lst:
                    if len(osa_dct) > 0:
                        if osa_dct['osa_id'] == osa_id:
                            osa_dct['active'] = 1
                        else:
                            osa_dct['active'] = 0

        reply = self.parent.zmq_dev_server_thread.send_receive(['modified zonePlate definition',
                                                                json.dumps(self.parent.zone_plate_definition)])
        if reply[0]['status'] == 'ok':
            res = True
        else:
            print(f"send_scan_request: send set_osa_definitions failed, reply={reply}")

        return res

    def set_oscilloscope_definition(self, osc_def: dict) -> bool:
        """
        construct the oscilloscope definition from teh app data given in osc_def
        osc_def = {}
        osc_def["feedback_interval"] = float(self.interval_fld.text())
        osc_def["feedback_on_off"] = self.on_off_checkbox.isChecked()
        osc_def["count_rate"] = self.count_checkbox.isChecked()

        for Pixelator send the following
        oscilloscopeDefinition
        {
            "interval": 0.5
            , "on": 0
            , "countRate": 1
        }
        """
        #
        dct = {
            "interval": osc_def["feedback_interval"]
            , "on": 1 if osc_def["feedback_on_off"] else 0
            , "countRate": osc_def["count_rate"]
        }

        reply = self.parent.zmq_dev_server_thread.send_receive(['oscilloscopeDefinition', json.dumps(dct)])
        if reply[0]['status'] == 'ok':
            res = True
        else:
            print(f"send_scan_request: send set_osa_definitions failed, reply={reply}")

        return res

    def get_osa_definitions(self) -> dict:
        """
        Pixelator doesnt take a command to "get" information it will publish information when it changes
        So for now this function will only return the dict found in
        self.parent.dcs_server_config['OSA_DEFS']
        Parameters
        ----------

        Returns: dict of zoneplates configured on the dcs server
        -------

        """
        return self.parent.dcs_server_config['OSA_DEFS']


    def on_exec_finished(self, msg_dct):
        """
        process the scanFinished message into a standard dict the UI can use

        '{"filename":"/tmp/2024-12-05/discard/Detector_2024-12-05_010.hdf5","flag":0,"neXusBaseDirectory":"/tmp","neXusDiscardSubDirectory":"discard","neXusLocalBaseDirectory":"/tmp"}'
        dct['file_name'] = None
        dct['local_base_dir'] = None
        dct['dcs_server_base_dir'] = None
        dct['flags'] = None

        """
        dct = self.make_scan_finished_dct()
        fname = msg_dct['filename']
        if fname.find('Detector_') == -1:
            # fix a bug in PixelatorController
            # this is a detector file, so we need to replace the Detector_ with Sample_Image_
            fname = fname.replace('/discard', '')
        dct['file_name'] = fname
        dct['local_base_dir'] = msg_dct['neXusLocalBaseDirectory']
        dct['dcs_server_base_dir'] = msg_dct['neXusBaseDirectory']
        dct['flags'] = msg_dct['flag']
        dct['run_uids'] = [0]
        self.paused = False
        self.parent.exec_result.emit(dct)
        self.load_file_q.put_nowait(dct)

    def process_load_file_queue(self):
        """
        Process all items in the load_file_q, calling load_file for each one
        """
        if not self.busy:
            self.busy = True
            while not self.load_file_q.empty():

                try:
                    dct = self.load_file_q.get_nowait()
                    # Extract directory and filename from the full path
                    file_path = dct.get('file_name', '')

                    if file_path:
                        data_dir, fprefix, fsuffix = get_file_path_as_parts(file_path)
                        # Call load_file
                        self.load_file(data_dir, file_path)

                except Queue.empty:
                    # Queue is empty, we're done
                    break
                except Exception as e:
                    _logger.error(f"Error processing load_file_q item: {e}")
                    continue
            self.busy = False

    def on_msg_to_app(self, msg: dict) -> None:
        """
        send a specific message from DCS server to pyStxm
        """
        print(f"DcsServerApi: on_msg_to_app: emitting [{msg}]")
        self.parent.msg_to_app.emit(msg)

    def get_selected_detector_names(self) -> []:
        """
        To be implemented by inheriting class
        Parameters
        ----------
        self

        Returns: list of strings
        -------

        """
        # self.parent.devices['DETECTORS'][det_name] = {'idx': idx, 'unit': det_dct['unit'], 'selected': selected}
        # self.parent.selected_detectors = [det_name]
        # print("DcsServerApi: get_selected_detector_names: has not been implemented")
        app_det_names = []
        for dcs_det_name in self.parent.selected_detectors:
            if dcs_det_name[0:4] == "DNM_":
                app_det_names.append(dcs_det_name)
            else:
                app_det_names.append(self.dcs_to_app_devname_map[dcs_det_name])

        return app_det_names

    def select_detectors(self, det_nm_lst):
        """
        send the message to the Pixelator to select the detectors by name
        """
        if len(det_nm_lst) > 0:
            det_names = self.ensure_dcs_detector_names(det_nm_lst)
            reply = self.parent.zmq_dev_server_thread.send_receive(['recordedChannels', json.dumps(det_names)])
            if reply[0]['status'] == 'ok':
                selected = True

    def ensure_dcs_detector_names(self, det_nm_lst: [list]) -> [list]:
        """
        take a list of detector names and make sure that all names returned are DCS names
        """
        ret_lst = []
        for nm in det_nm_lst:
            if nm.find('DNM_') > -1:
                ret_lst.append(self.app_to_dcs_devname_map[nm])
            else:
                ret_lst.append(nm)
        return ret_lst


