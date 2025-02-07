'''
Created on Nov 19, 2015

@author: bergr
'''

'''
Created on 2012-05-16

@author: bergr
'''
# BCM GLOBAL Settings for stxm
import os

import PyQt5.QtCore as QtCore
from PyQt5 import QtWidgets

# from bcm.device.counter import EpicsPv, EpicsPvCounter, BaseGate, BaseCounter

from bcm.devices import camera
from bcm.devices import aio
from bcm.devices import Mbbi
from bcm.devices import Mbbo

#from bcm.epics_devices.motor_v2 import Motor_V2 as apsMotor
from bcm.devices import Motor_Qt as apsMotor
from bcm.devices import sample_motor, sample_abstract_motor
from bcm.devices import  Scan
from bcm.devices import  Transform

from bcm.devices import BaseGate, BaseCounter
from bcm.devices.device_names import *
from bcm.devices import PvShutter



from cls.appWidgets.main_object import main_object_base, dev_config_base, POS_TYPE_BL, POS_TYPE_ES
from cls.appWidgets.splashScreen import get_splash
from cls.app_data.defaults import Defaults
from cls.applications.pyStxm import abs_path_to_ini_file, abs_path_to_top
from cls.scanning.e712_wavegen.e712 import E712ControlWidget
from cls.types.beamline import BEAMLINE_IDS
from cls.types.stxmTypes import sample_positioning_modes, sample_fine_positioning_modes, endstation_id_types
from cls.utils.cfgparser import ConfigClass
from cls.utils.log import get_module_logger

# from twisted.python.components import globalRegistry
_logger = get_module_logger(__name__)

appConfig = ConfigClass(abs_path_to_ini_file)


__version__ = '1.0.0'


AMBIENT_STXM = False


BEAMLINE_NAME = '10ID-1'
BEAMLINE_TYPE = 'STXM'
BEAMLINE_ENERGY_RANGE = (4.0, 18.5)



# class SplashScreen(QtWidgets.QWidget):
#     def __init__(self, hdr_msg, parent=None):
#         super(SplashScreen, self).__init__(parent)
#
#         self.msg = QtWidgets.QLabel(hdr_msg)
#         self.connect_lbl = QtWidgets.QLabel("Connecting: ")
#         vbox = QtWidgets.QVBoxLayout()
#         vbox.addWidget(self.msg)
#         vbox.addWidget(self.connect_lbl)
#         self.setLayout(vbox)
#
#     def on_new_connection(self, msg):
#         self.connect_lbl.setText(msg)

SCANNING_MODE = 'SAMPLEXY'
#SCANNING_MODE = 'GONI'

class dev_config_sim_ambient(dev_config_base):
    def __init__(self, splash=None):
        super(dev_config_sim_ambient, self).__init__(splash=splash)
        print 'Using simulated DEVICES'
        self.beamline = 'Ambient STXM 10ID1'
        self.sscan_rec_prfx = 'amb'
        self.es_id = endstation_id_types.AMBIENT
        self.sample_positioning_mode = sample_positioning_modes.COARSE
        self.splash = splash
        self.done = False
        #self.timer = QtCore.QTimer()
        #self.timer.timeout.connect(self.on_timer)
        self.init_devices()
        self.init_presets()


    def init_presets(self):
        self.devices['PRESETS']['MAX_SCAN_RANGE_X'] = 350
        self.devices['PRESETS']['MAX_SCAN_RANGE_Y'] = 200

        self.devices['PVS'][DNM_ENERGY_ENABLE].put(0)


    def init_devices(self):

        self.devices['POSITIONERS'][DNM_SAMPLE_FINE_X] = apsMotor('IOC:m1',pos_set=POS_TYPE_ES)
        self.devices['POSITIONERS'][DNM_SAMPLE_FINE_Y] = apsMotor('IOC:m2',pos_set=POS_TYPE_ES)
        self.devices['POSITIONERS'][DNM_COARSE_X] = apsMotor( 'IOC:m3',pos_set=POS_TYPE_ES)
        self.devices['POSITIONERS'][DNM_COARSE_Y] = apsMotor( 'IOC:m4',pos_set=POS_TYPE_ES)
        self.devices['POSITIONERS'][DNM_OSA_X] = apsMotor('IOC:m5',pos_set=POS_TYPE_ES)
        self.devices['POSITIONERS'][DNM_OSA_Y] = apsMotor('IOC:m6',pos_set=POS_TYPE_ES)
        self.devices['POSITIONERS'][DNM_DETECTOR_X] = apsMotor( 'IOC:m7',pos_set=POS_TYPE_ES)
        self.devices['POSITIONERS'][DNM_DETECTOR_Y] = apsMotor( 'IOC:m8',pos_set=POS_TYPE_ES)
        self.devices['POSITIONERS'][DNM_DETECTOR_Z] = apsMotor( 'IOC:m9',pos_set=POS_TYPE_ES)
        self.devices['POSITIONERS'][DNM_ZONEPLATE_Z] = apsMotor( 'IOC:m10',pos_set=POS_TYPE_ES)
        self.devices['POSITIONERS'][DNM_SAMPLE_X] = apsMotor( 'IOC:m11',pos_set=POS_TYPE_ES)
        self.devices['POSITIONERS'][DNM_SAMPLE_Y] = apsMotor('IOC:m12',pos_set=POS_TYPE_ES)

        self.devices['POSITIONERS'][DNM_COARSE_Z] = apsMotor('IOC:m13',pos_set=POS_TYPE_ES)

        prfx = self.sscan_rec_prfx
        connect_standard_beamline_positioners(self.devices, prfx)
        connect_devices(self.devices, prfx)

        print 'finished connecting to devices'
        self.done = True


class dev_config_amb(dev_config_base):
    def __init__(self, splash=None):
        super(dev_config_amb, self).__init__(splash=splash)
        print 'Using Full Ambient STXM Hardware Devices'
        self.beamline = 'AMB STXM 10ID1'
        self.sscan_rec_prfx = 'amb'
        self.es_id = endstation_id_types.AMBIENT
        self.sample_positioning_mode = sample_positioning_modes.COARSE
        self.splash = splash
        self.done = False
        #self.timer = QtCore.QTimer()
        #self.timer.timeout.connect(self.on_timer)
        self.init_devices()
        self.init_presets()


    def init_presets(self):
        self.devices['PRESETS']['MAX_SCAN_RANGE_X'] = 350
        self.devices['PRESETS']['MAX_SCAN_RANGE_Y'] = 200
        use_laser = appConfig.get_value('DEFAULT', 'use_laser')

        self.devices['PVS'][DNM_ENERGY_ENABLE].put(0)

        self.devices['PRESETS']['USE_LASER'] = use_laser


    def init_devices(self):

        #I don't have an elegant way yet to create these and also emit a signal to the splash screen
        #so this is a first attempt
        #self.timer.start(100)
        # maps names to device objects

        #self.msg_splash("Creating device[SampleFineX]")
        #								ApsMotorRecordMotor(motorCfgObj, positioner, pv_name, motor_type)
        #self.devices['POSITIONERS'][DNM_SAMPLE_FINE_X] = apsMotor('IOC:m1',pos_set=POS_TYPE_ES)
        #self.devices['POSITIONERS'][DNM_SAMPLE_FINE_Y] = apsMotor('IOC:m2',pos_set=POS_TYPE_ES)

        self.devices['POSITIONERS'][DNM_SAMPLE_FINE_X] = sample_motor('IOC:m1',pos_set=POS_TYPE_ES)
        self.devices['POSITIONERS'][DNM_SAMPLE_FINE_Y] = sample_motor('IOC:m2',pos_set=POS_TYPE_ES)

        self.devices['POSITIONERS'][DNM_COARSE_X] = apsMotor( 'IOC:m3',pos_set=POS_TYPE_ES)
        self.devices['POSITIONERS'][DNM_COARSE_Y] = apsMotor( 'IOC:m4',pos_set=POS_TYPE_ES)
        self.devices['POSITIONERS'][DNM_OSA_X] = apsMotor('IOC:m5',pos_set=POS_TYPE_ES)
        self.devices['POSITIONERS'][DNM_OSA_Y] = apsMotor('IOC:m6',pos_set=POS_TYPE_ES)
        self.devices['POSITIONERS'][DNM_DETECTOR_X] = apsMotor( 'IOC:m7',pos_set=POS_TYPE_ES)
        self.devices['POSITIONERS'][DNM_DETECTOR_Y] = apsMotor( 'IOC:m8',pos_set=POS_TYPE_ES)
        self.devices['POSITIONERS'][DNM_DETECTOR_Z] = apsMotor( 'IOC:m9',pos_set=POS_TYPE_ES)
        self.devices['POSITIONERS'][DNM_ZONEPLATE_Z] = apsMotor( 'IOC:m10',pos_set=POS_TYPE_ES)
        self.devices['POSITIONERS'][DNM_ZONEPLATE_Z_BASE] = apsMotor( 'IOC:m10')

        #self.devices['POSITIONERS'][DNM_SAMPLE_X] = apsMotor( 'IOC:m11',pos_set=POS_TYPE_ES)
        #self.devices['POSITIONERS'][DNM_SAMPLE_Y] = apsMotor('IOC:m12',pos_set=POS_TYPE_ES)

        self.devices['POSITIONERS'][DNM_SAMPLE_X] = sample_abstract_motor( 'IOC:m11',pos_set=POS_TYPE_ES)
        self.devices['POSITIONERS'][DNM_SAMPLE_Y] = sample_abstract_motor('IOC:m12',pos_set=POS_TYPE_ES)

        self.devices['POSITIONERS'][DNM_COARSE_Z] = apsMotor('IOC:m13',pos_set=POS_TYPE_ES)

        prfx = self.sscan_rec_prfx
        connect_standard_beamline_positioners(self.devices, prfx)
        connect_devices(self.devices, prfx)


        #key, value in self.devices.iteritems():
        #	print key,value
        print 'finished connecting to devices'
        self.done = True

