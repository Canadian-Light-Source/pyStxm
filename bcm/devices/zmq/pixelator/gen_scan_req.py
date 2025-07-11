from cls.utils.roi_dict_defs import *

class GenScanRequestClass(object):
    """
    This class is used to generate the scanRequest dictionary for the pixelator
    It is used by the pixelator GUI to create the scanRequest dictionary
    """

    def __init__(self, app_to_dcs_devname_map):
        self.app_to_dcs_devname_map = app_to_dcs_devname_map

    def gen_axis_dict(self, roi, prioritize_center=False):
        """
        "axes": [
            {
                "nPoints": 10
                , "trajectories": [
                {
                    "start": 650.0
                    , "end": 680.0
                    , "range": 30.0
                    , "step": 3.3333333333333335
                    , "positionerName": "Energy"
                }
            ]
        Parameters
        ----------
        rois
    
        Returns
        -------
    
    
        """
    
        dct = {}
        dct["nPoints"] = roi[NPOINTS]
        dct["trajectories"] = []
        r = {}
        if prioritize_center:
            r["start"] = roi[CENTER] - (roi[RANGE] * 0.5)
            r["end"] = roi[CENTER] + (roi[RANGE] * 0.5)
            r["range"] = roi[RANGE]
            r["step"] = roi[RANGE] / roi[NPOINTS]
            r["center"] = roi[CENTER]
    
        else:
            r["start"] = roi[START]
            r["end"] = roi[STOP]
            r["range"] = roi[RANGE]
            r["step"] = roi[STEP]
            r["center"] = roi[CENTER]
    
        r["positionerName"] = self.app_to_dcs_devname_map[roi[POSITIONER]]
        dct["trajectories"].append(r)
    
        return dct
    
    def gen_axis_dicts(self, axis_str_lst, rois):
        dct = {}
        axis_zip = zip(axis_str_lst, rois)
        for axis_str, roi in axis_str_lst:
            dct[axis_str] = self.gen_axis_dict(roi)
    
        return dct
    
    def gen_regions(self, scan_type_str, dwell, parent, is_outer=False):
        """
        based on the scan type string call gen_region_dict to create the required regions
        for the scanRequest dictionary
        outer regions look like they can only be energy or polarization regions
    
        Parameters
        ----------
        scan_type_str
        dwell
        parent
        is_outer
        Returns
        -------
    
        """
        regions = []
        region_lst = []
        add_axes = False
        if scan_type_str in ["Detector", "OSA", "Motor2D", "Focus", "OSA Focus"]:
            # outer is dwell only, inner is X and Y
            if is_outer:
                region_lst = [parent.e]
            else:
                add_axes = True
                region_lst = [parent.y, parent.x]
        elif scan_type_str in ["Motor"]:
            region_lst = [parent.x]
            if not is_outer:
                add_axes = True
    
        elif scan_type_str in ["Sample"]:
            add_axes = True
            if is_outer:
                region_lst = parent.e
            else:
                region_lst = [parent.y, parent.x]
    
        regs = self.gen_region_dict(dwell, region_lst, add_axes, is_outer, scan_type_str=scan_type_str)
        if type(regs) == list:
            if not is_outer:
                for r in regs:
                    regions.append(r)
            else:
                regions = regs
        else:
            regions.append(regs)
        return regions
    
    def gen_region_dict(self, dwell: float, rois: [dict], add_axes=False, is_outer=False, scan_type_str='') -> dict:
        """
        generate a region dictionary that is used inside the scanRequest dictionary
        [
            {
                "dwellTime": 0.012500000000000001
                , "axes": [
                {
                    "nPoints": 10
                    , "trajectories": [
                    {
                        "start": 650.0
                        , "end": 680.0
                        , "range": 30.0
                        , "step": 3.3333333333333335
                        , "positionerName": "Energy"
                    }
                ]
                }
            ]
            }
        ]
    
        or if only 1 energy
    
        "outerRegions": [
            #         {
            #             "dwellTime": self.dwell_ms * 0.001
            #         }
            #     ]
    
        Parameters
        ----------
        dwell
        roi
    
        Returns
        -------
    
        """
        prioritize_center = False
        if scan_type_str.find('Focus') > -1:
            prioritize_center = True
    
        if len(rois) == 1 and (add_axes == False):
            # simply return a dict with dwell
            dct = {}
            dct["dwellTime"] = dwell
            return dct
        else:
            if is_outer:
                lst = []
                for roi in rois:
                    dct = {}
                    if is_outer:
                        dct["dwellTime"] = dwell
                    dct["axes"] = []
                    dct["axes"].append(self.gen_axis_dict(roi, prioritize_center=prioritize_center))
                    lst.append(dct)
                return lst
            else:
                #inner
                dct = {}
                dct["axes"] = []
                for roi in rois:
                    dct["axes"].append(self.gen_axis_dict(roi, prioritize_center=prioritize_center))
                return dct
    
    def gen_displayed_axis_dict(self, inner=True, index=0):
        if inner:
            region_str = "inner"
        else:
            region_str = "outer"
    
        dct = {}
        dct["region"] = region_str
        dct["index"] = index
        return dct
    
    def gen_displayed_axis_dicts(self, axis_str_lst, axis_rois, inner_outer_lst):
        dct = {}
        axis_zip = zip(axis_str_lst, axis_rois,inner_outer_lst)
        index = 0
        for axis_str, roi, inout in axis_zip:
            dct[axis_str] = self.gen_displayed_axis_dict(inout, index)
            index += 1
        return dct
    
    def gen_point_displayed_axis_dicts(self, axis_str_lst, axis_rois, inner_outer_lst):
        dct = {}
        axis_zip = zip(axis_str_lst, axis_rois,inner_outer_lst)
        index = -1
        for axis_str, roi, inout in axis_zip:
            dct[axis_str] = self.gen_displayed_axis_dict(inout, index)
            index += 1
        return dct
    
    def gen_base_req_structure(self, scan_type_str: str) -> dict:
        """
        Create a base scnRequest dictionary then use other code to populate it
        Returns dict
        -------
        """
        if scan_type_str == "OSA Focus":
            from bcm.devices.zmq.pixelator.scan_reqs.osa_focus_req import scanRequest as scan_request
        elif scan_type_str == "Detector":
            from bcm.devices.zmq.pixelator.scan_reqs.det_scan_req import scanRequest as scan_request
        elif scan_type_str == "OSA":
            from bcm.devices.zmq.pixelator.scan_reqs.osa_req import scanRequest as scan_request
        elif scan_type_str == "Focus":
            from bcm.devices.zmq.pixelator.scan_reqs.focus_req import scanRequest as scan_request
        elif scan_type_str == "Motor2D":
            from bcm.devices.zmq.pixelator.scan_reqs.motor_2D_req import scanRequest as scan_request
        elif scan_type_str == "Motor":
            from bcm.devices.zmq.pixelator.scan_reqs.motor_scan_req import scanRequest as scan_request
        else:
            scan_request = {
                "scanType": "",
                "spatialType": "",
                "meander": 0,
                "yAxisFast": 0,
                "osaInFocus": 0,
                "lineMode": "",
                "outerRegions": [],
                "innerRegions": [],
                "nOuterRegions": 0,
                "nInnerRegions": 0,
                "displayedAxes": {},
                "accelerationDistance": 0.0,
                "tileDelay": 0.0,
                "lineDelay": 0.0,
                "pointDelay": 0.0,
                "lineRepetition": 1,
                "singleOuterRegionValue": 0,
    
    
            }
        return scan_request
    
    def convert_positioner_name(self, roi: dict) -> str:
        """
           this should also convert the pyStxm positioner name ot one pixelator knows
    
            AxisName=BeamShutter
            AxisName=SampleX
            AxisName=SampleY
            AxisName=DetectorX
            AxisName=DetectorY
            AxisName=DetectorZ
            AxisName=Energy
            AxisName=SampleX
            AxisName=SampleY
            AxisName=ID1Off
            AxisName=ID2Off
            AxisName=MoenchNumFrames
            AxisName=OSAX
            AxisName=OSAY
            AxisName=Polarization
            AxisName=Zoneplate
    
    
           Parameters
           ----------
           posner_nm
    
           Returns
           -------
    
        """
        posner_nm = roi[POSITIONER]
        if posner_nm.find('SAMPLE') > -1:
            # need to find out if scan is coarse or fine and use the coarse or fine positioner names
            if roi['SCAN_RES'] == 'FINE':
                posner_nm = posner_nm.replace('SAMPLE_','')
            else:
                posner_nm = posner_nm.replace('SAMPLE', 'COARSE')
    
        nm = posner_nm.replace('DNM_','')
        words = nm.replace('_', ' ').replace('-', ' ').split()
        if len(words) > 1:
            if words[0].find('OSA') > -1:
                camel_case_str = ''.join(word for word in words)
            else:
                camel_case_str = ''.join(word.capitalize() for word in words)
        else:
            camel_case_str = words[0].capitalize()
        #nm = nm.replace('_','')
        return camel_case_str
    
    def make_base_energy_region(self, e_roi, app_to_dcs_devname_map):
        dct = {
            "dwellTime": e_roi['DWELL'] * 0.001,
            "axes": [
                {
                    "nPoints": e_roi['NPOINTS'],
                    "trajectories": [
                        {
                            "start": e_roi['START'],
                            "end": e_roi['STOP'],
                            "range": e_roi['RANGE'],
                            "step": e_roi['STEP'],
                            "positionerName": self.app_to_dcs_devname_map['DNM_ENERGY']
                        }
                    ]
                }
            ]
        }
        return dct
    
    def make_point_spatial_region(self, sp_roi_0, sp_roi_1, app_to_dcs_devname_map):
        dct = {
                "axes": [
                    {
                        "nPoints": sp_roi_0['NPOINTS'],
                        "trajectories": [
                            {
                                "center": sp_roi_0['CENTER'],
                                "range": sp_roi_0['RANGE'],
                                "positionerName": self.app_to_dcs_devname_map[sp_roi_0['POSITIONER']]
                            },
                            {
                                "center": sp_roi_1['CENTER'],
                                "range": sp_roi_1['RANGE'],
                                "positionerName": self.app_to_dcs_devname_map[sp_roi_1['POSITIONER']]
                            }
                        ]
                    }
                ]
            }
        return dct


if __name__ == '__main__':
    from gen_region_data import parent_e, parent_x, parent_y, sp_db, wdg_com
    from PyQt5.QtCore import QObject
    from cls.utils.roi_utils import wdg_to_sp, get_sp_roi_dct_from_wdg_com

    parent = QObject()
    parent.e = parent_e
    parent.x = parent_x
    parent.y = parent_y
    sp_roi_dct = get_sp_roi_dct_from_wdg_com(wdg_com, sp_id=None)
    outer_regs = []
    inner_regs = []
    for e_roi in parent_e:
        outer_regs.append(make_base_energy_region(e_roi))

    for spid, sp_dct in sp_roi_dct.items():
        inner_regs.append(make_point_spatial_region(sp_dct['X'], sp_dct['Y']))

    print(inner_regs)