
import os.path
import numpy as np
import sys
import zmq
import zmq.asyncio
from PyQt5 import QtCore, QtWidgets
from datetime import datetime
import pathlib
from importlib import import_module
from tinydb import TinyDB, Query
import simplejson as json

from nx_server.nx_server import NX_SERVER_CMNDS, NX_SERVER_REPONSES
from cls.utils.arrays import nulls_to_nans
from cls.utils.dict_utils import dct_put, dct_get, dct_merge, find_key_in_dict
from cls.utils.version import get_version
from cls.utils.process_utils import check_windows_procs_running
from cls.data_io.zmq_utils import send_to_server
from cls.utils.roi_dict_defs import *
from cls.utils.log import get_module_logger
from cls.utils.fileUtils import get_module_name
from cls.utils.json_utils import json_to_dict
from cls.utils.environment import get_environ_var
from cls.types.stxmTypes import (
    sample_fine_positioning_modes,
    sample_positioning_modes,
)

from cls.scan_engine.bluesky.qt_run_engine import EngineWidget, ZMQEngineWidget

from bcm.devices import BACKEND

if BACKEND == 'zmq':
    from bcm.devices.zmq.zmq_dev_manager import ZMQRunEngine
# from bcm.devices.device_names import *

# POS_TYPE_BL = 'BL'
# POS_TYPE_ES = 'ES'

POS_TYPE_BL = "POS_TYPE_BL"
POS_TYPE_ES = "POS_TYPE_ES"
USE_ZMQ = False

devq = Query()

NX_SERVER_DATA_SUB_PORT = os.getenv('NX_SERVER_DATA_SUB_PORT', 56566)
PIX_DATA_SUB_PORT = os.getenv('PIX_DATA_SUB_PORT', 55563)
DATA_SERVER_HOST = os.getenv('DATA_SERVER_HOST', None)

_logger = get_module_logger(__name__)


def gen_session_obj():
    """
    this function is meant to be the one stop location that defines what teh session object will
    consist of that exists in the MAIN_OBJ
    """
    ses_obj = {}
    dct_put(ses_obj, "AO", 500)  # default AO
    dct_put(ses_obj, "ZP", 2)  # default Zoneplate selected is #2
    dct_put(ses_obj, "FL", 0)  # calculated focal length
    dct_put(ses_obj, "DWELL", 1)  # current dwell
    dct_put(
        ses_obj, "SAMPLE_HLDR", 12131
    )  # unique ID for the 6 position sample holder, maybe from a barcode?
    dct_put(ses_obj, "SAMPLE_POS", 1)  # current sample position (1 - 6)
    return ses_obj

class DataSubListenerThread(QtCore.QThread):
    message_received = QtCore.pyqtSignal(object)

    def __init__(self, sub_socket):
        super().__init__()
        self.sub_socket = sub_socket
        self._running = True

    def run(self):
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        while self._running:
            msg = self.sub_socket.recv_string()
            self.message_received.emit(msg)

    def stop(self):
        self._running = False
        self.quit()
        self.wait()