class dev_config_uhv(dev_config_base):
    def __init__(self, splash=None, sample_pos_mode=sample_positioning_modes.COARSE, fine_sample_pos_mode=sample_fine_positioning_modes.SAMPLEFINE):
        super(dev_config_uhv, self).__init__(splash=splash)
        print 'Using UHV STXM DEVICES'
        self.beamline = 'UHV STXM 10ID1'
        self.sscan_rec_prfx = 'uhv'
        self.es_id = endstation_id_types.UHV
        self.sample_pos_mode = sample_pos_mode
        self.fine_sample_pos_mode = fine_sample_pos_mode
        #self.splash = splash
        self.done = False
        #self.timer = QtCore.QTimer()
        #self.timer.timeout.connect(self.on_timer)
        self.init_devices()
        self.init_presets()

        self.get_cainfo()

        if(self.sample_pos_mode is sample_positioning_modes.GONIOMETER):
            self.set_exclude_positioners_list([DNM_SAMPLE_X, DNM_SAMPLE_Y, DNM_ZONEPLATE_Z_BASE, DNM_SAMPLE_FINE_X, DNM_SAMPLE_FINE_Y, DNM_COARSE_X, DNM_COARSE_Y, 'AUX1', 'AUX2', 'Cff', 'PeemM3Trans'])
        elif(self.sample_pos_mode is sample_positioning_modes.COARSE):
            if(self.fine_sample_pos_mode is sample_fine_positioning_modes.SAMPLEFINE):
                self.exclude_list = [DNM_GONI_X, DNM_GONI_Y, DNM_GONI_Z, DNM_GONI_THETA, DNM_ZONEPLATE_Z_BASE, DNM_SAMPLE_FINE_X, DNM_SAMPLE_FINE_Y, DNM_ZONEPLATE_X, DNM_ZONEPLATE_Y,
                                     DNM_COARSE_X, DNM_COARSE_Y, 'AUX1', 'AUX2', 'Cff', 'PeemM3Trans']
            else:
                #zoneplate
                self.exclude_list = [DNM_GONI_X, DNM_GONI_Y, DNM_GONI_Z, DNM_GONI_THETA, DNM_ZONEPLATE_X, DNM_ZONEPLATE_Y, DNM_ZONEPLATE_Z_BASE,
                                     DNM_SAMPLE_FINE_X, DNM_SAMPLE_FINE_Y,
                                     DNM_COARSE_X, DNM_COARSE_Y, 'AUX1', 'AUX2', 'Cff', 'PeemM3Trans']
        #init_posner_snapshot_cbs(self.devices['POSITIONERS'])
        #self.close_splash()
        print 'leaving dev_config_uhv'

    def parse_cainfo_stdout_to_dct(self, s):
        dct = {}
        s2 = s.split('\n')
        for l in s2:
            l2 = l.replace(' ', '')
            l3 = l2.split(':')
            if(len(l3) > 1):
                dct[l3[0]] = l3[1]
        return(dct)

    def do_cainfo(self, pvname):
        import subprocess
        #print 'cainfo [%s]' % pvname
        proc = subprocess.Popen('cainfo %s' % pvname, stdout=subprocess.PIPE)
        stdout_str = proc.stdout.read()
        _dct = self.parse_cainfo_stdout_to_dct(stdout_str)
        return(_dct)

    def get_cainfo(self):

        #skip_lst = ['PVS_DONT_RECORD', 'PRESETS','DETECTORS_NO_RECORD','WIDGETS']
        skip_lst = ['PRESETS', 'WIDGETS']
        dev_dct = {}
        sections = self.devices.keys()
        for section in sections:
            keys = []
            if(section not in skip_lst):
                keys = self.devices[section].keys()
                #check to see if this is a subsectioned section that has pvs for BL (beamline) and ES (endstation)
                #if so do those
                if(keys == ['BL', 'ES']):
                    dev_dct[section] = {}
                    for subsec in keys:
                        for pvname in self.devices[section][subsec].keys():
                            _dct = self.do_cainfo(pvname)
                            dev_dct[section][pvname] = {}
                            dev_dct[section][pvname]['dev'] = self.devices[section][subsec][pvname]
                            dev_dct[section][pvname]['cainfo'] = _dct
                            if (_dct['State'].find('dis') > -1):
                                print '[%s] does not appear to exist' % k
                                print _dct
                else:
                    for k in keys:
                        dev = self.devices[section][k]
                        dev_dct[section] = {}
                        dev_dct[section][k] = {}
                        dev_dct[section][k]['dev'] = dev
                        if(type(dev) == list):
                            for d in dev:
                                if (not hasattr(d, 'get_name')):
                                    print 'get_cainfo: crap!', d
                                else:
                                    _dct = self.do_cainfo(d.get_name())
                                    dev_dct[section][k]['cainfo'] = _dct
                                    if (_dct['State'].find('dis') > -1):
                                        print '[%s] does not appear to exist' % k
                                        print _dct
                            continue
                        elif(type(dev) == dict):
                            all_good = True
                            for k,dct in dev.iteritems():
                                if (not hasattr(dct['dev'], 'get_name')):
                                    print 'get_cainfo: crap!', k
                                    all_good = False
                                else:
                                    _dct = self.do_cainfo(dct['dev'].get_name())
                                    if(not k in dev_dct[section].keys()):
                                        dev_dct[section][k] = {}
                                        dev_dct[section][k]['dev'] = dct['dev']

                                    dev_dct[section][k]['cainfo'] = _dct
                                    if (_dct['State'].find('dis') > -1):
                                        print '[%s] does not appear to exist' % k
                                        print _dct
                            continue
                        elif(not hasattr(dev, 'get_name')):
                            print 'get_cainfo: crap!', dev

                        _dct = self.do_cainfo(dev.get_name())
                        dev_dct[section][k]['cainfo'] = _dct
                        if(_dct['State'].find('dis') > -1):
                            print '[%s] does not appear to exist' % k
                            print _dct

        #dev_dct



    def init_presets(self):
        # these need to come from teh app.ini file FINE_SCAN_RANGES, leave as hack for now till I get time

        maxCX = appConfig.get_value('SCAN_RANGES', 'coarse_x')
        maxCY = appConfig.get_value('SCAN_RANGES', 'coarse_y')
        maxFX = appConfig.get_value('SCAN_RANGES', 'fine_x')
        maxFY = appConfig.get_value('SCAN_RANGES', 'fine_y')
        use_laser = appConfig.get_value('DEFAULT', 'use_laser')



        #self.devices['PRESETS']['MAX_SCAN_RANGE_X'] = 98
        #self.devices['PRESETS']['MAX_SCAN_RANGE_Y'] = 98

        if(self.sample_pos_mode is sample_positioning_modes.GONIOMETER):
            self.devices['PRESETS']['MAX_SCAN_RANGE_X'] = maxFX
            self.devices['PRESETS']['MAX_SCAN_RANGE_Y'] = maxFY
        else:
            self.devices['PRESETS']['MAX_SCAN_RANGE_X'] = maxCX
            self.devices['PRESETS']['MAX_SCAN_RANGE_Y'] = maxCY

        self.devices['PRESETS']['MAX_FINE_SCAN_RANGE_X'] = maxFX
        self.devices['PRESETS']['MAX_FINE_SCAN_RANGE_Y'] = maxFY

        #self.devices['PRESETS']['MAX_ZP_SCAN_RANGE_X'] = maxFX
        #self.devices['PRESETS']['MAX_ZP_SCAN_RANGE_Y'] = maxFY


       # self.devices['PRESETS']['MAX_ZP_SUBSCAN_RANGE_X'] = maxFX
       # self.devices['PRESETS']['MAX_ZP_SUBSCAN_RANGE_Y'] = maxFY

        #self.devices['PVS'][DNM_ENERGY_ENABLE].put(0)
        self.devices['PRESETS']['USE_LASER'] = use_laser


    def init_devices(self):

        #I don't have an elegant way yet to create these and also emit a signal to the splash screen
        #so this is a first attempt
        #self.timer.start(100)
        # maps names to device objects
        #self.devices['POSITIONERS'][DNM_SAMPLE_FINE_X] = apsMotor('IOC:m100',pos_set=POS_TYPE_ES)
        #self.devices['POSITIONERS'][DNM_SAMPLE_FINE_Y] = apsMotor('IOC:m101',pos_set=POS_TYPE_ES)


        prfx = self.sscan_rec_prfx
        prfx = self.sscan_rec_prfx
        self.msg_splash("connecting to: [%s]" % DNM_SAMPLE_FINE_X)
        self.devices['POSITIONERS'][DNM_SAMPLE_FINE_X] = sample_motor('IOC:m100',pos_set=POS_TYPE_ES)
        self.msg_splash("connecting to: [%s]" % DNM_SAMPLE_FINE_Y)
        self.devices['POSITIONERS'][DNM_SAMPLE_FINE_Y] = sample_motor('IOC:m101',pos_set=POS_TYPE_ES)
        self.msg_splash("connecting to: [%s]" % DNM_COARSE_X)
        self.devices['POSITIONERS'][DNM_COARSE_X] = apsMotor( 'IOC:m112',pos_set=POS_TYPE_ES)
        self.msg_splash("connecting to: [%s]" % DNM_COARSE_Y)
        self.devices['POSITIONERS'][DNM_COARSE_Y] = apsMotor( 'IOC:m113',pos_set=POS_TYPE_ES)
        self.msg_splash("connecting to: [%s]" % DNM_OSA_X)
        self.devices['POSITIONERS'][DNM_OSA_X] = apsMotor('IOC:m104',pos_set=POS_TYPE_ES)
        self.msg_splash("connecting to: [%s]" % DNM_OSA_Y)
        self.devices['POSITIONERS'][DNM_OSA_Y] = apsMotor('IOC:m105',pos_set=POS_TYPE_ES)
        self.msg_splash("connecting to: [%s]" % DNM_OSA_Z)
        self.devices['POSITIONERS'][DNM_OSA_Z] = apsMotor('IOC:m106C',pos_set=POS_TYPE_ES, collision_support=True)
        self.msg_splash("connecting to: [%s]" % DNM_OSA_Z_BASE)
        self.devices['POSITIONERS'][DNM_OSA_Z_BASE] = apsMotor('IOC:m106')

        self.msg_splash("connecting to: [%s]" % DNM_DETECTOR_X)
        self.devices['POSITIONERS'][DNM_DETECTOR_X] = apsMotor( 'IOC:m114',pos_set=POS_TYPE_ES)
        self.msg_splash("connecting to: [%s]" % DNM_DETECTOR_Y)
        self.devices['POSITIONERS'][DNM_DETECTOR_Y] = apsMotor( 'IOC:m115',pos_set=POS_TYPE_ES)
        self.msg_splash("connecting to: [%s]" % DNM_DETECTOR_Z)
        self.devices['POSITIONERS'][DNM_DETECTOR_Z] = apsMotor( 'IOC:m116',pos_set=POS_TYPE_ES)
        self.msg_splash("connecting to: [%s]" % DNM_ZONEPLATE_X)
        self.devices['POSITIONERS'][DNM_ZONEPLATE_X] = sample_motor( 'IOC:m102',pos_set=POS_TYPE_ES)
        self.msg_splash("connecting to: [%s]" % DNM_ZONEPLATE_Y)
        self.devices['POSITIONERS'][DNM_ZONEPLATE_Y] = sample_motor( 'IOC:m103',pos_set=POS_TYPE_ES)
        self.msg_splash("connecting to: [%s]" % DNM_ZONEPLATE_Z)
        self.devices['POSITIONERS'][DNM_ZONEPLATE_Z] = apsMotor( 'IOC:m111C',pos_set=POS_TYPE_ES, collision_support=True)
        self.msg_splash("connecting to: [%s]" % DNM_ZONEPLATE_Z_BASE)
        self.devices['POSITIONERS'][DNM_ZONEPLATE_Z_BASE] = apsMotor( 'IOC:m111')

        #self.devices['POSITIONERS'][DNM_SAMPLE_X] = apsMotor( 'IOC:m117',pos_set=POS_TYPE_ES)
        #self.devices['POSITIONERS'][DNM_SAMPLE_Y] = apsMotor('IOC:m118',pos_set=POS_TYPE_ES)
        self.msg_splash("connecting to: [%s]" % DNM_SAMPLE_X)
        self.devices['POSITIONERS'][DNM_SAMPLE_X] = sample_abstract_motor( 'IOC:m117',pos_set=POS_TYPE_ES)
        self.msg_splash("connecting to: [%s]" % DNM_SAMPLE_Y)
        self.devices['POSITIONERS'][DNM_SAMPLE_Y] = sample_abstract_motor('IOC:m118',pos_set=POS_TYPE_ES)
        self.msg_splash("connecting to: [%s]" % DNM_GONI_X)
        self.devices['POSITIONERS'][DNM_GONI_X] = apsMotor('IOC:m107',pos_set=POS_TYPE_ES)
        self.msg_splash("connecting to: [%s]" % DNM_GONI_Y)
        self.devices['POSITIONERS'][DNM_GONI_Y] = apsMotor('IOC:m108',pos_set=POS_TYPE_ES)
        self.msg_splash("connecting to: [%s]" % DNM_GONI_Z)
        self.devices['POSITIONERS'][DNM_GONI_Z] = apsMotor('IOC:m109',pos_set=POS_TYPE_ES)
        self.msg_splash("connecting to: [%s]" % DNM_GONI_THETA)
        self.devices['POSITIONERS'][DNM_GONI_THETA] = apsMotor('IOC:m110',pos_set=POS_TYPE_ES)

        #self.msg_splash("connecting to: [%s]" % DNM_CALIB_CAMERA_SRVR)
        #self.devices['DETECTORS_NO_RECORD'][DNM_CALIB_CAMERA_SRVR] = camera('CCD1610-I10:%s' % prfx, server=True)
        self.msg_splash("connecting to: [%s]" % DNM_CALIB_CAMERA_CLIENT)
        self.devices['DETECTORS_NO_RECORD'][DNM_CALIB_CAMERA_CLIENT] = camera('CCD1610-I10:%s' % prfx)

        connect_standard_beamline_positioners(self.devices, prfx, devcfg=self)
        connect_devices(self.devices, prfx, devcfg=self)

        #check_if_pv_exists(self.devices['POSITIONERS'])
        # for key, value in self.devices.iteritems():
        # 	print key,value

        print 'finished connecting to devices'
        self.done = True






