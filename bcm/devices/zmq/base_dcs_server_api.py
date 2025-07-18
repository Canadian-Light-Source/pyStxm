from typing import Union

from PyQt5 import QtCore

from cls.utils.log import get_module_logger

_logger = get_module_logger(__name__)

class BaseDcsServerApi(QtCore.QObject):

    new_data = QtCore.pyqtSignal(object) # a signal to be emitted when new data arrives
    scan_status = QtCore.pyqtSignal(object)  # a signal to be emitted when scan status changes
    progress = QtCore.pyqtSignal(object)  # a signal to be emitted when scan status changes
    exec_result = QtCore.pyqtSignal(object)
    msg_to_app = QtCore.pyqtSignal(object) # a singal used to send message to the app from the DCS server,
                                           # ex: filename to tell app what teh filename and data dir are before scan
                                           # execution

    def __init__(self, parent):
        super().__init__(None)
        self.parent = parent
        self.paused = False
        self.app_to_dcs_devname_map = {}
        self.dcs_to_app_devname_map = {}
        self._loadfile_timer = QtCore.QTimer()
        self._loadfile_timer.setSingleShot(True)
        self._loadfile_timer.timeout.connect(self.load_file)
        # args used by load_file
        self._loadfile_directory = None
        self._loadfile_file_name = None

        self.exec_result.connect(self.on_exec_finished)

    def load_file(self, directory: str="/tmp/2025-07-04", filename: str="SampleData.hdf5"):
        """
        load a file from the DCS server, to be implemented by inheriting class
        Args:
            directory: the directory to load the file from
            filename: the name of the file to load

        """
        _logger.warning("BaseDcsServerApi.load_file: This method should be implemented by the inheriting class.")
        #

    def get_base_data_dir(self):
        """
        return value from DCS server
        to be implemented by the inheriting class
        """
        pass

    def get_data_file_extension(self):
        """
        return value from DCS server
        to be implemented by the inheriting class
        """
        pass


    def load_file(self, directory: str="/tmp/2025-07-04", filename: str="SampleData.hdf5"):
        """
        load a file from the DCS server, to be implemented by inheriting class
        Args:
            directory: the directory to load the file from
            filename: the name of the file to load

        """
        pass

    def set_device_name_maps(self, app_to_dcsname_map: dict, dcs_to_appname_map: dict):
        """
        set the device name maps for this server api
        Args:
            app_to_dcsname_map: map from app device names to dcs device names
            dcs_to_appname_map: map from dcs device names to app device names
        """
        self.app_to_dcs_devname_map = app_to_dcsname_map
        self.dcs_to_app_devname_map = dcs_to_appname_map

    def on_exec_finished(self, msg):
        """
        process the scanFinished message into a standard dict the UI can use
        to be implemented by the inheriting class
         in which it will emit:
            self.parent.exec_result.emit(msg)
        """
        pass

    def make_scan_finished_dct(self):
        """
        create a standard dict that teh UI will use when a scan is finished on a DCS server
        """
        dct = {}
        dct['file_name'] = None
        dct['local_base_dir'] = None
        dct['dcs_server_base_dir'] = None
        dct['flags'] = None
        dct['run_uids'] = []

        return dct


    def _update_device_feedback(self, dcs_devname: str, value: Union[int, float], app_devname: str=None) -> None:
        """
        a convenience function to find the ZMQ device and call update_position()
        Parameters
        ----------
        dcs_devname

        Returns
        -------

        """

        if app_devname is None:
            app_devname = self.parent.dcs_to_appname_map[dcs_devname]
        if app_devname in self.parent.devs.keys():
            #print(f"_update_device_feedback: updating [{app_devname}={value}]")
            dev = self.parent.devs[app_devname]['dev']
            #print(f"_update_device_feedback: dev.name={dev.name} dcs_devname={dcs_devname} app_devname={app_devname} value={value}")
            dev.update_position(value, False)

    def _update_device_status(self, dcs_devname: str, value: Union[int, float, str], app_devname: str=None) -> None:
        """
        a convenience function to find the ZMQ device and call update_position()
        Parameters
        ----------
        dcs_devname

        Returns
        -------

        """

        if app_devname is None:
            app_devname = self.parent.dcs_to_appname_map[dcs_devname]
        if app_devname in self.parent.devs.keys():
            #print(f"_update_device_feedback: updating [{app_devname}={value}]")
            dev = self.parent.devs[app_devname]['dev']
            dev.update_device_status(value)

    def _update_detector_device_feedback(self, dct: dict) -> None:
        """
        a convenience function to find the ZMQ detector device and call update_position()
        Parameters
        ----------
        dcs_devname

        Returns
        -------

        """
        dcs_devname = dct['det_name']
        value = dct['value']

        app_devname = self.parent.dcs_to_appname_map[dcs_devname]
        dct["app_devname"] = app_devname
        if app_devname in self.parent.devs.keys():
            dev = self.parent.devs[app_devname]['dev']
            #dev.update_position(value, False)
            if hasattr(dev, 'waveform_changed'):
                dev.waveform_changed(dct)

    def connect_to_dcs_server(self) -> bool:
        """
        Connect to the DCS server and sort info returned from dcs server into sections in a dict
        sections include: 'POSITIONERS', 'DETECTORS', 'PRESSURES','TEMPERATURES','PVS'
        in self.parent.devices

        To be implemented by inheriting class
        Parameters
        ----------
        self

        Returns
        -------

        """
        print("BaseDcsServerApi: connect_to_dcs_server: has not been implemented")
        return False

    def get_detector_names(self) -> [str]:
        """
        To be implemented by inheriting class
        Parameters
        ----------
        self

        Returns: list of strings
        -------

        """
        print("BaseDcsServerApi: get_detector_names: has not been implemented")

    def set_detector_names(self, det_names: [str]) -> None:
        """
        To be implemented by inheriting class
        Parameters
        ----------
        det_names: list

        Returns
        -------

        """
        print("BaseDcsServerApi: set_detector_names: has not been implemented")

    def get_selected_detector_names(self) -> [str]:
        """
        To be implemented by inheriting class
        Parameters
        ----------
        self

        Returns: list of strings
        -------

        """
        print("BaseDcsServerApi: get_selected_detector_names: has not been implemented")

    def start_scan(self, scan_def: dict) -> bool:
        """
        To be implemented by inheriting class
        Parameters
        ----------
        self

        Returns
        -------

        """
        print("BaseDcsServerApi: start_scan: has not been implemented")
        return False

    def move_positioner(self, name: str, value: float) -> bool:
        """
        To be implemented by inheriting class
        Parameters
        ----------
        self

        Returns True if sent successful else False
        -------

        """
        print("BaseDcsServerApi: move_positioner: has not been implemented")
        return False

    def stop_positioner(self, name: str) -> bool:
        """
        To be implemented by inheriting class
        Parameters
        ----------
        name: of the positioner

        Returns
        -------

        """
        print("BaseDcsServerApi: stop_positioner: has not been implemented")
        return False

    def get_positioner_details(self, name: str) -> dict:
        """
        To be implemented by inheriting class
        Parameters
        ----------
        name: of the positioner

        Returns: dict of positioner details
        -------

        """
        print("BaseDcsServerApi: get_positioner_details: has not been implemented")
        return {}

    def get_zoneplate_definitions(self) -> dict:
        """
        To be implemented by inheriting class
        Parameters
        ----------

        Returns: dict of zoneplates configured on the dcs server
        -------

        """
        print("BaseDcsServerApi: get_zoneplate_definitions: has not been implemented")
        return {}

    def set_zoneplate_definitions(self, zp_defs: dict) -> bool:
        """
        To be implemented by inheriting class
        Parameters
        ----------
        name: of the zoneplate
        zp_def: dict of zoneplate details

        Returns: bool True for success False for failed
        -------

        """
        print("BaseDcsServerApi: set_zoneplate_definitions: has not been implemented")
        return False

    def get_osa_definitions(self) -> dict:
        """
        To be implemented by inheriting class
        Parameters
        ----------
        name: of the osa

        Returns: dict of positioner details
        -------

        """
        print("BaseDcsServerApi: get_osa_definitions: has not been implemented")
        return {}

    def set_osa_definitions(self, osa_defs: dict) -> bool:
        """
        To be implemented by inheriting class
        Parameters
        ----------
        name: of the osa
        zp_def: dict of osa details

        Returns: bool True for success False for failed
        -------

        """
        print("BaseDcsServerApi: set_osa_definitions: has not been implemented")
        return False

    def set_oscilloscope_definition(self, osc_def: dict) -> bool:
        """
        To be implemented by inheriting class
        Parameters
        ----------
        name: of the osa
        zp_def: dict of osa details

        Returns: bool True for success False for failed
        -------

        """
        print("BaseDcsServerApi: set_oscilloscope_definition: has not been implemented")
        return False

    def on_new_data(self, data: dict) -> None:
        """
        To be implemented by inheriting class
        Parameters
        ----------
        data: data from server to app

        Returns: None
        -------

        """
        print(f"BaseDcsServerApi: on_new_data: emitting [{data}]")
        self.new_data.emit(data)

    def on_msg_to_app(self, data: dict) -> None:
        """
        To be implemented by inheriting class
        Parameters
        ----------
        data: data from server to app

        Returns: None
        -------

        """
        pass


    def on_init_beamline_components(self,components_dct: dict) -> None:
        """
            param: components_dct: a dict that carry the list component params for that component type

            This function initializes the member variable self.parent.dcs_server_config = {}
                self.parent.dcs_server_config['OSAS'] = {}
                self.parent.dcs_server_config['ZONEPLATES'] = {}

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
        # to be implemented by inheriting class
        pass

    def set_zoneplate_definitions(self, zp_defs: dict) -> bool:
        """
        a function to send the zoneplate definition dictionary to the DCS server

        returns True if successful or False if failed
        """
        # to be implemented by inheriting class
        print("BaseDcsServerApi: set_zoneplate_definitions: has not been implemented")
        return False

    def set_osa_definitions(self, osa_defs: dict) -> bool:
        """
        a function to send the osa definition dictionary to the DCS server

        returns True if successful or False if failed
        """
        # to be implemented by inheriting class
        print("BaseDcsServerApi: set_osa_definitions: has not been implemented")
        return False

    def select_detectors(self, det_nm_lst):
        """
        send the message to the DCS server to select the detectors by name
        """
        # to be implemented by inheriting class
        print("BaseDcsServerApi: select_detectors: has not been implemented")



