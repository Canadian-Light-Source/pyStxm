############
# Standard #
############
import logging
import time

from time import localtime, gmtime
import simplejson as json

from bcm.devices import BACKEND
if BACKEND == 'zmq':
    # ZMQDevManager is going to take the place of `engine` for zmq
    from bcm.devices.zmq.zmq_dev_manager import ZMQDevManager

from bluesky import RunEngine
from bluesky.utils import RunEngineInterrupted
from bluesky.preprocessors import SupplementalData
from ophyd.log import set_handler

from databroker import list_configs
from databroker import Broker

from PyQt5.QtWidgets import QVBoxLayout, QLabel, QComboBox, QGroupBox
from PyQt5.QtWidgets import QWidget, QStackedWidget, QPushButton
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer

from cls.utils.log import get_module_logger

_logger = get_module_logger(__name__)

class QRunEngine(QObject, RunEngine):
    engine_state_changed = pyqtSignal(str, str)
    msg_changed = pyqtSignal(object)
    doc_changed = pyqtSignal(str, object)
    exec_result = pyqtSignal(object)
    prog_changed = pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Attach the state_hook to emit signals
        self.state_hook = self.on_engine_state_change
        self._execution_result = None
        self.msg_hook = self.on_msg_hook
        #send RE docs to the progress func
        self.subscribe(self.update_progress)

        # Allow a plan to be stored on the RunEngine
        self.plan_creator = None
        self.meters = []

    def print_msg(self, name, doc):
        print("PRINT_MSG: name=%s" % name)
        print(doc)

    def on_engine_state_change(self, state, old_state):
        """
        Report a state change of the RunEngine
        This is added directly to the `RunEngine.state_hook` and emits the
        `engine_state_change` signal.
        Parameters
        ----------
        state: str
        old_state: str
        """
        self.engine_state_changed.emit(state, old_state)


    def on_msg_hook(self, msg):
        """ """
        self.msg_changed.emit(msg)

    @pyqtSlot()
    def start(self):
        """Start the RunEngine"""
        self._max_prog_events = 0
        self._event_uid = 0
        self._start_time = 0
        self._stop_time = 0
        self._scan_idx = -1
        self._master_start_time = 0
        if not self.plan_creator:
            print(
                "ERROR: Commanded RunEngine to start but there " "is no source for a plan"
            )
            return
        # Execute our loaded function
        try:
            self._execution_result = None
            self._execution_result = self.__call__(self.plan_creator())
            self.exec_result.emit(self._execution_result)
            # print(ret)
        # Pausing raises an exception
        # except RunEngineInterrupted as exc:
        #     print("DEBUG: RunEngine paused")
        except RunEngineInterrupted as exc:
            print("DEBUG: RunEngine interrupted")
            self.exec_result.emit(self._run_start_uids)

    @pyqtSlot()
    def pause(self):
        """Pause the RunEngine
        calls the RunEngine function request_pause()
        """
        self.request_pause()

    def create_prog_dict(self, scan_idx, start_time, stop_time, prog):
        """
        create a progress dictionary and return it
        """
        elapsed_tm = gmtime(stop_time - start_time)
        elapsed_tm_str = time.strftime("Elapsed time %H:%M:%S", elapsed_tm)
        mstr_elapsed_tm = gmtime(stop_time - self._master_start_time)
        mstr_elapsed_tm_str = time.strftime("%H:%M:%S", mstr_elapsed_tm)
        dct = {}
        dct["scan_idx"] = scan_idx
        dct["prog"] = prog
        dct["elapsed_tm_str"] = elapsed_tm_str
        dct["elapsed_tm"] = elapsed_tm
        dct["mstr_elapsed_tm_str"] = mstr_elapsed_tm_str
        dct["mstr_elapsed_tm"] = mstr_elapsed_tm
        return dct

    def update_progress(self, name, doc):
        """
        update_progress subscribes to the msgs from the run engine and pulls out the parts needed to determine the
        progress of the current scan
        :param name:
        :param doc:
        :return:
        """
        self.doc_changed.emit(name, doc)
        if name.find("start") > -1:
            if self._master_start_time == 0:
                self._master_start_time = doc["time"]

            self._start_time = doc["time"]
            self._scan_idx += 1
            if "metadata" in list(doc.keys()):
                dct = json.loads(doc["metadata"])
                self._max_prog_events = dct["num_prog_events"]
            else:
                # indicate that the scan is a flyer
                self._max_prog_events = -1
                # print("Scan progress: Flyer scan in progress...")
                if self._stop_time <= self._start_time:
                    # elapsed_tm = gmtime((self._start_time + 1.0) - self._start_time)
                    # elapsed_tm_str = time.strftime("Elapsed time %H:%M:%S", elapsed_tm)
                    # d = self.create_prog_dict((self._start_time + 1.0), self._start_time)
                    # self.prog_changed.emit({'scan_idx': self._scan_idx, 'prog': 0.0, 'elapsed_tm_str': elapsed_tm_str, 'elapsed_tm': elapsed_tm})
                    d = self.create_prog_dict(
                        self._scan_idx,
                        (self._start_time + 1.0),
                        self._start_time,
                        prog=0.0,
                    )
                    if d["elapsed_tm"].tm_year >= 1970:
                        self.prog_changed.emit(d)

                else:
                    # elapsed_tm = gmtime(self._stop_time - self._start_time)
                    # elapsed_tm_str = time.strftime("Elapsed time %H:%M:%S", elapsed_tm)
                    # print('Scan progress: %d/%d %.2f complete| %s ' % (seq_num, self._max_prog_pnts, prog, elapsed_tm_str))
                    # self.prog_changed.emit({'scan_idx': self._scan_idx, 'prog': 0.0, 'elapsed_tm_str': elapsed_tm_str,
                    #                         'elapsed_tm': elapsed_tm})
                    d = self.create_prog_dict(
                        self._scan_idx, self._stop_time, self._start_time, prog=0.0
                    )
                    if d["elapsed_tm"].tm_year >= 1970:
                        self.prog_changed.emit(d)

        if name.find("bulk_events") > -1:
            # keep updating the stop time from teh first of the bulk events
            # self._event_uid = list(doc.keys())[0]
            # self._stop_time = doc[self._event_uid][0]['time']
            # print(name, doc)
            # self._stop_time = time.time()
            # self._scan_idx = doc['scan_id']
            pass

        elif name.find("event") > -1:
            seq_num = doc["seq_num"]
            if seq_num == 1:
                # print('Scan progress: 0.0% complete')
                # self.prog_changed.emit(0.0)
                return
            elif seq_num <= self._max_prog_events:
                self._stop_time = doc["time"]
                if self._event_uid == 0:
                    # these are the events we want to look at for progress, all others skipped
                    self._event_uid = doc["descriptor"]
                if doc["descriptor"] == self._event_uid:
                    prog = (float(seq_num) / float(self._max_prog_events)) * 100.0
                    # elapsed_tm = gmtime(self._stop_time - self._start_time)
                    # elapsed_tm_str = time.strftime("Elapsed time %H:%M:%S", elapsed_tm)
                    # print('Scan progress: %d/%d %.2f complete| %s ' % (seq_num, self._max_prog_pnts, prog, elapsed_tm_str))
                    # self.prog_changed.emit({'scan_idx': self._scan_idx, 'prog':prog, 'elapsed_tm_str':elapsed_tm_str, 'elapsed_tm': elapsed_tm})
                    d = self.create_prog_dict(
                        self._scan_idx, self._start_time, self._stop_time, prog=prog
                    )
                    # skip the last 100 % prog that has a elapsed time of 23:59:59 ( also has tm_year of 1969)
                    if d["elapsed_tm"].tm_year >= 1970:
                        self.prog_changed.emit(d)

        if name.find("stop") > -1:
            self._stop_time = doc["time"]
            # time_str = time.strftime("%H:%M:%S", localtime(self._stop_time))
            # print('Scan progress: 100% complete | %s ' % (time_str))
            if self._stop_time <= self._start_time:
                # elapsed_tm = gmtime((self._start_time + 1.0) - self._start_time)
                # elapsed_tm_str = time.strftime("Elapsed time %H:%M:%S", elapsed_tm)
                # self.prog_changed.emit(
                #     {'scan_idx': self._scan_idx, 'prog': 0.0, 'elapsed_tm_str': elapsed_tm_str, 'elapsed_tm': elapsed_tm})
                d = self.create_prog_dict(
                    self._scan_idx, (self._start_time + 1.0), self._start_time, prog=0.0
                )
                if d["elapsed_tm"].tm_year >= 1970:
                    self.prog_changed.emit(d)

            else:
                # elapsed_tm = gmtime(self._stop_time - self._start_time)
                # elapsed_tm_str = time.strftime("Elapsed time %H:%M:%S", elapsed_tm)
                # #print('Scan progress: complete | %s ' % (elapsed_tm_str))
                # self.prog_changed.emit({'scan_idx': self._scan_idx, 'prog': 100.0, 'elapsed_tm_str': elapsed_tm_str, 'elapsed_tm': elapsed_tm})
                d = self.create_prog_dict(
                    self._scan_idx, self._stop_time, self._start_time, prog=100.0
                )
                if d["elapsed_tm"].tm_year >= 1970:
                    self.prog_changed.emit(d)

            self._max_prog_events = 0

        # print(name, doc)