def connect_standard_beamline_positioners(dev_dct, prfx='uhv', devcfg=None):
    devcfg.msg_splash("connecting to: [%s]" % DNM_ENERGY)
    dev_dct['POSITIONERS'][DNM_ENERGY] = apsMotor('BL1610-I10:ENERGY',pos_set=POS_TYPE_ES)
    devcfg.msg_splash("connecting to: [%s]" % DNM_SLIT_X)
    dev_dct['POSITIONERS'][DNM_SLIT_X] = apsMotor('BL1610-I10:slitX',pos_set=POS_TYPE_BL)
    devcfg.msg_splash("connecting to: [%s]" % DNM_SLIT_Y)
    dev_dct['POSITIONERS'][DNM_SLIT_Y] = apsMotor('BL1610-I10:slitY',pos_set=POS_TYPE_BL)
    devcfg.msg_splash("connecting to: [%s]" % DNM_M3_PITCH)
    dev_dct['POSITIONERS'][DNM_M3_PITCH] = apsMotor('BL1610-I10:m3STXMPitch',pos_set=POS_TYPE_BL)
    devcfg.msg_splash("connecting to: [%s]" % DNM_EPU_GAP)
    dev_dct['POSITIONERS'][DNM_EPU_GAP] = apsMotor('BL1610-I10:epuGap',pos_set=POS_TYPE_BL)
    devcfg.msg_splash("connecting to: [%s]" % DNM_EPU_OFFSET)
    dev_dct['POSITIONERS'][DNM_EPU_OFFSET] = apsMotor('BL1610-I10:epuOffset',pos_set=POS_TYPE_BL)

    devcfg.msg_splash("connecting to: [%s]" % DNM_EPU_HARMONIC)
    dev_dct['POSITIONERS'][DNM_EPU_HARMONIC] = apsMotor('BL1610-I10:epuHarmonic',pos_set=POS_TYPE_BL)
    devcfg.msg_splash("connecting to: [%s]" % DNM_EPU_POLARIZATION)
    dev_dct['POSITIONERS'][DNM_EPU_POLARIZATION] = apsMotor('BL1610-I10:epuPolarization',pos_set=POS_TYPE_BL)
    devcfg.msg_splash("connecting to: [%s]" % DNM_EPU_ANGLE)
    dev_dct['POSITIONERS'][DNM_EPU_ANGLE] = apsMotor('BL1610-I10:epuAngle',pos_set=POS_TYPE_BL)


