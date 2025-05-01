import os

from cls.utils.log import get_module_logger
from cls.app_data import IS_WINDOWS

_logger = get_module_logger(__name__)


def reconnect_signal(obj, sig, cb):
    """
    Connects a PyQt signal to a slot, ensuring no duplicate connections.

    :param obj: The object containing the signal.
    :param sig: The signal to connect.
    :param slot: The slot (function) to connect to the signal.
    """
    try:
        # Safely disconnect the signal
        sig.disconnect()
    except TypeError:
        # Ignore if the signal was not connected
        pass
    # Connect the signal to the provided slot
    sig.connect(cb)

def disconnect_signal(obj, sig):
    """
    Safely disconnects a PyQt signal from all its connections.

    :param obj: The object containing the signal.
    :param sig: The signal to disconnect.
    """
    try:
        # Safely disconnect the signal
        sig.disconnect()
    except TypeError:
        # Ignore if the signal was not connected
        pass