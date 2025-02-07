
from typing import Dict, Optional, Tuple

from cls.utils.log import get_module_logger

_logger = get_module_logger(__name__)


def check_windows_procs_running(procs_to_check: Optional[Dict[str, Tuple[str, Optional[str]]]] = None):
    """
    a function where a battery of checks can be executed prior to a scan running
    :return:
    """
    if procs_to_check is None:
        procs_to_check = {"DataRecorder Process": ("python.exe", "nx_server.py")}

    import wmi
    c = wmi.WMI()

    running_procs = {exec_name: c.Win32_Process(name=exec_name) for exec_name, _ in procs_to_check.values()}

    # check to see if procs are running
    for alias, (exec_name, search_name) in procs_to_check.items():
        proc_running = False
        for process in running_procs.get(exec_name, []):
            cmdline: str = process.CommandLine
            if not isinstance(cmdline, str):
                # in some cases the process does not specify a command, but we may not care.
                # we should be explicit that the requested name string is NOT specified.
                proc_running = search_name is None
                # otherwise, fall through until we do get a valid command line
                continue

            if (
                search_name is None  # see note above
                or search_name in cmdline
                or ("python" in exec_name and ("-m" in cmdline and search_name.removesuffix(".py") in cmdline))
            ):
                proc_running = True
                break

        if not proc_running:
            from cls.appWidgets.dialogs import info

            _logger.error("required process [%s] is NOT running", alias)
            info(
                "Scan cannot execute because required process is not running",
                f"Required process [{alias}] is NOT running",
                ok_str="OK",
                cancel_str="Nope",
            )
            return False

    return True




