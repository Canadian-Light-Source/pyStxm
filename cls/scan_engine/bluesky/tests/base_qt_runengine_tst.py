
############
# Standard #
############
import logging
import time

from time import localtime, gmtime

############
# External #
############
from bluesky import RunEngine
from bluesky.utils import RunEngineInterrupted
from bluesky.preprocessors import SupplementalData

from databroker import Broker

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

import bluesky.preprocessors as bpp
import bluesky.plan_stubs as bps
from ophyd.sim import det1, det2, det3, motor1, motor2, motor3, SynGauss, noisy_det


def point_spec_scan(
    dets, motors, rois, num_ev_pnts=4, md={"scan_type": "point_spec_scan"}
):
    @bpp.run_decorator(md=md)
    def do_scan():
        ev_mtr = motor3

        for ev in range(num_ev_pnts):
            yield from bps.mv(ev_mtr, ev)
            for i in range(len(motors)):
                yield from bps.mv(motors[i], rois[i]["START"])

                yield from bps.create(name="primary")
                yield from bps.read(dets[0])
                yield from bps.save()
                print(
                    "ev[%d] : done read for motor[%d] at %.2f"
                    % (ev, i, rois[i]["START"])
                )
                yield from bps.sleep((1.0))

    return (yield from do_scan())

class QRunEngine(QObject, RunEngine):
    engine_state_changed = pyqtSignal(str, str)
    msg_changed = pyqtSignal(object)
    exec_result = pyqtSignal(object)
    prog_changed = pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Attach the state_hook to emit signals
        self.state_hook = self.on_engine_state_change
        self._execution_result = None
        self.msg_hook = self.on_msg_hook

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
        self._max_prog_pnts = 0
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


class EngineControl(QWidget):
    """
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
        self._cur_state = None

    @pyqtSlot("QString", "QString")
    def on_engine_state_change(self, state, old_state):
        """Update the control widget based on the state"""
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
            except:
                print("stop was called: current state is %s" % self.engine.state)

        # self.engine.exec_result.emit(uids)


class EngineWidget(QWidget):
    """
    intermediate widget that has the instances of QRunEngine and
    """
    state_changed = pyqtSignal(str, str)
    msg_changed = pyqtSignal(str)

    def __init__(self, engine=None, plan_creator=None, parent=None):
        # Instantiate widget information and layout
        super().__init__(parent=parent)
        # Create a new RunEngine if we were not provided one
        self._engine = None
        self.control = None
        self.engine = engine or QRunEngine()
        self.msg_changed = self.engine.msg_changed
        self.setStyleSheet("QLabel {qproperty-alignment: AlignCenter}")

        # self.db = Broker.named('temp')
        self.db = Broker.named("pystxm_amb_bl10ID1")
        self.engine.subscribe(self.db.insert)

        self.sd = SupplementalData()
        self.engine.preprocessors.append(self.sd)
        # install a metadata validator
        # self.engine.md_validator = self.ensure_sample_number

        if plan_creator:
            self.engine.plan_creator = plan_creator

        self.engine.exec_result.connect(self.on_exec_result)

    def on_state_changed(self, new_state, old_state):
        self.state_changed.emit( new_state, old_state)

    def on_exec_result(self, uids):
        print("on_exec_result: state is [%s]" % self.engine.state)
        print("on_exec_result: uids are ", uids)

    @property
    def engine(self):
        """
        Underlying QRunEngine object
        """
        return self._engine

    @engine.setter
    def engine(self, engine):
        print("DEBUG: Storing a new RunEngine object")
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


class Window(QWidget):

    def __init__(self, show_re_msgs=False):
        super(Window, self).__init__()

        self.scan_plan = None
        self.ew = EngineWidget()
        self.ew.state_changed.connect(self.on_state_changed)
        if show_re_msgs:
            self.ew.msg_changed.connect(self.on_msg_changed)

        self._start_btn = QPushButton("Start")
        self._stop_btn = QPushButton("Stop")
        self._pause_btn = QPushButton("Pause")
        self._resume_btn = QPushButton("Resume")
        self._status_lbl = QLabel("STOPPED")

        self._start_btn.clicked.connect(self.on_start_btn)
        self._stop_btn.clicked.connect(self.on_stop_btn)
        self._pause_btn.clicked.connect(self.on_pause_btn)
        self._resume_btn.clicked.connect(self.on_resume_btn)

        vbox = QVBoxLayout()
        vbox.addWidget((self._start_btn))
        vbox.addWidget((self._pause_btn))
        vbox.addWidget((self._resume_btn))
        vbox.addWidget((self._stop_btn))
        vbox.addWidget(self._status_lbl)
        self.setLayout(vbox)
        
    def create_point_spec_scan_plan(self):
        """
        creates a simple plan for testing
        """
        x_roi = {"START": -25}
        y_roi = {"START": -15}

        rois = [x_roi, y_roi]
        mtrs = [motor1, motor2]
        dets = [noisy_det]
        return(point_spec_scan(dets, mtrs, rois))

    def on_msg_changed(self, msg):
        print(msg)

    def on_state_changed(self, new, old):
        print(f"on_state_changed old={old} new={new}")
        self._status_lbl.setText(new)

    def on_start_btn(self):
        print("Start pressed")
        self.ew.engine.plan_creator = lambda: self.create_point_spec_scan_plan()
        self.ew.control.state_widgets["start"].clicked.emit()

    def on_pause_btn(self):
        print("Pause pressed")
        self.ew.control.state_widgets["pause"].clicked.emit()

    def on_resume_btn(self):
        print("Resume pressed")
        self.ew.control.state_widgets["resume"].clicked.emit()

    def on_stop_btn(self):
        print("Stop pressed")
        self.ew.control.state_widgets["stop"].clicked.emit()



if __name__ == '__main__':
    import sys

    app = QApplication([])
    w = Window(show_re_msgs=False)

    w.show()
    sys.exit(app.exec_())
