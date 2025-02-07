import os
import sys
import pprint
import random
import queue
import asyncio

from PyQt5.QtCore import pyqtSlot, QTimer
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt5 import QtWidgets

#make sure that the applications modules can be found, used to depend on PYTHONPATH environ var
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..", "..", ".."))

from bcm.backend import BACKEND

if BACKEND != 'zmq':
    print(f"The current BACKEND configuration is not zmq, exiting")
    exit(1)

from bcm.devices.zmq.sim_dcs_device import sim_dcs_fbk_dev
from bcm.devices.zmq.zmq_client_thread import ZMQClientThread
from bcm.devices.zmq.utils import make_label_tuple
from bcm.devices.zmq.pixelator.pixelator_mtr_limits import motor_limits
class ClientWidget(QWidget):
    def __init__(self, setter_cmd_lst, getter_cmd_lst, dcs_devname_dct={}):
        super().__init__()
        self.device_dct = {}
        self.queue = queue.Queue()
        self.updateTimer = QTimer()
        self.updateTimer.timeout.connect(self._process_queue_synchronously)

        self.dcs_client_commands = []
        self.dev_widget_map = {}
        self.dcs_devname_dct = dcs_devname_dct
        self.dcs_devnames = dcs_devname_dct
        # Layout and label to show status
        layout = QVBoxLayout()
        self.label = QLabel("Client connected. Waiting for messages.")
        layout.addWidget(self.label)

        # Create a QScrollArea and set its properties
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)  # Make the scroll area resizable

        # Create a widget to hold the scroll area content
        scroll_content = QWidget()

        # Create a QVBoxLayout for the scroll content
        scroll_layout = QVBoxLayout(scroll_content)

        # Create buttons for each command
        commands = ['scanStarted', 'scanLineData', 'scanFinished', 'scanFileContent', 'positionerDefinition']
        self.buttons = []
        for command in commands:
            button = QPushButton(command)
            button.clicked.connect(lambda checked, cmd=command: self.dcs_to_app_send_command({"command": cmd, "value": 1}))
            scroll_layout.addWidget(button)
            self.buttons.append(button)

        self.devs = {}
        self.appname_to_dcsname_dev_map = {}
        self.dcsname_to_appname_dev_map = {}
        self.get_all_device_names_btn = QPushButton("Send Command GET_DEVNAME_LIST")
        self.get_all_device_names_btn.clicked.connect(
            lambda: self.dcs_to_app_send_command({"command": "GET_DEVNAME_LIST", "value": 1}))
        scroll_layout.addWidget(self.get_all_device_names_btn)

        self.send_button7 = QPushButton("MOVE all devices")
        self.send_button7.clicked.connect(lambda: self.move_all_dcs_devices())
        scroll_layout.addWidget(self.send_button7)

        self.send_button8 = QPushButton("MOVE all devices to 0")
        self.send_button8.clicked.connect(lambda: self.move_all_dcs_devices(0))
        scroll_layout.addWidget(self.send_button8)

        self.send_button9 = QPushButton("Register all commands with server")
        self.send_button9.clicked.connect(lambda: self.dcs_to_app_register_commands())
        scroll_layout.addWidget(self.send_button9)
        # init all devices

        #self.dcs_to_app_send_command({"command": "GET_DEVNAME_LIST", "value": 1})
        for dev_category in self.dcs_devnames:
            for dcs_devname in self.dcs_devnames[dev_category]:
                dct = make_label_tuple(dcs_devname)
                # dct['fld'].returnPressed.connect(self._on_dev_setpoint_changed)
                dct['dcs_name'] = dcs_devname
                self.dev_widget_map[dcs_devname] = dct
                scroll_layout.addLayout(dct['hbox'])

        self.init_all_dcs_devices(self.dcs_devnames)
        self.set_motor_limits(motor_limits)

        # Set the scroll content widget as the scroll area's widget
        scroll_area.setWidget(scroll_content)

        # Add the scroll area to the central widget's layout
        layout.addWidget(scroll_area)
        self.setLayout(layout)

        # Start ZMQ client thread
        self.zmq_client_thread = ZMQClientThread(self)
        self.zmq_client_thread.message_received.connect(self._on_message_received)
        self.zmq_client_thread.start()

        self._start_feedback()

        self.singelshot = QTimer()
        self.singelshot.setSingleShot(True)
        self.singelshot.timeout.connect(self.get_all_device_names)
        self.singelshot.start(550)
        #init all the devices
        #self.get_all_device_names_btn.clicked.emit()

    def get_all_device_names(self):
        """
        this needs to wait to run a bit so executing it from a single shot after app has had a chance to fire up
        """
        self.get_all_device_names_btn.clicked.emit()

    def _on_dev_setpoint_changed(self):
        fld = self.sender()
        val = float(fld.text())
        dev_name = fld.toolTip()
        if dev_name in self.dev_widget_map.keys():
            dev_dct = self.dev_widget_map[dev_name]
            dcs_name = dev_dct['dcs_name']
            self.move_dcs_device(dcs_name, val)

    def _update_feedback_cb(self, app_devname, dcs_devname, value, status):
        #print(f"update_feedback_cb: got value={value}")
        dev = self.sender()
        #app_devname = self.dev_widget_map[dev.name]
        fbk_lbl = self.dev_widget_map[dev.name]['fbk_lbl']
        sts_lbl = self.dev_widget_map[dev.name]['sts_lbl']
        fbk_lbl.setText(str(value))
        if status:
            status_str = 'MOVING'
            clr = 'QLabel{ background-color: rgb(255, 255, 0);color: rgb(0, 0, 0);}'
        else:
            status_str = 'STOPPED'
            clr = 'QLabel{ background-color: rgb(0, 128, 128);color: rgb(255, 255, 255);}'

        sts_lbl.setText(status_str)
        sts_lbl.setStyleSheet(clr)
        #print(f"update_feedback_cb: received a CHANGED signal: {value}")

    def _process_queue_synchronously(self):
        # Schedule the async processQueue to run on the asyncio event loop
        if self.zmq_client_thread.loop:
            asyncio.run_coroutine_threadsafe(self._update_server(), self.zmq_client_thread.loop)

    def set_motor_limits(self, lim_lst):
        for dct in lim_lst:
            dcs_devname = dct['dcs_devname']
            self.devs[dcs_devname].set_low_limit(dct['low_limit'])
            self.devs[dcs_devname].set_high_limit(dct['high_limit'])

    def load_dcs_client_commands(self, command_lst):
        """
        this function loads a list of pcommands that something like Pixelator would send to pyStxm
        """
        self.dcs_client_commands = command_lst
        self.dcs_to_app_register_commands()

    def dcs_to_app_register_commands(self):
        """
        register a command with the server
        """
        for command, response in self.dcs_client_commands.items():
            self.dcs_to_app_register_command(command, response)

    def dcs_to_app_register_command(self, command, response):
        """
        register a command with the server
        """

        self.queue.put_nowait(
                {"command": "REGISTER_COMMAND", "value": command, "response": response})

    # def send_command(self, command):
    #     self.queue.put_nowait({"command": command})
    def _start_feedback(self):
        self.updateTimer.start(10)

    def init_all_dcs_devices(self, dcs_dict):
        """
        initialize all of the Pixelator devices based on the names retrieved from pyStxm
        """
        for dev_category in dcs_dict:
            dcs_devnames = dcs_dict[dev_category]
            for dcs_devname in dcs_devnames:
                #print(f"init_all_devices: [{app_devname}] = [{dcs_devname}]")
                self.devs[dcs_devname] = sim_dcs_fbk_dev(dcs_devname, dcs_devname)
                self.devs[dcs_devname].changed.connect(self.dcs_to_app_update_position)
                self.devs[dcs_devname].changed.connect(self._update_feedback_cb)
                #app_devname = self.dcsname_to_appname_dev_map[dcs_devname]
                #self.dcs_to_app_dev_connected(app_devname, 1)
                if dcs_devname in self.dev_widget_map.keys():
                    self.dev_widget_map[dcs_devname]['fld'].returnPressed.connect(self._on_dev_setpoint_changed)
                    self.dev_widget_map[dcs_devname]['stopBtn'].clicked.connect(self._on_stop_btn_clicked)
                else:
                    print(f"init_all_devices: [{dcs_devname}] does not appear in self.dev_widget_map.keys(), why?")


    def _on_stop_btn_clicked(self):
        btn = self.sender()
        dcs_devname = btn._dcs_devname
        if dcs_devname in self.devs.keys():
            self.devs[dcs_devname].stop()
            print(f'CLIENT: Stopping {dcs_devname}')


    def move_all_dcs_devices(self, val=None):
        """
        move all of the devices in the devs_dict by random values
        ifg val is None then set each to a random number else to the val
        """
        use_rand = False
        if val == None:
            use_rand = True

        for dcs_devname in list(self.devs.keys()):
            if use_rand:
                # Generates a random number between
                # a given positive range
                val = random.randint(0, 10000)
            self.devs[dcs_devname].move(val)
            #print(f'CLIENT: moving {app_devname} to {val}')
            #time.sleep(0.4)

    def move_dcs_device(self, dcs_devname, val=None):
        """
        move all of the devices in the devs_dict by random values
        ifg val is None then set each to a random number else to the val
        """
        if dcs_devname in self.devs.keys():
            self.devs[dcs_devname].move(val)
            print(f'CLIENT: moving {dcs_devname} to {val}')

    def stop_dcs_device(self, dcs_devname):
        """
        move all of the devices in the devs_dict by random values
        ifg val is None then set each to a random number else to the val
        """
        if dcs_devname in self.devs.keys():
            self.devs[dcs_devname].stop()
            print(f'CLIENT: Stopping {dcs_devname} ')

    async def _update_server(self):
        call_task_done = False
        while not self.queue.empty():
            msg = self.queue.get()
            # print(f"ZMQDevManager: update_server: msg={msg}")
            if isinstance(msg, dict):

                await self.zmq_client_thread.send_message(msg)

        if call_task_done:
            self.queue.task_done()

    def dcs_to_app_update_position(self, app_devname, dcs_devname, value, is_moving):
        #print(f"update_position: [{app_devname}]={value}, is_moving={is_moving}")
        #self.send_command({"dev_name":app_devname, "command": "UPDATE_POSITION", "value": value})
        self.queue.put_nowait({"dev_name":app_devname, "command": "UPDATE_POSITION", "value": value, 'is_moving': is_moving})

    def dcs_to_app_dev_connected(self, app_devname, value):
        #print(f"update_position: [{app_devname}]={value}, is_moving={is_moving}")
        #self.send_command({"dev_name":app_devname, "command": "UPDATE_POSITION", "value": value})
        self.queue.put_nowait({"dev_name":app_devname, "command": "DEV_CONNECTED", "value": value})

    @pyqtSlot(dict)
    def _on_message_received(self, message_dict):
        print(f"PIXELATOR SIM: on_message_received=[{message_dict}]")
        if message_dict['command'].find('MOVE') == 0:
            dcs_devname = message_dict['dev_name']
            val = message_dict['value']
            self.move_dcs_device(dcs_devname, val)

        elif message_dict['command'].find('STOP') == 0:
            dcs_devname = message_dict['dev_name']
            self.stop_dcs_device(dcs_devname)

        elif message_dict['command'].find('PUT') == 0:
            # {'command': 'PUT', 'name': 'PIXELATOR_COARSE_X', 'dcs_name': 'PIXELATOR_COARSE_X', 'attr': 'user_setpoint', 'value': 100.0}
            dcs_devname = message_dict['name']
            val = message_dict['value']
            self.move_dcs_device(dcs_devname, val)

        pprint.pprint(f"on_message_received: Received dictionary from server: \n{message_dict}")

    def dcs_to_app_send_command(self, command_dict):
        """
        Sends a command to the ZMQ client thread to be sent via the PUB socket.
        """
        #self.zmq_client_thread.send_message(command_dict)
        asyncio.run_coroutine_threadsafe(self.zmq_client_thread.send_message(command_dict), self.zmq_client_thread.loop)


    def closeEvent(self, event):
        # Ensure the client thread is stopped properly when the application is closed
        self.zmq_client_thread.stop()
        event.accept()