class main_object_base(QtCore.QObject):
    """
    This class represents the main object for the application where all
    information is stored, it is designed thisway so that any module can import
    the main object and have access to its sections:
        main[APP]
                APP/STATUS
                APP/UI
                APP/USER

        main[SCAN]
                SCAN/CFG            all info required to recreate the scan if loaded from disk
                     CFG/TYPE        type of scan (the main scan class)
                     CFG/ROIS        list of ROI dicts used to create the scan
                SCAN/DATA
                     DATA/CHANNELS  list of channel(s) counter data
                     DATA/POINTS    2d np array of points for the current being acquired
                     DATA/SSCAN        list of sscan classes used in this scan
                     DATA/DEVICES    dict of devices found in devices and their feedback values at the time of the scan

    """

    changed = QtCore.pyqtSignal()
    export_msg = QtCore.pyqtSignal(object)
    seldets_changed = QtCore.pyqtSignal(list) #when the user selects different detectors emit this signal with list of app_devnames
    new_data = QtCore.pyqtSignal(object)  # when new data is received from the zmq server emit this signal with the data
    data_sub_message_received = QtCore.pyqtSignal(str)
    load_files_status = QtCore.pyqtSignal(bool)

    def __init__(self, name, endstation, beamline_cfg_dct=None, splash=None, main_cfg=None):

        super(main_object_base, self).__init__()

        self.beamline = name
        self.endstation = endstation
        self.beamline_cfg_dct = beamline_cfg_dct
        self.beamline_id = beamline_cfg_dct["BL_CFG_MAIN"]["endstation_prefix"]
        self.beamline_plugin_dir = beamline_cfg_dct["BL_CFG_MAIN"]["plugin_dir"]
        self.main_obj = {}
        self.endstation_prefix = "uhv"  # for default
        self.devdb_path = None
        self.dev_db = None
        self.default_ptycho_cam_nm = None
        self.device_backend = BACKEND #default
        self.zmq_dev_mgr = None
        self.dcs_settings = None
        self.win_data_dir = self.data_dir = beamline_cfg_dct["BL_CFG_MAIN"]['data_dir']
        self.linux_data_dir = beamline_cfg_dct["BL_CFG_MAIN"]['linux_data_dir']
        self.default_detector = beamline_cfg_dct["BL_CFG_MAIN"].get('default_detector', None)
        self.data_sub_context = zmq.Context()

        if DATA_SERVER_HOST is None:
            _logger.error("DATA_SERVER_HOST environment variable is not set, cannot continue")
            raise Exception("ERROR: DATA_SERVER_HOST environment variable is not set, cannot continue")

        if self.device_backend == 'zmq':
            # a ZMQ DCS Server is running and so mongo and nx_server are not needed
            self.mongo_db_nm = None
            self.nx_server_host = None
            self.nx_server_port = None
            self.nx_server_is_windows = None
            # SUB socket: Subscribing to the publisher
            print(f"Connecting to data server at tcp://{DATA_SERVER_HOST}:{PIX_DATA_SUB_PORT}")
            self.data_sub_socket = self.data_sub_context.socket(zmq.SUB)
            self.data_sub_socket.connect(f"tcp://{DATA_SERVER_HOST}:{PIX_DATA_SUB_PORT}")  # Connect to the PUB socket
            self.data_sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")  # Subscribe to all messages

        else:
            # SUB socket: Subscribing to the publisher
            self.data_sub_socket = self.data_sub_context.socket(zmq.SUB)
            print(f"Connecting to data server at tcp://{DATA_SERVER_HOST}:{NX_SERVER_DATA_SUB_PORT}")
            self.data_sub_socket.connect(f"tcp://{DATA_SERVER_HOST}:{NX_SERVER_DATA_SUB_PORT}")  # Connect to the PUB socket
            self.data_sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")  # Subscribe to all messages

            if main_cfg:
                self.mongo_db_nm = main_cfg.get_value("MAIN", "mongo_db_nm")
                self.nx_server_host = main_cfg.get_value("MAIN", "nx_server_host")
                self.nx_server_port = main_cfg.get_value("MAIN", "nx_server_port")
            else:
                self.mongo_db_nm = 'mongo_databroker'
                self.nx_server_host = 'localhost'
                self.nx_server_port = 5555
            self.nx_server_is_windows = self.check_is_nx_server_windows()

        ver_dct = get_version()

        dct_put(self.main_obj, "APP.STATUS", "THIS IS THE STATUS")
        dct_put(self.main_obj, "APP.UI", "THIS IS THE UI")
        dct_put(self.main_obj, "APP.USER", "THIS IS THE USER")
        dct_put(self.main_obj, "APP.SESSION", gen_session_obj())
        dct_put(self.main_obj, "APP.VER", ver_dct["ver"])
        dct_put(self.main_obj, "APP.MAJOR_VER", ver_dct["major_ver"])
        dct_put(self.main_obj, "APP.MINOR_VER", ver_dct["minor_ver"])
        dct_put(self.main_obj, "APP.AUTHOR", ver_dct["auth"])
        dct_put(self.main_obj, "APP.DATE", ver_dct["date"])
        dct_put(self.main_obj, "APP.COMMIT", ver_dct["commit"])
        dct_put(self.main_obj, "APP.COMMITED_BY", ver_dct["commited_by"])
        dct_put(self.main_obj, "SCAN.CFG.SCAN_TYPE", "THIS IS THE SCAN CFG TYPE")
        dct_put(self.main_obj, "SCAN.CFG.UNIQUEID", 0)
        dct_put(self.main_obj, "SCAN.CFG.ROI", None)
        dct_put(self.main_obj, "SCAN.DATA.CHANNELS", [])
        dct_put(self.main_obj, "SCAN.DATA.POINTS", {})
        dct_put(self.main_obj, "SCAN.DATA.SSCANS", {})

        dct_put(self.main_obj, "DEVICES", {})

        dct_put(self.main_obj, "PRESETS", {})

        self.sample_positioning_mode = None
        self.sample_fine_positioning_mode = None
        self.enable_multi_region = True

        # created to be a central location for all scan params and data
        # that can be used by any widget class or function, the keys for this
        # dict will be spatial_id's
        dct_put(self.main_obj, "SCAN_DB", {})
        self.rot_angle_dev = None

        if self.device_backend == 'zmq':
            # this will be set later after the devices have been created (init_zmq_dev_manager)
            self.engine_widget = None #ZMQEngineWidget(self.main_obj["DEVICES"].get_devices())
            self.nx_server_is_running = None
        else:
            self.engine_widget = EngineWidget(mongo_db_nm=self.mongo_db_nm)
            self.nx_server_is_running = self.check_nx_server_running()
            # when the engine widget receives new data it will emit this signal
            self.new_data = self.engine_widget.new_data
            self.load_files_status = self.engine_widget.load_files_status

        self.data_sub_message_received.connect(self.on_data_sub_message_received)
        self.start_sub_listener_thread()

    def start_sub_listener_thread(self):
        """
        start a thread to listen for messages from the data server
        """
        self.data_sub_listener_thread = DataSubListenerThread(self.data_sub_socket)
        self.data_sub_listener_thread.message_received.connect(self.on_data_sub_message_received)
        self.data_sub_listener_thread.start()

    def on_data_sub_message_received(self, msg):
        """
        The data server sends hf_file_dct's so convert jstrs to dicts and emit the new_data signal
        """
        if isinstance(msg, str):
            if len(msg) < 5:
                return
            # print(f"MAIN_OBJ:on_data_sub_message_received: DATA SUB MSG: {msg[:100]}")
            msg_dct = json.loads(msg)
            if 'load_file_data' in msg_dct.keys():
                if len(msg_dct['load_file_data']) < 5:
                    return
                h5_file_dct = json.loads(msg_dct['load_file_data'])
                self.engine_widget.new_data.emit(h5_file_dct)

            elif 'load_files_status' in msg_dct.keys():
                done = False
                status_str = msg_dct['load_files_status']
                if status_str.find('complete') >= 0:
                    done = True
                self.engine_widget.load_files_status.emit(done)



    def init_zmq_engine_widget(self, devices_dct):
        """
        the BACKEND is set to zmq so instantiate the zmq_device_manager
        """
        self.engine_widget = ZMQEngineWidget(devices_dct)
        self.engine_widget.set_default_detector(self.default_detector)
        result, dcs_params_dct = self.engine_widget.engine.connect_to_dcs_server(devices_dct)
        # when the engine widget receives new data it will emit this signal
        self.new_data = self.engine_widget.new_data
        self.load_files_status = self.engine_widget.load_files_status

        self.dcs_settings = self.engine_widget.engine.get_settings()

        self.check_dcs_settings(self.dcs_settings)

        if not result:
            _logger.error(f"Failed to connect to DCS server")
            raise Exception("ERROR >> Failed to connect to DCS server")
        else:
            #update the config

            self.beamline_cfg_dct['OSA_DEFS'] = {}
            for osa_nm, o_dct in dcs_params_dct['OSA_DEFS'].items():
                self.beamline_cfg_dct['OSA_DEFS'][osa_nm] = {'name': osa_nm, 'osa_id': o_dct['osa_id'], 'D': o_dct['diameter'],
                                                         'selected': o_dct['selected'], 'osa_gap':o_dct['osa_gap']}

            self.beamline_cfg_dct['ZP_DEFS'] = {}
            for zp_nm, z_dct in dcs_params_dct['ZP_DEFS'].items():
                # {'zp_id': 0, 'a1': -4.840, 'D': 100.0, 'CsD': 45.0, 'OZone': 60.0}
                self.beamline_cfg_dct['ZP_DEFS'][zp_nm] = {'name': zp_nm, 'zp_id': z_dct['zp_id'], 'a1':z_dct['b'][1],
                                                              'D':z_dct['outer_diameter'],
                                                              'CsD': z_dct['central_stop_diameter'],
                                                              'OZone': z_dct['outermost_zone_width'],
                                                              'selected': z_dct['selected']}

            #now updates teh PRESETS sections
            dct_put(self.main_obj, "PRESETS.OSA_DEFS", self.beamline_cfg_dct['OSA_DEFS'])
            dct_put(self.main_obj, "PRESETS.ZP_DEFS", self.beamline_cfg_dct['ZP_DEFS'])

        return result

    def check_dcs_settings(self, settings: dict=None):

        if self.get_device_backend() == 'zmq':
            # {'Detector_Archive_Default': 'no',
            #  'Focus_Archive_Default': 'no',
            #  'Motor_Archive_Default': 'no',
            #  'NeXusBaseDirectory': '/home/bergr/srv-unix-home/Data',
            #  'NeXusDiscardSubDirectory': 'discard',
            #  'NeXusLocalBaseDirectory': '/home/bergr/srv-unix-home/Data',
            #  'NeXusScanDate': '2025-08-26',
            #  'NeXusScanNumber': '001',
            #  'OSA Focus_Archive_Default': 'yes',
            #  'OSA_Archive_Default': 'yes',
            #  'SampleImagePreifx': '.',
            #  'Sample_Archive_Default': 'locked',
            #  'axisConfigFileName': './config/axis.json',
            #  'beamline': 'SLS PolLux X07DA',
            #  'changeUserScript': 'echo',
            #  'compression': 'LZW',
            #  'controllerConfigFileName': './config/controllerNoHardware.json',
            #  'dataPublisherPort': '56563',
            #  'defaultSaveLocal': 'yes',
            #  'defaultUsername': 'stxm',
            #  'detectorConfigFileName': './config/detectorNoHardware.json',
            #  'endOfScanScript': './scripts/endOfScan',
            #  'instrumentConfigFileName': './config/instrument.json',
            #  'log4cppPropertiesFileName': './config/log4cpp.properties',
            #  'microscopeControlConfigFileName': './config/microscopeControl.json',
            #  'missingDataCheckInterval': '0.1',
            #  'missingDataCheckMaxChecks': '5',
            #  'pixelClockConfigFileName': './config/pixelClockNoHardware.json',
            #  'positionerConfigFileName': './config/positionerNoHardware.json',
            #  'publisherPort': '56561',
            #  'requestPort': '56562',
            #  'sampleConfigFileName': './config/sample.json',
            #  'topupConfigFileName': './config/topupNoHardware.json',
            #  'zonePlateConfigFileName': './config/zonePlate.json'}
            # check that the settings specified by the dcs are the ones that we are using
            DCS_HOST = get_environ_var('DCS_HOST')
            DCS_HOST_PROC_NAME = get_environ_var('DCS_HOST_PROC_NAME')
            DCS_SUB_PORT = int(get_environ_var('DCS_SUB_PORT'))
            DCS_REQ_PORT = int(get_environ_var('DCS_REQ_PORT'))

            if self.data_dir != settings['NeXusBaseDirectory'] and self.data_dir != settings['NeXusLocalBaseDirectory']:
                _logger.error(f"Data directory in DCS server [{settings['NeXusBaseDirectory']}] does not match the one in the GUI [{self.data_dir}]")
                print(f"\nERROR: Data directory in DCS server [{settings['NeXusBaseDirectory']}] does not match the one in the GUI [{self.data_dir}]\n")
                #update the dcs server
                # self.engine_widget.engine.set_data_directory(self.data_dir)

            if int(settings['dataPublisherPort']) != int(PIX_DATA_SUB_PORT):
                _logger.error(f"Data publisher port in DCS server [{settings['dataPublisherPort']}] does not match the one in the GUI [{PIX_DATA_SUB_PORT}]")
                print(f"ERROR: Data publisher port in DCS server [{settings['dataPublisherPort']}] does not match the one in the GUI [{PIX_DATA_SUB_PORT}]")
                #update the dcs server
                #self.engine_widget.engine.set_data_publisher_port(PIX_DATA_SUB_PORT)

            if int(settings['publisherPort']) != DCS_SUB_PORT:
                _logger.error(f"Command publisher port in DCS server [{settings['publisherPort']}] does not match the one in the GUI [{DCS_SUB_PORT}]")
                print(f"ERROR: Command publisher port in DCS server [{settings['publisherPort']}] does not match the one in the GUI [{DCS_SUB_PORT}]")
                #update the dcs server
                #self.engine_widget.engine.set_command_publisher_port(DCS_SUB_PORT)

            if int(settings['requestPort']) != DCS_REQ_PORT:
                _logger.error(f"Command request port in DCS server [{settings['requestPort']}] does not match the one in the GUI [{DCS_REQ_PORT}]")
                print(f"ERROR: Command request port in DCS server [{settings['requestPort']}] does not match the one in the GUI [{DCS_REQ_PORT}]")
                #update the dcs server
                #self.engine_widget.engine.set_command_request_port(DCS_REQ_PORT)



    def reload_data_directory(self, data_dir: str=None):
        """
        send out a request to teh remote servers/services to send back teh contents of the data directory
        """
        if data_dir is None:
            data_dir = self.data_dir
            current_date = datetime.now().strftime('%Y-%m-%d')
            data_dir = os.path.join(data_dir, current_date)

        if self.get_device_backend() == 'zmq':
            # request that the DCS sends back the current contents of the data directory
            #current_date = datetime.now().strftime('%Y-%m-%d')
            #self.zmq_reload_data_directory(os.path.join(self.data_dir, current_date))
            self.zmq_reload_data_directory(data_dir)
        else:
            self.nx_server_reload_data_directory(data_dir)

    def get_master_file_seq_names(self, data_dir: str=None,
        thumb_ext="jpg",
        dat_ext="hdf5",
        stack_dir=False,
        num_desired_datafiles=1,
        new_stack_dir=False,
        prefix_char=None,
        dev_backend='epics'
        ) -> list:
        """
        get a list of master file sequence names from the data directory from teh remote
        """
        if data_dir is None:
            data_dir = self.data_dir

        if dev_backend == 'epics':
            cmd_args = {}
            cmd_args['data_dir'] = data_dir
            cmd_args['thumb_ext'] = thumb_ext
            cmd_args['dat_ext'] = dat_ext
            cmd_args['stack_dir'] = stack_dir
            cmd_args['num_desired_datafiles'] = num_desired_datafiles
            cmd_args['new_stack_dir'] = new_stack_dir
            cmd_args['prefix_char'] = prefix_char
            cmd_args['dev_backend'] = dev_backend

            master_seq_jstr = self.send_to_nx_server(NX_SERVER_CMNDS.GET_FILE_SEQUENCE_NAMES, [], '', data_dir, nx_app_def='nxstxm',
                                             host=self.nx_server_host, port=self.nx_server_port,
                                             verbose=False, cmd_args=cmd_args)
            dct = json.loads(master_seq_jstr['seq_name_jstr'])
            # the integer keys have been turned into strings, so we need to convert them back to integers
            master_seq_dct = {}
            keys = dct.keys()
            for key in keys:
                if isinstance(key, str):
                    if key.isdigit():
                        int_key = int(key)
                elif isinstance(key, int):
                    int_key = key
                master_seq_dct[int_key] = dct[key]

        else:
            from cls.utils.file_system_tools import master_get_seq_names

            master_seq_dct = master_get_seq_names(data_dir=data_dir,
                    thumb_ext=thumb_ext,
                    dat_ext=dat_ext,
                    stack_dir=stack_dir,
                    num_desired_datafiles=num_desired_datafiles,
                    new_stack_dir=new_stack_dir,
                    prefix_char=prefix_char,
                    dev_backend=dev_backend)

        return master_seq_dct

    def nx_server_load_data_directory(self, data_dir: str=None, *, extension: str='.hdf5') -> None:
        """
        This function loads the data directory from the DCS server and updates the remote file system info.
        It is used to load the data directory from the DCS server.
        """
        if data_dir is None:
            data_dir = self.data_dir
        #file_lst = self.dcs_server_api.load_directory(data_dir, extension=extension)
        cmd_args = {}
        cmd_args['directory'] = data_dir
        cmd_args['extension'] = extension
        res_dct = self.send_to_nx_server(NX_SERVER_CMNDS.LOADFILE_DIRECTORY, [], '', data_dir, nx_app_def='nxstxm',
                                     host=self.nx_server_host, port=self.nx_server_port,
                                     verbose=False, cmd_args=cmd_args)
        if 'directories' in res_dct.keys():
            file_lst = res_dct['directories']['files']
            if isinstance(file_lst, list):
                self.nx_server_load_files(data_dir, file_lst=file_lst)

            subdir_lst = res_dct['directories']['directories']
            if isinstance(subdir_lst, list):
                for subdir in subdir_lst:
                    #self.nx_server_load_file(data_dir, fname)
                    # cause a directory data thumbnail to be created
                    fname = subdir + extension
                    self.nx_server_load_file(os.path.join(data_dir, subdir), fname, extension=extension)

    def nx_server_load_file(self, data_dir: str=None, fname: str=None, extension: str='.hdf5') -> None:
        """
        This function loads the data directory from the DCS server and updates the remote file system info.
        It is used to load the data directory from the DCS server.
        """
        if data_dir is None:
            data_dir = self.data_dir
        #file_lst = self.dcs_server_api.load_directory(data_dir, extension=extension)
        cmd_args = {}
        cmd_args['directory'] = data_dir
        cmd_args['extension'] = extension
        cmd_args['file'] = os.path.join(data_dir, fname)
        res_dct = self.send_to_nx_server(NX_SERVER_CMNDS.LOADFILE_FILE, [], '', data_dir, nx_app_def='nxstxm',
                                     host=self.nx_server_host, port=self.nx_server_port,
                                     verbose=False, cmd_args=cmd_args)
        # #print(f"ZMQDevManager: nx_server_load_file: {h5_file_dct}")
        if 'directories' in res_dct.keys():
            h5_file_dct = nulls_to_nans(json.loads(res_dct['directories']))
            # emit the signal that new data has arrived, the contact_sheet will be called to create a data thumbnail with
            # this dict
            self.engine_widget.new_data.emit(h5_file_dct)

    def nx_server_load_files(self, data_dir: str=None, *, file_lst: [str], extension='.hdf5') -> None:
        """
        This function loads the data directory from the DCS server and updates the remote file system info.
        It is used to load the data directory from the DCS server.
        """
        if data_dir is None:
            data_dir = self.data_dir
        #file_lst = self.dcs_server_api.load_directory(data_dir, extension=extension)
        cmd_args = {}
        cmd_args['directory'] = data_dir
        cmd_args['extension'] = extension
        fpaths_lst = [os.path.join(data_dir, f) for f in file_lst]
        # most recent first
        #sorted_paths = sorted(fpaths_lst, key=lambda x: int(x.split('/')[-1][1:10]), reverse=True)
        cmd_args['files'] = json.dumps(fpaths_lst)
        res = self.send_to_nx_server(NX_SERVER_CMNDS.LOADFILE_FILES, [], '', data_dir, nx_app_def='nxstxm',
                                     host=self.nx_server_host, port=self.nx_server_port,
                                     verbose=True, cmd_args=cmd_args)
        # data_lst = json.loads(res['data_lst'])
        print(f"ZMQDevManager: nx_server_load_files: {fpaths_lst}")


    def nx_server_request_data_directory_list(self, data_dir: str=None, extension: str='.hdf5') -> None:
        """
        This function requests the data directory list from the DCS server and updates the remote file system info.
        It is used to request the data directory list from the DCS server.
        """
        if data_dir is None:
            data_dir = self.data_dir
        # file_lst = self.dcs_server_api.load_directory(data_dir, extension=extension)
        cmd_args = {}
        cmd_args['directory'] = data_dir
        cmd_args['fileExtension'] = extension
        res_dct = self.send_to_nx_server(NX_SERVER_CMNDS.LIST_DIRECTORY, [], '', data_dir, nx_app_def='nxstxm',
                                         host=self.nx_server_host, port=self.nx_server_port,
                                         verbose=False, cmd_args=cmd_args)
        return res_dct['sub_directories']

    def nx_server_reload_data_directory(self, data_dir: str=None):
        """
        reload the data directory from nxserver
        """
        if data_dir is None:
            _logger.error(
                f"nx_server_reload_data_directory: data_dir passed cannot be None")
            return False

        if self.get_device_backend() == 'epics':
            resp_dct = self.nx_server_load_data_directory(data_dir)
            return True
        else:
            _logger.error(f"nx_server_reload_data_directory: not implemented for this backend ->[{self.get_device_backend()}] ")
            return False

    def zmq_reload_data_directory(self, data_dir: str=None):
        """
        reload the data directory in the zmq engine widget
        """
        if self.get_device_backend() == 'zmq':
            if data_dir is None:
                _data_dir = self.data_dir
                current_date = datetime.now().strftime('%Y-%m-%d')
                self.engine_widget.engine.load_data_directory(data_dir=f'{os.path.join(_data_dir,current_date)}')
            else:
                self.engine_widget.engine.load_data_directory(data_dir=data_dir)
            return True
        else:
            _logger.error(f"zmq_reload_data_directory: not implemented for this backend ->[{self.get_device_backend()}] ")
            return False

    def request_data_dir_list(self, base_dir: str=None):
        """
        request the zmq server to return a list of data directories
        """
        if self.get_device_backend() == 'zmq':
            if base_dir is None:
                _base_dir = self.data_dir
            else:
                _base_dir = base_dir
            return self.zmq_req_data_dir_list(data_dir=_base_dir)
        else:
            return self.nx_server_request_data_directory_list(data_dir=base_dir, extension='.hdf5')
            #_logger.error(f"request_data_dir_list: not implemented for this backend ->[{self.get_device_backend()}] ")


    def zmq_req_data_dir_list(self, data_dir: str=None):
        """
        request the zmq server to return a list of data directories
        """
        if self.get_device_backend() == 'zmq':
            if data_dir is None:
                _data_dir = self.data_dir
            else:
                _data_dir = data_dir
            return self.engine_widget.engine.request_data_directory_list(data_dir=_data_dir)
        else:
            _logger.error(f"zmq_req_data_dir_list: not implemented for this backend ->[{self.get_device_backend()}] ")
            return False

    def get_beamline_cfg_preset(self, preset_name: str =None):
        """
        search the entire bl config dict and return the preset if it exists
        """
        result = None
        if preset_name:
            result = find_key_in_dict(self.beamline_cfg_dct, preset_name)
        return result

    def set_dcs_zoneplate_definitions(self, zp_defs: dict):
        """
        set the zoneplate definitions in the DCS server (assuming this func is called only when BACKEND == 'zmq')
        """
        if self.get_device_backend() == 'zmq':
            self.engine_widget.engine.set_zoneplate_definitions(zp_defs)

    def set_dcs_osa_definitions(self, osa_defs: dict):
        """
        set the zoneplate definitions in the DCS server (assuming this func is called only when BACKEND == 'zmq')
        """
        if self.get_device_backend() == 'zmq':
            self.engine_widget.engine.set_osa_definitions(osa_defs)

    def get_detectors(self) -> dict:
        """
        get the list of seleected detector names from the engine widget
        """
        dct = {}
        if self.get_device_backend() == 'zmq':
            detector_devs = self.get_devices_in_category("DETECTORS")
            det_nms = list(detector_devs.keys())
            # selected_det_names = self.engine_widget.engine.get_selected_detector_names()
            # for det_nm in det_nms:
            #     for sel_det_nm in selected_det_names:
            #         selected = False
            #         if sel_det_nm == det_nm:
            #             selected = True
            #         dct[det_nm] = {'selected': selected, 'dev': detector_devs[det_nm]}
            for det_nm in det_nms:
                dct[det_nm] = {'selected': True, 'dev': detector_devs[det_nm]}
        return dct

    def set_selected_detectors(self, det_nm_lst: [list]):
        """
        set the selected detectors in the engine widget -> BSky or ZMQ DCS server

        Only ZMQ supported at the moment
        """
        if self.get_device_backend() == 'zmq':
            self.engine_widget.engine.select_detectors(det_nm_lst)
        #emit to all connected handlers that the user has selected different detectors
        self.seldets_changed.emit(det_nm_lst)

    def set_oscilloscope_definition(self, osc_def: dict):
        """

        """
        if self.get_device_backend() == 'zmq':
            self.engine_widget.engine.set_oscilloscope_definition(osc_def)

    def dev_exists(self, app_devname):
        """
        takes a device name and returns True if the device exists in the database and False if not
        Parameters
        ----------
        app_devname

        Returns
        -------

        """
        dev = self.device(app_devname)
        if dev:
            return True
        else:
            return False


    def make_linux_data_dir(self, data_dir: str) -> str:
        """
        translate the data_dir from windows to linux
        """
        data_dir = data_dir.replace(self.win_data_dir, self.linux_data_dir)
        data_dir = data_dir.replace("\\", "/")
        return data_dir

    def send_to_nx_server(self, cmnd, run_uids=[], fprefix='', data_dir='', nx_app_def=None, fpaths=[],
                          host='localhost', port=5555, verbose=False, cmd_args={}):
        """
        a function to send data to the nx server over a zmq pubsub socket
        run_uids: tuple of run_uids retuirned from teh RE following a scan
        fprefix: string, data file prefix such as A24040523001
        data_dir: string,  the data directory,
        nx_app_def: string, name like nxstxm, nxptycho
        host='localhost',
        port=5555,
        verbose=False
        """
        res = send_to_server(cmnd, run_uids, fprefix, data_dir, nx_app_def=nx_app_def, fpaths=fpaths, host=host,
                             port=port, verbose=verbose, cmd_args=cmd_args)
        if res == -1:
            _logger.error(
                "There was an error sending/receiving data from nx_server, check that it is running properly")
            print(
                "There was an error sending/receiving data from nx_server, check that it is running properly")
            exit(-1)

        js = res.decode('utf-8')
        res_dct = json_to_dict(js)
        # emit message from exporter for display in teh main GUI log window
        self.export_msg.emit(res_dct)
        # maybe check output here of res
        return res_dct

    def test_nx_server_connection(self):
        """
        before a scan is started check to make sure tha tthe NX serever is ready to receive data
        """
        res = self.send_to_nx_server(NX_SERVER_CMNDS.TEST_CONNECTION, host=self.nx_server_host,
                                     port=self.nx_server_port, verbose=False)
        return res

    def save_nx_files(self, run_uids: list, fprefix: str, data_dir: str, nx_app_def: str = None, host='localhost',
                      port=5555, verbose=False):
        """
        makes calls to save a scan file(s)
        """
        if not self.nx_server_is_windows:
            data_dir = data_dir.replace(self.win_data_dir, self.linux_data_dir)
            data_dir = data_dir.replace("\\", "/")

        res = self.send_to_nx_server(NX_SERVER_CMNDS.SAVE_FILES, run_uids, fprefix, data_dir, nx_app_def=nx_app_def,
                                     host=self.nx_server_host, port=self.nx_server_port,
                                     verbose=verbose)

        # now ask nx server to load the file
        self.nx_server_load_file(data_dir, fprefix)

        return res['status']

    def remove_ptycho_tif_files(self, data_dir: str, fpaths: list, host: str = 'localhost', port: int = 5555,
                                verbose: bool = False) -> bool:
        """
        makes calls to save a scan file(s)
        """
        final_paths = fpaths
        if not self.nx_server_is_windows:
            data_dir = data_dir.replace(self.win_data_dir, self.linux_data_dir)
            data_dir = data_dir.replace("\\", "/")

        res = self.send_to_nx_server(NX_SERVER_CMNDS.REMOVE_FILES, data_dir=data_dir, fpaths=final_paths,
                                     host=self.nx_server_host, port=self.nx_server_port, verbose=verbose)
        return res['status']

    def check_is_nx_server_windows(self, host: str = 'localhost', port: int = 5555, verbose: bool = False) -> bool:
        """
        asks the nx_server what it is running on
        ToDO: implement an elegant solution to the situation that the service is not running
        """
        _logger.debug(
            f"Checking if process [nx_server] is running on host [{self.nx_server_host}] port [{self.nx_server_port}]")
        print(
            f"Checking if process [nx_server] is running on host [{self.nx_server_host}] port [{self.nx_server_port}]")
        if self.test_nx_server_connection():
            _logger.debug(
                f"Yes it is running on host [{self.nx_server_host}] port [{self.nx_server_port}]")
            print(
                f"Yes it is running on host [{self.nx_server_host}] port [{self.nx_server_port}]")
            res = self.send_to_nx_server(NX_SERVER_CMNDS.IS_WINDOWS, host=self.nx_server_host, port=self.nx_server_port,
                                         verbose=verbose)
            if res:
                if res['status'] == NX_SERVER_REPONSES.SUCCESS:
                    return True
        return False

    def check_nx_server_running(self):
        """
        this function looks for specific process'es running on specific OS's, at the moment in only checks
        that nx_server is running, the MAIN_OBJ has already determined if the process is running on windows
        or linux
        """
        if self.nx_server_is_windows:
            return check_windows_procs_running(procs_to_check={
                "DataRecorder Process": ("python.exe", "nx_server.py"),
                "MongoDB": ("mongod.exe", None),
            })
        else:
            # linux
            return self.check_linux_nx_server_running()

    def check_linux_nx_server_running(self):
        '''
        Checks to see if the nx_server.service is running on the host and port given in the beamline configuration

        :return:
        '''
        try:
            ret_dct = self.test_nx_server_connection()
            if ret_dct:
                if 'status' in ret_dct.keys():
                    response = int(ret_dct['status'])
                    if response == NX_SERVER_REPONSES.SUCCESS:
                        return True
            return False
        except:
            _logger.error('check_linux_nx_server_running: server doesnt appear to be running')
        return False

    def set_devdb_path(self, db_path):
        """
        sets the path to the d3evice database used to query device names
        """
        self.devdb_path = pathlib.Path(db_path)
        if self.devdb_path.exists():
            self.dev_db = TinyDB(self.devdb_path.as_posix())
        else:
            _logger.error(f"Path to dev_db [{self.devdb_path}] does not exist")
            exit()

    def set_presets(self, preset_dct):
        #self.main_obj["PRESETS"] = preset_dct
        for k, v in preset_dct.items():
            # do not overwrite any keys that have already been set (most likely by DCS server if there is one
            if k not in self.main_obj["PRESETS"].keys():
                self.main_obj["PRESETS"][k] = v


    def is_device_supported(self, devname):
        """
        check through all of the configured devices and return True if device exists and False if it doesnt
        :param devname:
        :return:
        """
        ret = self.device(devname, do_warn=False)
        return ret

    def get_sample_positioner(self, axis="X"):
        """
        return based on the sample positioning mode which sample positioner
        :return:
        """

        goniometer_mode = self.sample_positioning_mode == sample_positioning_modes.GONIOMETER
        if axis.find("X") > -1:
            if goniometer_mode:
                posner = self.device("DNM_GONI_X")
            else:
                posner = self.device("DNM_SAMPLE_X")
        else:
            if goniometer_mode:
                posner = self.device("DNM_GONI_Y")
            else:
                posner = self.device("DNM_SAMPLE_Y")
        return posner

    def get_sample_fine_positioner(self, axis="X"):
        """
        return based on the sample positioning mode which sample positioner
        :return:
        """

        zoneplate_mode = self.sample_fine_positioning_mode == sample_fine_positioning_modes.ZONEPLATE
        if axis.find("X") > -1:
            if zoneplate_mode:
                posner = self.device("DNM_ZONEPLATE_X")
            else:
                posner = self.device("DNM_SAMPLE_FINE_X")
        else:
            if zoneplate_mode:
                posner = self.device("DNM_ZONEPLATE_Y")
            else:
                posner = self.device("DNM_SAMPLE_FINE_Y")
        return posner

    def get_device_reverse_lu_dct(self):
        return self.main_obj["DEVICES"].device_reverse_lookup_dct

    def set_rot_angle_device(self, dev):
        """
        set the device to be used to retrieve the rsample rotation angle
        :param dev:
        :return:
        """
        self.rot_angle_dev = dev

    def get_sample_rotation_angle(self):
        if self.rot_angle_dev is None:
            return 0.0
        else:
            return self.rot_angle_dev.get_position()

    def cleanup(self):
        # self.zmq_client.terminate()
        pass

    def engine_assign_baseline_devs(self, baseline_dev_lst):
        """
        a list of ophyd devices that will be read and recorded in the data stream 'baseline' once at start of
        scan and once agan at stop

        :param baseline_dev_lst:
        :return:
        """
        self.engine_widget.assign_baseline_devs(baseline_dev_lst)

    def engine_subscribe(self, func):
        sub_id = self.engine_widget.subscribe_cb(func)
        return sub_id

    def set_engine_metadata(self, md_dct):
        """
        pass a dict that will be included in the scan meta data
        :param md_dct:
        :return:
        """
        for k, v in md_dct.items():
            self.engine_widget.engine.md[k] = v

    def get_beamline_id(self):
        return self.beamline_id

    def get_beamline_plugin_dir(self):
        """
        return the beamline plugin directory where all of the scan plugins are located
        """
        return self.beamline_plugin_dir

    def get_sample_positioning_mode(self):
        return self.sample_positioning_mode

    def set_sample_positioning_mode(self, mode):
        self.sample_positioning_mode = mode

    def set_fine_sample_positioning_mode(self, mode):
        self.sample_fine_positioning_mode = mode

    def set_sample_scanning_mode_string(self, mode_str):
        self.sample_scanning_mode_string = mode_str

    def get_sample_scanning_mode_string(self):
        return self.sample_scanning_mode_string

    def get_fine_sample_positioning_mode(self):
        return self.sample_fine_positioning_mode

    def set_datafile_prefix(self, prfx):
        self.datafile_prfx = prfx

    def get_datafile_prefix(self):
        return self.datafile_prfx

    def get_scan_panel_order(self, fname):
        """
        from the beamline configuration file get teh enumeration for the scan_name, the scan_name should match the
        name of the module
        return enumeration if scan_name exists, None if it doesnt
        :param scan_name:
        :return:
        """
        scan_mod_name = get_module_name(fname)

        idx = self.get_preset_as_int(scan_mod_name, "SCAN_PANEL_ORDER")
        return idx

    def get_module_stxm_scan_type_map(self):
        """
        retrieve the list from bl config and turn into proper dict
        """
        dct = {}
        module_type_map = self.beamline_cfg_dct['SCAN_PANEL_STXM_SCAN_TYPES']
        panel_order_dct = self.beamline_cfg_dct['SCAN_PANEL_ORDER']

        for mod_nm, stxm_scan_name in module_type_map.items():
            if stxm_scan_name.find(',') > -1:
                #its a list
                stxm_scan_names = [item.strip() for item in stxm_scan_name.split(",")]
                for s_nm in stxm_scan_names:
                    #dct[s_nm] = {'stxm_scan_name': s_nm, 'panel_idx': int(panel_order_dct[mod_nm])}
                    dct[s_nm] = int(panel_order_dct[mod_nm])
                continue

            #dct[stxm_scan_name] = {'stxm_scan_name': stxm_scan_name, 'panel_idx': int(panel_order_dct[mod_nm])}
            if mod_nm not in panel_order_dct.keys():
                _logger.warn(f"Module name [{mod_nm}] does not have a panel order defined in the beamline configuration")
                print(f"Module name [{mod_nm}] does not have a panel order defined in the beamline configuration")
                continue
            else:
                dct[stxm_scan_name] = int(panel_order_dct[mod_nm])
        return dct

    def get_scan_panel_id_from_scan_name(self, scan_name):
        """
        in order to support the dragging and dropping of other labs nxstxm data we need to take the name of the scan
        and find the appropriate scan in the list of loaded scans and return the panel number for it

        ALSO

        The beamline configuration loads defines the scan panel order, BUT the data file being dropped might have been
        collected by another beamline configuration, in that case the dct passed as mime data might not match the "numer"
        so that is why a string search of what the scan is and what scans are loaded must be done to find the best match
        here is the dct passed as mime data for example:

                {'file': 'T:\\operations\\STXM-data\\ASTXM_upgrade_tmp\\2024\\guest\\2024_05\\0517\\A240517091.hdf5',
                     'scan_type_num': 6,
                     'scan_type': 'sample_image Point_by_Point',
                     'energy': [252.4129180908203],
                     'estart': 252.4129180908203,
                     'estop': 252.46316528320312,
                     'e_npnts': 1,
                     'polarization': 'CircLeft',
                     'offset': 0.0,
                     'angle': 0.0,
                     'dwell': 1.0000000474974513,
                     'npoints': [200, 200],
                     'date': '2024-05-17',
                     'start_time': '20:37:16',
                     'end_time': '20:38:20',
                     'center': [257.4129104614258, 4633.1767578125],
                     'range': [9.999984741210938, 10.0],
                     'step': [0.0502471923828125, 0.05029296875],
                     'start': [252.4129180908203, 4628.1767578125],
                     'stop': [262.41290283203125, 4638.1767578125],
                     'xpositioner': 'DNM_SAMPLE_X',
                     'ypositioner': 'DNM_SAMPLE_Y'
                }

        so use 'scan_type' string to find the match
        """
        # names = scan_name.split(' ')
        # scan_name = names[0]
        panel_order_dct = self.get_module_stxm_scan_type_map()

        if scan_name in  panel_order_dct.keys():
            return panel_order_dct[scan_name]
        else:
            _logger.error(f"Scan type [{scan_name}] does not have an enabled plugin for it")
            print(f"Scan type [{scan_name}] does not have an enabled plugin for it")
            return None

    def set_thumbfile_suffix(self, sffx):
        self.thumbfile_suffix = sffx

    def get_thumbfile_suffix(self):
        return self.thumbfile_suffix

    def get_spatial_region(self, sp_id):
        if sp_id in list(self.main_obj["SCAN_DB"].keys()):
            return self.main_obj["SCAN_DB"][sp_id]
        else:
            return {}

    def set_spatial_region(self, sp_id, dct):
        self.main_obj["SCAN_DB"][sp_id] = dct

    def get_is_multi_region_enabled(self):
        return self.enable_multi_region

    def get_beamline_name(self):
        return self.beamline

    def get_endstation_name(self):
        return self.endstation

    def get(self, name):
        """get the object section by name"""
        obj = dct_get(self.main_obj, name)
        return obj

    def set(self, name, obj):
        """get the object section by name"""
        dct_put(self.main_obj, name, obj)

    def get_main_obj(self):
        """return the entire main object dict"""
        return self.main_obj

    def set_endstation_prefix(self, prfx="uhv"):
        self.endstation_prefix = prfx

    def get_endstation_prefix(self):
        return self.endstation_prefix

    def set_device_backend(self, backend):
        """
        records what backend the devices are using ('epics','zmq')
        """
        self.device_backend = backend

    def get_device_backend(self):
        return self.device_backend

    def set_ptycho_default_cam_nm(self, def_cam_nm):
        self.default_ptycho_cam_nm = def_cam_nm

    def get_default_ptycho_cam(self):
        def_cam = self.device(self.default_ptycho_cam_nm)
        if def_cam == None:
            _logger.error(
                f"It looks like the default ptychography camera[{self.default_ptycho_cam_nm}] does not exist in device database")
        return (def_cam)

    def set_devices(self, dev_cls):
        """assign the device section of themain object"""
        self.main_obj["DEVICES"] = dev_cls

        if self.device_backend == 'zmq':
            # get the devices dictionary in categories and pass it to the zmq_dev_manager
            self.init_zmq_engine_widget(self.main_obj["DEVICES"].get_devices())

        self.reload_data_directory()

        self.changed.emit()



    def device(self, name, do_warn=True):
        """return the device if it exists"""
        dev = None
        dn_lst = self.dev_db.search(devq.name == name)
        if len(dn_lst) > 0:
            # dev = self.main_obj['DEVICES'].device(name, do_warn=do_warn)
            dev_dct = dn_lst[0]
            cat = dev_dct["category"]
            dev = self.main_obj["DEVICES"].devices[cat][name]
        if dev is None:
            if do_warn:
                _logger.warn("Warning: dev [%s] does not exist in master object" % name)
        return dev

    def get_device_obj(self):
        return self.main_obj["DEVICES"]

    def get_devices_in_category(self, category=None, pos_type=None):
        """call the device method from the devices class"""
        # if category in self.main_obj['DEVICES'].keys():
        #     return (self.main_obj['DEVICES'][category].get_devices())
        # else:
        #     return(None)

        devs = {}
        if category is None:
            # return all devices
            dn_lst = self.dev_db.all()

        elif pos_type:
            # get all in category that are also in the position set of endstation or beamline
            dn_lst = self.dev_db.search(
                (devq.category == category) & (devq.pos_type == pos_type)
            )
        else:
            # get all in category
            dn_lst = self.dev_db.search(devq.category == category)

        if len(dn_lst) > 0:
            # dev = self.main_obj['DEVICES'].device(name, do_warn=do_warn)
            for dev_dct in dn_lst:
                name = dev_dct["name"]
                cat = dev_dct["category"]
                # devs.append(self.main_obj['DEVICES'].devices[cat][name])
                devs[name] = self.main_obj["DEVICES"].devices[cat][name]
            return devs
        else:
            return None

    def get_devices(self):
        """call the device method from the devices class"""
        return self.main_obj["DEVICES"].get_devices()

    def get_sscan_prefix(self):
        return self.main_obj["DEVICES"].sscan_rec_prfx

    def get_device_list(self, detectors=False):
        return self.main_obj["DEVICES"].get_device_list(detectors)

    def add_scan(self, scan):
        """add a scan to the list of scans to execute"""
        self.main_obj["SSCANS"].append(scan)
        self.changed.emit()

    def clear_scans(self):
        """delete all scans from list of scans to execeute"""
        self.main_obj["SSCANS"] = []
        self.changed.emit()

    # def get_preset(self, name):
    #     devices = self.get_devices()
    #     if(name in list(devices['PRESETS'].keys())):
    #         return(devices['PRESETS'][name])
    #     else:
    #         _logger.warn('PRESET [%s] not found in device configuration' % name)
    #         return(None)
    def get_preset_section(self, section):
        presets = self.main_obj["PRESETS"]
        sections = presets.keys()
        if section in sections:
            return presets[section]
        else:
            return None


    def get_preset(self, name, section=None):
        """
        search through all sections looking for the FIRST instance of the desired preset, this is case insensitive
        :param name:
        :param section: is section is None, then search entire PRESET dict
        :return:
        """
        result = None
        name_upper = name.upper()
        name_lower = name.lower()

        presets = self.main_obj["PRESETS"]
        sections = presets.keys()
        if section:
            if section in sections:
                if name_upper in presets[section].keys():
                    result = presets[section][name_upper]
                elif name_lower in presets[section].keys():
                    result = presets[section][name_lower]
                else:
                    _logger.debug(
                        "PRESET [%s][%s] not found in presets" % (section, name)
                    )
        else:
            for s in sections:
                if name_upper in list(presets[s].keys()):
                    result = presets[s][name_upper]
                    break
                if name_lower in list(presets[s].keys()):
                    result = presets[s][name_lower]
                    break
        if result is None:
            _logger.debug("PRESET [%s] not found in presets" % name)

        return result

    def get_preset_as_float(self, name, section=None):
        val = self.get_preset(name, section)
        if val is not None:
            return float(val)
        else:
            return None

    def get_preset_as_int(self, name, section=None):
        val = self.get_preset(name, section)
        if val is not None:
            return int(val)
        else:
            return None

    def get_preset_as_bool(self, name, section=None):
        val = self.get_preset(name, section)
        if val is not None:
            if val.lower().find("true") > -1:
                return True
            else:
                return False
        else:
            return False

    def get_preset_as_dict(self, name, section=None):
        val = self.get_preset(name, section)
        if val is not None:
            val = val.replace("'", '"')
            dct = json_to_dict(val)
            return dct
        else:
            return {}

    def take_positioner_snapshot(self, posners_dct):
        """
        take_positioner_snapshot(): description

        :param posners_dct: posners_dct description
        :type posners_dct: posners_dct type

        :returns: None
        """
        """
        This function grabs the current values of all positioners for the 
        data saving thread to use

        """
        dct = {}
        for k in list(posners_dct.keys()):
            dct[k] = {}
            dct[k]["VELO"] = posners_dct[k].get("velocity")
            dct[k]["VAL"] = posners_dct[k].get("user_setpoint")
            dct[k]["DESC"] = posners_dct[k].get("description")
            dct[k]["NAME"] = posners_dct[k].get_name()
            dct[k]["ACCL"] = posners_dct[k].get("acceleration")
            # dct[k]['RRBV'] = posners_dct[k].get('raw_readback')
            dct[k]["LLM"] = posners_dct[k].get_low_limit()
            dct[k]["HLM"] = posners_dct[k].get_high_limit()
            # dct[k]['RDBD'] = posners_dct[k].get('retry_deadband')
            dct[k][RBV] = posners_dct[k].get("user_readback")

        return dct

    def take_detectors_snapshot(self, detectors_dct):
        """
        take_detectors_snapshot(): description

        :param detectors_dct: detectors_dct description
        :type detectors_dct: detectors_dct type

        :returns: None
        """
        """
        This function grabs the current values of all detectors for the 
        data saving thread to use

        """
        dct = {}
        for k in list(detectors_dct.keys()):
            dct[k] = {}
            # need some compatibility between detectors that are straight ophyd devices and those that are Qt/ophyd devices
            if hasattr(detectors_dct[k], "_ophyd_dev"):
                odev = detectors_dct[k]._ophyd_dev
                dct[k][RBV] = odev.read()[odev.name]["value"]
            else:
                rd_key = list(detectors_dct[k].read().keys())[0]
                dct[k][RBV] = detectors_dct[k].read()[rd_key]["value"]
        return dct

    def take_pvs_snapshot(self, pvs_dct):
        """
        take_pvs_snapshot(): description

        :param pvs_dct: pvs_dct description
        :type pvs_dct: pvs_dct type

        :returns: None
        """
        """
        This function grabs the current values of all positioners for the 
        data saving thread to use

        """
        try:
            dct = {}
            for k in list(pvs_dct.keys()):
                dct[k] = {}
                dct[k][RBV] = pvs_dct[k].get_position()
                dct[k]["PVNAME"] = pvs_dct[k].get_name()

            return dct
        except:
            print("Problem connecting to pv [%s]" % k)

    def take_temps_snapshot(self, pvs_dct):
        """
        take_temps_snapshot(): description

        :param pvs_dct: pvs_dct description
        :type pvs_dct: pvs_dct type

        :returns: None
        """
        """
        This function grabs the current values of all temperatures for the
        data saving thread to use

        """
        dct = {}
        for k in list(pvs_dct.keys()):
            dct[k] = {}
            rbv = pvs_dct[k].get_position()
            if rbv is None:
                dct[k][RBV] = -99999.0
            else:
                dct[k][RBV] = rbv

            desc = pvs_dct[k].get_desc()
            if desc is None:
                dct[k]["DESC"] = "Not Connected"
            else:
                dct[k]["DESC"] = desc

            egu = pvs_dct[k].get_egu()
            if egu is None:
                dct[k]["EGU"] = "Unknown"
            else:
                dct[k]["EGU"] = egu

        return dct

    def take_pressures_snapshot(self, pvs_dct):
        """
        take_pressures_snapshot(): description

        :param pvs_dct: pvs_dct description
        :type pvs_dct: pvs_dct type

        :returns: None
        """
        """
        This function grabs the current values of all pressures for the
        data saving thread to use

        """
        dct = {}
        for k in list(pvs_dct.keys()):
            dct[k] = {}
            rbv = pvs_dct[k].get_position()
            desc = pvs_dct[k].get_desc()
            egu = pvs_dct[k].get_egu()
            if rbv is None:
                dct[k][RBV] = -99999.0
            else:
                dct[k][RBV] = rbv

            dct[k]["DESC"] = desc
            dct[k]["EGU"] = egu

        return dct


