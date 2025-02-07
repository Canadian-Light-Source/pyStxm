from PyQt5 import QtCore, QtWidgets
import queue
import time

import numpy as np

from cls.appWidgets.dialogs import message_no_btns

from bcm.devices import BaseObject, BaseDevice
from bcm.devices.ophyd.e712_wavegen.e712_com_cmnds import (
    e712_cmds,
    make_base_e712_com_dict,
)

# RUSS FEB 25 from cls.appWidgets.splashScreen import get_splash
"""
with this module the goal is not to implement EVERY connection to the E712 only the really
time consuming ones like retrienving waveform data
 
"""


# class PI_E712_wave_generator_wavedata(QtCore.QObject):
class PI_E712_wave_generator_wavedata(BaseObject):
    def __init__(self, prefix="IOCE712:", wvgen_num=1):
        super(PI_E712_wave_generator_wavedata, self).__init__("E712_wavdata")
        self.prefix = prefix
        self.wg_num = wvgen_num

        # self.get_wavtbl = PV('%sGetWavTbl%d' % (self.prefix, self.wg_num))
        # self.wavtbl_rbv = PV('%sWaveTbl%d_RBV' % (self.prefix, self.wg_num))
        #
        # self.get_ddltbl = PV('%sGetDDLTbl%d' % (self.prefix, self.wg_num))
        # self.ddltbl_rbv = PV('%sDDLTbl%d_RBV' % (self.prefix, self.wg_num))
        # self.ddl_tbl = PV('%sDDLTbl%d' % (self.prefix, self.wg_num))
        self.get_wavtbl = self.add_device("%sGetWavTbl%d" % (self.prefix, self.wg_num))
        self.wavtbl_rbv = self.add_device(
            "%sWaveTbl%d_RBV" % (self.prefix, self.wg_num)
        )

        self.get_ddltbl = self.add_device("%sGetDDLTbl%d" % (self.prefix, self.wg_num))
        self.ddltbl_rbv = self.add_device("%sDDLTbl%d_RBV" % (self.prefix, self.wg_num))
        self.ddl_tbl = self.add_device("%sDDLTbl%d" % (self.prefix, self.wg_num))

    def get_ddl_table(self):
        # first force the table pv to update
        self.get_ddltbl.put(1)
        # give it time
        time.sleep(0.25)
        # now read it
        data = self.ddltbl_rbv.get()
        return data

    def get_wav_table(self):
        # first force the table pv to update
        self.get_wavtbl.put(1)
        # give it time
        time.sleep(0.25)
        # now read it
        data = self.wavtbl_rbv.get_array()
        return data

    def put_ddl_table(self, data):
        # clear the ddl table first
        self.clr_ddltbl.put(1, wait=True)
        # give it time
        time.sleep(0.25)
        # now put it to the controller
        self.ddl_tbl.put(data, wait=True)


