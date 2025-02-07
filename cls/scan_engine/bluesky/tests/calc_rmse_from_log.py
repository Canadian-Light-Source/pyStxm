import numpy as np

from cls.utils.stats_utils import calc_rmse

def process_log(fname):

    with open(fname) as f:
        lines = f.readlines()

    dwells_arr = []
    err_arr = []
    prev_err = 0.0
    npnts = 0
    for l in lines:
        #[0,0] Done: dwell_time=0.047 sec delta actual=0.086 sec : ERROR = 0.039 ms
        if l.find("dwell_time=") > -1:
            idx1 = l.find("=") + 1
            idx2 = l.find(" sec")
            val = float(l[idx1:idx2])
            dwells_arr.append(val)

            idx_start = l.find("ERROR = ")
            l = l[idx_start:]
            idx1 = l.find("=") + 1
            idx2 = l.find("ms")
            val = float(l[idx1:idx2])
            if val > 1.0:
                val = prev_err
            prev_err = val
            err_arr.append(val)
            npnts += 1

    dwells_arr = np.array(dwells_arr)
    err_arr = np.array(err_arr)
    rmse = calc_rmse(dwells_arr, err_arr)
    av_dwells = np.average(dwells_arr)
    print("for npnts=%d av_dwells=%.3f rmse = %.3f" % (npnts, av_dwells, rmse))

def show_only_bs_msgs(fname):
    """
    |   seq_num |       time | det_intensity |
    +-----------+------------+---------------+
    |     15750 | 19:47:58.3 |             0 |
    """
    with open(fname) as f:
        lines = f.readlines()

    for l in lines:
        # [0,0] Done: dwell_time=0.047 sec delta actual=0.086 sec : ERROR = 0.039 ms
        if l[0] in ["|","+"]:
            print(l)

if __name__ == '__main__':
    fname = r'C:\controls\sandbox\pyStxm3\cls\scan_engine\bluesky\tests\sieman_star_log.txt'
    show_only_bs_msgs(fname)