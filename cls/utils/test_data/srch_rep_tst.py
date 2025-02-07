import pathlib


def extract_dev_name_from_line(l):
    term_chars = [".", ",", " ", ")"]
    l = l.strip()
    idx1 = l.find("DNM_")
    l = l[idx1:]
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


def fix_dnms(map_file):
    """
    ----------------------------------------
    Find '.device(DNM_' in 'C:\controls\sandbox\pyStxm3\cls\applications\pyStxm\bl_configs\basic\scan_plugins\coarse_image_scan\CoarseSampleImageScan.py' :
    C:\controls\sandbox\pyStxm3\cls\applications\pyStxm\bl_configs\basic\scan_plugins\coarse_image_scan\CoarseSampleImageScan.py('84'):             shutter = self.main_obj.device('DNM_SHUTTER')
    C:\controls\sandbox\pyStxm3\cls\applications\pyStxm\bl_configs\basic\scan_plugins\coarse_image_scan\CoarseSampleImageScan.py('125'):             mtr_x = self.main_obj.device('DNM_SAMPLE_X')
    C:\controls\sandbox\pyStxm3\cls\applications\pyStxm\bl_configs\basic\scan_plugins\coarse_image_scan\CoarseSampleImageScan.py('126'):             mtr_y = self.main_obj.device('DNM_SAMPLE_Y')
    C:\controls\sandbox\pyStxm3\cls\applications\pyStxm\bl_configs\basic\scan_plugins\coarse_image_scan\CoarseSampleImageScan.py('127'):             shutter = self.main_obj.device('DNM_SHUTTER')
    C:\controls\sandbox\pyStxm3\cls\applications\pyStxm\bl_configs\basic\scan_plugins\coarse_image_scan\CoarseSampleImageScan.py('374'):                 #scan_velo = self.get_mtr_max_velo('self.main_obj.device('DNM_SAMPLE_FINE_X')')
    Found '.device(DNM_' 5 time(s).

    """
    with open(map_file, "r") as f:
        lines = f.readlines()

    for l in lines:

        if l.find("Search complete") > -1:
            continue
        if l.find("Find ") > -1:
            continue
        if l.find("Found ") > -1:
            continue
        if l.find("-----") > -1:
            continue
        # ll is now ( file path and line num,  text to change)
        ll = l.split("):")

        ff = ll[0].split("(")
        # ff is now (filepath final, line num and ')'  )
        fpath = ff[0]

        lnum = int(ff[1].replace(")", "")) - 1
        if lnum == 742:
            print()

        dnm = extract_dev_name_from_line(ll[1])

        # open file to change
        try:
            fout = open(fpath, "r")
            outlines = fout.readlines()
            fout.close()
            if len(outlines) < lnum:
                print()
            if len(outlines) > 0:

                # outlines[lnum] = 'cx_pwr = self.main_obj.device('DNM_CX_AUTO_DISABLE_POWER', do_warn=False)'
                # #outlines[lnum] = outlines[lnum].replace('(', "('").replace(')',"')")
                # outlines[lnum] = outlines[lnum].replace('(%s' % dnm, "('%s')" % dnm)
                # outlines[lnum] = outlines[lnum].replace("''", "'")
                print(lnum)
                res = fix_line(outlines[lnum])
                if res:
                    outlines[lnum] = res
                    # output to disk
                    # newfpath = fpath + '.mod.py'
                    modfile = open(fpath, "w")
                    modfile.writelines(outlines)
                    modfile.close()
                    # for oline in outlines:
                    #     print(oline.replace('\n',''))
                    #
                    # print()
                    print("outputed [%s]" % fpath)
                else:
                    print()
        except IndexError:
            print()


def fix_line(l):
    # ll = l.replace('(%s' % dnm, "('%s')" % dnm)
    term_chars = [".", ",", " ", ")"]
    idx1 = l.find("DNM_")
    if idx1 > -1:
        ll = l[idx1:]
        rep_char = ""
        rep_idx = 100
        # find the term char that is at end of device name
        for t in term_chars:
            # ll = ll.replace(t, '|')
            idx2 = ll.find(t)
            if (idx2 < rep_idx) and (idx2 != -1):
                rep_idx = idx2
                rep_char = t

        # idx2 = l[idx1:].find(rep_char)
        dev_name = l[idx1 : idx1 + rep_idx]
        srch_str = "(%s" % dev_name
        rep_str = "('%s'" % dev_name  # + '%s' % (rep_char)
        lll = l.replace(srch_str, rep_str)
        return lll
    else:
        return None


if __name__ == "__main__":
    fix_dnms("C:/controls/sandbox/pyStxm3/cls/utils/test_data/fix_dnm_access.txt")