def connect_devices(dev_dct, prfx='uhv', devcfg=None):

    devcfg.msg_splash("connecting to: [%s]" % DNM_GATE)
    dev_dct['DIO'][DNM_GATE] = BaseGate('%sCO:gate' % prfx)
    devcfg.msg_splash("connecting to: [%s]" % DNM_SHUTTER)
    dev_dct['DIO'][DNM_SHUTTER] = PvShutter('%sDIO:shutter:ctl' % prfx)
    devcfg.msg_splash("connecting to: [%s]" % DNM_SHUTTERTASKRUN)
    #dev_dct['DIO'][DNM_SHUTTERTASKRUN] = aio('%sDIO:shutter:Run' % prfx)
    dev_dct['DIO'][DNM_SHUTTERTASKRUN] = aio('%sDIO:shutter:Run' % prfx)

    devcfg.msg_splash("connecting to: [%s]" % DNM_COUNTER_APD)
    dev_dct['DETECTORS'][DNM_COUNTER_APD] = BaseCounter('%sCI:counter' % prfx)
    #dev_dct['DETECTORS']['Det_Cntr'] = EpicsPvCounter('%sPMT:ctr:SingleValue_RBV' % prfx)
    devcfg.msg_splash("connecting to: [%s]" % DNM_PMT)
    dev_dct['DETECTORS'][DNM_PMT] = aio('%sPMT:ctr:SingleValue_RBV' % prfx)

    dev_dct['DETECTORS'][DNM_RING_CURRENT] = aio('PCT1402-01:mA:fbk', egu='mA')
    #dev_dct['DETECTORS'][DNM_TYCHO_CAMERA] = SimCamera(sim_get_time=0.5)

    #dev_dct['DETECTORS_NO_RECORD'][DNM_DETCNTR_SNAPSHOT] = aio('%sPMT:det_snapshot_RBV' % prfx)
    #dev_dct['DETECTORS_NO_RECORD'][DNM_OSACNTR_SNAPSHOT] = aio('%sPMT:osa_snapshot_RBV' % prfx)

    #dev_dct['DETECTORS']['Ax1InterferVolts'] = EpicsPvCounter('%sAi:ai:ai0_RBV' % prfx)
    #dev_dct['DETECTORS']['Ax2InterferVolts'] = EpicsPvCounter('%sAi:ai:ai1_RBV' % prfx)

    dev_dct['PVS'][DNM_IDEAL_A0] = aio('BL1610-I10:ENERGY:%s:zp:fbk:tr.K' % prfx)
    #dev_dct['PVS'][DNM_CALCD_ZPZ] = aio('BL1610-I10:ENERGY:%s:zp:fbk:tr.L' % prfx)
    dev_dct['PVS'][DNM_CALCD_ZPZ] = aio('BL1610-I10:ENERGY:%s:zp:fbk:tr.I' % prfx)

    dev_dct['PVS'][DNM_ZPZ_ADJUST] = aio('BL1610-I10:ENERGY:%s:zp:adjust_zpz' % prfx)

    devcfg.msg_splash("connecting to: [%s]" % DNM_ZONEPLATE_SCAN_MODE)
    #dev_dct['PVS']['Zpz_scanModeFlag'] = Mbbo('BL1610-I10:ENERGY:%s:zp:scanselflag' % prfx) #used to control which value gets sent to Zpz, fl or fl - A0
    dev_dct['PVS'][DNM_ZONEPLATE_SCAN_MODE] = aio('BL1610-I10:ENERGY:%s:zp:scanselflag' % prfx)  # used to control which value gets sent to Zpz, fl or fl - A0
    dev_dct['PVS'][DNM_ZONEPLATE_INOUT] = aio('BL1610-I10:%s:zp_inout' % prfx)  # used to convieniently move zp z in and out
    dev_dct['PVS'][DNM_ZONEPLATE_INOUT_FBK] = Mbbi('BL1610-I10:%s:zp_inout:fbk' % prfx)  # used to convieniently move zp z in and out
    #used to adjust the current focus value, the delta represents the relative microns for zpz to move to new focus position
    dev_dct['PVS'][DNM_DELTA_A0] = aio('BL1610-I10:ENERGY:%s:delta_A0' % prfx)
    dev_dct['PVS'][DNM_FOCAL_LENGTH] = aio('BL1610-I10:ENERGY:%s:zp:FL' % prfx, egu='um')
    dev_dct['PVS'][DNM_A0] = aio('BL1610-I10:ENERGY:%s:A0' % prfx)
    dev_dct['PVS'][DNM_A0MAX] = aio('BL1610-I10:ENERGY:%s:A0Max' % prfx)
    dev_dct['PVS'][DNM_A0FORCALC] = aio('BL1610-I10:ENERGY:%s:A0:for_calc' % prfx)

    devcfg.msg_splash("connecting to: [%s]" % 'zoneplate definitions')
    dev_dct['PVS'][DNM_ZPZ_POS] = aio('BL1610-I10:ENERGY:%s:zp:zpz_pos' % prfx)
    dev_dct['PVS'][DNM_ZP_DEF] = Transform('BL1610-I10:ENERGY:%s:zp:def' % prfx)
    dev_dct['PVS'][DNM_OSA_DEF] = Transform('BL1610-I10:ENERGY:%s:osa:def' % prfx)

    dev_dct['PVS'][DNM_ZP_SELECT] = Mbbo('BL1610-I10:ENERGY:%s:zp' % prfx)
    dev_dct['PVS'][DNM_OSA_SELECT] = Mbbo('BL1610-I10:ENERGY:%s:osa' % prfx)

    devcfg.msg_splash("connecting to: [%s]" % DNM_ENERGY_ENABLE)
    dev_dct['PVS'][DNM_ENERGY_ENABLE] = aio('BL1610-I10:ENERGY:%s:enabled' % prfx)
    dev_dct['PVS'][DNM_ENERGY_RBV] = aio('BL1610-I10:ENERGY.RBV', egu='um')
    dev_dct['PVS'][DNM_ZPZ_RBV] = aio('IOC:m111C.RBV', egu='um')
    dev_dct['PVS'][DNM_ZP_DEF_A] = aio('BL1610-I10:ENERGY:%s:zp:def.A' % prfx)

    devcfg.msg_splash("connecting to: [%s]" % 'Zp_def1 -> 7')
    dev_dct['PVS'][DNM_ZP_DEF1_A] = aio('BL1610-I10:ENERGY:%s:zp1:def.A' % prfx)
    dev_dct['PVS'][DNM_ZP_DEF2_A] = aio('BL1610-I10:ENERGY:%s:zp2:def.A' % prfx)
    dev_dct['PVS'][DNM_ZP_DEF3_A] = aio('BL1610-I10:ENERGY:%s:zp3:def.A' % prfx)
    dev_dct['PVS'][DNM_ZP_DEF4_A] = aio('BL1610-I10:ENERGY:%s:zp4:def.A' % prfx)
    dev_dct['PVS'][DNM_ZP_DEF5_A] = aio('BL1610-I10:ENERGY:%s:zp5:def.A' % prfx)
    dev_dct['PVS'][DNM_ZP_DEF6_A] = aio('BL1610-I10:ENERGY:%s:zp6:def.A' % prfx)
    dev_dct['PVS'][DNM_ZP_DEF7_A] = aio('BL1610-I10:ENERGY:%s:zp7:def.A' % prfx)

    #dev_dct['PVS']['SRStatus_msgL1'] = aio('SRStatus:msg:tL1')
    #dev_dct['PVS']['SRStatus_msgL2'] = aio('SRStatus:msg:tL2')
    #dev_dct['PVS']['SRStatus_msgL3'] = aio('SRStatus:msg:tL3')
    devcfg.msg_splash("connecting to: [%s]" % DNM_SRSTATUS_SHUTTERS)
    dev_dct['PVS'][DNM_SRSTATUS_SHUTTERS] = aio('SRStatus:shutters')

    devcfg.msg_splash("connecting to: [%s]" % DNM_MONO_EV_FBK)
    dev_dct['PVS'][DNM_MONO_EV_FBK] = aio('SM01PGM01:ENERGY_MON.VAL', egu='eV')
    devcfg.msg_splash("connecting to: [%s]" % DNM_MONO_GRATING_FBK)
    _pv = aio('SM01PGM01:GRT_DENSITY')
    # _pv.get_position = _pv.get_enum_str_as_int
    dev_dct['PVS'][DNM_MONO_GRATING_FBK] = _pv

    devcfg.msg_splash("connecting to: [%s]" % DNM_EPU_POL_FBK)
    dev_dct['PVS'][DNM_EPU_POL_FBK] = Mbbi('UND1410-01:polarization')
    devcfg.msg_splash("connecting to: [%s]" % DNM_EPU_POL_ANGLE)
    dev_dct['PVS'][DNM_EPU_POL_ANGLE] = aio('UND1410-01:polarAngle', egu='udeg')

    devcfg.msg_splash("connecting to: [%s]" % DNM_EPU_GAP_FBK)
    dev_dct['PVS'][DNM_EPU_GAP_FBK] = aio('UND1410-01:gap:mm:fbk', egu='mm')

    # devcfg.msg_splash("connecting to: [%s]" % DNM_EPU_GAP_FBK)
    # dev_dct['PVS'][DNM_EPU_GAP_FBK] = aio('RUSSTEST:VAL')

    devcfg.msg_splash("connecting to: [%s]" % DNM_EPU_GAP_OFFSET)
    dev_dct['PVS'][DNM_EPU_GAP_OFFSET] = aio('UND1410-01:gap:offset', egu='mm')
    devcfg.msg_splash("connecting to: [%s]" % DNM_EPU_HARMONIC_PV)
    dev_dct['PVS'][DNM_EPU_HARMONIC_PV] = aio('UND1410-01:harmonic')


    devcfg.msg_splash("connecting to PVs: [1]")
    dev_dct['PVS'][DNM_SYSTEM_MODE_FBK] = aio(DNM_SYSTEM_MODE_FBK)
    #dev_dct['PVS']['mbbiSYSTEM:mode:fbk'] = Mbbi(DNM_SYSTEM_MODE_FBK)
    dev_dct['PVS'][DNM_BEAM_DEFOCUS] = aio('BL1610-I10:ENERGY:%s:zp:defocus' % prfx, egu='um')


    dev_dct['PVS_DONT_RECORD'][DNM_TICKER] = aio('TRG2400:cycles', egu='counts')

    dev_dct['PVS_DONT_RECORD'][DNM_CX_AUTO_DISABLE_POWER] = aio('IOC:m112:XPS_AUTO_DISABLE_MODE')
    dev_dct['PVS_DONT_RECORD'][DNM_CY_AUTO_DISABLE_POWER] = aio('IOC:m113:XPS_AUTO_DISABLE_MODE')
    dev_dct['PVS_DONT_RECORD'][DNM_DX_AUTO_DISABLE_POWER] = aio('IOC:m114:XPS_AUTO_DISABLE_MODE')
    dev_dct['PVS_DONT_RECORD'][DNM_DY_AUTO_DISABLE_POWER] = aio('IOC:m115:XPS_AUTO_DISABLE_MODE')

    dev_dct['PVS_DONT_RECORD'][DNM_ACCRANGE] = aio('uhvTestSIG:signal:MaxPoints')

    dev_dct['PVS_DONT_RECORD'][DNM_FX_FORCE_DONE] = aio('IOC:m100:ForceDone')
    dev_dct['PVS_DONT_RECORD'][DNM_FY_FORCE_DONE] = aio('IOC:m101:ForceDone')

    #dev_dct['PVS_DONT_RECORD'][DNM_OX_FORCE_DONE] = aio('IOC:m104:ForceDone')
    #dev_dct['PVS_DONT_RECORD'][DNM_OY_FORCE_DONE] = aio('IOC:m105:ForceDone')

    dev_dct['PVS_DONT_RECORD'][DNM_OSAX_TRACKING] = aio('BL1610-I10:ENERGY:%s:osax_track_enabled' % prfx)
    dev_dct['PVS_DONT_RECORD'][DNM_OSAY_TRACKING] = aio('BL1610-I10:ENERGY:%s:osay_track_enabled' % prfx)
    dev_dct['PVS_DONT_RECORD'][DNM_OSAZ_TRACKING] = aio('BL1610-I10:ENERGY:%s:osaz_track_enabled' % prfx)

    #dev_dct['PVS_DONT_RECORD'][DNM_OSAXYZ_LOCKPOSITION_ENABLED] = aio('BL1610-I10:ENERGY:%s:osaxyz_lockpos_enabled' % prfx)

    #dev_dct['PVS_DONT_RECORD'][DNM_OSAXY_GOTO_LOCKPOSITION] = aio('BL1610-I10:ENERGY:%s:osaxy_goto_lockpos' % prfx)
    #dev_dct['PVS_DONT_RECORD'][DNM_OSAZ_GOTO_LOCKPOSITION] = aio('BL1610-I10:ENERGY:%s:osaz_goto_lockpos' % prfx)

    devcfg.msg_splash("connecting to PVs: [15]")

    dev_dct['PVS_DONT_RECORD'][DNM_SET_XY_LOCKPOSITION] = aio('BL1610-I10:ENERGY:%s:set_xy:lockposn' % prfx, egu='um')
    #dev_dct['PVS_DONT_RECORD'][DNM_SET_Z_LOCKPOSITION] = aio('BL1610-I10:ENERGY:%s:set_z:lock_posn' % prfx, egu='um')

    dev_dct['PVS'][DNM_AX1_INTERFER_VOLTS] = aio('%sAi:ai:ai0_RBV' % prfx)
    dev_dct['PVS'][DNM_AX2_INTERFER_VOLTS] = aio('%sAi:ai:ai1_RBV' % prfx)


    devcfg.msg_splash("connecting to SSCAN: [%s]" % ('%sstxm:det:' % prfx))

    devcfg.msg_splash("connecting to SSCAN: [%s]" % ('%sstxm:' % prfx))
    dev_dct['PVS_DONT_RECORD']['%sstxm:cmd_file' % prfx] = aio('%sstxm:cmd_file' % prfx)
    dev_dct['SSCANS']['%sstxm:scan1' % prfx] = Scan('%sstxm:scan1' % prfx)
    dev_dct['SSCANS']['%sstxm:scan2' % prfx] = Scan('%sstxm:scan2' % prfx)
    dev_dct['SSCANS']['%sstxm:scan3' % prfx] = Scan('%sstxm:scan3' % prfx)
    dev_dct['SSCANS']['%sstxm:scan4' % prfx] = Scan('%sstxm:scan4' % prfx)
    dev_dct['SSCANS']['%sstxm:scan5' % prfx] = Scan('%sstxm:scan5' % prfx)
    dev_dct['SSCANS']['%sstxm:scan6' % prfx] = Scan('%sstxm:scan6' % prfx)
    dev_dct['SSCANS']['%sstxm:scan7' % prfx] = Scan('%sstxm:scan7' % prfx)
    dev_dct['SSCANS']['%sstxm:scan8' % prfx] = Scan('%sstxm:scan8' % prfx)

    dev_dct['PVS_DONT_RECORD']['%sstxm:scan1:sts' % prfx] = aio('%sstxm:scan1.SMSG' % prfx)
    dev_dct['PVS_DONT_RECORD'][DNM_ABORT_SSCANS] = aio('%sstxm:AbortScans' % prfx)

    # ES = endstation temperatures
    devcfg.msg_splash("connecting to TEMPERATURES: [TM1610-3-I12-01]")
    dev_dct['TEMPERATURES'][POS_TYPE_ES]['TM1610-3-I12-01'] = aio('TM1610-3-I12-01', desc='Turbo cooling water', egu='deg C')
    devcfg.msg_splash("connecting to TEMPERATURES: [TM1610-3-I12-30]")
    dev_dct['TEMPERATURES'][POS_TYPE_ES]['TM1610-3-I12-30'] = aio('TM1610-3-I12-30', desc='Sample Coarse Y', egu='deg C')
    devcfg.msg_splash("connecting to TEMPERATURES: [TM1610-3-I12-32]")
    dev_dct['TEMPERATURES'][POS_TYPE_ES]['TM1610-3-I12-32'] = aio('TM1610-3-I12-32', desc='Detector Y', egu='deg C')
    devcfg.msg_splash("connecting to TEMPERATURES: [TM1610-3-I12-21]")
    dev_dct['TEMPERATURES'][POS_TYPE_ES]['TM1610-3-I12-21'] = aio('TM1610-3-I12-21', desc='Chamber temp #1', egu='deg C')
    devcfg.msg_splash("connecting to TEMPERATURES: [TM1610-3-I12-22]")
    dev_dct['TEMPERATURES'][POS_TYPE_ES]['TM1610-3-I12-22'] = aio('TM1610-3-I12-22', desc='Chamber temp #2', egu='deg C')
    devcfg.msg_splash("connecting to TEMPERATURES: [TM1610-3-I12-23]")
    dev_dct['TEMPERATURES'][POS_TYPE_ES]['TM1610-3-I12-23'] = aio('TM1610-3-I12-23', desc='Chamber temp #3', egu='deg C')
    devcfg.msg_splash("connecting to TEMPERATURES: [TM1610-3-I12-24]")
    dev_dct['TEMPERATURES'][POS_TYPE_ES]['TM1610-3-I12-24'] = aio('TM1610-3-I12-24', desc='Chamber temp #4', egu='deg C')


    #pressures
    devcfg.msg_splash("connecting to PRESSURES: [FRG1610-3-I12-01:vac:p]")
    dev_dct['PRESSURES'][POS_TYPE_ES]['FRG1610-3-I12-01:vac:p'] = aio('FRG1610-3-I12-01:vac:p', desc='Chamber pressure', egu='torr')
    devcfg.msg_splash("connecting to PRESSURES: [TCG1610-3-I12-03:vac:p]")
    dev_dct['PRESSURES'][POS_TYPE_ES]['TCG1610-3-I12-03:vac:p'] = aio('TCG1610-3-I12-03:vac:p', desc='Turbo backing pressure', egu='torr')
    devcfg.msg_splash("connecting to PRESSURES: [TCG1610-3-I12-04:vac:p]")
    dev_dct['PRESSURES'][POS_TYPE_ES]['TCG1610-3-I12-04:vac:p'] = aio('TCG1610-3-I12-04:vac:p', desc='Load lock pressure', egu='torr')
    devcfg.msg_splash("connecting to PRESSURES: [TCG1610-3-I12-05:vac:p]")
    dev_dct['PRESSURES'][POS_TYPE_ES]['TCG1610-3-I12-05:vac:p'] = aio('TCG1610-3-I12-05:vac:p', desc='Rough line pressure', egu='torr')

    connect_ES_devices(dev_dct, prfx)
    connect_BL_devices(dev_dct, prfx)
    connect_heartbeats(dev_dct, prfx)
    connect_e712(dev_dct, prfx)


