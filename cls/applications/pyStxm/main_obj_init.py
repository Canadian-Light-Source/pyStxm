"""
Created on May 16, 2019

@author: bergr
"""

# BCM GLOBAL Settings for stxm
import os
import pathlib
from PyQt5 import QtWidgets

from cls.appWidgets.main_object import main_object_base

# RUSS FEB25 from cls.appWidgets.splashScreen import get_splash
from cls.app_data.defaults import Defaults
from cls.applications.pyStxm import abs_path_to_ini_file
from cls.types.stxmTypes import sample_positioning_modes, sample_fine_positioning_modes
from cls.utils.cfgparser import ConfigClass
from cls.utils.log import get_module_logger
from cls.appWidgets.bl_config_loader import (
    load_beamline_device_config,
    load_beamline_preset,
)

# from bcm.devices import BACKEND

# from twisted.python.components import globalRegistry
_logger = get_module_logger(__name__)

appConfig = ConfigClass(abs_path_to_ini_file)

# when simulating un comment the next line
DEVPRFX = "SIM_"

MAIN_OBJ = None
DEVICE_CFG = None

# get the current scanning mode from teh app.ini configuration
bl_config_nm = appConfig.get_value("MAIN", "bl_config")
abs_bl_config_path = f"{abs_path_to_ini_file}".replace("app.ini",os.path.join("bl_configs",bl_config_nm))
bl_config_dct = load_beamline_preset(bl_config_nm)
print(f"Loading beam line configuration from [{bl_config_nm}]")

# get the beamline specifics, found in bl_configs/<bl>/<bl>.ini
bl_config_dct['UI_OVERRIDES']['bl_config_path'] = abs_bl_config_path

beamline_desc = bl_config_dct["BL_CFG_MAIN"]["beamline_desc"]
endstation_name = bl_config_dct["BL_CFG_MAIN"]["endstation_name"]
endstation_prefix = bl_config_dct["BL_CFG_MAIN"]["endstation_prefix"]
datafile_prefix = bl_config_dct["BL_CFG_MAIN"]["datafile_prefix"]
dcs_backend = bl_config_dct["BL_CFG_MAIN"]["dcs_backend"]
scanning_mode = bl_config_dct["SCANNING_MODE"]["scanning_mode"]

if "PTYCHO_CAMERA" in bl_config_dct.keys():
    default_ptycho_cam = bl_config_dct["PTYCHO_CAMERA"]["default_cam"]
else:
    default_ptycho_cam = None

# MAIN_OBJ = main_object_base(beamline_desc, endstation_name, BEAMLINE_IDS.STXM)


#MAIN_OBJ = main_object_base(beamline_desc, endstation_name, beamline_id=bl_config_nm, main_cfg=appConfig)
MAIN_OBJ = main_object_base(beamline_desc, endstation_name, beamline_cfg_dct=bl_config_dct, main_cfg=appConfig)
MAIN_OBJ.set_device_backend(dcs_backend)
MAIN_OBJ.set_datafile_prefix(datafile_prefix)
# MAIN_OBJ.set_thumbfile_suffix('jpg')
MAIN_OBJ.set_endstation_prefix(endstation_prefix)
ver_str = "Version %s.%s" % (
    MAIN_OBJ.get("APP.MAJOR_VER"),
    MAIN_OBJ.get("APP.MINOR_VER"),
)

MAIN_OBJ.set_sample_scanning_mode_string(scanning_mode)
MAIN_OBJ.set_ptycho_default_cam_nm(default_ptycho_cam)
# set the path to the device database created by device_configurator
MAIN_OBJ.set_devdb_path(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "bl_configs",
        bl_config_nm,
        "device_db.json",
    )
)

sample_mode = None
fine_sample_mode = None


# COARSE_SAMPLEFINE (formerly 'conventional') scanning mode = Sample_pos_mode=COARSE, sample_fine_pos_mode=SAMPLE_FINE
# GONI_ZONEPLATE scanning mode = Sample_pos_mode=GONIOMETER, sample_fine_pos_mode=ZONEPLATE
# COARSE_ZONEPLATE scanning mode = Sample_pos_mode=COARSE, sample_fine_pos_mode=ZONEPLATE

if scanning_mode == "GONI_ZONEPLATE":
    # must be ZONEPLATE SCANNING, so set all
    MAIN_OBJ.set_sample_positioning_mode(sample_positioning_modes.GONIOMETER)
    MAIN_OBJ.set_fine_sample_positioning_mode(sample_fine_positioning_modes.ZONEPLATE)

    sample_mode = sample_positioning_modes.GONIOMETER
    fine_sample_mode = sample_fine_positioning_modes.ZONEPLATE


elif scanning_mode == "COARSE_SAMPLEFINE":
    # set coarse mode
    MAIN_OBJ.set_sample_positioning_mode(sample_positioning_modes.COARSE)
    sample_mode = sample_positioning_modes.COARSE

    MAIN_OBJ.set_fine_sample_positioning_mode(sample_fine_positioning_modes.SAMPLEFINE)
    fine_sample_mode = sample_fine_positioning_modes.SAMPLEFINE
    # else:
    #    MAIN_OBJ.set_fine_sample_positioning_mode(sample_fine_positioning_modes.ZONEPLATE)
    #    fine_sample_mode = sample_fine_positioning_modes.ZONEPLATE

elif scanning_mode == "COARSE_ZONEPLATE":
    # set coarse mode
    MAIN_OBJ.set_sample_positioning_mode(sample_positioning_modes.COARSE)
    MAIN_OBJ.set_fine_sample_positioning_mode(sample_fine_positioning_modes.ZONEPLATE)
    sample_mode = sample_positioning_modes.COARSE
    fine_sample_mode = sample_fine_positioning_modes.ZONEPLATE


# DEVICE CONNECTION
if (sample_mode is not None) and (fine_sample_mode is not None):
    # connect to all teh devices for the desired beamline configuration
    DEVICE_CFG, cfg_dir = load_beamline_device_config(bl_config_nm)
    MAIN_OBJ.set_devices(DEVICE_CFG)
    MAIN_OBJ.set_rot_angle_device(DEVICE_CFG.sample_rot_angle_dev)
    # blConfig = load_beamline_preset(bl_config_nm)
    mainConfig = appConfig.get_all()
    mainConfig["MAIN"]["bl_config_dir"] = os.path.join(cfg_dir, "scan_plugins")
    mainConfig["MAIN"]["base_scan_plugin_dir"] = os.path.join(
        pathlib.Path(__file__).parent, "bl_configs", "base_scan_plugins"
    )
    mainConfig.update(bl_config_dct)
    MAIN_OBJ.set_presets(mainConfig)

    # DEFAULTS = Defaults('uhvstxm_dflts.json', new=False)
    DEFAULTS = Defaults("%s_dflts.json" % bl_config_nm)
else:
    print("NO SAMPLE POSITIONING MODE SELECTED")
    exit()


if __name__ == "__main__":
    global app
    import sys

    app = QtWidgets.QApplication(sys.argv)
    # def on_dev_status(msg):
    #     print(msg)
    #
    # cfgRdr = cfgReader()
    # cfgRdr.new_message.connect(on_dev_status)
    # cfgRdr.read_devices()
    load_beamline_device_config()

    app.quit()

    print("done")