class EngineControl(QWidget):
    """
    RunEngine through a QComboBox
    Listens to the state of the RunEngine and shows the available commands for
    the current state.
    Attributes
    ----------
    state_widgets: dict
    pause_commands: list
        Available RunEngine commands while the Engine is Paused
    """
    ec_state_changed = pyqtSignal(str, str)
    pause_commands = ["Abort", "Halt", "Resume", "Stop"]

    def __init__(self, engine, parent=None):
        super().__init__(parent=parent)
        # Create our widgets
        self._stop_timer = QTimer()
        self._stop_timer.setSingleShot(True)
        self._stop_timer.timeout.connect(self._on_request_stop)
        self.engine = engine
        self.startBtn = QPushButton("Start")
        self.pauseBtn = QPushButton("Pause")
        self.resumeBtn = QPushButton("Resume")
        self.stopBtn = QPushButton("Stop")
        self.haltBtn = QPushButton("Halt")

        self.state_widgets = {
            "start": self.startBtn,
            "pause": self.pauseBtn,
            "resume": self.resumeBtn,
            "stop": self.stopBtn,
            "halt": self.haltBtn,
        }
        # 'paused': QComboBox()}
        # Add the options to QComboBox
        self._cur_state = None
        ## Add all the widgets to the stack
        # for nm, widget in self.state_widgets.items():
        #     self.addWidget(widget)

    def ask_for_a_stop(self):
        self._stop_timer.start(250)

    def _on_request_stop(self):
        self.on_stop_clicked()

    @pyqtSlot("QString", "QString")
    def on_engine_state_change(self, state, old_state):
        """Update the control widget based on the state"""
        # self.setCurrentWidget(self.state_widgets[state])
        self._cur_state = (state, old_state)
        self.ec_state_changed.emit(state, old_state)

    def connect(self, engine):
        """Connect a QRunEngine object"""
        # Connect all the control signals to the engine slots
        self.state_widgets["start"].clicked.connect(self.on_start_clicked)
        self.state_widgets["pause"].clicked.connect(self.on_pause_clicked)
        self.state_widgets["resume"].clicked.connect(self.on_resume_clicked)
        self.state_widgets["halt"].clicked.connect(self.on_halt_clicked)
        self.state_widgets["stop"].clicked.connect(self.on_stop_clicked)

        # Update our control widgets based on this engine
        engine.engine_state_changed.connect(self.on_engine_state_change)
        # Set the current widget correctly
        self.on_engine_state_change(engine.state, None)

    def on_start_clicked(self):
        if self.engine.state.find("idle") > -1:
            self.engine.start()
        else:
            print("cant start: current state is %s" % self.engine.state)
            self.on_stop_clicked()

    def on_pause_clicked(self):
        if self.engine.state.find("running") > -1:
            try:
                self.engine.pause()
            except:
                print("pause was called: current state is %s" % self.engine.state)
        else:
            print("cant pause: current state is %s" % self.engine.state)

    def on_resume_clicked(self):
        if self.engine.state.find("paused") > -1:
            try:
                self.engine.resume()
            except:
                print("resume was called: current state is %s" % self.engine.state)
        else:
            print("cant resume: current state is %s" % self.engine.state)

    def on_halt_clicked(self):
        self.engine.halt()

    def on_stop_clicked(self):
        if self.engine.state.find("idle") == -1:
            try:
                print("on_stop_clicked: ", self._cur_state)
                uids = self.engine.stop()
                self.engine.exec_result.emit(uids)
            except:
                print("stop was called: current state is %s" % self.engine.state)

        # self.engine.exec_result.emit(uids)