def connect_heartbeats(dev_dct, prfx='uhv'):
    '''

    :param dev_dct:
    :param prfx:
    :return:
    '''
    dev_dct['PVS_DONT_RECORD']['HEARTBEATS'] = {}
    dev_dct['PVS_DONT_RECORD']['HEARTBEATS']['sscan_hrtbt'] = {'dev':aio('uhvstxm:hrtbt:alive'), 'desc':'SSCAN App'}
    dev_dct['PVS_DONT_RECORD']['HEARTBEATS']['blApi_hrtbt'] = {'dev':aio('uhvBlApi:hrtbt:alive'), 'desc':'BlApi App'}
    dev_dct['PVS_DONT_RECORD']['HEARTBEATS']['ai_hrtbt'] = {'dev': aio('uhvAI:hrtbt:alive'),
                                                            'desc': 'AnalogInput App'}
    dev_dct['PVS_DONT_RECORD']['HEARTBEATS']['ci_hrtbt'] = {'dev':aio('uhvCI:hrtbt:alive'), 'desc':'CounterInput App'}
    dev_dct['PVS_DONT_RECORD']['HEARTBEATS']['co_hrtbt'] = {'dev':aio('uhvCO:hrtbt:alive'), 'desc':'CounterOutput App'}
    dev_dct['PVS_DONT_RECORD']['HEARTBEATS']['dio_hrtbt'] = {'dev':aio('uhvDIO:hrtbt:alive'), 'desc':'Digital IO App'}
    dev_dct['PVS_DONT_RECORD']['HEARTBEATS']['mtrs_hrtbt'] = {'dev':aio('UHVMTRS:hrtbt:alive'), 'desc':'Main Motors App'}
    dev_dct['PVS_DONT_RECORD']['HEARTBEATS']['mtr_calib_hrtbt'] = {'dev':aio('UHVMTR_CALIB:hrtbt:alive'), 'desc':'MotorCalibrations'}
    dev_dct['PVS_DONT_RECORD']['HEARTBEATS']['mtrs_osa_hrtbt'] = {'dev':aio('UHVMTR_OSA:hrtbt:alive'), 'desc':'OSA Motors App'}
    dev_dct['PVS_DONT_RECORD']['HEARTBEATS']['mtrs_zp_hrtbt'] = {'dev':aio('UHVMTR_ZP:hrtbt:alive'), 'desc':'ZPz Motors App'}
    dev_dct['PVS_DONT_RECORD']['HEARTBEATS']['gate_cntr_scan_cfg'] = {'dev':aio('gate_cntr_scan_cfg:hrtbt:alive'), 'desc':'Gate/Counter scan cfg App'}



