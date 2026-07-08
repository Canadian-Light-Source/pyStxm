import sys
import pathlib
from PyQt5 import QtWidgets, uic, QtGui, QtCore, Qt






if __name__ == "__main__":
    import importlib
    import os
    from bcm.backend import BACKEND
    from device_cfg_epics import Device_Configure as Device_Configure_epics
    from device_cfg_zmq import Device_Configure as Device_Configure_zmq
    from utils import gen_device_names_file

    app = QtWidgets.QApplication([])
    # get bl_config_dir from the command line
    bl_config_dirname = sys.argv[1]
    dbpath = pathlib.PurePath(
        os.path.join(
            pathlib.Path(os.getcwd()).parent.as_posix(), bl_config_dirname
        )
    )
    if pathlib.Path(dbpath).exists():
        import_Str = f"cls.applications.pyStxm.bl_configs.{bl_config_dirname}.devs"
        devs = importlib.import_module(import_Str, package=None)
        gen_device_names_file(dbpath, devs.dev_dct)
        if BACKEND == "zmq":
            dcfg = Device_Configure_zmq(dbpath, devs)
        else:
            dcfg = Device_Configure_epics(dbpath, devs)

        dcfg.show()
    else:
        print(f"Error: db path [{str(dbpath)}] does not exist")
    sys.exit(app.exec_())