class EngineWidget(QWidget):
    """
    RunEngine Control Widget
    Parameters
    ----------
    engine : RunEngine, optional
        The underlying RunEngine object. A basic version wil be instatiated if
        one is not provided
    plan_creator : callable, optional
        A callable  that takes no parameters and returns a generator. If the
        plan is meant to be called repeatedly the function should make sure
        that a refreshed generator is returned each time
    """
    state_changed = pyqtSignal(str, str)
    exec_result = pyqtSignal(object)
    prog_changed = pyqtSignal(object)

    def __init__(self, engine=None, plan_creator=None, mongo_db_nm="mongo_databroker",parent=None):
        # Instantiate widget information and layout
        super().__init__(parent=parent)
        # Create a new RunEngine if we were not provided one
        self._engine = None
        self.control = None
        self.engine = engine or QRunEngine()
        self._old_state = ""
        self._new_state = ""
        self.prog_changed = self.engine.prog_changed

        self.db = Broker.named(mongo_db_nm)#"pystxm_amb_bl10ID1")
        self.engine.subscribe(self.db.insert)

        self.sd = SupplementalData()
        self.engine.preprocessors.append(self.sd)
        # install a metadata validator
        # self.engine.md_validator = self.ensure_sample_number

        if plan_creator:
            self.engine.plan_creator = plan_creator

        self.engine.exec_result.connect(self.on_exec_result)

    def on_state_changed(self, new_state, old_state):
        self._old_state = old_state
        self._new_state = new_state
        self.state_changed.emit( new_state, old_state)

    def on_exec_result(self, uids):
        #print("EngineWidget: on_exec_result: state is [%s]" % self.engine.state)
        #print("EngineWidget: on_exec_result: uids are ", uids)
        self.on_state_changed(self.engine.state, self._old_state)
        self.exec_result.emit(uids)

    @property
    def engine(self):
        """
        Underlying QRunEngine object
        """
        return self._engine

    @engine.setter
    def engine(self, engine):
        _logger.debug("Storing a new RunEngine object")
        # Do not allow engine to be swapped while RunEngine is active
        if self._engine and self._engine.state != "idle":
            raise RuntimeError(
                "Can not change the RunEngine while the " "RunEngine is running!"
            )
        self.control = EngineControl(engine=engine)
        self.control.ec_state_changed.connect(self.on_state_changed)
        # Connect signals
        self._engine = engine
        self.control.connect(self._engine)

    def subscribe_cb(self, func, filter="all"):
        """
        subscribe a function to the engine on a particular filter
        :param func:
        :param filter:
        :return:
        """
        _id = self.engine.subscribe(func)
        return _id

    def unsubscribe_cb(self, _id):
        """
        unsubscribe a function with cb id _id
        :param _id:
        :return:
        """
        self.engine.unsubscribe(_id)

    def assign_baseline_devs(self, devs):
        if type(devs) is list:
            self.sd.baseline = devs
        else:
            print("assign_baseline_devs: arg devs must be a list")



