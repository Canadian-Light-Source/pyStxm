"""
Created on Dec 2, 2016

@author: bergr
"""
import simplejson as json
import numpy as np
import datetime
import ctypes

from cls.appWidgets.user_account.user_object import user_obj


class NumpyAwareJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        # try:
        #print(type(obj))
        if isinstance(obj, np.ndarray) and obj.ndim == 1:
            return obj.tolist()
        elif isinstance(obj, np.ndarray) and obj.ndim == 2:
            return obj.tolist()
        elif isinstance(obj, np.ndarray) and obj.ndim == 3:
            return obj.tolist()
        elif isinstance(obj, np.generic):
            return obj.item()
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, datetime.date):
            str = obj.isoformat()
            # str = unicode(str, errors='replace')
            str = str(str, errors="ignore")
            return str

        elif isinstance(obj, user_obj):
            # return(obj.__dict__)
            return "USER_OBJ_NOT_SAVED"
        elif isinstance(obj, ctypes.c_longlong):
            return obj.value

        else:
            return json.JSONEncoder.default(self, obj)

        # except TypeError:
        #    print('dataRecorder.py: NumpyAwareJSONEncoder: TypeError')