def connect_e712(dev_dct, prfx='uhv', e712_prfx='IOCE712'):
    
    # dev_dct['SSCANS']['SampleImageWithE712Wavegen'] = SampleImageWithE712Wavegen()
    dev_dct['WIDGETS']['E712ControlWidget'] = E712ControlWidget('%s:' % e712_prfx,
                                                                counter=dev_dct['DETECTORS'][DNM_COUNTER_APD],
                                                                gate=dev_dct['DIO'][DNM_GATE])
    # waveform PV
    dev_dct['PVS_DONT_RECORD']['e712_dwells'] = aio('%s:dwells' % e712_prfx)
    dev_dct['PVS_DONT_RECORD']['e712_xresetposns'] = aio('%s:xreset:posns' % e712_prfx)
    dev_dct['PVS_DONT_RECORD']['e712_yresetposns'] = aio('%s:yreset:posns' % e712_prfx)
    dev_dct['PVS_DONT_RECORD']['e712_sp_ids'] = aio('%s:sp_roi:ids' % e712_prfx)
    dev_dct['PVS_DONT_RECORD']['e712_current_sp_id'] = aio('%s:sp_roi:current' % e712_prfx)

    # pvs that will hold up to 10 DDL tables for a multi spatial scan
    dev_dct['PVS_DONT_RECORD']['e712_ddl_tbls'] = [ aio('%s:ddl:0' % e712_prfx),
                                                    aio('%s:ddl:1' % e712_prfx),
                                                    aio('%s:ddl:2' % e712_prfx),
                                                    aio('%s:ddl:3' % e712_prfx),
                                                    aio('%s:ddl:4' % e712_prfx),
                                                    aio('%s:ddl:5' % e712_prfx),
                                                    aio('%s:ddl:6' % e712_prfx),
                                                    aio('%s:ddl:7' % e712_prfx),
                                                    aio('%s:ddl:8' % e712_prfx),
                                                    aio('%s:ddl:9' % e712_prfx) ]



    dev_dct['PVS_DONT_RECORD']['e712_image_idx'] = aio('%s:image_idx' % e712_prfx)
    dev_dct['PVS_DONT_RECORD']['e712_scan_mode'] = aio('%s:ScanMode' % e712_prfx)

    if (MAIN_OBJ.get_fine_sample_positioning_mode() is sample_fine_positioning_modes.ZONEPLATE):
        # here using x2 and y2 because we are zoneplate scanning and they are channels 3 and 4 respectively
        # waveform PV's

        dev_dct['PVS_DONT_RECORD']['e712_x_start_mode'] = aio('%s:wg3:startmode' % e712_prfx)
        dev_dct['PVS_DONT_RECORD']['e712_y_start_mode'] = aio('%s:wg4:startmode' % e712_prfx)

        dev_dct['PVS_DONT_RECORD']['e712_x_wavtbl_ids'] = aio('%s:wg3_tbl:ids' % e712_prfx)
        dev_dct['PVS_DONT_RECORD']['e712_y_wavtbl_ids'] = aio('%s:wg4_tbl:ids' % e712_prfx)

        # short PV's
        dev_dct['PVS_DONT_RECORD']['e712_x_npts'] = aio('%s:wg3:npts' % e712_prfx)
        dev_dct['PVS_DONT_RECORD']['e712_y_npts'] = aio('%s:wg4:npts' % e712_prfx)

        # pvs that hold the flags for each waveformgenerator (4) for each supported sp_roi (max of 10)
        dev_dct['PVS_DONT_RECORD']['e712_x_useddl'] = aio('%s:wg3:useddl' % e712_prfx)
        dev_dct['PVS_DONT_RECORD']['e712_y_useddl'] = aio('%s:wg4:useddl' % e712_prfx)

        dev_dct['PVS_DONT_RECORD']['e712_x_usereinit'] = aio('%s:wg3:usereinit' % e712_prfx)
        dev_dct['PVS_DONT_RECORD']['e712_y_usereinit'] = aio('%s:wg4:usereinit' % e712_prfx)

        dev_dct['PVS_DONT_RECORD']['e712_x_strtatend'] = aio('%s:wg3:strtatend' % e712_prfx)
        dev_dct['PVS_DONT_RECORD']['e712_y_strtatend'] = aio('%s:wg4:strtatend' % e712_prfx)

    else:
        # here using x1 and y1 because we are sample scanning and they are channels 1 and 2 respectively
        # waveform PV's
        dev_dct['PVS_DONT_RECORD']['e712_x_start_mode'] = aio('%s:wg1:startmode' % e712_prfx)
        dev_dct['PVS_DONT_RECORD']['e712_y_start_mode'] = aio('%s:wg2:startmode' % e712_prfx)

        dev_dct['PVS_DONT_RECORD']['e712_x_wavtbl_ids'] = aio('%s:wg1_tbl:ids' % e712_prfx)
        dev_dct['PVS_DONT_RECORD']['e712_y_wavtbl_ids'] = aio('%s:wg2_tbl:ids' % e712_prfx)

        # short PV's
        dev_dct['PVS_DONT_RECORD']['e712_x_npts'] = aio('%s:wg1:npts' % e712_prfx)
        dev_dct['PVS_DONT_RECORD']['e712_y_npts'] = aio('%s:wg2:npts' % e712_prfx)

        # pvs that hold the flags for each waveformgenerator (4) for each supported sp_roi (max of 10)
        dev_dct['PVS_DONT_RECORD']['e712_x_useddl'] = aio('%s:wg1:useddl' % e712_prfx)
        dev_dct['PVS_DONT_RECORD']['e712_y_useddl'] = aio('%s:wg2:useddl' % e712_prfx)

        dev_dct['PVS_DONT_RECORD']['e712_x_usereinit'] = aio('%s:wg1:usereinit' % e712_prfx)
        dev_dct['PVS_DONT_RECORD']['e712_y_usereinit'] = aio('%s:wg2:usereinit' % e712_prfx)

        dev_dct['PVS_DONT_RECORD']['e712_x_strtatend'] = aio('%s:wg1:strtatend' % e712_prfx)
        dev_dct['PVS_DONT_RECORD']['e712_y_strtatend'] = aio('%s:wg2:strtatend' % e712_prfx)

