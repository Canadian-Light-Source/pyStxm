"""
Created on 2014-10-06

@author: bergr
"""
import os
import datetime
import simplejson as json
import threading
import tempfile
import numpy as np
import types

from cls.appWidgets.user_account.user_object import user_obj
from cls.utils.log import get_module_logger

from cls.data_utils.jsonEncoder import NumpyAwareJSONEncoder

_logger = get_module_logger(__name__)

_FILE_LOCKS = {}
_FILE_LOCKS_GUARD = threading.Lock()


def _get_file_lock(fpath):
    """Return a process-local lock for a specific file path."""
    norm = os.path.abspath(str(fpath))
    with _FILE_LOCKS_GUARD:
        if norm not in _FILE_LOCKS:
            _FILE_LOCKS[norm] = threading.Lock()
        return _FILE_LOCKS[norm]


def atomic_save_json(filename, data_dct):
    """Safely save JSON using temp-file + atomic replace to avoid partial writes."""
    if data_dct is None:
        return

    fpath = os.path.abspath(str(filename))
    dpath = os.path.dirname(fpath)
    if dpath and (not os.path.exists(dpath)):
        os.makedirs(dpath, exist_ok=True)

    payload = json.dumps(data_dct, sort_keys=True, indent=4, cls=NumpyAwareJSONEncoder)
    lock = _get_file_lock(fpath)

    tmp_name = None
    with lock:
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".tmp", prefix=".jsonsave_", dir=dpath if dpath else None, delete=False
            ) as tf:
                tmp_name = tf.name
                tf.write(payload)
                tf.flush()
                os.fsync(tf.fileno())

            os.replace(tmp_name, fpath)
        except Exception:
            if tmp_name and os.path.exists(tmp_name):
                try:
                    os.remove(tmp_name)
                except Exception:
                    pass
            raise


def mime_to_dct(mimeData):
    """
    the mime data is a json string that has been written to a mime datastream
    """
    if mimeData.hasText():
        dct = json.loads(str(mimeData.text()))
        return dct
    else:
        return {}


def dict_to_json_string(dct, to_unicode=False):
    s = json.dumps(dct, sort_keys=True, indent=4, cls=NumpyAwareJSONEncoder)
    if to_unicode:
        s = str(s)
    return s


def json_string_to_dct(jstr):
    dct = json.loads(jstr)  # [0]
    return dct


class ThreadJsonSave(threading.Thread):
    """Threaded file Save"""

    def __init__(self, data_dct, name="", fpath="", verbose=False):
        threading.Thread.__init__(self, name=name)
        self.data_dct = data_dct
        self.name = "JSON-SV." + name
        self.fpath = str(fpath)
        self.verbose = verbose
        # print 'ThreadJsonSave: [%s] started' % self.name

    def run(self):
        if self.data_dct != None:
            fstr = self.fpath
            try:
                atomic_save_json(fstr, self.data_dct)
            except Exception as ex:
                _logger.error("ThreadJsonSave: failed saving [%s]: %s", fstr, ex)
                return
            # _logger.info('ThreadJsonSave: [%s] saved [%s]' % (self.name, self.data_dct['fpath']))
            if self.verbose:
                print(
                    "ThreadJsonSave: [%s] saved [%s]"
                    % (self.name, self.data_dct["fpath"])
                )

        # _logger.info('ThreadJsonSave: [%s] DONE' % self.name)


def loadJson(filename):
    """load json data from disk"""
    if os.path.exists(filename):
        with open(filename, "r") as fh:
            js = json.loads(fh.read())
    else:
        print(
            "json_ThreadSave: loadJson: file [%s] doesn't exist: No File Loaded"
            % filename
        )
        js = None
    return js


def saveJson(filename, data_dct):
    atomic_save_json(filename, data_dct)