if __name__ == "__main__":

    from bcm.devices.zmq.pixelator.pixelator_commands import dcs_client_cmnds

    def generate_funcdefs(cmnds):

        for cmd_dct in cmnds:
            cmd = cmd_dct['command']
            cmd_fixed = cmd.replace(' ','_')
            print(f"def PIXELATOR_{cmd_fixed}(**kwargs):")
            print('\t"""')
            print(f'\tFunction {cmd_fixed} description:')
            print(f'\treturns: {cmd_dct["response"]}')
            print("\t")
            print('\t"""')
            print(f'\tprint(f"PIXELATOR: function [{cmd}] called from ZMQ REQ/REP socket")')
            print('\n')

    def generate_CLIENT_if_conds(cmnds):
        i = 0
        for cmd_dct in cmnds:
            cmd = cmd_dct['command']
            cmd_fixed = cmd.replace(' ','_')
            if i == 0:
                print(f"if message_dict['command'].find('{cmd}') == 0: ")
            else:
                print(f"elif message_dict['command'].find('{cmd}') == 0:")

            print("\tif 'value' in message_dict.keys():")
            print("\t\tval = message_dict['value']")
            print(f"\t\tPIXELATOR_{cmd_fixed}(val)")
            print("\telse:")
            print(f"\t\tPIXELATOR_{cmd_fixed}()")
            i += 1

    def generate_SERVER_if_conds(cmnds):
        i = 0
        for cmd_dct in cmnds:
            cmd = cmd_dct['command']
            cmd_fixed = cmd.replace(' ','_')
            if i == 0:
                print(f"if message_dict['command'].find('{cmd}') == 0: ")
            else:
                print(f"elif message_dict['command'].find('{cmd}') == 0:")
            print("\tval = message_dict['value']")
            print(f"\tPIXELATOR_{cmd_fixed}(val)")
            i += 1

    def generate_command_func_map(cmnds):
        i = 0
        print("cmd_func_map_dct = {}")
        for cmd in cmnds:
            cmd_fixed = cmd.replace(' ', '_')
            print(f"cmd_func_map_dct['{cmd_fixed}'] = PIXELATOR_{cmd_fixed}")
            i += 1

    stxmui_setters = ['scan_start', 'scan_abort', 'scan_pause', 'scan_resume',
                    'posner_move', 'posner_stop'
                    'device_config', 'device_set']
    stxmui_getters = ['scan_progress', 'scan_status'
                    'posner_position', 'posner_status'
                    'device_status', 'device_position']
        

    # generate_funcdefs(dcs_client_cmnds)

    # generate_CLIENT_if_conds(dcs_client_cmnds)

    #generate_SERVER_if_conds(dcs_client_cmnds)

    # generate_command_func_map(list(dcs_client_cmnds.keys()))

    dcs_devname_dct = {}
    dcs_devname_dct['POSITIONERS'] = ['PIXELATOR_SAMPLE_FINE_X',
                    'PIXELATOR_SAMPLE_FINE_Y',
                    'PIXELATOR_OSA_X',
                    'PIXELATOR_OSA_Y',
                    'PIXELATOR_ZONEPLATE_Z',
                    'PIXELATOR_COARSE_X',
                    'PIXELATOR_COARSE_Y',
                    'PIXELATOR_COARSE_Z',
                    'PIXELATOR_DETECTOR_X',
                    'PIXELATOR_DETECTOR_Y',
                    'PIXELATOR_DETECTOR_Z',
                    'PIXELATOR_SAMPLE_X',
                    'PIXELATOR_SAMPLE_Y',
                    'PIXELATOR_ENERGY',
                    'PIXELATOR_SLIT_X',
                    'PIXELATOR_SLIT_Y',
                    'PIXELATOR_M3_PITCH',
                    'PIXELATOR_EPU_GAP',
                    'PIXELATOR_EPU_OFFSET',
                    'PIXELATOR_EPU_HARMONIC',
                    'PIXELATOR_EPU_POLARIZATION',
                    'PIXELATOR_EPU_ANGLE']

    dcs_devname_dct['PVS'] = ['PIXELATOR_BASELINE_RING_CURRENT',
                   'PIXELATOR_RING_CURRENT',
                   'PIXELATOR_AX2_INTERFER_VOLTS',
                   'PIXELATOR_SFY_PIEZO_VOLTS',
                   'PIXELATOR_SFX_PIEZO_VOLTS',
                   'PIXELATOR_AX1_INTERFER_VOLTS',
                   'PIXELATOR_MONO_EV_FBK',
                   'PIXELATOR_SRSTATUS_SHUTTERS',
                   'PIXELATOR_SYSTEM_MODE_FBK',
                   'PIXELATOR_FINE_DECCEL_DIST_PRCNT',
                   'PIXELATOR_FINE_ACCEL_DIST_PRCNT',
                   'PIXELATOR_CRS_ACCEL_DIST_PRCNT',
                   'PIXELATOR_CRS_DECCEL_DIST_PRCNT',
                   'PIXELATOR_CALCD_ZPZ',
                   'PIXELATOR_RESET_INTERFERS',
                   'PIXELATOR_SFX_AUTOZERO',
                   'PIXELATOR_SFY_AUTOZERO',
                   'PIXELATOR_ZPZ_ADJUST',
                   'PIXELATOR_ZONEPLATE_SCAN_MODE',
                   'PIXELATOR_ZONEPLATE_SCAN_MODE_RBV',
                   'PIXELATOR_DELTA_A0',
                   'PIXELATOR_IDEAL_A0',
                   'PIXELATOR_FOCAL_LENGTH',
                   'PIXELATOR_A0',
                   'PIXELATOR_A0MAX',
                   'PIXELATOR_ZPZ_POS',
                   'ASTXM1610:bl_api:enabled',
                   'PIXELATOR_ENERGY_RBV',
                   'PIXELATOR_ZPZ_RBV',
                   'PIXELATOR_ZP_DEF_A',
                   'PIXELATOR_ZP_DEF',
                   'PIXELATOR_OSA_DEF',
                   'PIXELATOR_BEAM_DEFOCUS',
                   'PIXELATOR_DFLT_PMT_DWELL',
                   'PIXELATOR_TICKER',
                   ]
    dcs_devname_dct['TEMPERATURES'] = ['TM1610-3-I12-01',
                    'TM1610-3-I12-30',
                    'TM1610-3-I12-32',
                    'TM1610-3-I12-21',
                    'TM1610-3-I12-22',
                    'TM1610-3-I12-23',
                    'TM1610-3-I12-24']

    dcs_devname_dct['PRESSURES'] = ['CCG1410-01:vac:p',
                    'CCG1410-I00-01:vac:p',
                    'CCG1410-I00-02:vac:p',
                    'CCG1610-1-I00-02:vac:p',
                    'HCG1610-1-I00-01:vac:p',
                    'CCG1610-1-I00-03:vac:p',
                    'CCG1610-I10-01:vac:p',
                    'CCG1610-I10-03:vac:p',
                    'CCG1610-I10-04:vac:p',
                    'CCG1610-I12-01:vac:p',
                    'CCG1610-I12-02:vac:p',
                    'CCG1610-3-I12-01:vac:p']

    dcs_devname_dct['DETECTORS'] = ['PIXELATOR_PMT',
                    'PIXELATOR_TUCSEN_AD']

    dcs_devname_dct['DIO'] = ['PIXELATOR_SHUTTERTASKRUN',
                   'PIXELATOR_SHUTTER']

    app = QApplication(sys.argv)
    client_widget = ClientWidget(stxmui_setters, stxmui_getters, dcs_devname_dct=dcs_devname_dct)
    client_widget.load_dcs_client_commands(dcs_client_cmnds)
    client_widget.setWindowTitle("Pixelator ZMQ Client Simulator")
    client_widget.setGeometry(650, 50, 500, 500)
    client_widget.resize(550, 150)
    client_widget.show()
    sys.exit(app.exec_())

    
