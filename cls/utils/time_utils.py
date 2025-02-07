"""
Created on Apr 24, 2015

@author: bergr
"""
import datetime
from time import mktime, strftime, strptime, gmtime


def msec_to_sec(ms):
    return ms * 0.001


class CST(datetime.tzinfo):
    def utcoffset(self, dt):
        return datetime.timedelta(hours=-6)

    def dst(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return "Saskatchewan Canada"


def make_timestamp_now():
    """
    create a ISO 8601 formatted time string for the current time and return it
    """
    t = datetime.datetime.now(tz=CST()).isoformat()
    return t


def secondsToStr(sec):
    return strftime("%H:%M:%S", gmtime(sec))


def datetime_string_to_seconds(s):
    """
    'END_TIME': '2017-09-22T09:07:02.833000-06:00',
    'START_TIME': '2017-09-22T09:06:23.628000-06:00',

    :param s:
    :return:
    """
    from datetime import datetime
    import time

    s2 = s.split(".")[0]
    d = datetime.strptime(s2, "%Y-%m-%dT%H:%M:%S")
    sec = time.mktime(d.timetuple())
    return sec


def on_new_est_scan_time(self, time_sec):
    """
    a signal handler that accepts total seconds estimated by the scan plugin
    the QLabel self.estimatedTimeLbl is only the time, there is another label on the UI that contains "Estimated Time:"
    """
    est_time_str = secondsToStr(time_sec)
    idx1 = est_time_str.find(".")
    time_str = est_time_str[:idx1]
    self.estimatedTimeLbl.setText(f"{time_str}")


import time


def measure_execution_time(func, *args, **kwargs):
    """
    Measures the elapsed time for executing a function.

    Args:
    - func: The function to measure.
    - *args: Positional arguments to pass to the function.
    - **kwargs: Keyword arguments to pass to the function.

    Returns:
    - result: The return value of the function.
    - elapsed_time: The elapsed time in seconds.
    """
    start_time = time.perf_counter()  # Record the start time
    result = func(*args, **kwargs)  # Call the function
    end_time = time.perf_counter()  # Record the end time

    elapsed_time = end_time - start_time
    return result, elapsed_time


# Example usage
def example_function(n):
    return sum(range(n))


# result, elapsed_time = measure_execution_time(example_function, 1000000)
# print(f"Result: {result}, Elapsed Time: {elapsed_time:.6f} seconds")
