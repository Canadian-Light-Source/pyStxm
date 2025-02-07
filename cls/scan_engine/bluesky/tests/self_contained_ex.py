############
# Standard #
############
import logging
import time
import simplejson as json
import numpy as np
from cycler import cycler

from time import localtime, gmtime

############
# External #
############
from bluesky import RunEngine
from bluesky.utils import RunEngineInterrupted
from bluesky.preprocessors import SupplementalData

from databroker import Broker

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication, QProgressBar
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer

import bluesky.preprocessors as bpp
import bluesky.plan_stubs as bps
from bluesky.plans import scan, rel_scan, scan_nd
from ophyd.sim import det1, det2, det3, motor1, motor2, motor3, SynGauss, noisy_det

from cls.stylesheets import master_colors
from bcm.devices.ophyd.motor import MotorQt


def point_spec_scan(
        dets, motors, rois, num_ev_pnts=4, md={"scan_type": "point_spec_scan"}
):
    md["metadata"] = json.dumps({"num_points": num_ev_pnts})

    @bpp.run_decorator(md=md)
    def do_scan():
        ev_mtr = motor3

        ev_mtr.settle_time = 500.0
        for ev in range(num_ev_pnts):
            yield from bps.mv(ev_mtr, ev)
            for i in range(len(motors)):
                yield from bps.mv(motors[i], rois[i]["START"])
                yield from bps.trigger_and_read(dets)

        # yield from bps.create(name="primary")
        # yield from bps.read(dets)
        # yield from bps.save()
        print(
            "ev[%d] : done read for motor[%d] at %.2f"
            % (ev, i, rois[i]["START"])
        )
        yield from bps.sleep((1.0))

    return (yield from do_scan())