# class E712Com(QtCore.QObject):
class E712ComThread(QtCore.QThread):

    data_changed = QtCore.pyqtSignal(
        object
    )  # a dict that contains all info needed to know who this data belongs to

    def __init__(self, prefix, cmnd_queue, xaxis_id=3, yaxis_id=4, parent=None):
        super(E712ComThread, self).__init__(parent)
        self.setObjectName(prefix + "com_thread")
        self.prefix = prefix
        self.xaxis_id = xaxis_id
        self.yaxis_id = yaxis_id
        self.abort = False
        self.mutex = QtCore.QMutex()
        self.condition = QtCore.QWaitCondition()
        self.cmnd_queue = cmnd_queue
        self.wg1 = PI_E712_wave_generator_wavedata(prefix=prefix, wvgen_num=1)
        self.wg2 = PI_E712_wave_generator_wavedata(prefix=prefix, wvgen_num=2)
        self.wg3 = PI_E712_wave_generator_wavedata(prefix=prefix, wvgen_num=3)
        self.wg4 = PI_E712_wave_generator_wavedata(prefix=prefix, wvgen_num=4)

        # self.wg_cmnds = PV('%sSendCmnds' % self.prefix)
        # self.get_trig_table = PV('%sGetTrigTbl' % self.prefix)
        # self.trig_table_rbv = PV('%sTrigTbl_RBV' % self.prefix)
        self.wg_cmnds = BaseDevice("%sSendCmnds" % self.prefix)
        self.wg_trig_cmnds = BaseDevice("%sSendTrigCmnds" % self.prefix)
        self.get_trig_table = BaseDevice("%sGetTrigTbl" % self.prefix)
        self.trig_table_rbv = BaseDevice("%sTrigTbl_RBV" % self.prefix)

        self.wg_dct = {}
        self.wg_dct[1] = self.wg1
        self.wg_dct[2] = self.wg2
        self.wg_dct[3] = self.wg3
        self.wg_dct[4] = self.wg4
        self.is_busy = False

    def send_command_string(self, cmnds, verbose=False):
        """
        sends a long string of commands down to the E712 controller
        """

        cmnds += ";"
        cmnds = cmnds.replace(";;", ";")
        if verbose:
            print("sending: <%s>" % cmnds)
        #print("e712_com_thread: send_command_string: starting")
        self.wg_cmnds.put(cmnds, wait=True)
        time.sleep(0.1)
        #print("e712_com_thread: send_command_string: done")


    def send_trig_command_string(self, cmnds, verbose=False):
        """
        sends a long string of commands down to the E712 controller
        """

        cmnds += ";"
        cmnds = cmnds.replace(";;", ";")
        if verbose:
            print("sending: <%s>" % cmnds)
        #print("e712_com_thread: send_trig_command_string: starting")
        self.wg_trig_cmnds.put(cmnds, wait=True)
        time.sleep(0.1)
        #print("e712_com_thread: send_trig_command_string: done")

    def get_triggers_table(self):
        data = []
        self.get_trig_table.put(1, wait=True)
        time.sleep(0.25)
        data = self.trig_table_rbv.get_array()
        return data

    def stop(self):
        self.abort = True

    def run(self):
        print("Starting E712 Com Queue monitoring")
        # splash = get_splash()
        # splash.show_msg('Starting E712 Com Queue monitoring')

        while not self.abort:

            # self.mutex.lock()
            # copy some member vars if need be to local ones
            # print 'sleeping'
            # time.sleep(1.500)
            time.sleep(0.500)
            #time.sleep(0.050)

            call_task_done = False
            while not self.cmnd_queue.empty():
                # pull a command dict from the queue
                resp = self.cmnd_queue.get()

                # check the command
                if resp["cmnd"] is e712_cmds.EXIT:
                    self.abort = True
                    break

                if resp["cmnd"] is e712_cmds.SEND_COMMANDS:
                    cmnds = resp["arg"]
                    #print('Pulled from Queue: <%s>' % cmnds)
                    self.send_command_string(cmnds)

                if resp["cmnd"] is e712_cmds.SEND_TRIG_COMMANDS:
                    cmnds = resp["arg"]
                    #print('Pulled from Queue: <%s>' % cmnds)
                    self.send_trig_command_string(cmnds)

                if resp["cmnd"] is e712_cmds.GET_ALL_WAV_DATA:
                    # pull the arg (which is which table to get and make the call

                    cb = resp["cb"]
                    xdata = self.wg_dct[self.xaxis_id].get_wav_table()
                    ydata = self.wg_dct[self.yaxis_id].get_wav_table()
                    trigdata = self.get_triggers_table()
                    if (type(xdata) or type(ydata) or type(trigdata))!= np.ndarray:
                        print("no wave table data to load")
                        return
                    (x_len,) = xdata.shape
                    (y_len,) = ydata.shape
                    (trig_len,) = trigdata.shape
                    shortest = None
                    if y_len < x_len:
                        shortest = y_len
                    else:
                        shortest = x_len
                    if x_len < trig_len:
                        shortest = x_len
                    else:
                        shortest = trig_len

                    e712com_dct = make_base_e712_com_dict(
                        e712_cmds.GET_WAV_DATA,
                        None,
                        (xdata[:shortest], ydata[:shortest], trigdata[:shortest]),
                        cb=cb,
                    )
                    self.data_changed.emit(e712com_dct)
                    call_task_done = True

                if resp["cmnd"] is e712_cmds.GET_WAV_DATA:
                    # pull the arg (which is which table to get and make the call
                    tblid = resp["arg"]
                    cb = resp["cb"]
                    data = self.wg_dct[tblid].get_wav_table()
                    e712com_dct = make_base_e712_com_dict(
                        e712_cmds.GET_WAV_DATA, tblid, data, cb=cb
                    )
                    self.data_changed.emit(e712com_dct)
                    call_task_done = True

                if resp["cmnd"] is e712_cmds.GET_DDL_DATA:
                    # pull the arg (which is which table to get and make the call
                    tblid = resp["arg"]
                    cb = resp["cb"]
                    data = self.wg_dct[tblid].get_ddl_table()
                    e712com_dct = make_base_e712_com_dict(
                        e712_cmds.GET_WAV_DATA, tblid, data, cb=cb
                    )
                    self.data_changed.emit(e712com_dct)
                    call_task_done = True

                if resp["cmnd"] is e712_cmds.GET_TRIG_DATA:
                    # pull the arg (which is which table to get and make the call
                    cb = resp["cb"]
                    data = self.get_triggers_table()
                    e712com_dct = make_base_e712_com_dict(
                        e712_cmds.GET_WAV_DATA, 0, data, cb=cb
                    )
                    self.data_changed.emit(e712com_dct)
                    call_task_done = True

            if call_task_done is True:
                self.cmnd_queue.task_done()

        print("exiting E712 Com Queue monitoring")
        # self.mutex.unlock()
