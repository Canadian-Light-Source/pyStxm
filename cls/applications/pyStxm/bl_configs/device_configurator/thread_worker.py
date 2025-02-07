import sys
import traceback
import time
from PyQt5 import QtCore, QtGui, QtWidgets


class WorkerSignals(QtCore.QObject):
    """
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        `tuple` (exctype, value, traceback.format_exc() )

    result
        `object` data returned from processing, anything

    progress
        `int` indicating % progress

    """

    finished = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal(tuple)
    result = QtCore.pyqtSignal(object)
    progress = QtCore.pyqtSignal(int)


class Worker(QtCore.QRunnable):
    """
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    """

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.delay_return = 0.5
        if len(args) > 0:
            self.fnames = self.args[0]

        # Add the callback to our kwargs
        # kwargs['progress_callback'] = self.signals.progress

    @QtCore.pyqtSlot()
    def run(self):
        """
        Initialise the runner function with passed args, kwargs.
        """

        # Retrieve args/kwargs here; and fire processing using them
        try:
            skip = False
            result = self.fn(*self.args, **self.kwargs)

            if result is None:
                # print('WORKER: skipping result')
                skip = True
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            if not skip:
                print("WORKER: emitting result(res)")
                if self.delay_return > 0.0:
                    time.sleep(self.delay_return)
                    print("WORKER: delayed emitting result(res)")
                    self.signals.result.emit(
                        result
                    )  # Return the result of the processing
                else:
                    print("WORKER: emitting result(res)")
                    self.signals.result.emit(
                        result
                    )  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done
