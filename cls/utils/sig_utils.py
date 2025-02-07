import os

from cls.utils.log import get_module_logger
from cls.app_data import IS_WINDOWS

_logger = get_module_logger(__name__)

# def reconnect_signal(obj, sig, cb):
#     """
#     This function takes the base object, the signal addr and the callback and checks first to see if the signal is still connected
#     if it is it is disconnected before being connected to the callback
#     ex:
#         was:
#             self.executingScan.sigs.changed.connect(self.add_line_to_plot)
#         is:
#             self.reconnect_signal(self.executingScan.sigs, self.executingScan.sigs.changed, self.add_line_to_plot)
#
#     :param obj: base QObject
#     :param sig: addr of signal instance
#     :param cb: callback to attach signal to
#     :return:
#
#
#     """
#     if IS_WINDOWS:
#         # windows allows access to the protected function 'recievers'
#         if obj.receivers(sig) > 0:
#             # _logger.info('stxmMain: this sig is still connected, disconnnecting before reconnecting')
#             sig.disconnect()
#     else:
#         sig.disconnect()
#
#     # _logger.debug('stxmMain: connecting this signal')
#     sig.connect(cb)
#
#
# def disconnect_signal(obj, sig):
#     """
#     This function takes the base object, the signal addr and checks first to see if the signal is still connected
#     if it is it is disconnected
#
#     :param obj: base QObject
#     :param sig: addr of signal instance
#     :return:
#
#
#     """
#     if IS_WINDOWS:
#         # windows allows access to the protected function 'recievers'
#         if obj.receivers(sig) > 0:
#             # _logger.debug('stxmMain: this sig is still connected, disconnnecting')
#             sig.disconnect()
#     else:
#         sig.disconnect()
#


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