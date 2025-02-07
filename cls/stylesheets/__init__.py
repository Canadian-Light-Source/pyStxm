# -*- coding: utf-8 -*-
#
"""
"""
import os
from PyQt5 import QtGui

from cls.utils.cfgparser import ConfigClass
from cls.utils.dirlist import dirlist
from cls.utils.log import (
    get_module_logger,
)
from cls.app_data import IS_WINDOWS

_logger = get_module_logger(__name__)

base_style_sheet_dir = os.path.dirname(os.path.abspath(__file__))

base_app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),"..", "applications", f"pyStxm{os.path.sep}")

abs_path_to_ini_file = os.path.join(base_app_dir, "app.ini")
appConfig = ConfigClass(abs_path_to_ini_file)
styleDir = appConfig.get_value("MAIN", "styleDir")
master_colors = {}
font_sizes = {}

# 3840 x 2160
default_app_screen_sz = (None,None)

is_style_light = True
if styleDir.find("dark") > -1:
    is_style_light = False

def color_str_as_hex(color_str):
    """
    depending on the if the item getting its color changed is a Qt Widget or a Qwt Widget
    it expects color assignments differently, this function is passed a string of either
    an rgb(r,g,b) string of the color of a hex string #RRGGBB so see which it is and return
    the hex string version of it
    """
    if color_str.find("rgb(") == -1:
        #assume its already a hex string
        return(color_str)
    else:
        return(rgb_as_hex(color_str))

def color_str_as_rgb(color_str):
    """
    depending on the if the item getting its color changed is a Qt Widget or a Qwt Widget
    it expects color assignments differently, this function is passed a string of either
    an rgb(r,g,b) string of the color of a hex string #RRGGBB so see which it is and return
    the rgb string version of it
    """
    if color_str[0] == "#":
        return(hex_str_to_rgb(color_str))
    else:
        #assume its already an rgb string
        return(color_str)

def rgb_as_hex(rgb_str):
    """
    take an rgb string like the ones found in qss stylesheets (ex: 'rgb(0, 128,64);')
    and    return a hex version of it
    """
    # s =
    s2 = rgb_str.strip("rgb(")
    s2 = s2.strip(");")
    s3 = s2.split(",")
    r = int(s3[0])
    g = int(s3[1])
    b = int(s3[2])
    return "#%02x%02x%02x" % (r, g, b)

def hex_str_to_rgb(hex_str):
    """
    given a string like #d7d5d7 return teh string rgb()
    """
    rs = "0x" + hex_str[1:3]
    gs = "0x" + hex_str[3:5]
    bs = "0x" + hex_str[5:7]
    r = int(rs, 0)
    g = int(gs, 0)
    b = int(bs, 0)
    return(f"rgb({r}, {g}, {b})")


def key_val_to_dct(lines):
    dct = {}
    for l in lines:
        if len(l) > 0:
            l1 = l.split("=")
            k = l1[0].replace(" ", "")
            val = l1[1].replace(" ", "")
            dct[k] = val
    return dct

def gen_gray_rgb_str():
    v = 0
    while v < 255:
        print(f"gray_{int(v)} = rgb({int(v)},{int(v)},{int(v)})")
        v += 5

#force_screen_size=1920
force_screen_size=None
def get_style_dir(force_screen_size=force_screen_size):
    """
    figure out if we need the hi res stylesheets or not and return the actual stylesheet directory
    """
    from PyQt5 import QtWidgets

    curr_app = QtWidgets.QApplication.instance()
    if curr_app == None:
        styledir = styleDir + "_hires_disp"
        # print(f'get_style: Using stylesheets in {styledir}')
        baseDir = os.path.join(base_style_sheet_dir, styledir)
        return (baseDir)
    else:
        screen = curr_app.primaryScreen()
        print('Screen: %s' % screen.name())
        size = screen.size()
        ht = size.height()
        if force_screen_size:
            wdth = force_screen_size
        else:
            wdth = size.width()
        print('Final destination screen size: %d x %d' % (wdth, ht))
        if wdth > 2560 and IS_WINDOWS:
            styledir = styleDir + "_hires_disp"
            print(f'get_style: Using stylesheets in {styledir}')
        elif not IS_WINDOWS:
            styledir = styleDir + "_linux_hires_disp"
            print(f'get_style: Using stylesheets in {styledir}')
        else:
            styledir = styleDir
            print(f'get_style: Using stylesheets in {styledir}')

        baseDir = os.path.join(base_style_sheet_dir, styledir)
        return(baseDir)

