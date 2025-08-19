"""
Created on Dec 2, 2016

@author: control
"""
import os
from datetime import datetime

from cls.utils.cfgparser import ConfigClass
from cls.appWidgets.user_account.sample_holder_object import sample_holder_obj
from cls.appWidgets.enum import Enum
from cls.appWidgets.bl_config_loader import load_beamline_preset

ACCESS_LVLS = Enum(["GUEST", "USER", "STAFF", "ADMIN"])


class user_obj(object):
    def __init__(self, abs_path_to_ini_file):
        super(user_obj, self).__init__()
        appConfig = ConfigClass(abs_path_to_ini_file)
        bl_config_nm = appConfig.get_value("MAIN", "bl_config")
        blConfig = load_beamline_preset(bl_config_nm)
        data_dir = blConfig["BL_CFG_MAIN"]["data_dir"]
        data_sub_dir = blConfig["BL_CFG_MAIN"]["data_sub_dir"]
        if "ptycho_cam_data_dir" in blConfig["BL_CFG_MAIN"].keys():
            #self.ptycho_cam_data_dir = blConfig["BL_CFG_MAIN"]["ptycho_cam_data_dir"]
            self.ptycho_cam_data_dir = blConfig["BL_CFG_MAIN"]["linux_data_dir"]
        else:
            self.ptycho_cam_data_dir = None

        self._userName = None
        self._password = None
        self._access_lvl = ACCESS_LVLS.GUEST  # default
        self._description = ""
        #self._date_created = date.fromtimestamp(time.time())
        self._date_created = datetime.now()
        self._enabled = False
        self._group = None
        self._base_data_dir = data_dir
        self._data_sub_dir = data_sub_dir
        self._data_dir = None
        self._sample_ids = {}
        self._cur_sample_id = None
        self._seq_num = 0

    def get_seq_num(self):
        return self._seq_num
        self._seq_num += 1

    def create_new_sampleholder(self, id="H110212"):
        self._cur_sample_id = id
        shobj = sample_holder_obj(self._userName, id, self._data_dir)
        self._sample_ids[id] = shobj

    def print_user(self):
        print(f"username: {self._userName}")
        # print 'password: %s' % self.password
        print(f"access_lvl: {self._access_lvl}")
        print(f"description: {self._description}")
        print(f"date_created: {self._date_created}")
        print(f"enabled: {self._enabled}")
        print(f"group: {self._group}")
        #print(f"base_data_dir: {os.path.join(self._base_data_dir, self._userName)}")
        print(f"base_data_dir: {self._base_data_dir}")
        print(f"data_sub_dir: {self._data_sub_dir}")
        # print 'data_dir: %s' % self._data_dir

    def set_username(self, name):

        self._userName = name

    def get_username(self):
        return self._userName

    def set_password(self, password):
        self._password = password

    def get_password(self):
        return self._password

    def set_access_level(self, new_lvl):
        self._access_lvl = new_lvl

    def get_access_level(self):
        return self._access_lvl

    def set_description(self, desc):
        self._description = desc

    def get_description(self):
        return self._description

    def set_enabled(self, en):
        self._enabled = en

    def is_enabled(self):
        return self._enabled

    def set_group(self, group):
        self._group = group

    def get_group(self):
        return self._group

    def get_base_data_dir(self):
        return self._base_data_dir

    def get_data_dir(self, pos=None):
        return self._data_dir

    def get_scan_defs_dir(self):
        return os.path.join(self._data_dir, "scan_defs")

    def create_data_dir(self):
        """
        generate a standard data directory for the user for taoday,
        result should be :
            <base_data_dir>/<username>/MonSep2013/,<sample holder id>/<pos1 - pos6>
        """
        current_date = datetime.now().strftime('%Y-%m-%d')

        if self._data_sub_dir == '_cur_date_':
            self._data_dir = os.path.join(self._base_data_dir, current_date)

        elif self._data_sub_dir == '_default_':
            self._data_dir = os.path.join(self._base_data_dir, current_date)

        else:
            self._data_dir = os.path.join(self._base_data_dir, current_date)

        # self.ensure_dir(self._data_dir)

    # def ensure_dir(self, dir):
    #     if os.path.exists(dir):
    #         pass
    #     else:
    #         os.makedirs(dir, exist_ok=True)
    #         #os.mkdir(dir)

    # def make_basedata_dir(self):
    #     if os.path.exists(self._data_dir):
    #         pass
    #     else:
    #         #os.mkdir(self._data_dir)
    #         os.makedirs(self._data_dir, exist_ok=True)


if __name__ == "__main__":
    pass