def connect_ES_devices(dev_dct, prfx='uhv'):
    if(prfx.find('uhv') > -1):
        dev_dct['TEMPERATURES'][POS_TYPE_ES]['CCTL1610-I10:temp:fbk'] = aio('CCTL1610-I10:temp:fbk', desc='Gatan rod temp')
    else:
        pass

def connect_BL_devices(dev_dct, prfx='uhv'):
    if(prfx.find('uhv') > -1):
        dev_dct['DIO']['InterferShutter'] = PvShutter('%sDIO-2:shutter:ctl' % prfx)

        dev_dct['PRESSURES'][POS_TYPE_BL]['CCG1410-01:vac:p'] = aio('CCG1410-01:vac:p', desc='Sec. 1')
        dev_dct['PRESSURES'][POS_TYPE_BL]['CCG1410-I00-01:vac:p'] = aio('CCG1410-I00-01:vac:p', desc='Sec. 2')
        dev_dct['PRESSURES'][POS_TYPE_BL]['CCG1410-I00-02:vac:p'] = aio('CCG1410-I00-02:vac:p', desc='Sec. 4')
        dev_dct['PRESSURES'][POS_TYPE_BL]['CCG1610-1-I00-02:vac:p'] = aio('CCG1610-1-I00-02:vac:p', desc='Sec. 6')
        dev_dct['PRESSURES'][POS_TYPE_BL]['HCG1610-1-I00-01:vac:p'] = aio('HCG1610-1-I00-01:vac:p', desc='Sec. 7')
        dev_dct['PRESSURES'][POS_TYPE_BL]['CCG1610-1-I00-03:vac:p'] = aio('CCG1610-1-I00-03:vac:p', desc='Sec. 8')
        dev_dct['PRESSURES'][POS_TYPE_BL]['CCG1610-I10-01:vac:p'] = aio('CCG1610-I10-01:vac:p', desc='Sec. 10')
        dev_dct['PRESSURES'][POS_TYPE_BL]['CCG1610-I10-02:vac:p'] = aio('CCG1610-I10-02:vac:p', desc='Sec. 11')
        dev_dct['PRESSURES'][POS_TYPE_BL]['CCG1610-I10-03:vac:p'] = aio('CCG1610-I10-03:vac:p', desc='Sec. 12')
        dev_dct['PRESSURES'][POS_TYPE_BL]['CCG1610-I10-04:vac:p'] = aio('CCG1610-I10-04:vac:p', desc='Sec. 13')
        dev_dct['PRESSURES'][POS_TYPE_BL]['CCG1610-I12-01:vac:p'] = aio('CCG1610-I12-01:vac:p',desc='Sec. 14')
        dev_dct['PRESSURES'][POS_TYPE_BL]['CCG1610-I12-02:vac:p'] = aio('CCG1610-I12-02:vac:p', desc='Sec. 15')
        dev_dct['PRESSURES'][POS_TYPE_BL]['CCG1610-3-I12-01:vac:p'] = aio('CCG1610-3-I12-01:vac:p', desc='Sec. 16')

    else:
        pass

#Feb6	dev_dct['ACTUATORS']['SSH'] = PvValve('SSH1410-I00-01')
#Feb6	dev_dct['ACTUATORS']['PSH'] = PvValve('PSH1410-I00-02')
#Feb6	dev_dct['ACTUATORS']['SM-PSH'] = PvValve('PSH1610-1-I10-01')
#Feb6	dev_dct['ACTUATORS']['BSH'] = PvValve('VVR1610-I12-03')


def print_keys(d):
    if(isinstance(d, list)):
        print_keys(d[0])

    for key in d:
        if(isinstance(d[key], dict)):
            print_keys(d[key])
        else:
            print key, d[key].is_active()






MAIN_OBJ = None
DEVICE_CFG = None