def init_master_color_config():
    """
    re read the master color config and regen the master color dicts
    """
    global master_colors, default_app_screen_sz, font_sizes
    master_colors.clear()
    #read the common colors into a dict
    common_clrs_path_to_ini_file = os.path.join(base_style_sheet_dir, "common_colors.ini")
    commonClrConfig = ConfigClass(common_clrs_path_to_ini_file)
    common_all = commonClrConfig.get_all()

    #read the speciofic stylesheets colors into a master dict
    final_style_dir = get_style_dir()
    mstr_clrs_path_to_ini_file = os.path.join(final_style_dir, "master_colors.ini")
    masterClrConfig = ConfigClass(mstr_clrs_path_to_ini_file)
    master_all = masterClrConfig.get_all()

    #add the common colors to the master
    master_allclrs = master_all["MAIN"] | common_all["MAIN"]
    for k, v in master_allclrs.items():
        if len(v) > 30:
            # this is only an rgb_str
            master_colors[k] = {"rgb_str": v, "rgb_qclr": None}
        else:
            v = v.replace(";", "")
            r, g, b = v.replace("rgb(", "").replace(")", "").split(",")
            master_colors[k] = {"rgb_str": v, "rgb_qclr": QtGui.QColor(int(r), int(g), int(b)), "rgb_hex": rgb_as_hex(v)}

    for k, v in master_all['FONT'].items():
        font_sizes[k] = v

    default_app_screen_wd = masterClrConfig.get_value("SCREEN_SIZE", "default_app_screen_wd")
    default_app_screen_ht = masterClrConfig.get_value("SCREEN_SIZE", "default_app_screen_ht")
    default_app_screen_sz = (int(default_app_screen_wd), int(default_app_screen_ht))


def get_default_screen_size():
    global default_app_screen_sz
    return default_app_screen_sz

def get_style(force=False, skip_lst=[]):
    """
    retrieve that the directory from the ini file and load the stylesheets
    in that directory into a single string that can be applied in one shot
    """
    sh_outpath = os.path.join(os.path.dirname(__file__), "ssheet.txt")
    if os.path.exists(sh_outpath) and not force:
        # read it off of disk
        with open(sh_outpath, "r") as fin:
            ssheet_str = fin.read()
    else:
        # # recreate it
        init_master_color_config()
        #styledir = styleDir + "_hires_disp" #get_style_dir()
        #baseDir = os.path.join(base_style_sheet_dir, styledir)
        baseDir = get_style_dir()
        sheets = dirlist(baseDir, ".qss", fname=None)

        ssheet_str = ""
        for f in sheets:
            if f in skip_lst:
                continue
            sshFile = os.path.join(baseDir, f)
            fh = open(sshFile, "r")
            qstr = fh.read()
            ssheet_str += qstr
            fh.close()
        # put any replacements here
        srch_rplc = {}
        srch_rplc.update(master_colors)
        srch_rplc.update(font_sizes)
        for s_r in srch_rplc:
            if s_r.find("font") > -1:
                #font
                ssheet_str = ssheet_str.replace(s_r, srch_rplc[s_r])
            else:
                #color
                ssheet_str = ssheet_str.replace(s_r, srch_rplc[s_r]["rgb_str"])
            # print 'get_style: replaced [%s] with [%s]' % (clr, master_colors[clr])

        # dump to disk if not exist
        #ll = ssheet_str.split("\n")
        ll = ssheet_str
        with open(sh_outpath, "w") as fout:
            for l in ll:
                #fout.write(l.replace("\n", ""))
                fout.write(l)


    return ssheet_str


init_master_color_config()

# final_style_dir = get_style_dir()
# mstr_clrs_path_to_ini_file = os.path.join(final_style_dir, "master_colors.ini")
# masterClrConfig = ConfigClass(mstr_clrs_path_to_ini_file)
# master_all = masterClrConfig.get_all()

#now generate master colors from master_colors.ini file

# for k,v in master_all["MAIN"].items():
#     if len(v) > 30:
#         #this is only an rgb_str
#         master_colors[k] = {"rgb_str": v, "rgb_qclr": None}
#     else:
#         v = v.replace(";","")
#         r, g, b = v.replace("rgb(", "").replace(")", "").split(",")
#         master_colors[k] = {"rgb_str": v, "rgb_qclr": QtGui.QColor(int(r), int(g), int(b)),"rgb_hex": rgb_as_hex(v) }
#
