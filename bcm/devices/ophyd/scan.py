#!/usr/bin/env python
"""
Epics scan record
"""

import threading

from bcm.devices import BaseObject

from cls.utils.decorators import timeit
from cls.utils.log import get_module_logger

NUM_POSITIONERS = 4
NUM_TRIGGERS = 4
# NUM_DETECTORS   = 70
NUM_DETECTORS = 4

_logger = get_module_logger(__name__)


class Scan(BaseObject):
    """
    A Device representing an Epics sscan record.

    The Scan Device represents an sscan record.
    """

    # attrs = ['VAL', 'SMSG', 'CMND', 'NPTS', 'EXSC', 'NAME', 'PDLY', 'PAUS', 'CPT', 'DESC', 'FAZE']
    attrs = ["SMSG", "CMND", "NPTS", "NAME", "CPT", "DESC", "FAZE"]
    write_attrs = ["EXSC", "PDLY", "PAUS"]

    posit_attrs = ("PV", "SP", "EP", "SI", "CP", "WD", "PA", "AR", "SM", "RA")
    trig_attrs = ("PV", "NV")
    det_attrs = ("PV", "DA", "HR", "LR")
    _delim = "."
    # _alias = {'device':	  'P1PV',
    # 		  'start':	   'P1SP',
    # 		  'end':		 'P1EP',
    # 		  'step':		'P1SI',
    # 		  'table':	   'P1PA',
    # 		  'absrel':	  'P1AR',
    # 		  'mode':		'P1SM',
    # 		  'npts':		'NPTS',
    # 		  'execute':	 'EXSC',
    # 		  'trigger':	 'T1PV',
    # 		  'pause':	   'PAUS',
    # 		  'current_point':  'CPT'}

    def __init__(self, base_signal_name, **kwargs):
        """
        Initialize the scan.

        name: The name of the scan record.
        """
        if base_signal_name.endswith("."):
            base_signal_name = base_signal_name[:-1]

        if "enable_detectors" in list(kwargs.keys()):
            enable_detectors = True
        else:
            enable_detectors = False

        attrs = list(self.attrs)
        # for i in range(1, NUM_POSITIONERS+1):
        # 	for a in self.posit_attrs:
        # 		self.attrs.append('P%i%s' % (i, a))
        # for i in range(1, NUM_TRIGGERS+1):
        # 	for a in self.trig_attrs:
        # 		self.attrs.append('T%i%s' % (i, a))

        if enable_detectors:
            for i in range(1, NUM_DETECTORS + 1):
                for a in self.det_attrs:
                    self.attrs.append("D%2.2i%s" % (i, a))

        # self.waitSemaphore = threading.Semaphore(0)
        super(Scan, self).__init__(base_signal_name)

        # _logger.debug('connecting scan [%s]' % base_signal_name)

        # for attr, pv in list(Scan._alias.items()):
        #  	self.add_device('%s%s%s' % (base_signal_name, self._delim, pv))
        for _attr in self.attrs:
            # sig_name = self.base_signal_name + self._delim + '%s' % _attr
            # self.add_device(sig_name, write_pv=sig_name)
            # print('SCAN: adding device for [%s]' % _attr)
            self.add_device(_attr, is_dev_attr=True)

        for _attr in self.write_attrs:
            # sig_name = self.base_signal_name + self._delim + '%s' % _attr
            # self.add_device(sig_name, write_pv=sig_name)
            # print('SCAN: adding device for [%s]' % _attr)
            self.add_device(_attr, write_pv=_attr, is_dev_attr=True)

    def get_ophyd_device(self):
        return self

    def run(self, wait=False):
        """
        Execute the scan.
        """
        self.add_callback("EXSC", self._onDone)
        self.put("EXSC", 1)
        if wait:
            cbindex = self.waitSemaphore.acquire()
            self.remove_callbacks("EXSC", cbindex)
        # could consider using
        # self.put('EXSC', 1, use_complete=wait)

    def _onDone(self, **kwargs):
        if kwargs["value"] == 0:
            self.waitSemaphore.release()

    # #@timeit
    # def reset(self):
    # 	"""Reset scan to some default values"""
    # 	for i in range(1, NUM_TRIGGERS+1):
    # 		self.put('T%iPV' % i, '')
    # 	for i in range(1, NUM_POSITIONERS+1):
    # 		self.put('P%iPV' % i, '')
    # 	for i in range(1, NUM_DETECTORS+1):
    # 		self.put('D%2.2iPV' % i, '')
    #
    # 	self.put('CMND', '1')

    # def get_posner_table(self, pos):
    # 	npts = self.get('NPTS')
    # 	pts = self.get('P%dPA' % pos)[0:npts]
    # 	return(pts)
    #
    # def set_posner_table(self, pos, arr):
    # 	npts = self.get('NPTS')
    # 	pts = self.put('P%dPA' % pos, arr[0:npts])

    def reset_triggers(self):
        """Reset scan to some default values"""
        for i in range(1, NUM_TRIGGERS + 1):
            self.put("T%iPV" % i, "")

    def _print(self):
        print(("PV = %s" % self.get("P1PV")))
        print(("SP = %s" % self.get("P1SP")))
        print(("EP = %s" % self.get("P1EP")))
        print(("NPTS = %s" % self.get("NPTS")))
        print((" T = %s" % self.get("T1PV")))


class ScanException(Exception):
    """raised to indicate a problem with a scan"""

    def __init__(self, msg, *args):
        Exception.__init__(self, *args)
        self.msg = msg

    def __str__(self):
        return str(self.msg)


if __name__ == "__main__":
    import sys
    from PyQt5 import QtWidgets

    def on_cpt(**kw):
        print(kw)

    def on_smsg(**kw):
        print(kw["value"])

    app = QtWidgets.QApplication(sys.argv)
    sscan = Scan("uhvstxm:scan1")
    # sscan.add_callback('CPT', on_cpt)
    sscan.add_callback("SMSG", on_smsg)
    app.exec_()
