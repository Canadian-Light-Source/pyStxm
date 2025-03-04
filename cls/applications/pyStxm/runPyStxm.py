import sys
import os

#make sure that the applications modules can be found, used to depend on PYTHONPATH environ var
sys.path.append( os.path.join(os.path.dirname(os.path.abspath(__file__)), "..","..","..") )

import time
import logging

from PyQt5 import QtWidgets

from cls.appWidgets.splashScreen import get_splash, del_splash, create_splash
from cls.utils.version import get_version
from cls.utils.log import log_to_qt_and_to_file
from epics.ca import context_destroy
import ophyd
import profile
import pstats
import psutil

from PyQt5 import QtCore, QtGui, uic, QtWidgets

# if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
#     QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
#     QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_Use96Dpi, True)

# if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
#    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts, True)

TIMEOUT = 5
# set default timeout for all EpicsSignal connections & communications
if not ophyd.signal.EpicsSignalBase._EpicsSignalBase__any_instantiated:
    ophyd.signal.EpicsSignalBase.set_defaults(auto_monitor=True, timeout=TIMEOUT, write_timeout=TIMEOUT, connection_timeout=TIMEOUT)

def clean_up():
    from cls.applications.pyStxm.main_obj_init import MAIN_OBJ

    MAIN_OBJ.cleanup()


def check_for_existing_python_processes():
    """
    sometimes I have seen during development that old python.exe processes are still kicking around which
    could lead to strange behaviour, do a check and see if there are more than 1 running, if so force exit
    """
    py_cnt = 0
    ex = False
    # procs = [p.name() for p in psutil.process_iter()]
    procs = list(psutil.process_iter())
    for p in procs:
        pnm = p.name()
        if pnm.find("python.exe") > -1:
            if py_cnt > 1:
                print(
                    f"There appears to already be a python executable running in [{p.cwd()}]"
                )
                if p.cwd().find("Stxm") == 0:
                    p.kill()
                    ex = True
            py_cnt += 1
        # else:
        #     print(f'Found [{pnm}]')
    if ex:
        exit()


def determine_profile_bias_val():
    """
    determine_profile_bias_val(): description

    :param determine_profile_bias_val(: determine_profile_bias_val( description
    :type determine_profile_bias_val(: determine_profile_bias_val( type

    :returns: None
    """
    pr = profile.Profile()
    v = 0
    v_t = 0
    for i in range(5):
        v_t = pr.calibrate(100000)
        v += v_t
        print(v_t)

    bval = v / 5.0
    print("bias val = ", bval)
    profile.Profile.bias = bval
    return bval


def profile_it():
    """
    profile_it(): description

    :param profile_it(: profile_it( description
    :type profile_it(: profile_it( type

    :returns: None
    """

    # bval = determine_profile_bias_val()

    profile.Profile.bias = 1.36987840635e-05

    profile.run("go()", "testprof.dat")

    p = pstats.Stats("testprof.dat")
    p.sort_stats("cumulative").print_stats(100)


def trace_calls(frame, event, arg):
    if event not in ["call"]:  # ,'c_call']:
        return

    co = frame.f_code
    func_name = co.co_name
    # if func_name == 'write':
    #     # Ignore write() calls from print statements
    #     return
    func_line_no = frame.f_lineno
    func_filename = co.co_filename
    caller = frame.f_back
    caller_line_no = caller.f_lineno
    caller_filename = caller.f_code.co_filename

    #if caller_filename.find("qwt") > -1:
    found = False

    if caller_filename.find("bl_configs") > -1:
        found = True
    elif caller_filename.find("ophyd") > -1:
        found = True
    elif caller_filename.find("bluesky") > -1:
        found = True
        # print('Call to %s on line %s of %s from line %s of %s' % \
        #     (func_name, func_line_no, func_filename,
        #      caller_line_no, caller_filename))
    if found:
        print(
            "Call to %s on line %s of %s from line %s of %s"
            % (func_name, func_line_no, func_filename, caller_line_no, caller_filename)
        )
    # print('Call to %s of %s  of %s' % \
    #       (func_name, func_filename,
    #        caller_filename))
    return


# set the backend to use so that when other modules import this one they can get the correct devices
def update_backend_string_from_beamline_config():
    """
    this function write the backend string to the backend.py file based on the backend specified in the beamline config
    file
    """
    from cls.applications.pyStxm import abs_path_to_ini_file
    from cls.utils.cfgparser import ConfigClass
    from cls.appWidgets.bl_config_loader import (
        load_beamline_device_config,
        load_beamline_preset,
    )

    appConfig = ConfigClass(abs_path_to_ini_file)
    # get the current scanning mode from teh app.ini configuration
    bl_config_nm = appConfig.get_value("MAIN", "bl_config")
    bl_config_dct = load_beamline_preset(bl_config_nm)
    dcs_backend = bl_config_dct["BL_CFG_MAIN"]["dcs_backend"]
    content = f"""
# this generated file simply delcares the name of the backend to be used, it is purely just this variable so\n
# that it can simply be imported and checked by other files\n
# set the backend that should be used\n
BACKEND='{dcs_backend}'"""

    absolute_path = os.path.abspath(__file__)
    # Get the directory containing the file
    abs_directory = os.path.dirname(absolute_path)
    file_path = os.path.join(abs_directory, "..","..","..","bcm","backend.py")

    try:
        # Open the file in write mode
        with open(file_path, 'w') as file:
            file.write(content)
        print(f"Successfully wrote to {file_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

def go():
    """
    the main launch function for pystxm
    :return:
    """

    app = QtWidgets.QApplication(sys.argv)

    debugger = sys.gettrace()
    from cls.appWidgets.dialogs import excepthook

    sys.excepthook = excepthook

    #sys.settrace(trace_calls)

    # check to see if the last instance of python didnt die on exit
    check_for_existing_python_processes()

    logdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    if not os.path.exists(logdir):
        os.makedirs(logdir)

    logfile = os.path.join(logdir, time.strftime("%Y%m%d") + ".log")
    log = log_to_qt_and_to_file(logfile, level=logging.DEBUG)

    # app = QtWidgets.QApplication(sys.argv)
    ver_dct = get_version()

    # create the splash screen
    # RUSS FEB25 splash = get_splash(ver_str=ver_dct['ver_str'])
    splash = create_splash(ver_str=ver_dct["ver_str"])

    from cls.applications.pyStxm.stxmMain import pySTXMWindow

    if debugger is None:
        pystxm_win = pySTXMWindow(exec_in_debugger=False, log=log)
    else:
        pystxm_win = pySTXMWindow(exec_in_debugger=True, log=log)

    if splash:
        splash.hide()

    app.aboutToQuit.connect(clean_up)
    pystxm_win.show()
    pystxm_win.on_update_style()
    # try:
    #     #starts event loop
    #     sys.exit(app.exec_())
    # except:
    #     print("runPyStxm; Exiting")
    sys.exit(app.exec_())


if __name__ == "__main__":
    # profile_it()
    update_backend_string_from_beamline_config()
    time.sleep(0.1)
    go()
