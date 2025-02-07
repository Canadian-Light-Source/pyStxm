import time

from ophyd import Component as Cpt, EpicsSignal, Device, EpicsSignalRO



class SIS3820ScalarDevice(Device):
    run = Cpt(EpicsSignal, "mcs:startScan", kind="omitted", put_complete=True)
    dwell = Cpt(EpicsSignalRO, "mcs:dwell", kind="omitted")
    waveform_rbv = Cpt(EpicsSignalRO, "mcs:scan", kind="omitted")

    def __init__(self, prefix, name):
        super(SIS3820ScalarDevice, self).__init__(prefix, name=name)
        self._cb_ids = []
        self.row = 0
        self.col = 0
        self.num_rows = 0
        self.num_cols = 0
        self.is_pxp_scan = False

    def init_indexs(self):
        '''
        initialize the different row and column indexes
        '''
        self.row = 0
        self.col = 0
        self.num_rows = 0
        self.num_cols = 0

    def increment_indexes(self):
        '''
        increment the different indexes based on a pxp scan or lxl
        '''
        if self.is_pxp_scan:
            if (self.col + 1) > self.num_cols:
                # start a new row
                self.col = 0
                self.row = self.row + 1
            else:
                self.col = self.col + 1
        else:
            # is lxl
            self.row = self.row + 1

    def enable_on_change_sub(self):
        self.row = 0
        self.disable_on_change_sub()
        print("enable_on_change_sub: self._cb_ids.append(self.dwell.subscribe(self.on_waveform_changed))")
        #self._cb_ids.append(self.waveform_rbv.subscribe(self.on_waveform_changed))
        self._cb_ids.append(self.waveform_rbv.subscribe(self.on_waveform_changed))
        #self._cb_ids.append(self.on_waveform_changed)

    def disable_on_change_sub(self):
        #self.destroy()
        self.waveform_rbv.unsubscribe_all()
        #self.waveform_rbv.clear_sub(self.on_waveform_changed)
        print("disable_on_change_sub: self.dwell.unsubscribe_all()")
        # for cb_id in self._cb_ids:
        #     self.waveform_rbv.unsubscribe(cb_id)
        #     self._cb_ids.remove(cb_id)

        #self.waveform_rbv._read_pv.clear_callbacks()
        # for cbid in self._cb_ids:
        #     self.waveform_rbv.unsubscribe(cbid)
        #
        #     self._cb_ids.remove(cbid)

    def on_waveform_changed(self, *args, **kwargs):
        #print(kwargs)

        # self.row += 1
        #if self.run.get() == 1:
        print(f"Row: {self.row}")
        self.increment_indexes()



if __name__ == '__main__':
    import sys
    import numpy as np
    from bluesky import RunEngine
    from databroker import Broker
    import bluesky.plan_stubs as bps
    import bluesky.preprocessors as bpp
    from ophyd.sim import det1, det2, det3, motor1, motor2
    from bcm.devices.ophyd.stxm_sample_mtr import e712_sample_motor

    from ophyd import EpicsMotor
    from epics import PV
    import pprint



    # def qt_plot_handler(plot_dct):
    #     print(plot_dct)
    # from PyQt5.QtWidgets import QApplication
    #
    # app = QApplication([])

    # piezo_mtr = EpicsMotor('PZAC1610-3-I12-40', name="sfx")
    cx_mtr = EpicsMotor("SMTR1610-3-I12-45", name="CoarseX")
    cy_mtr = EpicsMotor("SMTR1610-3-I12-46", name="CoarseY")
    piezo_mtr_x = e712_sample_motor('PZAC1610-3-I12-40', name="sfx")
    piezo_mtr_y = e712_sample_motor('PZAC1610-3-I12-41', name="sfy")

    sis3820_dev = SIS3820ScalarDevice('MCS1610-310-01:', name='SIS3820')
    sis3820_dev.enable_on_change_sub()

    # the following produces a 10 event run
    RE = RunEngine({})
    db = Broker.named("pystxm_amb_bl10ID1")
    # Insert all metadata/data captured into db.
    RE.subscribe(db.insert)
    dets = [sis3820_dev]

    while True:
        t_row = sis3820_dev.row
        for i in range(10):
            time.sleep(0.2)
            if sis3820_dev.row >= 50:
                sis3820_dev.enable_on_change_sub()


    print("Done processing")
