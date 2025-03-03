# -*- coding:utf-8 -*-
"""
This module provides an interface to load and retrieve elements of a config file
based on the ConfigParser python module
"""
import sys
import configparser, os
import simplejson as json

from cls.utils.log import get_module_logger


# put 3rd party imports here
_logger = get_module_logger(__name__)


class ConfigClass(object):
    """
    classdocs
    """

    def __init__(self, filename, exit_on_fail=True):
        """
        Constructor
        """
        super(ConfigClass, self).__init__()
        self.config = configparser.ConfigParser()
        self.filename = filename
        self.exit_on_fail = exit_on_fail
        self.cfgDict = {}
        self.update()

    def update(self):
        """
        read/load the config file into member variable
        """
        if os.path.exists(self.filename):
            self.config.read(self.filename)

            # Replace placeholders in .ini files with environment variable values if they exist
            # if the .ini file specifies a placeholder that does not exist as an environment variable then raise
            # Exception and exit
            for section in self.config.sections():
                for key, value in self.config[section].items():
                    if value.find("${") > -1:
                        if os.path.expandvars(value) == value:
                            # the environment variable does not exist
                            raise Exception(f"The Environment variable [{value.replace('${', '').replace('}','')}] does not exist, This must be added before software will run")
                        self.config[section][key] = os.path.expandvars(value)

        else:
            if self.exit_on_fail:
                print("ConfigClass: Error: cannot load %s" % self.filename)
                sys.exit()
            else:
                f = open(self.filename, "w+")
                f.write("")
                f.close()
        self.cfgDict["MAIN"] = self.config.defaults()
        self.sections = self.config.sections()

    def get_value(self, section, option, all=False):
        # use the configParser that will perform substitutions 0, 1 is for raw
        if (section == "MAIN") or self.config.has_section(section):

            if self.config.has_option(section, option):

                val = self.config.get(section, option)
                if all:
                    return val
                else:
                    val = val.replace(" ", "").split(",")[0]
            else:
                _logger.error(
                    "option [%s] does not exist in section [%s]" % (option, section)
                )
                val = None
        else:
            _logger.error("section [%s] does not exist" % section)
            val = None
        # print self.config.get(section, item, 0)
        return val

    def get_list(self, section, option, all=False):
        """
        return a list of values from a comma separated list
        """
        list_str = self.get_value(section, option, all=True)
        if list_str:
            ret_list = json.loads(list_str)
            return ret_list
        else:
            return None

    def get_all(self):
        """
        return the configuration as a dict
        :return:
        """
        dct = {}
        # print('config has:')
        sections = self.config.sections()
        for sec in sections:
            # print('\t [%s] = ' % (sec))
            dct[sec] = {}
            for opt in self.config.options(sec):
                v = self.config.get(sec, opt)
                # check and remove comments
                s = v.replace(" ", "")
                s2 = s.split("#")
                if len(s2) > 1:
                    dct[sec][opt] = s2[0]
                else:
                    # print('\t\t [%s] = %s' % (opt,v))
                    dct[sec][opt] = v
        return dct

    def set_value(self, section, option, value):
        # use the configParser that will perform substitutions 0, 1 is for raw
        self.config.set(section, option, value)

    # print self.config.set(section, item, value)

    def get_bool_value(self, section, option):
        if (section == "MAIN") or self.config.has_section(section):
            if self.config.has_option(section, option):
                val = self.config.getboolean(section, option)
            else:
                _logger.error(
                    "option [%s] does not exist in section [%s]" % (option, section)
                )
                val = None
        else:
            _logger.error("section [%s] does not exist" % section)
            val = None
        return val

    def _tst_gen_cfg_file(self):
        config = configparser.RawConfigParser()

        # When adding sections or items, add them in the reverse order of
        # how you want them to be displayed in the actual file.
        # In addition, please note that using RawConfigParser's and the raw
        # mode of ConfigParser's respective set functions, you can assign
        # non-string values to keys internally, but will receive an error
        # when attempting to write to a file or when you get it in non-raw
        # mode. SafeConfigParser does not allow such assignments to take place.
        config.add_section("Section1")
        config.set("Section1", "int", "15")
        config.set("Section1", "bool", "true")
        config.set("Section1", "float", "3.1415")
        config.set("Section1", "baz", "fun")
        config.set("Section1", "bar", "Python")
        config.set("Section1", "foo", "%(bar)s is %(baz)s!")

        # Writing our configuration file to 'example.cfg'
        with open("example.cfg", "wb") as configfile:
            config.write(configfile)

    def _read_cfg_file(self, fname):
        config = configparser.ConfigParser()
        config.read(fname)

        # Set the third, optional argument of get to 1 if you wish to use raw mode.
        print(config.get("MAIN", "top", 0))
        print(config.get("MAIN", "appDir", 0))
        print(config.get("MAIN", "dataDir", 0))
        print(config.get("MAIN", "uiDir", 0))
        print(config.get("MAIN", "cfgDir", 0))
        print(config.get("MAIN", "autoSaveData", 0))


if __name__ == "__main__":

    cfgObj = ConfigClass(r"C:\controls\github\pyStxm3\cls\applications\pyStxm\app.ini")
    # print(cfgObj.get_value('MAIN', 'uiDir'))

    cfg = cfgObj.get_all()
    print(cfg)
