import os
import zmq
import zmq.asyncio
import queue
import asyncio
import pprint
import simplejson as json

from PyQt5.QtCore import QTimer, pyqtSignal, QObject
from PyQt5.QtWidgets import QWidget

from bcm.devices.zmq.zmq_server_thread import ZMQServerThread
from bcm.devices.zmq import dcs_server_name

from cls.utils.prog_dict_utils import set_prog_dict, make_progress_dict
from cls.utils.environment import get_environ_var
from cls.utils.ssh.port_forwarding_utils import is_port_forwarded
from cls.utils.process_utils import is_linux_process_running
from cls.appWidgets.dialogs import message_no_btns

DCS_HOST = get_environ_var('DCS_HOST')
DCS_HOST_PROC_NAME = get_environ_var('DCS_HOST_PROC_NAME')
DCS_SUB_PORT = int(get_environ_var('DCS_SUB_PORT'))
DCS_REQ_PORT = int(get_environ_var('DCS_REQ_PORT'))

HOST_IS_LOCAL = True

if is_port_forwarded(DCS_SUB_PORT):
    # check to see if even though the ports are forwarded Pixelator is running on the same machine as this one
    if not is_linux_process_running(DCS_HOST_PROC_NAME):
        # message_no_btns(f"Remote [{DCS_HOST_PROC_NAME}] DCS Detected", f"It has been detected that the DCS server for [{DCS_HOST_PROC_NAME}] is remote because it "
        #                     f"appears the DCS ports ({DCS_SUB_PORT},{DCS_REQ_PORT}), are being forwarded, \n"
        #                     f"\tjust wanted to let you know",
        #                 )
        HOST_IS_LOCAL = False

if dcs_server_name.find(DCS_HOST_PROC_NAME.lower()) > -1:
    from bcm.devices.zmq.pixelator.pixelator_dcs_server_api import DcsServerApi
else:
    # not supported
    print("zmq_dev_manager.py: NO DCS SERVER SPECIFIED, exiting")
    exit(1)