class dev_config_base(QtCore.QObject):
    def __init__(self, splash=None):
        super(dev_config_base, self).__init__()

        if splash is None:
            # self.splash = CSplashScreen("Starting to connect devices:")
            # self.splash = SplashScreen()
            # RUSS FEB25 self.splash = get_splash()
            self.splash = None
        else:
            self.splash = splash

        self.devices = {}
        self.devices["POSITIONERS"] = {}
        self.devices["TEMPERATURES"] = {}
        # self.devices['TEMPERATURES'][POS_TYPE_ES] = {}    # Endstation temperatures
        # self.devices['TEMPERATURES'][POS_TYPE_BL] = {}    # Beamline temperatures
        self.devices["PRESSURES"] = {}
        # self.devices['PRESSURES'][POS_TYPE_ES] = {}    # Endstation pressures
        # self.devices['PRESSURES'][POS_TYPE_BL] = {}    # Beamline pressures

        self.devices["DETECTORS"] = {}
        self.devices["DETECTORS_NO_RECORD"] = {}
        self.devices["DIO"] = {}
        self.devices["SSCANS"] = {}
        self.devices["PVS"] = {}
        self.devices["PVS_DONT_RECORD"] = {}
        self.devices["HEARTBEATS"] = {}
        # self.devices['PRESETS'] = {}
        self.devices["ACTUATORS"] = {}
        self.devices["WIDGETS"] = {}

        self.snapshot = {}
        self.snapshot["HEARTBEATS"] = {}

        # provide a variable that will hold a list of positioners that are excluded from being offered on the GUI
        self.exclude_list = []

        self.sscan_rec_prfx = None  # either 'ambient' or 'uhv'
        self.es_id = None  # needs to be defined by inheriting class

        self.posner_reverse_lookup_dct = {}

        self.dev_dct = None

    def get_dev_dct(self, fpath):
        """
        This is a convienience function which handles relative imports for all scan pluggins of their respective scan classes.
        I was unable to make relative imports work when i moved the scan pluggins into their own bl_config directories so
        this function was created to handle the import.

        fpath: is the path to the calling scan pluggin, typically passed in as __file__
        mod_nm: is the module that contains the desired scan class
        cls_nm: is the scan class name in the module that the caller needs

        in order for teh module to be imported its path must be added to sys.path

        """
        mod_dir = pathlib.Path(os.path.abspath(fpath))
        sys.path.append(str(mod_dir.parent))
        # get the name of the beamline config directory
        bl_config_dirname = mod_dir.name.replace(".py", "")
        # construct a string with an absolute path to the module
        _import_str = (
            _import_str
        ) = f"cls.applications.pyStxm.bl_configs.{bl_config_dirname}.devs"
        # import the module
        _mod = import_module(_import_str, package=None)
        # now get a reference to the dev-dct
        dev_dct = getattr(_mod, "dev_dct")
        return dev_dct

    def parse_cainfo_stdout_to_dct(self, s):
        dct = {}
        s2 = s.split("\n")
        for l in s2:
            l2 = l.replace(" ", "")
            l3 = l2.split(":")
            if len(l3) > 1:
                dct[l3[0]] = l3[1]
        return dct

    def do_pv_conn_check(self, num_pvs, pvname, verbose=False):
        import subprocess

        proc = subprocess.Popen("cainfo %s" % pvname, stdout=subprocess.PIPE)
        stdout_str = proc.stdout.read()
        _dct = self.parse_cainfo_stdout_to_dct(stdout_str.decode("utf-8"))
        if verbose:
            if self.check_cainfo(_dct):
                print(
                    "[%d] pv connection check [%s] is connected and ready"
                    % (num_pvs, pvname)
                )
        else:
            if self.check_cainfo(_dct):
                print("", end=".")
            else:
                # just make a new line for the error that will be printed shortly
                print()
        return _dct

    def perform_device_connection_check(self, verbose=False):

        print(
            "Performing individual device connection check, this may take a few minutes depending:"
        )
        skip_lst = ["PVS_DONT_RECORD", "PRESETS", "DETECTORS_NO_RECORD", "WIDGETS"]
        dev_dct = {}
        num_pvs = 0
        num_fail_pvs = 0
        sections = list(self.devices.keys())
        for section in sections:
            keys = []
            if section not in skip_lst:
                keys = list(self.devices[section].keys())
                # check to see if this is a subsectioned section that has pvs for BL (beamline) and ES (endstation)
                # if so do those
                if keys == ["BL", "ES"]:
                    dev_dct[section] = {}
                    for subsec in keys:
                        for pvname in list(self.devices[section][subsec].keys()):
                            num_pvs += 1
                            _dct = self.do_pv_conn_check(
                                num_pvs, self.build_pv_name(pvname), verbose
                            )
                            dev_dct[section][pvname] = {}
                            dev_dct[section][pvname]["dev"] = self.devices[section][
                                subsec
                            ][pvname]
                            dev_dct[section][pvname]["cainfo"] = _dct
                            if not self.check_cainfo(_dct):
                                num_fail_pvs += 1
                                print(
                                    "[%d][%s] does not appear to exist" % (num_pvs, k)
                                )

                else:
                    for k in keys:
                        dev = self.devices[section][k]
                        dev_dct[section] = {}
                        dev_dct[section][k] = {}
                        if type(dev) is dict:
                            for kk in dev.keys():
                                num_pvs += 1
                                dev_dct[section][k][kk] = {}
                                dev_dct[section][k][kk]["dev"] = dev[kk]
                                _dct = self.do_pv_conn_check(
                                    num_pvs, self.build_pv_name(dev[kk]), verbose
                                )
                                dev_dct[section][k][kk]["cainfo"] = _dct
                                if not self.check_cainfo(_dct):
                                    num_fail_pvs += 1
                                    print(
                                        "[%d][%s] does not appear to exist"
                                        % (num_pvs, dev[kk].prefix)
                                    )

                        else:
                            num_pvs += 1
                            _dct = self.do_pv_conn_check(
                                num_pvs, self.build_pv_name(dev), verbose
                            )
                            dev_dct[section][k]["cainfo"] = _dct
                            if not self.check_cainfo(_dct):
                                num_fail_pvs += 1
                                print(
                                    "[%d][%s] does not appear to exist"
                                    % (num_pvs, dev.prefix)
                                )

        # report
        if num_fail_pvs > 0:
            print(
                "\n%d devices failed to connect out of a total of %d"
                % (num_fail_pvs, num_pvs)
            )
            exit()
        else:
            print("\nall %d devices are connected" % (num_pvs))

    def build_pv_name(self, dev):
        pvname = None
        if hasattr(dev, "component_names"):
            # just use the first one
            a = getattr(dev, dev.component_names[0])
            pvname = a.pvname
        else:
            pvname = dev.prefix
        return pvname

    def check_cainfo(self, d):
        if d is None:
            return False
        if len(d) == 0:
            return False
        if d["State"].find("dis") > -1:
            return False
        return True

    def devs_as_list(self, skip_lst=["DNM_RING_CURRENT"]):
        """
        this function pulls the names of all the devices that have been configured so that it can be passed on to the RunEngine
        and recorded into the proper datastream during datacollection.
        Skipping RING_CURRENT because it is included as part of the primary data stream and bluesky will complain if it sees
        that device name in the baseline list of devices to record
        :return:
        """
        _logger.debug("devs_as_list: returning list of Devices")
        dlst = []
        for k, dev in self.devices["TEMPERATURES"].items():
            # print('devs_as_list: [%s]' % k)
            if k in skip_lst:
                # skip it
                continue
            ophyd_dev = dev.get_ophyd_device()
            if ophyd_dev is not None:
                dlst.append(ophyd_dev)

        for k, dev in self.devices["PRESSURES"].items():
            # print('devs_as_list: [%s]' % k)
            if k in skip_lst:
                # skip it
                continue
            ophyd_dev = dev.get_ophyd_device()
            if ophyd_dev is not None:
                dlst.append(ophyd_dev)

        for k, ophyd_dev in self.devices["POSITIONERS"].items():
            # print('devs_as_list: [%s]' % k)
            if k in skip_lst:
                # skip it
                continue
            if ophyd_dev is not None:
                dlst.append(ophyd_dev)

        for k, dev in self.devices["PVS"].items():
            if k in skip_lst:
                # skip it
                continue
            dev_nm = dev.get_name()
            if dev_nm.find(".") > -1:
                # skip pv's with a .field cause they screwup BlueSky
                # print('devs_as_list: SKIPPING: [%s]' % k)
                continue
            if hasattr(dev, "get_ophyd_device"):
                ophyd_dev = dev.get_ophyd_device()
                if ophyd_dev is not None:
                    # print('devs_as_list: [%s]' % k)
                    dlst.append(ophyd_dev)

        return dlst

    def close_splash(self):
        self.splash.close()

    def on_timer(self):
        print("main_object.py: on_timer()")
        QtWidgets.QApplication.processEvents()

    def msg_splash(self, msg):

        now = datetime.now()  # current date and time
        date_time = now.strftime("%m/%d/%Y, %H:%M:%S")
        print("%s: %s" % (date_time, msg))
        # return
        if self.splash:
            self.splash.show_msg(self.splash.tr(msg))

    def set_exclude_positioners_list(self, excl_lst):
        self.exclude_list = excl_lst

    def get_exclude_positioners_list(self):
        return self.exclude_list

    def get_all_pvs_of_type(self, category_name=None):
        # first check for cetegory then in PV_DONT_RECORD
        if category_name in self.devices.keys():
            return self.devices[category_name]
        # look in PVS_DONT_RECORD
        pv_devs = self.devices["PVS_DONT_RECORD"]
        if category_name in list(pv_devs.keys()):
            return pv_devs[category_name]
        else:
            _logger.warning(
                "Pvs of type [%s] not found in devices or PVS_DONT_RECORD configuration"
                % category_name
            )
            return None

    def get_all_temperatures(self, category_name=None):
        if category_name is None:
            return dct_merge(
                self.devices["TEMPERATURES"][POS_TYPE_ES],
                self.devices["TEMPERATURES"][POS_TYPE_BL],
            )

        elif category_name == POS_TYPE_ES:
            return self.devices["TEMPERATURES"][POS_TYPE_ES]
        elif category_name == POS_TYPE_BL:
            return self.devices["TEMPERATURES"][POS_TYPE_BL]
        else:
            _logger.warning(
                "Temperature Category [%s] not found in temperature configuration"
                % category_name
            )
            return None

    def get_tm(self, name):
        if name in list(self.devices["TEMPERATURES"][POS_TYPE_ES].keys()):
            return self.devices["TEMPERATURES"][POS_TYPE_ES][name]
        elif name in list(self.devices["TEMPERATURES"][POS_TYPE_BL].keys()):
            return self.devices["TEMPERATURES"][POS_TYPE_BL][name]
        else:
            _logger.warning(
                "Temperature [%s] not found in temperature configuration" % name
            )
            return None

    def get_all_pressures(self, category_name=None):
        """
        someday this should use the device database but its too much work right now
        """
        if category_name is None:
            return dct_merge(
                self.devices["PRESSURES"][POS_TYPE_ES],
                self.devices["PRESSURES"][POS_TYPE_BL],
            )

        elif category_name == POS_TYPE_ES:
            return self.devices["PRESSURES"][POS_TYPE_ES]
        elif category_name == POS_TYPE_BL:
            return self.devices["PRESSURES"][POS_TYPE_BL]
        else:
            _logger.warning(
                "Pressure Category [%s] not found in pressures configuration" % name
            )
            return None

    def get_pressure(self, name):
        if name in list(self.devices["PRESSURES"][POS_TYPE_ES].keys()):
            return self.devices["PRESSURES"][POS_TYPE_ES][name]
        elif name in list(self.devices["PRESSURES"][POS_TYPE_BL].keys()):
            return self.devices["PRESSURES"][POS_TYPE_BL][name]
        else:
            _logger.warning("Pressure [%s] not found in pressures configuration" % name)
            return None

    def get_widget(self, name):
        if name in list(self.devices["WIDGETS"].keys()):
            return self.devices["WIDGETS"][name]
        else:
            _logger.warning("Widget [%s] not found in widgets configuration" % name)
            return None

    def device(self, name, do_warn=True):
        """
            search entire device database looking for device
        :param name:
        :param do_warn:
        :return:
        """
        for cat in list(self.devices.keys()):
            if name in list(self.devices[cat].keys()):
                return self.devices[cat][name]
        if do_warn:
            _logger.debug("Device [%s] not found in device configuration" % name)
        return None

    def device_report(self):
        """
        dump a report of all devices
        :return:
        """
        skip_list = ["PRESETS", "WIDGETS", "ACTUATORS"]
        for category in list(self.devices.keys()):
            print("[%s]" % category)
            if category in skip_list:
                continue
            for name in list(self.devices[category].keys()):
                if (name.find("ES") > -1) or (name.find("BL") > -1):
                    for _name in list(self.devices[category][name].keys()):
                        self.devices[category][name][_name].report()
                elif name.find("HEARTBEATS") > -1:
                    for _name in list(self.devices[category][name].keys()):
                        self.devices[category][name][_name]["dev"].report()

                else:
                    # print('NAME=[%s]' % name)
                    if type(self.devices[category][name]) == list:
                        for _dev in list(self.devices[category][name]):
                            _dev.report()
                    else:
                        self.devices[category][name].report()

    def init_snapshot(self):
        self.snapshot = dict.copy(self.devices)

    def get_posner_snapshot(self):
        return self.snapshot["POSITIONERS"]

    def get_devices(self):
        return self.devices

    def get_device_list(self, detectors=False):
        if detectors:
            dets = list(self.devices["DETECTORS"].keys())
            if 'DNM_SIS3820' in dets:
                # retrievce all channel names as if they were individual detectors
                sis3820 = self.device('DNM_SIS3820')
                sis3820_chan_nms = sis3820.get_all_channel_names()
                dets.remove('DNM_SIS3820')
                return (dets + sis3820_chan_nms)
            else:
                return list(self.devices["DETECTORS"].keys())
        else:
            return list(self.devices["POSITIONERS"].keys())

    def init_scans(self, scan_prefix):
        scans = []
        for i in range(1, 17):
            scans.append(Scan(scan_prefix + ":scan%d" % (i)))

        return scans