class ZMQEngineWidget(QWidget):
    """
    RunEngine Control Widget
    Parameters
    ----------
    Somehow this class must appear to be a BlueSky EngineWidget but only talks to the DCS server connected over ZMQ
    """
    state_changed = pyqtSignal(str, str)
    exec_result = pyqtSignal(object)
    prog_changed = pyqtSignal(object)
    msg_to_app =  pyqtSignal(object)

    def __init__(self, devices_dct={}, parent=None):
        # Instantiate widget information and layout
        super().__init__(parent=parent)
        # Create a new RunEngine if we were not provided one
        self._engine = ZMQDevManager(devices_dct)
        self.control = None
        self.engine = self._engine
        self._old_state = ""
        self._new_state = ""
        self.prog_changed = self.engine.prog_changed
        self.msg_to_app = self.engine.msg_to_app

        #skip connecting a broker
        self.db = None # Broker.named(mongo_db_nm)#"pystxm_amb_bl10ID1")
        self.engine.exec_result.connect(self.on_exec_result)

    def is_dcs_server_local(self):
        return self.engine.is_dcs_server_local()

    def on_state_changed(self, new_state, old_state):
        self._old_state = old_state
        self._new_state = new_state
        self.state_changed.emit( new_state, old_state)

    def on_exec_result(self, exec_result_dct):
        _logger.debug(f"on_exec_result: passed {exec_result_dct['run_uids']} (unused)")
        #SKIP self.on_state_changed(self.engine.state, self._old_state)
        self.exec_result.emit(exec_result_dct['run_uids'])
        _logger.info(f"DCS server saved: {exec_result_dct['file_name']}")

    def on_msg_to_app(self, msg):
        """
        send a specific message from the DCS server to pyStxm
        """
        self.msg_to_app.emit(msg)


    @property
    def engine(self):
        """
        Underlying QRunEngine object
        """
        return self._engine

    @engine.setter
    def engine(self, engine):
        _logger.debug("Storing a new ZMQRunEngine object (unused)")
        # Do not allow engine to be swapped while RunEngine is active
        # if self._engine and self._engine.state != "idle":
        #     raise RuntimeError(
        #         "Can not change the RunEngine while the " "RunEngine is running!"
        #     )
        # self.control = EngineControl(engine=engine)
        # self.control.ec_state_changed.connect(self.on_state_changed)
        # # Connect signals
        # self._engine = engine
        # self.control.connect(self._engine)

    def subscribe_cb(self, func, filter="all"):
        """
        subscribe a function to the engine on a particular filter
        :param func:
        :param filter:
        :return:
        """
        _logger.debug(f"subscribe_cb: passed {func} (unused)")
        # _id = self.engine.subscribe(func)
        _id = 0
        return _id

    def unsubscribe_cb(self, _id):
        """
        unsubscribe a function with cb id _id
        :param _id:
        :return:
        """
        _logger.debug(f"unsubscribe_cb: passed {_id} (unused)")
        #  self.engine.unsubscribe(_id)

    def assign_baseline_devs(self, devs):
        # if type(devs) is list:
        #     self.sd.baseline = devs
        # else:
        #     print("assign_baseline_devs: arg devs must be a list")
        _logger.debug(f"assign_baseline_devs: passed {devs} (unused)")