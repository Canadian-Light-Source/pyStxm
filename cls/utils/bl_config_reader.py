import configparser
import os

from cls.applications.pyStxm import abs_path_to_ini_file, abs_path_to_top

class BeamlineConfigReader:
    """
    BeamlineConfigReader reads the beamline configuration based on the main application beamline config
    specified in app.ini file.
    """
    def __init__(self):
        self.app_config = configparser.ConfigParser()
        self.app_config.read(abs_path_to_ini_file)
        bl_config_name = self.app_config.get('MAIN', 'bl_config')
        bl_config_path = os.path.join(abs_path_to_top, 'cls/applications/pyStxm/bl_configs', bl_config_name, f'{bl_config_name}.ini')
        self.bl_config = configparser.ConfigParser()
        self.bl_config.read(bl_config_path)

    def get_setting(self, section, key):
        return self.bl_config.get(section, key)