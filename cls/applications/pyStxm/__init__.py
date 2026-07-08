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

    tag = subprocess.check_output(["git", "describe", "--tags", "--abbrev=0"]).decode('utf-8').strip()
    _major = tag.split(".")[0].replace("v", "")
    _minor = tag.split(".")[1]
    _patch = tag.split(".")[2]

    branch_lines = subprocess.check_output(["git", "branch", "--contains", "HEAD"]).decode('utf-8').strip().split(" ")
    branch = branch_lines[1]

    lines = str(subprocess.check_output(["git", "show", "-s", commit_uid])).split("\\n")
    for l in lines:
        if l.find("Date:") > -1:
            commit_date = l.replace("Date: ", "")
        elif l.find("Author:") > -1:
            commited_by = l.replace("Author: ", "")

    dct = {
        "ver": tag,
        "ver_str": f"Version {tag.replace('v', '')}",
        "major_ver": f"{_major}",
        "minor_ver": f"{_minor}",
        "patch_ver": f"{_patch}",
        "branch": branch,
        "commit": str(commit_uid),
        "commited_by": commited_by,
        "date": commit_date,
        "auth": "Russ Berg"
    }
    os.chdir(wd)

    js = dict_to_json(dct)
    ver_path = os.path.join(abs_path_to_top, "version.json")
    json_to_file(ver_path, js)


gen_version_json()
