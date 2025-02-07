import os
import pathlib
from cls.utils.list_utils import merge_to_one_list
from cls.utils.dirlist import dirlist, dirlist_withdirs, get_files_with_extension
from tinydb import TinyDB, Query


def extract_dev_name_from_line(l):
    term_chars = [".", ",", " ", ")"]

    l = l.strip()
    for t in term_chars:
        l = l.replace(t, "|")

    if len(l) > 0:
        if l[0] == "#":
            # this line is commented out ignore it
            return None
    else:
        return None

    if l.find("DNM_") > -1:
        idx1 = l.find("DNM_")
        idx2 = l[idx1:].find("|")
        dev_name = l[idx1 : idx1 + idx2]
        return dev_name
    else:
        return None


def get_dev_names(fpath):
    dev_names = []
    hashlst = []
    line_num = 1
    with open(fpath, "r") as f:
        lines = f.readlines()
    for l in lines:
        dev_name = extract_dev_name_from_line(l)
        if dev_name:
            hash_name = hash(dev_name)
            if hash_name not in hashlst:
                hashlst.append(hash_name)
                dev_names.append((dev_name, fpath, line_num))
        line_num += 1
    return dev_names


def clean_dev_name(dn):
    term_chars = [".", ",", " ", ")", "'", "]"]
    for t in term_chars:
        dn = dn.replace(t, "")
    return dn


def get_dependant_device_names(plugin_path, skip_dir_lst=[]):
    """
    load the text of a all scan pluggin files and find what devices it is dependant on and return those names
    plugin_path: points to the base bl config scan_plugins directory
    """
    dep_nms_lst = []
    hashlst = []
    # dirs = os.listdir(plugin_path)
    # for plugin_dir in pathlib.Path(plugin_path).iterdir():
    fnames = get_files_with_extension(plugin_path, ext=".py", skip_lst=skip_dir_lst)
    # for plugin_dir in pathlib.Path(plugin_path).glob('**/*'):
    #
    #     if plugin_dir.is_dir():
    #         if plugin_dir.name in skip_dir_lst:
    #             continue
    #         print(plugin_dir.name)
    #         fnames = dirlist(os.path.join(plugin_path,plugin_dir), '.py')
    for fname in fnames:
        if fname.find("focusAndZoneplateParms") > -1:
            print()
        dep_names = get_dev_names(fname)
        if len(dep_names) > 0:
            for d_nm_tpl in dep_names:
                d_nm = clean_dev_name(d_nm_tpl[0])
                hash_name = hash(d_nm)
                if hash_name not in hashlst:
                    hashlst.append(hash_name)
                    dep_nms_lst.append((d_nm, fname, d_nm_tpl[2]))

    return dep_nms_lst


def pre_flight_device_check(basepath, dev_db_fpath, skip_dir_lst=[]):
    """
    load the text of a scan pluggin module and find what devices it is dependant on and return those names
    """
    # basepath = pathlib.PurePath(os.path.join(pathlib.os.getcwd(), bl_config_nm, 'scan_plugins'))
    dep_devnames = get_dependant_device_names(
        basepath.as_posix(), skip_dir_lst=skip_dir_lst
    )
    dev_db = TinyDB(dev_db_fpath.as_posix())
    dev_lst = dev_db.all()
    q = Query()
    non_exist_devs = []
    # check to see if a dependant device name is not in the current device database
    for dn_tpl in dep_devnames:
        dn = dn_tpl[0]
        fname = dn_tpl[1]
        line_num = dn_tpl[2]
        dev_dct_lst = dev_db.search(q.name == dn)
        if len(dev_dct_lst) == 0:
            non_exist_devs.append((dn, fname, line_num))

    print(
        f"the following dependant devices do not exist in the device database for {basepath}"
    )
    for _dn in non_exist_devs:
        print(f"\t{_dn}")
        dev_db.close()
    return non_exist_devs


def check_plugin_dev_dep(appDir, bl_config_nm):
    # check scan plugin dependancies
    basepath = pathlib.PurePath(
        os.path.join(
            pathlib.Path(pathlib.os.getcwd()).parent.as_posix(),
            bl_config_nm,
            "scan_plugins",
        )
    )
    dbpath = pathlib.PurePath(
        os.path.join(
            pathlib.Path(pathlib.os.getcwd()).parent.as_posix(), bl_config_nm, "db.json"
        )
    )
    dep_devnames = pre_flight_device_check(basepath, dbpath)


def check_application_dev_dep(appDir, dbpath):
    skip_dir_lst = ["ui", "sim_bkps", "logs", "__pycache__", "bl_configs"]
    # check scan plugin dependancies
    dep_devnames = pre_flight_device_check(appDir, dbpath, skip_dir_lst=skip_dir_lst)


if __name__ == "__main__":

    # #check scan plugin dependancies
    appDir = pathlib.PurePath("C:/controls/sandbox/pyStxm3/cls/applications/pyStxm")
    dbpath = pathlib.PurePath(
        os.path.join(appDir.as_posix(), "bl_configs", "basic", "device_db.json")
    )

    # check_plugin_dev_dep(appDir, 'amb_bl10ID1')

    check_application_dev_dep(appDir, dbpath)
