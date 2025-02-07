"""
Created on Nov 30, 2016

@author: berg
"""

# standard names to use
# CNTR2PLOT_TYPE_ID = (
#     "type_id"  # to be used to indicate what kind of counter/scan is sending this info
# )
CNTR2PLOT_DETID = "det_id"
CNTR2PLOT_DETNAME = "det_name"
CNTR2PLOT_PROG_DCT = "prog_dct"
CNTR2PLOT_ROW = "row"  # a y position
CNTR2PLOT_COL = "col"  # an x position
CNTR2PLOT_VAL = "val"  # the point or array of data

# CNTR2PLOT_IMG_CNTR = "img_cntr"  # current image counter
# CNTR2PLOT_EV_CNTR = "ev_idx"  # current energy counter
CNTR2PLOT_SP_ID = "sp_id"  # spatial id this data belongs to
CNTR2PLOT_IS_POINT = "is_pxp"  # data is from a point by point scan
CNTR2PLOT_IS_LINE = "is_lxl"  # data is from a line by line scan
#CNTR2PLOT_SCAN_TYPE = "scan_type"  # the scan_type from types enum of this scan

#added for DCS server support
CNTR2PLOT_IS_PARTIAL = 'is_partial'
CNTR2PLOT_IS_TILED = 'is_tiled'



def make_counter_to_plotter_com_dct(row=None,
                                    col=None,
                                    val=None,
                                    is_point=True,
                                    prog_dct={},
                                    det_id=0,
                                    det_name=None,
                                    is_partial=False,
                                    is_tiled=False):
    """
    a function to be called by code that wants to pass the current counter information
    to a plotting widget so that it can be plotted.
    the values of this dct are to be filled out by the caller
        self._plot_dct[CNTR2PLOT_ROW] = int(dct["row"])
        self._plot_dct[CNTR2PLOT_COL] = int(dct["col"])
        self._plot_dct[CNTR2PLOT_VAL] = dct["data"]
        self._plot_dct[CNTR2PLOT_IS_LINE] = bool(dct["is_line"])
        self._plot_dct[CNTR2PLOT_IS_POINT] = bool(dct["is_point"])

        self.new_plot_data.emit(self._plot_dct)

    """
    dct = {}
    dct[CNTR2PLOT_ROW] = row  # a y position
    dct[CNTR2PLOT_COL] = col  # an x position
    dct[CNTR2PLOT_VAL] = val  # the point or array of data
    dct[CNTR2PLOT_IS_POINT] = is_point  # data is from a point by point scan
    dct[CNTR2PLOT_PROG_DCT] = prog_dct #if the device emitting the plot_dct contains a progress dictionary
    if is_point:
        dct[CNTR2PLOT_IS_LINE] = False  # data is from a line by line scan
    else:
        dct[CNTR2PLOT_IS_LINE] = True  # data is from a line by line scan

    dct[CNTR2PLOT_DETID] = det_id
    dct[CNTR2PLOT_DETNAME] = det_name
    dct[CNTR2PLOT_IS_PARTIAL] = is_partial
    dct[CNTR2PLOT_IS_TILED] = is_tiled
    return dct


def gen_complete_spec_chan_name(det_nm, sp_id, prefix='spid-'):
    """
    take the detector name and sp_id and create the standard channel name
    """
    #strip off the DNM_ if it exists
    det_nm = det_nm.replace("DNM_","")
    return(f"{det_nm}-{prefix}{sp_id}")

if __name__ == "__main__":
    pass