if(AMBIENT_STXM):
    MAIN_OBJ = main_object_base('CLS SM 10ID1', 'Ambient STXM', BEAMLINE_IDS.STXM)
    MAIN_OBJ.set_sample_positioning_mode(sample_positioning_modes.COARSE)
    MAIN_OBJ.set_fine_sample_positioning_mode(sample_fine_positioning_modes.SAMPLEFINE)
    MAIN_OBJ.set_datafile_prefix('A')
    MAIN_OBJ.set_thumbfile_suffix('jpg')
    MAIN_OBJ.set_endstation_prefix('amb')

    #DEVICE_CFG = dev_config()
    splash = get_splash(img_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pyStxmSplash.png'))
    DEVICE_CFG = dev_config_sim_ambient(splash=splash, sample_pos_mode=sample_positioning_modes.COARSE, fine_sample_pos_mode=sample_fine_positioning_modes.SAMPLEFINE)
    MAIN_OBJ.set_devices(DEVICE_CFG)
    DEFAULTS = Defaults('ambstxm_dflts.json', new=False)
    #scanning_mode = appConfig.get_value('DEFAULT', 'scanning_mode')
else:

    MAIN_OBJ = main_object_base('CLS SM 10ID1','UHV STXM', BEAMLINE_IDS.STXM)
    #MAIN_OBJ.set_sample_positioning_mode(sample_positioning_modes.COARSE)
    MAIN_OBJ.set_datafile_prefix('C')
    MAIN_OBJ.set_thumbfile_suffix('jpg')
    MAIN_OBJ.set_endstation_prefix('uhv')
    ver_str = 'Version %s.%s' % (MAIN_OBJ.get('APP.MAJOR_VER'), MAIN_OBJ.get('APP.MINOR_VER'))
    splash = get_splash(img_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pyStxmSplash.png'),
                        ver_str=ver_str)

    #sample_positioning_mode = appConfig.get_value('DEFAULT', 'sample_positioning_mode')
    #fine_sample_positioning_mode = appConfig.get_value('DEFAULT', 'fine_sample_positioning_mode')
    scanning_mode = appConfig.get_value('DEFAULT', 'scanning_mode')

    # sample_mode = None
    # fine_sample_mode = None
    #
    # if(sample_positioning_mode == 'GONIOMETER'):
    #     #must be ZONEPLATE SCANNING, so set all
    #     MAIN_OBJ.set_sample_positioning_mode(sample_positioning_modes.GONIOMETER)
    #     MAIN_OBJ.set_fine_sample_positioning_mode(sample_fine_positioning_modes.ZONEPLATE)
    #     MAIN_OBJ.set_sample_scanning_mode_string('Zoneplate Scanning')
    #
    #     sample_mode = sample_positioning_modes.GONIOMETER
    #     fine_sample_mode = sample_fine_positioning_modes.ZONEPLATE
    #
    #
    # elif(sample_positioning_mode == 'SAMPLEXY'):
    #     #set coarse mode
    #     MAIN_OBJ.set_sample_positioning_mode(sample_positioning_modes.COARSE)
    #     sample_mode = sample_positioning_modes.COARSE
    #     MAIN_OBJ.set_sample_scanning_mode_string('Conventional Scanning')
    #     #set fine mode
    #     if (fine_sample_positioning_mode == 'SAMPLE'):
    #         MAIN_OBJ.set_fine_sample_positioning_mode(sample_fine_positioning_modes.SAMPLEFINE)
    #         fine_sample_mode = sample_fine_positioning_modes.SAMPLEFINE
    #     else:
    #         MAIN_OBJ.set_fine_sample_positioning_mode(sample_fine_positioning_modes.ZONEPLATE)
    #         fine_sample_mode = sample_fine_positioning_modes.ZONEPLATE
    #
    # elif (sample_positioning_mode == 'HYBRID'):
    #     # set coarse mode
    #     MAIN_OBJ.set_sample_positioning_mode(sample_positioning_modes.COARSE)
    #     MAIN_OBJ.set_fine_sample_positioning_mode(sample_fine_positioning_modes.ZONEPLATE)
    #     sample_mode = sample_positioning_modes.COARSE
    #     fine_sample_mode = sample_fine_positioning_modes.ZONEPLATE
    #     MAIN_OBJ.set_sample_scanning_mode_string('Hybrid Scanning')
    #
    # if((sample_mode is not None) and (fine_sample_mode is not None)):
    #     DEVICE_CFG = dev_config_uhv(splash=splash, sample_pos_mode=sample_mode, fine_sample_pos_mode=fine_sample_mode)
    #     MAIN_OBJ.set_devices(DEVICE_CFG)
    #     DEFAULTS = Defaults('uhvstxm_dflts.json', new=False)
    # else:
    #     print 'NO SAMPLE POSITIONING MODE SELECTED'
    #     exit()
    sample_mode = None
    fine_sample_mode = None

    # COARSE_SAMPLEFINE (formerly 'conventional') scanning mode = Sample_pos_mode=COARSE, sample_fine_pos_mode=SAMPLE_FINE
    # scanning_mode = COARSE_SAMPLEFINE

    # GONI_ZONEPLATE scanning mode = Sample_pos_mode=GONIOMETER, sample_fine_pos_mode=ZONEPLATE
    # scanning_mode = GONI_ZONEPLATE

    # COARSE_ZONEPLATE scanning mode = Sample_pos_mode=COARSE, sample_fine_pos_mode=ZONEPLATE
    # scanning_mode = COARSE_ZONEPLATE

    if (scanning_mode == 'GONI_ZONEPLATE'):
        # must be ZONEPLATE SCANNING, so set all
        MAIN_OBJ.set_sample_positioning_mode(sample_positioning_modes.GONIOMETER)
        MAIN_OBJ.set_fine_sample_positioning_mode(sample_fine_positioning_modes.ZONEPLATE)
        MAIN_OBJ.set_sample_scanning_mode_string('GONI_ZONEPLATE Scanning')

        sample_mode = sample_positioning_modes.GONIOMETER
        fine_sample_mode = sample_fine_positioning_modes.ZONEPLATE


    elif (scanning_mode == 'COARSE_SAMPLEFINE'):
        # set coarse mode
        MAIN_OBJ.set_sample_positioning_mode(sample_positioning_modes.COARSE)
        sample_mode = sample_positioning_modes.COARSE
        MAIN_OBJ.set_sample_scanning_mode_string('COARSE_SAMPLEFINE Scanning')
        MAIN_OBJ.set_fine_sample_positioning_mode(sample_fine_positioning_modes.SAMPLEFINE)
        fine_sample_mode = sample_fine_positioning_modes.SAMPLEFINE
        #else:
        #    MAIN_OBJ.set_fine_sample_positioning_mode(sample_fine_positioning_modes.ZONEPLATE)
        #    fine_sample_mode = sample_fine_positioning_modes.ZONEPLATE

    elif (scanning_mode == 'COARSE_ZONEPLATE'):
        # set coarse mode
        MAIN_OBJ.set_sample_positioning_mode(sample_positioning_modes.COARSE)
        MAIN_OBJ.set_fine_sample_positioning_mode(sample_fine_positioning_modes.ZONEPLATE)
        sample_mode = sample_positioning_modes.COARSE
        fine_sample_mode = sample_fine_positioning_modes.ZONEPLATE
        MAIN_OBJ.set_sample_scanning_mode_string('COARSE_ZONEPLATE Scanning')

    if ((sample_mode is not None) and (fine_sample_mode is not None)):
        DEVICE_CFG = dev_config_uhv(splash=splash, sample_pos_mode=sample_mode, fine_sample_pos_mode=fine_sample_mode)
        MAIN_OBJ.set_devices(DEVICE_CFG)
        DEFAULTS = Defaults('uhvstxm_dflts.json', new=False)
    else:
        print 'NO SAMPLE POSITIONING MODE SELECTED'
        exit()



class cfgReader(QtCore.QObject):
    new_message = QtCore.pyqtSignal(object)

    def __init__(self):
        super(cfgReader, self).__init__()
    #globalRegistry.register([], IBeamline, '', self)

    def read_devices(self):
        devcfg = dev_config()
        DEVICES = devcfg.get_devices()
        for dev in DEVICES.keys():
            (hlth,hstr) = DEVICES[dev].state_info['health']
            if(hlth):
                conStr = 'GOOD'
            else:
                conStr = 'NOT_GOOD'
            s = 'Connection to : [%s] is %s' % (dev, conStr)
            self.new_message.emit(s)




if __name__ == '__main__':
    global app
    import sys
    app = QtWidgets.QApplication(sys.argv)
    def on_dev_status(msg):
        print msg

    cfgRdr = cfgReader()
    cfgRdr.new_message.connect(on_dev_status)
    cfgRdr.read_devices()


    app.quit()

    print 'done'
	

