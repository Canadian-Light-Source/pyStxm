from typing import cast, overload

from PyQt5 import QtCore, QtWidgets


# Windows DPI scale:
#   96.0 = 100%
#  120.0 = 125%
#  144.0 = 150%
#  192.0 = 200%


def _get_application_dpi() -> float:
    app = cast(QtWidgets.QApplication, QtWidgets.QApplication.instance() or QtWidgets.QApplication([]))
    window = app.activeWindow()
    screen_num = app.desktop().screenNumber(window)
    if screen_num >= 0:
        return app.screens()[screen_num].logicalDotsPerInch()
    return 96.


def _get_application_dpi_ratio() -> float:
    return _get_application_dpi() / 96.0


@overload
def dpi_scaled(size: int) -> int: ...
@overload
def dpi_scaled(size: float) -> float: ...
@overload
def dpi_scaled(size: QtCore.QSize) -> QtCore.QSize: ...
@overload
def dpi_scaled(size: QtCore.QSizeF) -> QtCore.QSizeF: ...
def dpi_scaled(size):
    """Scale up a size based on active desktop scaling.

    This should be used to calculate fixed-size bounding box geometries,
    where font scaling of any contained text is handled by the OS.
    Otherwise, text may appear cut-off on certain monitor setups.
    """
    if isinstance(size, int):
        return int(size * _get_application_dpi_ratio())
    return size * _get_application_dpi_ratio()


def get_signals(source):
    sigs = []
    cls = source if isinstance(source, type) else type(source)
    signal = type(QtCore.pyqtSignal())
    for name in dir(source):
        if hasattr(cls, name):
            if isinstance(getattr(cls, name), signal):
                print(name)
                sigs.append(name)
    return sigs


if __name__ == "__main__":
    get_signals(QtWidgets.QWidget)
