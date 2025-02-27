"""
Created on Mar 21, 2016

@author: bergr
"""
"""
Created on 2014-10-06

@author: bergr
"""
import os, sys
from PyQt5 import QtCore, QtGui

import simplejson as json
from cls.utils.dict_utils import dct_get, dct_put
from cls.utils.dirlist import dirlist
from cls.utils.log import get_module_logger
from cls.utils.json_threadsave import ThreadJsonSave
import copy

templateDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
SaveSettingsDir = os.path.dirname(os.path.abspath(__file__))

_logger = get_module_logger(__name__)


class SaveSettings(QtCore.QObject):
    """
    This class represents the main object for the application SaveSettings
    """

    changed = QtCore.pyqtSignal()

    def __init__(self, fpath, dct_template=None):
        super(SaveSettings, self).__init__()
        self.defdct = {}
        if dct_template is None:
            self.dct_template = {}
        else:
            self.dct_template = dct_template
        self.fpath = str(fpath)
        self.init_SaveSettings(self.fpath)

    def init_SaveSettings(self, fpath=None):
        fpath = str(fpath)
        if not os.path.isfile(self.fpath):
            self.defdct = self.get_default_dct()
            self.defdct["fpath"] = self.fpath
            self.save_json_obj(self.defdct, fpath=self.fpath)
        else:
            # read from disk
            self.defdct = self.loadJson(fpath)
            self.defdct["fpath"] = self.fpath

    def add_section(self, section, value, overwrite=False):
        dct_put(self.defdct, section, value, overwrite)
        self.update()

    def get_default_dct(self):
        dct = copy.copy(self.dct_template)
        dct["fpath"] = self.fpath
        return dct

    def update(self):
        # _logger.debug('SaveSettings.update()')
        self.save_json_obj(self.defdct, self.fpath)

    def save_json_obj(self, dct, fpath=None):
        saveThread = ThreadJsonSave(dct, fpath=fpath)
        saveThread.setDaemon(True)
        saveThread.start()

    def loadJson(self, filename):
        """internal load json data from disk"""
        if os.path.exists(filename):
            file = open(filename)
            js = json.loads(file.read())
            file.close()
        else:
            print("json file doesn't exist: died")
            js = {}
        return js

    def get(self, name, create=True):
        """get the object section by name"""
        dct = dct_get(self.defdct, name)
        if dct is None:
            dct = self.get_default_dct()
            self.add_section(name, dct)

        return dct

    def set(self, name, obj):
        """get the object section by name"""
        dct_put(self.defdct, name, obj, overwrite=True)

    def get_main_obj(self):
        """return the entire main object dict"""
        return self.defdct


__all__ = ["SaveSettings"]

if __name__ == "__main__":
    ss = SaveSettings("ss_test.json")
    ss.add_section("OSA_CENTER", (0, 0))
    print(ss.get_main_obj())
