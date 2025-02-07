# -*- coding:utf-8 -*-
"""
Created on 2011-03-04

@author: bergr
"""
import os, sys
import pathlib


def dirlist(path, suffix, fname=None, remove_suffix=False):
    """
    Takes a path and a file suffix as a filter and returns a list of the files in
    that path that match the filter
    ex: alist = dirlist(r'C:\pythonxy\workspace\PyQtStxmViewer\src\data\101207\A101207022', '.xim')
    """
    ret = []
    containsStr = suffix
    dirList = os.listdir(path)

    for f in dirList:
        # if(f.find(containsStr) > -1):
        # get the last 4 characters of filename as they are the file extension
        extension = f[-(len(suffix)) :]
        if suffix == extension:
            if remove_suffix:
                f = f.replace(extension, "")
            if fname:
                if f.find(fname) > -1:
                    ret.append(f)
            else:
                ret.append(f)

    return ret


def dirlist_withdirs(path, suffix, fname=None, remove_suffix=False, exclude=[".tmp"]):
    """
    Takes a path and a file suffix as a filter and returns a list of the files in
    that path that match the filter
    ex: alist = dirlist(r'C:\pythonxy\workspace\PyQtStxmViewer\src\data\101207\A101207022', '.xim')
    """
    ret = []
    containsStr = suffix
    dirList = os.listdir(path)
    files = []
    dirs = []

    for f in dirList:
        skip = False
        for e in exclude:
            if f.find(e) > -1:
                # we want to skip anything in the exclude list
                skip = True
        if skip:
            continue
        # if(f.find(containsStr) > -1):
        # get the last 4 characters of filename as they are the file extension
        if f.find(".") > -1:
            # its a file
            if f.find(suffix) > -1:
                # its a file we want
                if remove_suffix:
                    f = f.replace(suffix, "")
                files.append(f)
            else:
                # its a file but we dont want these kinds
                pass
        else:
            # its a directory
            dirs.append(f)

    # for f in files:
    # 	extension = f[-(len(suffix)):]
    # 	if (suffix == extension):
    # 		if (remove_suffix):
    # 			f = f.replace(extension, '')
    # 		if (fname):
    # 			if (f.find(fname) > -1):
    # 				ret.append(f)
    # 		else:
    # 			ret.append(f)

    return dirs, files


def get_dirs(dirpath, skip_lst=[]):
    dir_lst = []
    for i in pathlib.Path(dirpath).iterdir():
        if i.is_dir():
            if i.name in skip_lst:
                continue
            dir_lst.append(i)
            l = get_dirs(i, skip_lst)
            if len(l) > 0:
                dir_lst.append(l)
    return dir_lst


def get_all_dirs(basedir, skip_lst=[]):
    basepath = pathlib.PurePath(basedir)
    _lst = get_dirs(basepath, skip_lst)
    dir_lst = [x for x in _lst if x != []]

    return dir_lst


def get_all_files_and_subdirs(basepath_str, skip_lst=[]):
    l = []
    for path, subdirs, files in os.walk(basepath_str):
        for name in files:
            skip = False
            subdir = path.replace(basepath_str + "\\", "")
            for skipit in skip_lst:
                if subdir.find(skipit) > -1:
                    skip = True
            if not skip:
                l.append(os.path.join(path, name))
    return l

def get_subdir_names(basepath_str, skip_lst=[]):
    subs = []
    dirs = os.listdir(basepath_str)
    for d in dirs:
        for skip in skip_lst:
            if d.find(skip) > -1:
                break
            else:
                if d not in subs:
                    subs.append(d)
    return subs

def get_files_with_extension(basepath_str, ext=".py", skip_lst=[]):
    lst = get_all_files_and_subdirs(basepath_str, skip_lst=skip_lst)
    ll = []
    for nm in lst:
        if nm.find(ext) > -1:
            ll.append(nm)
    return ll


if __name__ == "__main__":
    from cls.utils.list_utils import merge_to_one_list

    # dirlist(sys.argv[1:])
    # dirlist(r'S:\STXM-data\Cryo-STXM\2018\guest\0111', '.hdf5')
    # dirlist(r'S:\STXM-data\Cryo-STXM\2018\guest\0111', 'C180111004')
    # dirlist(r'S:\STXM-data\Cryo-STXM\2018\guest\0111', '.hdf5', fname = 'C180111004')

    # dirs, files = dirlist_withdirs(r'S:\STXM-data\Cryo-STXM\2018\guest\0111', '.hdf5')
    # dirs, files = dirlist_withdirs(r'S:\STXM-data\Cryo-STXM\2018\guest\0111', 'C180111004')
    # dirs, files = dirlist_withdirs(r'S:\STXM-data\Cryo-STXM\2018\guest\0111', '.hdf5', fname='C180111004')

    # skip_lst = ['ui', 'sim_bkps', 'logs', '__pycache__', 'bl_configs', 'icons']
    # dirs = get_all_dirs('C:/controls/sandbox/pyStxm3/cls/applications/pyStxm', skip_lst=skip_lst)
    # #lst = merge_to_one_list(dirs)
    # for d in dirs:
    # 	print(d)
    skip_dir_lst = ["ui", "sim_bkps", "logs", "__pycache__", "bl_configs", "icons"]
    # dirs = get_all_files_and_subdirs('C:/controls/sandbox/pyStxm3/cls/applications/pyStxm', skip_lst=skip_dir_lst)
    # # for d in dirs:
    # # 	print(d)

    names = get_files_with_extension(
        "C:/controls/sandbox/pyStxm3/cls/applications/pyStxm",
        ext=".py",
        skip_lst=skip_dir_lst,
    )
    for d in names:
        print(d)


# __all__ = ['dirlist']
