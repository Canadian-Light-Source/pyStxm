# -*- coding: utf-8 -*-
#
"""
cls:
This will house all of the Canadian Lightsource specific modules 
"""
import os
import subprocess
from cls.utils.json_utils import json_to_file, dict_to_json

# create a user account manager
# usr_acct_mgr = user_accnt_mgr(os.path.dirname(os.path.abspath(__file__)) + '\users.p')
# abs_path_to_top = os.path.dirname(os.path.abspath(__file__))
abs_path_to_ini_file = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "app.ini"
)
abs_path_to_docs = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "..",
    "..",
    "docs",
    "_build",
    "html",
)
abs_path_to_top = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."
)
abs_path_of_ddl_file = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "..",
    "scanning",
    "e712_wavegen",
    "ddl_data",
    "ddl_data.hdf5",
)

abs_path_of_defaults_file = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "..",
    "app_data"
)



def gen_version_json():
    wd = os.getcwd()
    os.chdir(abs_path_to_top)
    commit_uid = subprocess.check_output(["git", "rev-parse", "HEAD"]).strip()
    commit_uid = commit_uid.decode("utf-8")
    # commit_date = subprocess.check_output(["git", "show", "-s", "--format=%ci", str(commit_uid)])
    #commit_date = [str(subprocess.check_output(["git", "show", "-s", commit_uid])).split("\\n")[2]
    lines = str(subprocess.check_output(["git", "show", "-s", commit_uid])).split("\\n")
    for l in lines:
        if l.find("Date:") > -1:
            commit_date = l.replace("Date: ", "")
        elif l.find("Author:") > -1:
            commited_by = l.replace("Author: ", "")

    dct = {
        "ver": "3.0",
        "ver_str": "Version 3.0",
        "major_ver": "3",
        "minor_ver": "0",
        "commit": str(commit_uid),
        "commited_by": commited_by,
        "date": commit_date,
        "auth": "Russ Berg"
    }
    os.chdir(wd)

    js = dict_to_json(dct)
    json_to_file("version.json", js)


gen_version_json()
