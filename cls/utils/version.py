import os

from cls.utils.json_utils import file_to_json, json_to_dict


def get_version():
    ver_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "version.json")
    if os.path.exists(ver_path):
        js = file_to_json(ver_path)
        ver_dct = json_to_dict(js)

    else:
        ver_dct = {}
        ver_dct["ver"] = "1.9"
        ver_dct["ver_str"] = "Version 1.9"
        ver_dct["major_ver"] = "1"
        ver_dct["minor_ver"] = "9"
        ver_dct["auth"] = "Russ Berg"
        ver_dct["date"] = "Jan 26 2017"

    return ver_dct