def two_D_raster_scan(
        dets, mtrs, rois, num_pts=10, md={"scan_type": "two_D_raster_scan"}
):
    md["metadata"] = json.dumps({"num_points": num_pts})


    def do_scan():
        xmtr = mtrs[0]
        ymtr = mtrs[1]

        # yield from scan(dets,
        #         ymtr, rois[0]["START"],  rois[0]["STOP"],  # scan motor1 from -1.5 to 1.5
        #         xmtr, rois[1]["START"],  rois[1]["STOP"],  # ...while scanning motor2 from -0.1 to 0.1
        #         num_pts, md=md)
        xsp = np.linspace(rois[0]["START"],  rois[0]["STOP"], num_pts)
        ysp = np.linspace(rois[1]["START"], rois[1]["STOP"], num_pts)
        cy = cycler(ymtr, ysp) * cycler(xmtr, xsp)

        yield from scan_nd([dets[0]], cy, md=md)
        # print(
        #     "ev[%d] : done read for motor[%d] at %.2f"
        #     % (ev, i, rois[i]["START"])
        # )
        # yield from bps.sleep((1.0))
        print("two_D_raster_scan: done")

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
        update_progress subscribes to the msgs from the runengine and pulls out the parts needed to determine the
        progress of the current scan
        :param name:
        :param doc:
        :return:
        """
        if name.find("start") > -1:
            if self._master_start_time == 0:
                self._master_start_time = doc["time"]

            self._start_time = doc["time"]
            self._scan_idx += 1
            if "metadata" in list(doc.keys()):
                dct = json.loads(doc["metadata"])
                self._max_prog_pnts = dct["num_points"]
            else:
                # indicate that the scan is a flyer
                self._max_prog_pnts = -1
                #print("Scan progress: Flyer scan in progress...")
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
                    #print('Scan progress: %d/%d %.2f complete| %s ' % (seq_num, self._max_prog_pnts, prog, elapsed_tm_str))
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
            elif seq_num <= self._max_prog_pnts:
                self._stop_time = doc["time"]
                if self._event_uid == 0:
                    # these are the events we want to look at for progress, all others skipped
                    self._event_uid = doc["descriptor"]
                if doc["descriptor"] == self._event_uid:
                    prog = (float(seq_num) / float(self._max_prog_pnts)) * 100.0
                    # elapsed_tm = gmtime(self._stop_time - self._start_time)
                    # elapsed_tm_str = time.strftime("Elapsed time %H:%M:%S", elapsed_tm)
                    # print('Scan progress: %d/%d %.2f complete| %s ' % (seq_num, self._max_prog_pnts, prog, elapsed_tm_str))
                    # self.prog_changed.emit({'scan_idx': self._scan_idx, 'prog':prog, 'elapsed_tm_str':elapsed_tm_str, 'elapsed_tm': elapsed_tm})
                    d = self.create_prog_dict(
                        self._scan_idx, self._start_time, self._stop_time, prog=prog
                    )
                    #skip the last 100 % prog that has a elapsed time of 23:59:59 ( also has tm_year of 1969)
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

            self._max_prog_pnts = 0

        #print(name, doc)




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
    exec_result = pyqtSignal(object)
    prog_changed = pyqtSignal(object)

    def __init__(self, engine=None, plan_creator=None, parent=None):
        # Instantiate widget information and layout
        super().__init__(parent=parent)
        # Create a new RunEngine if we were not provided one
        self._engine = None
        self.control = None
        self.engine = engine or QRunEngine()
        self.msg_changed = self.engine.msg_changed
        self.prog_changed = self.engine.prog_changed
        #self.setStyleSheet("QLabel {qproperty-alignment: AlignCenter}")
        self._old_state = ""
        self._new_state = ""

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
        self._old_state = old_state
        self._new_state = new_state
        self.state_changed.emit(new_state, old_state)



    def on_exec_result(self, uids):
        # print("on_exec_result: state is [%s]" % self.engine.state)
        # print("on_exec_result: uids are ", uids)
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
        #print("DEBUG: Storing a new RunEngine object")
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

class EngineLabel(QLabel):
    """
    QLabel to display the RunEngine Status
    Attributes
    ----------
    color_map : dict
        Mapping of Engine states to color displays
    """
    color_map = {
        "running": (
            master_colors["black"]["rgb_str"],
            master_colors["fbk_moving_ylw"]["rgb_str"], # Running ON
            master_colors["fbk_dark_ylw"]["rgb_str"], # Running OFF
            master_colors["app_red"]["rgb_str"],
        ),
        "pausing": (
            master_colors["black"]["rgb_str"],
            master_colors["app_yellow"]["rgb_str"],
            master_colors["app_ltblue"]["rgb_str"],
            master_colors["app_blue"]["rgb_str"],
        ),
        "paused": (
            master_colors["black"]["rgb_str"],
            master_colors["app_yellow"]["rgb_str"],
            master_colors["app_ltblue"]["rgb_str"],
            master_colors["app_blue"]["rgb_str"],
        ),
        "stopping": (
            master_colors["black"]["rgb_str"],
            master_colors["app_yellow"]["rgb_str"],
            master_colors["app_ltblue"]["rgb_str"],
            master_colors["app_blue"]["rgb_str"],
        ),
        "idle": (
            master_colors["white"]["rgb_str"],
            master_colors["app_drkgray"]["rgb_str"],
            master_colors["app_ltblue"]["rgb_str"],
            master_colors["app_blue"]["rgb_str"],
        ),
    }

    def __init__(self, lbl):
        super(EngineLabel, self).__init__()
        self._lbl = lbl
        self._blink_timer = QTimer()
        self._blink_timer.timeout.connect(self.on_timeout)
        self._tmr_en = False
        self._blink_timer.start(500)
        self._cur_color = None
        self._state_str = None


    def on_timeout(self):

        if self._tmr_en:
            if self.isEnabled():
                self.setEnabled(False)
            else:
                self.setEnabled(True)
        else:
            if not self.isEnabled():
                self.setEnabled(True)
        self._set_colors()
        self._blink_timer.start(500)

    #@QtCore.pyqtSlot("QString", "QString")
    def on_state_change(self, new_state, old_state):
        #print(f"EngineLabel: on_state_change: state=[{new_state}], old_state=[{old_state}] ")
        if new_state is None:
            return
        self._state_str = new_state.upper()
        # Update the label
        if new_state.find("running") > -1:
            self._tmr_en = True
        else:
            self._tmr_en = False

        self._lbl.setText(self._state_str)
        # Update the font and background color
        self._cur_color = self.color_map[new_state]


    def _set_colors(self):
        if self._tmr_en:
            if self.isEnabled():
                clr1, clr2, clr3, cl4 = self._cur_color
            else:
                clr1, clr3, clr2, clr4 = self._cur_color
        else:
            clr1, clr2, clr3, cl4 = self._cur_color

        ss = "QLabel {color: %s; background-color: %s;}" % (clr1, clr2)
        self._lbl.setStyleSheet(ss)

    def connect_to_engine(self, engine):
        """Connect an existing QRunEngine"""
        engine.engine_state_changed.connect(self.on_state_change)
        self.on_state_change(engine.state, "")


class Window(QWidget):
    def __init__(self, show_re_msgs=False):
        super(Window, self).__init__()

    
        self.scan_plan = None
        self.ew = EngineWidget()
        #self.ew.state_changed.connect(self.on_state_changed)
        self.ew.exec_result.connect(self.on_exec_result)
        self.ew.prog_changed.connect(self.on_prog_chg)
        if show_re_msgs:
            self.ew.msg_changed.connect(self.on_msg_changed)

        self._start_btn = QPushButton("Start")
        self._stop_btn = QPushButton("Stop")
        self._pause_btn = QPushButton("Pause")
        self._resume_btn = QPushButton("Resume")
        self._status_lbl = QLabel("STOPPED")
        self._elapsed_time_lbl = QLabel("Elapsed Time: ")
        self._progbar = QProgressBar()
        self._progbar.setMinimum(0)
        self._progbar.setMaximum(100)

        self.engine_status_lbl = EngineLabel(self._status_lbl)
        self.engine_status_lbl.connect_to_engine(self.ew.engine)


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
        vbox.addWidget(self._progbar)
        vbox.addWidget(self._elapsed_time_lbl)
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
        return (point_spec_scan(dets, mtrs, rois, num_ev_pnts=400))

    def create_2D_raster_scan_plan(self):

        x_roi = {"START": -150, "STOP": 150}
        y_roi = {"START": -150, "STOP": 150}
        rois = [x_roi, y_roi]
        osax = MotorQt("PZAC1610-3-I12-43", name="OSAX")
        osay = MotorQt("PZAC1610-3-I12-44", name="OSAY")
        motor1.settle_time = 100
        motor2.settle_time = 100
        mtrs = [motor1, motor2]
        #mtrs = [osax, osay]
        dets = [noisy_det]
        return(two_D_raster_scan(dets, mtrs, rois, num_pts=15))

    def on_msg_changed(self, msg):
        print(msg)

    def on_prog_chg(self, prog_dct):
        """
        dct["scan_idx"] = scan_idx
        dct["prog"] = prog
        dct["elapsed_tm_str"] = elapsed_tm_str
        dct["elapsed_tm"] = elapsed_tm
        dct["mstr_elapsed_tm_str"] = mstr_elapsed_tm_str
        dct["mstr_elapsed_tm"] = mstr_elapsed_tm
        """
        #print(prog_dct)
        self._progbar.setValue(prog_dct["prog"])
        self._elapsed_time_lbl.setText(f"Elapsed Time: {prog_dct['elapsed_tm_str']}")

    def on_exec_result(self, uids):
        print(f"on_exec_result: uids=[{uids}]")

    def on_start_btn(self):
        print("Start pressed")
        #self.ew.engine.plan_creator = lambda: self.create_point_spec_scan_plan()
        self.ew.engine.plan_creator = lambda: self.create_2D_raster_scan_plan()
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