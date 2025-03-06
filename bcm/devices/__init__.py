# the device files list in this directory show what the interface for each device
# must support, these are not for inheriting

from bcm.backend import BACKEND

#
if BACKEND == 'zmq':
    # implemented for connection to Pixelator
    USE_EPICS = False
    USE_TANGO = False
    USE_PIXELATOR = True
    USE_OPHYD_EPICS = False
    USE_OPHYD_SIM = False

else:
    # standard CLS
    USE_EPICS = False
    USE_TANGO = False
    USE_PIXELATOR = False
    USE_OPHYD_EPICS = True
    USE_OPHYD_SIM = False

REPORT_FIELDS = False

def init_pv_report_file():
    if REPORT_FIELDS:
        # reset file to empty
        f = open("reqd_pvs.txt", "w")
        f.close()


def report_fields(self):
    """
    an interface that will printout all the pv fields used by this class
    """
    if REPORT_FIELDS:
        # f = open('reqd_pvs.txt', 'a')
        # if hasattr(self, 'get_desc'):
        #     f.write('<%s> %s:\n' % (type(self), self.get_desc()))
        # elif hasattr(self, 'name'):
        #     f.write('<%s> %s:\n' % (type(self), self.name))
        # f.close()

        if hasattr(self, "_sig_attrs"):
            print_flds(self, self._sig_attrs)

        if hasattr(self, "_ophyd_dev"):
            print_flds(self, self._ophyd_dev._sig_attrs)

        if hasattr(self, "attrs"):
            print_flds(self, None, _attr_lst=self.attrs)


def print_flds(slf, _attrs, _attr_lst=None):
    f = open("reqd_pvs.txt", "a")
    if _attr_lst:
        for a in _attr_lst:
            f.write("\tREQUIRED_PV: [%s.%s]\n" % (slf.name, a))
    else:
        for k, v in _attrs.items():
            if v.suffix[0] == ".":
                if slf.prefix[-1] == ":":
                    _pvname = slf.prefix[0:-1] + v.suffix
                else:
                    _pvname = slf.prefix + v.suffix
            else:
                _pvname = slf.prefix + v.suffix
            # print('REQUIRED_PV: [%s]' % (_pvname))
            f.write("\tREQUIRED_PV: [%s]\n" % (_pvname))
    f.close()


if USE_EPICS:
    from .epics.base import BaseDevice
    from .epics.aio import basedevice as basedevice
    from .epics.camera import camera
    from .epics.counter import BaseGate, BaseCounter
    from .epics.shutter import PvShutter
    from .epics.dio import digitalIO
    from .epics.mbbi import Mbbi
    from .epics.mbbo import Mbbo
    from .epics.mca import Mca
    from .epics.motor_qt import Motor_Qt
    from .epics.scan import Scan
    from .epics.stringin import Stringin
    from .epics.stxm_sample_mtr import (
        sample_abstract_motor,
        sample_motor,
        e712_sample_motor,
    )
    from .epics.transform import Transform
    from .epics.waveform import Waveform

elif USE_OPHYD_EPICS:

    from .ophyd.base_device import BaseDevice
    from .ophyd.base_object import BaseObject

    # from .ophyd.base_sig_io import BaseSignalIO as aio

    from .ophyd.camera import camera
    from .ophyd.mbbi import Mbbi
    from .ophyd.mbbo import Mbbo
    from .ophyd.bo import Bo
    from .ophyd.shutter import DCSShutter
    from .ophyd.scan import Scan
    from .ophyd.transform import Transform
    from .ophyd.dio import digitalIO

    # from .ophyd.counter import BaseGate, BaseCounter, BaseOphydGate
    from .ophyd.qt.daqmx_counter_output import BaseOphydGate
    from .ophyd.stringin import Stringin
    from .ophyd.waveform import Waveform
    from .ophyd.motor import MotorQt
    from .ophyd.stxm_sample_mtr import (
        sample_abstract_motor,
        sample_motor,
        e712_sample_motor,
            )
    from .ophyd.pi_e712 import E712WGDevice
    from .ophyd.area_detectors import GreatEyesCCD, SimGreatEyesCCD
    from .ophyd.sis3820_scalar import SIS3820ScalarDevice
    from .ophyd.ad_tucsen import TucsenDetector

    #this is a placeholder for zmq testing when I jump back and forth to test
    from .ophyd.sis3820_scalar import SIS3820ScalarDevice as Counter

elif USE_OPHYD_SIM:

    from .ophyd_sim.base_device import BaseDevice
    from .ophyd_sim.base_object import BaseObject

    # from .ophyd.base_sig_io import BaseSignalIO as aio

    from .ophyd_sim.camera import camera
    from .ophyd_sim.mbbi import Mbbi
    from .ophyd_sim.mbbo import Mbbo
    from .ophyd_sim.shutter import PvShutter
    from .ophyd_sim.scan import Scan
    from .ophyd_sim.transform import Transform
    from .ophyd_sim.dio import digitalIO
    from .ophyd_sim.counter import BaseGate, BaseCounter
    from .ophyd_sim.stringin import Stringin
    from .ophyd_sim.waveform import Waveform
    from .ophyd_sim.motor import Motor_Qt
    from .ophyd_sim.stxm_sample_mtr import (
        sample_abstract_motor,
        sample_motor,
        e712_sample_motor,
    )
    from .ophyd_sim.pi_e712 import E712WGDevice

elif USE_TANGO:
    pass
elif USE_PIXELATOR:
    from .zmq.zmq_device import ZMQBaseDevice as BaseDevice

    #from .ophyd.base_object import BaseObject

    # from .ophyd.base_sig_io import BaseSignalIO as aio

    #from .ophyd.camera import camera
    #from .ophyd.mbbi import Mbbi
    from .zmq.counter import ZMQCounter as Counter
    from .zmq.mbbo import ZMQMBBo as Mbbo
    from .zmq.bo import ZMQBo as Bo
    from .zmq.shutter import DCSShutter
    #from .ophyd.scan import Scan
    # from .ophyd.transform import Transform
    from .zmq.transform import ZMQTransform as Transform
    from .zmq.multi_selectable import MultiSelectable
    #from .ophyd.dio import digitalIO

    # from .ophyd.counter import BaseGate, BaseCounter, BaseOphydGate
    #from .ophyd.qt.daqmx_counter_output import BaseOphydGate
    #from .ophyd.stringin import Stringin
    #from .ophyd.waveform import Waveform
    from .zmq.motor import ZMQMotor as MotorQt
    from .zmq.stxm_sample_motor import sample_abstract_motor, sample_motor
    # from .zmq.motor import ZMQMotor as sample_motor
    # from .zmq.zmq_device import ZMQMotor as e712_sample_motor

    # from .ophyd.pi_e712 import E712WGDevice
    # from .ophyd.area_detectors import GreatEyesCCD, SimGreatEyesCCD
    # from .ophyd.sis3820_scalar import SIS3820ScalarDevice
    # from .ophyd.ad_tucsen import TucsenDetector
else:
    print("ERROR: No DCS configured")
    exit(1)
