"""
Created on April 11, 2022

@author: bergr
"""
import os
import pathlib
from bcm.devices import DCSShutter, init_pv_report_file
from cls.applications.pyStxm import abs_path_to_ini_file
from cls.types.stxmTypes import (
    sample_positioning_modes,
    sample_fine_positioning_modes,
    endstation_id_types,
)
from cls.utils.cfgparser import ConfigClass
from cls.utils.log import get_module_logger
from cls.utils.json_utils import file_to_json, json_to_dict
from cls.appWidgets.splashScreen import create_splash, get_splash

from cls.applications.pyStxm.bl_configs.base_scan_plugins.device_loader import (
    device_config,
)

_logger = get_module_logger(__name__)

appConfig = ConfigClass(abs_path_to_ini_file)

init_pv_report_file()

bl_config_nm = appConfig.get_value("MAIN", "bl_config")
blConfig = ConfigClass(os.path.join(os.path.dirname(__file__), "%s.ini" % bl_config_nm))
scanning_mode = blConfig.get_value("SCANNING_MODE", "scanning_mode")

# tried moving this elsewhere but then the Splash screen would not be displayed
# app_dir = pathlib.Path(abs_path_to_ini_file).parent
# ver_dct = json_to_dict(file_to_json(os.path.join(app_dir, 'version.json')))
# ver_str = 'Version %s.%s' % (ver_dct['major_ver'], ver_dct['minor_ver'])
# splash = create_splash(img_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'pyStxmSplash.png'), ver_str=ver_str)
splash = get_splash()
splash.show()
# splash = None

DEVICE_CFG = None
sample_mode = None
fine_sample_mode = None

# COARSE_SAMPLEFINE (formerly 'conventional') scanning mode = Sample_pos_mode=COARSE, sample_fine_pos_mode=SAMPLE_FINE
# scanning_mode = COARSE_SAMPLEFINE

# GONI_ZONEPLATE scanning mode = Sample_pos_mode=GONIOMETER, sample_fine_pos_mode=ZONEPLATE
# scanning_mode = GONI_ZONEPLATE

# COARSE_ZONEPLATE scanning mode = Sample_pos_mode=COARSE, sample_fine_pos_mode=ZONEPLATE
# scanning_mode = COARSE_ZONEPLATE

if scanning_mode == "GONI_ZONEPLATE":
    # must be ZONEPLATE SCANNING, so set all
    sample_mode = sample_positioning_modes.GONIOMETER
    fine_sample_mode = sample_fine_positioning_modes.ZONEPLATE


elif scanning_mode == "COARSE_SAMPLEFINE":
    # set coarse mode
    sample_mode = sample_positioning_modes.COARSE
    fine_sample_mode = sample_fine_positioning_modes.SAMPLEFINE

elif scanning_mode == "COARSE_ZONEPLATE":
    # set coarse mode
    sample_mode = sample_positioning_modes.COARSE
    fine_sample_mode = sample_fine_positioning_modes.ZONEPLATE

if (sample_mode is not None) and (fine_sample_mode is not None):
    # instanciate DEVICE_CFG here which will be imported later
    DEVICE_CFG = device_config(
        splash=splash,
        bl_config_nm=bl_config_nm,
        sample_pos_mode=sample_mode,
        fine_sample_pos_mode=fine_sample_mode,
    )

else:
    print("NO SAMPLE POSITIONING MODE SELECTED")
    exit()