class ZMQRunEngine(QObject):
    """
    the main ZMQ device manager that creates the ZMQ context and socket,
    it processes the commands received in the queue, it also keeps a dict of devices so that it can pass the command to
    the correct device on either side of the ZMQ connection:

    [ pyQt App, ZMQDevManager ] <---- ZMQ socket PAIR ----> {pixelator, Contrast, etc}

    """
    # need same signals as QtRuneEngine
    engine_state_changed = pyqtSignal(str, str)
    msg_changed = pyqtSignal(object)
    doc_changed = pyqtSignal(str, object)
    exec_result = pyqtSignal(object)
    prog_changed = pyqtSignal(object)
    msg_to_app = pyqtSignal(object)
    new_data = pyqtSignal(object)  # this is used to update the data in the widgets
    # bl_component_changed = pyqtSignal(str, object) #component name, val or dict
    load_files_status = pyqtSignal(object)  # a signal to be emitted when loading files from the DCS server is
                                           # complete

    def __init__(self, devices_dct, parent=None):
        super().__init__(parent)

        self.running = True
        self.context = zmq.asyncio.Context()
        self.dcs_server_api = DcsServerApi(self)
        self.dcs_server_api.scan_status.connect(self.on_scan_status)
        self.dcs_server_api.progress.connect(self.on_scan_progress)
        self.dcs_server_is_local = HOST_IS_LOCAL
        self.new_data = self.dcs_server_api.new_data  # connect to the new_data signal from the DCS server API
        self.load_files_status = self.dcs_server_api.load_files_status

        # SUB socket: Subscribing to the publisher
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect(f"tcp://{DCS_HOST}:{DCS_SUB_PORT}")  # Connect to the PUB socket
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")  # Subscribe to all messages

        # REQ socket: Sending requests to the REP socket
        self.req_socket = self.context.socket(zmq.REQ)
        self.req_socket.connect(f"tcp://{DCS_HOST}:{DCS_REQ_PORT}")  # Connect to the REP socket

        self.loop = None  # Event loop placeholder

        # self.publish_thread = ZMQServerThread("PUB_TO_ZMQ", self.socket, read_only=False)
        self.zmq_dev_server_thread = ZMQServerThread("ZMQServerThread", self.sub_socket, self.req_socket, read_only=False)
        self.zmq_dev_server_thread.message_received.connect(self.add_to_SUB_rcv_queue)
        # # self.publish_thread.start()
        # self.zmq_dev_server_thread.start()

        self.rcv_queue = queue.Queue()
        self.updateTimer = QTimer()
        self.updateTimer.timeout.connect(self.process_queue_synchronously)

        self.positioner_definition = []
        self.detector_definition = []
        self.oscilloscope_definition = {}
        self.osa_definition = {}
        self.zone_plate_definition = {}
        self.remote_file_system_info = {}


        self.devices = {}
        self.devices['POSITIONERS'] = {}
        self.devices['DETECTORS'] = {}
        self.devices['PRESSURES'] = {}
        self.devices['TEMPERATURES'] = {}
        self.devices['PVS'] = {}

        self.dcs_server_config = {}
        self.dcs_server_config['ZP_DEFS'] = {}
        self.dcs_server_config['OSA_DEFS'] = {}
        self.dcs_server_config['REMOTE_FILE_SYSTEM'] = {}

        self.selected_detectors = []
        self.selected_osa = []

        self._state = 'idle'
        # connect_to_dcs_server() should happen here and the devices instanciated based on the
        # info returned from dcs_server

        # self.bl_component_changed.connect(self.on_bl_component_changed)

        # add devices to Widget
        # devices are in categories based on type
        self.devices_dct = devices_dct
        self.devs = {}
        self.dcs_to_appname_map = {}
        self.app_to_dcsname_map = {}
        device_types = list(devices_dct.keys())
        for dev_type in device_types:
            for app_devname, dev in devices_dct[dev_type].items():
                dcs_name = dev.dcs_name
                self.devs[app_devname] = {'dev': dev, 'dcs_name': dcs_name}
                self.app_to_dcsname_map[app_devname] = dcs_name
                self.dcs_to_appname_map[dcs_name] = app_devname

                #connect device signals
                if hasattr(dev, 'attrs'):
                    for _attr in dev.attrs:
                        a = getattr(dev, _attr)
                        # print(f"zmqDevMgr: connecting signal do_put for attribute {a.name}")
                        a.do_put.connect(self.on_dev_put)
                        a.do_get.connect(self.on_dev_get)

                # print(f"zmqDevMgr: connecting signal do_put for device {dev.name}")
                dev.do_put.connect(self.on_dev_put)
                dev.do_get.connect(self.on_dev_get)
                dev.on_connect.connect(self.on_dev_connect)

        # must set the device name maps after all devices have been added
        self.dcs_server_api.set_device_name_maps(self.app_to_dcsname_map, self.dcs_to_appname_map)
        # self.publish_thread.start()
        self.zmq_dev_server_thread.start()
        self.start_feedback()

    def set_default_detector(self, det_name):
        """
        This function sets the default detector to be used by the DCS server
        """
        if det_name in self.devs.keys():
            self.dcs_server_api.set_default_detector(det_name)
        else:
            print(f"ZMQDevManager: set_default_detector: {det_name} not found in devices")

    def is_dcs_server_local(self):
        """
        return if the dcs server host is local or not
        """
        return self.dcs_server_is_local

    @property
    def state(self):
        return self._state

    def on_scan_status(self, sts):
        """
        handler to deal with scan_status messages from teh dcs server
        """
        new_state = 'idle'
        old_state = 'idle'
        #print(f"ZMQDevManager: on_scan_status: {sts}")
        if self.running and sts == 1:
            old_state = 'running'
            new_state = 'running'
        elif self.running and sts == 2:
            old_state = 'running'
            new_state = 'paused'
        elif self.running and sts == 0:
            old_state = 'running'
            new_state = 'idle'
            # ok it has completed, the BS run engine returns a list of run UID's, so fake one here
            ############################################################################################
            #self.exec_result.emit([123456789])

        self.engine_state_changed.emit(new_state, old_state)

    def on_scan_progress(self, prog_dct):
        """
        handler to deal with scan_status messages from teh dcs server
        """
        # print(f"ZMQDevManager: on_scan_progress:   {prog_dct}")
        self.prog_changed.emit(prog_dct)

    def on_dcs_msg_to_app(self, msg):
        """

        """
        self.msg_to_app.emit(msg)

    def emit_progress(self, info_dct):
        # make_progress_dict(sp_id=None, percent=0.0, cur_img_idx=0)
        dct = make_progress_dict()

    def send_receive(self, message_dict):
        reply = self.zmq_dev_server_thread.send_receive(message_dict)
        return reply

    def connect_to_dcs_server(self, devices_dct):
        """
        send 'initialize' to pixelator
        """
        print(f"connect_to_dcs_server: \n\tDCS_HOST={DCS_HOST} \n\tDCS_HOST_PROC_NAME={DCS_HOST_PROC_NAME} \n\tDCS_SUB_PORT={DCS_SUB_PORT} \n\tDCS_REQ_PORT={DCS_REQ_PORT}")
        result = self.dcs_server_api.connect_to_dcs_server(devices_dct)

        #return lists of supported OSAS and ZONEPLATES
        dct = {}
        dct['ZP_DEFS'] = self.dcs_server_config['ZP_DEFS']
        dct['OSA_DEFS'] = self.dcs_server_config['OSA_DEFS']
        dct['REMOTE_FILE_SYSTEM'] = self.dcs_server_config['REMOTE_FILE_SYSTEM']

        return result, dct

    def load_data_directory(self, data_dir: str=None, *, extension: str='.hdf5') -> None:
        """
        This function loads the data directory from the DCS server and updates the remote file system info.
        It is used to load the data directory from the DCS server.
        """
        if data_dir is None:
            remote_file_system_info = self.remote_file_system_info
            data_dir = remote_file_system_info['directory']
        file_lst = self.dcs_server_api.load_directory(data_dir, extension=extension)
        # if isinstance(file_lst, list):
        #     for filename in file_lst:
        #         fname = os.path.join(data_dir, filename)
        #         self.dcs_server_api.load_file(data_dir, fname)
        if isinstance(file_lst, list):
            self.dcs_server_api.load_files(data_dir, file_lst)

    def request_data_directory_list(self, data_dir: str=None) -> None:
        """
        This function requests the data directory list from the DCS server and updates the remote file system info.
        It is used to request the data directory list from the DCS server.
        """
        if data_dir is None:
            remote_file_system_info = self.remote_file_system_info
            data_dir = remote_file_system_info['directory']
        file_lst = self.dcs_server_api.request_data_directory_list(data_dir, extension='.hdf5')
        print(f"ZMQDevManager: request_data_directory_list: {file_lst}")
        return file_lst

    def print_all_devs(self, title: str, devlist: [str]) -> None:
        print(f"{title}:")
        if type(devlist) == list:
            for dev in devlist:
                if 'axisName' in dev.keys():
                    print(f"\tAxisName={dev['axisName']}")
                elif 'name' in dev.keys():
                    print(f"\tname={dev['name']}")
                else:
                    print(f"\t{dev}")
        else:
            print(f"\t{devlist}")

    def on_dev_get(self, dct):
        # print(f'ZMQDevManager: on_dev_get: [{dct}]')
        self.zmq_dev_server_thread.send_receive(dct)

    def on_dev_put(self, dct):
        # print(f'ZMQDevManager: on_dev_put: [{dct}]')
        self.dcs_server_api.put(dct)

    def on_dev_connect(self, pvname=None, conn=None, pv=None):
        print(f'ZMQDevManager: on_dev_connect: {pv.name} [{conn}]')
        #print(f'ZMQDevManager: on_dev_connect: {dct["obj"].name} [{dct}]')
        #self.zmq_dev_server_thread.send_message(dct)

    def get_dev(self, app_devname):
        """
        return the device if it exists in the devs dict
        """
        if app_devname in self.devs.keys():
            return self.devs[app_devname]['dev']
        return None

    def get_devices(self):
        """
        return the device if it exists in the devs dict
        """
        return self.devs

    def get_device_names(self):
        """
        return the list of dicts for the device names
        """
        devs = self.get_devices()
        lst = []
        for app_devname, dev_dct in devs.items():
            if hasattr(dev_dct['dev'], 'enums'):
                lst.append({'app_devname': app_devname, 'dcs_devname': dev_dct['dcs_name'], 'high_limit_val': len(dev_dct['dev'].enums)})
            else:
                lst.append({'app_devname': app_devname, 'dcs_devname': dev_dct['dcs_name']})
        return lst

    def connect_to_dev_changed(self, app_devname, cb):
        """
        allow the Qt host application to connect a callback to teh devices changed signal
        typically for feedback
        """
        if app_devname in self.devs.keys():
            self.devs[app_devname].changed.connect(cb)

    def put_to_queue(self, message_dct):
        # self.send_command({"dev_name":app_devname, "command": "UPDATE_POSITION", "value": value})
        self.rcv_queue.put_nowait(message_dct)

    def start_feedback(self):
        self.updateTimer.start(10)

    def add_to_SUB_rcv_queue(self, dct):
        self.rcv_queue.put_nowait(dct)

    def process_queue_synchronously(self):
        # Schedule the async processQueue to run on the asyncio event loop
        asyncio.run_coroutine_threadsafe(self.process_SUB_rcv_messages(), self.zmq_dev_server_thread.loop)

    async def process_SUB_rcv_messages(self):
        """
        This function process messages received on the SUB socket from teh dcs server

        This is the pyStxm side of the ZMQ-Pixelator SUB connection, update_widgets means to update the ZMQ Devices
        with new values etc and the ZMQ devices Qt signals will take care of the rest

        it pulls dicts out of the queue and
        """

        call_task_done = False
        while not self.rcv_queue.empty():
            resp = self.rcv_queue.get()
            # print(f"process_SUB_rcv_messages: msg={resp}")
            self.msg_changed.emit(resp)
            if isinstance(resp, dict):
                # print(f"ZMQDevManager: update_widgets: resp={resp}")
                if resp['command'].find("UPDATE_POSITION") > -1:
                    dcs_devname = resp['dev_name']
                    app_devname = self.dcs_to_appname_map[dcs_devname]
                    if app_devname in self.devs.keys():
                        self.devs[app_devname]['dev'].update_position(resp['value'], resp['is_moving'])

                elif resp['command'].find("MOVE") > -1:
                    dev_name = resp['dev_name']
                    # print(f"[{dev_name}] setting value={resp['value']}")
                    # self.devs[dev_name].move(resp['value'])
                    await self.zmq_dev_server_thread.send_message \
                        ({'dev_name': dev_name, 'command': 'MOVE', 'value': resp['value']})

                elif resp['command'].find("GET_DEVNAME_LIST") > -1:
                    devname_lst = self.get_device_names()
                    # print(f"update_widgets: GET_DEVNAME_LIST: [{devname_lst}]")
                    await self.zmq_dev_server_thread.send_message({'command': 'GET_DEVNAME_LIST', 'value': devname_lst})

                elif resp['command'].find("DEV_CONNECTED") > -1:
                    print(f"RCVD from Client: DEV_CONNECTED: [{resp['dev_name']} = [{resp['value']}]")
                    #({"dev_name": app_devname, "command": "DEV_CONNECTED", "value": value}
                    app_devname = resp['dev_name']
                    val = resp['value']
                    if val == 0:
                        connected = False
                    else:
                        connected = True
                    dev = self.devs[app_devname]['dev']
                    dev.set_connected(connected)

                elif resp['command'].find("REGISTER_COMMAND") > -1:
                    print(f"RCVD from Client: REGISTER_COMMAND: [{resp['value']}] with response={resp['response']}")

                else:
                    await self.zmq_dev_server_thread.send_message(resp)

            elif isinstance(resp, list):
                # let teh dcs_server_api handle messages coming from the PUB port of the DCS server
                self.dcs_server_api.process_SUB_rcv_messages(resp)


        if call_task_done:
            self.rcv_queue.task_done()

    async def send_to_dcs_client(self, message_dct):
        """
        send a command to the DCS system
        """
        await self.zmq_dev_server_thread.send_message(message_dct)

    def stop(self):
        self.running = False
        # self.publish_thread.stop()
        self.zmq_dev_server_thread.stop()
        self.socket.close()
        self.context.term()


    def send_scan_request(self, wdg_com):
        """
        This function accepts a WDG_COM dict and pulls creates a dict required by DCS server to start a scan.

        the send_scan_request() function is responsible for converting hte wdg_com dict to something the DCS server
        accepts.
        Parameters
        ----------
        dct

        Returns
        -------

        """

        self.dcs_server_api.send_scan_request(wdg_com)

    def set_zoneplate_definitions(self, zp_defs: dict):
        """
        a function to send the zoneplate definition dictionary to the DCS server
        """
        self.dcs_server_api.set_zoneplate_definitions(zp_defs)

    def set_osa_definitions(self, osa_defs: dict):
        """
        a function to send the osa definition dictionary to the DCS server
        """
        self.dcs_server_api.set_osa_definitions(osa_defs)

    def set_ocilloscope_definition(self, osc_def: dict):
        """
        a function to send the osa definition dictionary to the DCS server
        """
        self.dcs_server_api.set_ocilloscope_definition(osc_def)

    def abort_scan(self):
        """
        This function makes the call to the dcs server to abort the current scan
        Returns
        -------

        """
        self.dcs_server_api.abort_scan()


    def pause_scan(self):
        """
        This function makes the call to the dcs server to pause the current scan
        Returns
        -------

        """
        self.dcs_server_api.pause_scan()

    def resume_scan(self):
        """
        This function makes the call to the dcs server to resume the current scan
        Returns
        -------

        """
        self.dcs_server_api.resume_scan()

    def get_selected_detector_names(self) -> list:
        """
        This function returns the list of detectors that are curently selected to send their data out of the DCS server
        """
        return self.dcs_server_api.get_selected_detector_names()

    def select_detectors(self, det_nm_lst: [list]):
        """
        This function accepts a list of detector names and sets the selected detectors to this list
        """
        assert isinstance(det_nm_lst, list), f"select_detectors: det_nm_lst must be a list, not {type(det_nm_lst)}"
        self.selected_detectors = det_nm_lst
        self.dcs_server_api.select_detectors(det_nm_lst)

    def set_oscilloscope_definition(self, osc_def: dict):
        """
        This function accepts a list of detector names and sets the selected detectors to this list
        """
        assert isinstance(osc_def, dict), f"set_oscilloscope_definition: osc_def must be a dict, not {type(osc_def)}"
        self.dcs_server_api.set_oscilloscope_definition(osc_def)


