import os.path

from cls.applications.pyStxm import abs_path_to_ini_file, abs_path_to_top
from cls.utils.cfgparser import ConfigClass
from cls.applications.pyStxm.bl_config_loader import (
    load_beamline_device_config,
    load_beamline_preset,
)
from cls.utils.dirlist import dirlist_withdirs
from cls.utils.list_utils import sort_str_list

appConfig = ConfigClass(abs_path_to_ini_file)
bl_config_nm = appConfig.get_value("MAIN", "bl_config")
blConfig = load_beamline_preset(bl_config_nm)
modules = blConfig["SCAN_PANEL_ORDER"]

scan_plugin_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "applications",
    "pyStxm",
    "bl_configs",
    bl_config_nm,
    "scan_plugins",
)
hsh_lst = []
blcfg_hsh_lst = []
modules = {}
# for mod_nm, idx in modules.items():
#     mod_path = os.path.join(scan_plugin_path, mod_nm, '%s.py' % mod_nm)
#     f = open(mod_path, 'r')
#     lines = f.readlines()
#     f.close()
#     dev_nms = []
#     for l in lines:
#         if l.find('DNM_') > -1:
#             l2 = l.split('DNM_')
#             iidx = l2[1].find(',')
#             if iidx == -1:
#                 iidx = l2[1].find(')')
#             dvnm = l2[1][:iidx]
#             hsh = hash(dvnm)
#             if hsh not in hsh_lst:
#                 dev_nms.append(dvnm)
#                 hsh_lst.append(hsh)
#
#     if len(dev_nms) > 0:
#         print('MOD: [%s] uses the following devices:' % mod_nm)
#         for dnm in dev_nms:
#             print('\t[DNM_%s]'%dnm)
#     else:
#         print('MOD: [%s] uses devices that have already been listed:' % mod_nm)
#
#     print()


def check_files(basedirs, bl_config_nm, verbose=False):
    for basedir in basedirs:
        skip_lst = ["device_names.py", "dev_check.py", "device_list.py"]
        for root, dirs, files in os.walk(basedir):
            if root.find("bl_configs") > -1:
                if root.find(os.path.join("bl_configs", bl_config_nm)) == -1:
                    # skip the beam line configurations that pyStxm is currently not setup to
                    continue
            for file in files:
                if file in skip_lst:
                    continue
                if file.endswith(".py"):
                    fname = os.path.join(root, file)
                    if verbose:
                        print("\tchecking [%s]" % fname)
                    f = open(fname, "r")
                    lines = f.readlines()
                    f.close()
                    dev_nms = []
                    for l in lines:
                        iidx = -1
                        if l.find("DNM_") > -1:
                            # if l.find('DNM_AX1_INTERFER_VOLTS') > -1:
                            #    print()
                            l2 = l.split("DNM_")
                            idx_lst = []
                            idx_lst.append(l2[1].find(" ="))
                            idx_lst.append(l2[1].find("="))
                            idx_lst.append(l2[1].find(","))
                            idx_lst.append(l2[1].find(")"))
                            idx_lst.append(l2[1].find("]"))
                            idx_lst.append(l2[1].find("#"))
                            idx_lst.append(l2[1].find(" in"))
                            idx_lst.append(l2[1].find("'"))

                            idx_lst.sort()
                            if idx_lst[-1] != -1:
                                while -1 in idx_lst:
                                    idx_lst.remove(-1)
                            iidx = idx_lst[0]

                            dvnm = l2[1][:iidx].strip("]")
                            dvnm = dvnm.strip(")")
                            dvnm = dvnm.strip()
                            hsh = hash(dvnm)
                            if fname == os.path.join(root, "%s.py" % bl_config_nm):
                                if hsh not in blcfg_hsh_lst:
                                    dev_nms.append(dvnm)
                                    blcfg_hsh_lst.append(hsh)
                            else:

                                if hsh not in hsh_lst:
                                    dev_nms.append(dvnm)
                                    hsh_lst.append(hsh)
                    dev_nms.sort()

                    if len(dev_nms) > 0:
                        if verbose:
                            print("MODULE: [%s] uses the following devices:" % fname)
                        if file == "%s.py" % bl_config_nm:
                            mnm = bl_config_nm
                        else:
                            mnm = fname

                        modules[mnm] = []
                        for dnm in dev_nms:
                            modules[mnm].append("DNM_%s" % dnm)
                            if verbose:
                                print("\t\tDNM_%s" % dnm)
                    else:
                        pass
                        # print('MOD: [%s] uses devices that have already been listed or there were no Devices used' % fname)
    return modules


def verify_devs(blcfg_lst, mod_lst):
    verified = True
    dont_exist_lst = []
    for m in mod_lst:
        if m not in blcfg_lst:
            print("\tThe device [%s] does not exist in the beamline configuration" % m)
            verified = False
            dont_exist_lst.append(m)
    if verified:
        print(
            "\tThe beamline configuration contains all entries for the devices needed"
        )
    else:
        print(
            "\tERROR! There are [%d] devices that are required that do not exist in the beamline configuration"
            % len(dont_exist_lst)
        )
    print()
    return dont_exist_lst


if __name__ == "__main__":
    dirs = [abs_path_to_ini_file.replace("app.ini", ""), abs_path_to_top]
    mods_dct = check_files(dirs, bl_config_nm, verbose=False)
    import pprint

    print(
        "Only listing unique devices, so if a module doesnt show up thats because the device has already been listed by another module"
    )
    # pprint.pprint(mods_dct)
    print()
    bl_dct = mods_dct[bl_config_nm]
    del mods_dct[bl_config_nm]
    dont_exist_dct = {}
    for k, v in mods_dct.items():
        dont_exist_dct[k] = []
        print("Verifying [%s]" % k)
        dnt_ex_lst = verify_devs(bl_dct, v)
        if len(dnt_ex_lst) > 0:
            dont_exist_dct[k].append(dnt_ex_lst)

    print(
        "After checking all the modules, the following devices were found not to exist in the beamline configuration"
    )
    i = 0
    for k, v in dont_exist_dct.items():
        print("\t %d: %s: %s" % (i, k, v))
        i += 1
