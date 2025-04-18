"""
Created on Jan 16, 2017

@author: berg
"""
"""
a collection of utilities that are used to create a standard dictionary that is used to communicate with the scan_queue_table widget
 
"""
from cls.utils.dict_utils import dct_get, dct_put

PROG_DCT_ID = "PROG_DICT"
PROG_DCT_SPID = "PROG.SPID"
PROG_DCT_PERCENT = "PROG.PERCENT"
PROG_DCT_STATE = "PROG.STATE"
PROG_CUR_IMG_IDX = "PROG.CUR_IMG_IDX"


def make_progress_dict(sp_id=None, percent=0.0, cur_img_idx=0):
    """
    create a standard dict that is used to send information to the scan_q_view
    """

    dct = {}
    dct_put(dct, PROG_DCT_ID, PROG_DCT_ID)
    dct_put(dct, PROG_DCT_SPID, sp_id)
    dct_put(dct, PROG_DCT_PERCENT, percent)
    dct_put(dct, PROG_CUR_IMG_IDX, cur_img_idx)
    dct_put(dct, PROG_DCT_STATE, 0)

    return dct

def set_prog_dict(dct, sp_id=None, percent=0.0, cur_img_idx=0, ev_idx=0, pol_idx=0):
    dct["PROG"]["SPID"] = sp_id
    dct["PROG"]["PERCENT"] = percent
    dct["PROG"]["CUR_IMG_IDX"] = cur_img_idx
    dct["PROG"]["EV_IDX"] = ev_idx
    dct["PROG"]["POL_IDX"] = pol_idx

