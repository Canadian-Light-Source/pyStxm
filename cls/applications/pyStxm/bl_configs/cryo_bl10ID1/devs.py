SIM = False
dev_dct = {}
dev_dct["POSITIONERS"] = [
    {
        "name": "DNM_SAMPLE_FINE_X",
        "desc": "Fine_X",
        "class": "e712_sample_motor",
        "dcs_nm": "IOC:m100",
        "pos_type": "POS_TYPE_ES",
        "sim": "False",
    },
    {
        "name": "DNM_SAMPLE_FINE_Y",
        "desc": "Fine_Y",
        "class": "e712_sample_motor",
        "dcs_nm": "IOC:m101",
        "pos_type": "POS_TYPE_ES",
        "sim": "False",
    },
    {
        "name": "DNM_OSA_X",
        "desc": "OSA_X",
        "class": "MotorQt",
        "dcs_nm": "IOC:m104",
        "pos_type": "POS_TYPE_ES",
        "sim": "False",
    },
    {
        "name": "DNM_OSA_Y",
        "desc": "OSA_Y",
        "class": "MotorQt",
        "dcs_nm": "IOC:m105",
        "pos_type": "POS_TYPE_ES",
        "sim": "False",
    },
    {
        "name": "DNM_OSA_Z",
        "desc": "OSA_Z",
        "class": "MotorQt",
        "dcs_nm": "IOC:m106C",
        "pos_type": "POS_TYPE_ES",
        "sim": "False",
    },
    {
        "name": "DNM_OSA_Z_BASE",
        "desc": "OSA_Z",
        "class": "MotorQt",
        "dcs_nm": "IOC:m106",
        "pos_type": "POS_TYPE_ES",
        "sim": "False",
    },
    {
        "name": "DNM_ZONEPLATE_Z",
        "Zoneplate_Z": "FineX",
        "class": "MotorQt",
        "dcs_nm": "IOC:m111C",
        "pos_type": "POS_TYPE_ES",
        "sim": "False",
    },
    {
        "name": "DNM_ZONEPLATE_Z_BASE",
        "Zoneplate_Z": "FineX",
        "class": "MotorQt",
        "dcs_nm": "IOC:m111",
        "pos_type": "POS_TYPE_ES",
        "sim": "False",
    },
    {
        "name": "DNM_COARSE_X",
        "desc": "Coarse_X",
        "class": "MotorQt",
        "dcs_nm": "IOC:m112",
        "pos_type": "POS_TYPE_ES",
        "sim": "False",
    },
    {
        "name": "DNM_COARSE_Y",
        "desc": "Coarse_Y",
        "class": "MotorQt",
        "dcs_nm": "IOC:m113",
        "pos_type": "POS_TYPE_ES",
        "sim": "False",
    },
    # {
    #     "name": "DNM_COARSE_Z",
    #     "desc": "Coarse_Z",
    #     "class": "MotorQt",
    #     "dcs_nm": "SIM",
    #     "pos_type": "POS_TYPE_ES",
    #     "sim": "True",
    # },
    {
        "name": "DNM_DETECTOR_X",
        "desc": "Detector_X",
        "class": "MotorQt",
        "dcs_nm": "IOC:m114",
        "pos_type": "POS_TYPE_ES",
        "sim": "False",
    },
    {
        "name": "DNM_DETECTOR_Y",
        "desc": "Detector_Y",
        "class": "MotorQt",
        "dcs_nm": "IOC:m115",
        "pos_type": "POS_TYPE_ES",
        "sim": "False",
    },
    {
        "name": "DNM_DETECTOR_Z",
        "desc": "Detector_Z",
        "class": "MotorQt",
        "dcs_nm": "IOC:m116",
        "pos_type": "POS_TYPE_ES",
        "sim": "False",
    },
    {
        "name": "DNM_SAMPLE_X",
        "desc": "Sample_X",
        "class": "sample_abstract_motor",
        "dcs_nm": "IOC:m117",
        "pos_type": "POS_TYPE_ES",
        "fine_mtr_name": "DNM_SAMPLE_FINE_X",
        "coarse_mtr_name": "DNM_COARSE_X",
        "sim": "False",
    },
    {
        "name": "DNM_SAMPLE_Y",
        "desc": "Sample_Y",
        "class": "sample_abstract_motor",
        "dcs_nm": "IOC:m118",
        "pos_type": "POS_TYPE_ES",
        "fine_mtr_name": "DNM_SAMPLE_FINE_Y",
        "coarse_mtr_name": "DNM_COARSE_Y",
        "sim": "False",

    },
    {
        "name": "DNM_ENERGY",
        "desc": "Energy",
        "class": "MotorQt",
        "dcs_nm": "SIM_VBL1610-I12:ENERGY" if SIM else "BL1610-I10:ENERGY",
        # "dcs_nm": "SIM_VBL1610-I12:ENERGY",
        # "dcs_nm": "BL1610-I10:ENERGY",
        "abstract_mtr": True,
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_SLIT_X",
        "desc": "Slit_X",
        "class": "MotorQt",
        "dcs_nm": "SIM_VBL1610-I12:slitX" if SIM else "BL1610-I10:slitX",
        # "dcs_nm": "BL1610-I10:slitX",
        "abstract_mtr": True,
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "DNM_SLIT_Y",
        "desc": "Slit_Y",
        "class": "MotorQt",
        "dcs_nm": "SIM_VBL1610-I12:slitY" if SIM else "BL1610-I10:slitY",
        # "dcs_nm": "BL1610-I10:slitY",
        "abstract_mtr": True,
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "DNM_M3_PITCH",
        "desc": "M3_Pitch",
        "class": "MotorQt",
        "dcs_nm": "SIM_VBL1610-I12:m3STXMPitch" if SIM else "BL1610-I10:m3STXMPitch",
        # "dcs_nm": "BL1610-I10:m3STXMPitch",
        "abstract_mtr": True,
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "DNM_EPU_GAP",
        "desc": "Epu_Gap",
        "class": "MotorQt",
        "dcs_nm": "SIM_VBL1610-I12:epuGap" if SIM else "BL1610-I10:epuGap",
        # "dcs_nm": "BL1610-I10:epuGap",
        "abstract_mtr": True,
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "DNM_EPU_OFFSET",
        "desc": "Epu_Offset",
        "class": "MotorQt",
        "dcs_nm": "SIM_VBL1610-I12:epuOffset" if SIM else "BL1610-I10:epuOffset",
        # "dcs_nm": "BL1610-I10:epuOffset",
        "abstract_mtr": True,
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "DNM_EPU_HARMONIC",
        "desc": "Epu_Harmonic",
        "class": "MotorQt",
        "dcs_nm": "SIM_VBL1610-I12:epuHarmonic" if SIM else "BL1610-I10:epuHarmonic",
        # "dcs_nm": "BL1610-I10:epuHarmonic",
        "abstract_mtr": True,
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "DNM_EPU_POLARIZATION",
        "desc": "Polarization",
        "class": "MotorQt",
        "dcs_nm": "SIM_VBL1610-I12:epuPolarization" if SIM else "BL1610-I10:epuPolarization",
        # "dcs_nm": "BL1610-I10:epuPolarization",
        "abstract_mtr": True,
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "DNM_EPU_ANGLE",
        "desc": "Epu_Angle",
        "class": "MotorQt",
        "dcs_nm": "SIM_VBL1610-I12:epuAngle" if SIM else "BL1610-I10:epuAngle",
        # "dcs_nm": "BL1610-I10:epuAngle",
        "abstract_mtr": True,
        "pos_type": "POS_TYPE_BL",
    },
     {
        "name": "DNM_GONI_X",
        "desc": "GONI_X",
        "class": "MotorQt",
        "dcs_nm": "IOC:m107",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_GONI_Y",
        "desc": "GONI_Y",
        "class": "MotorQt",
        "dcs_nm": "IOC:m108",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_GONI_Z",
        "desc": "GONI_Z",
        "class": "MotorQt",
        "dcs_nm": "IOC:m109",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_GONI_THETA",
        "desc": "GONI_THETA",
        "class": "MotorQt",
        "dcs_nm": "IOC:m110",
        "pos_type": "POS_TYPE_ES",
    },
]

dev_dct["DIO"] = [
    {
        "name": "DNM_SHUTTER",
        "class": "DCSShutter",
        "dcs_nm": "ASTXM1610:Dio:shutter:ctl" if SIM else "uhvDIO:shutter:ctl",
        "ctrl_enum_strs": ["Auto", "Open", "Close"],
        "fbk_enum_strs": ["CLOSED", "OPEN"],
        "fbk_enum_values": [0, 1]
    },
    {
        "name": "DNM_SHUTTERTASKRUN",
        "class": "make_basedevice",
        # "dcs_nm": "ASTXM1610:Dio:shutter:Run",
        "dcs_nm": "uhvDIO:shutter:Run",
    },
]

# dev_dct["DETECTORS"] = [
#     # {'name': 'DNM_COUNTER_APD', 'class': 'PointDetectorDevice', 'dcs_nm': 'CSTXM1610:Ci:counter:', 'name': 'DNM_COUNTER_APD', 'scale_val': 1.0, 'con_chk_nm': 'Run'},
#     # {
#     #     "name": "DNM_COUNTER_APD",
#     #     "class": "PointDetectorDevice",
#     #     "dcs_nm": "CSTXM1610:Ci:counter:",
#     #     "name": "DNM_COUNTER_APD",
#     #     "scale_val": 1.0,
#     #     "con_chk_nm": "Run",
#     # },
#     {
#         "name": "DNM_DEFAULT_COUNTER",
#         "class": "PointDetectorDevice",
#         "dcs_nm": "CSTXM1610:Ci-D1C0:cntr:",
#         "name": "DNM_DEFAULT_COUNTER",
#         "scale_val": 1.0,
#         "con_chk_nm": "Run",
#     },
#     {
#         "name": "DNM_PMT",
#         "class": "make_basedevice",
#         "dcs_nm": "CSTXM1610:Ci-D1C2:cntr:SingleValue_RBV",
#     },
#     # {
#     #     "name": "DNM_POINT_DET",
#     #     "class": "PointDetectorDevice",
#     #     "dcs_nm": "CSTXM1610:Ci:counter:",
#     #     "name": "DNM_POINT_DET",
#     #     "scale_val": 500.0,
#     #     "con_chk_nm": "Run",
#     # },
#     # {
#     #     "name": "DNM_LINE_DET_FLYER",
#     #     "class": "LineDetectorFlyerDevice",
#     #     "dcs_nm": "CSTXM1610:Ci:counter:",
#     #     "con_chk_nm": "Run",
#     #     "stream_names": {"line_det_strm": "primary"},
#     #     "monitor_attrs": ["waveform_rbv"],
#     #     "pivot": True,
#     # },
#     # {
#     #     "name": "DNM_LINE_DET",
#     #     "class": "LineDetectorDevice",
#     #     "dcs_nm": "CSTXM1610:Ci:counter:",
#     #     "name": "DNM_LINE_DET",
#     #     "con_chk_nm": "Run",
#     # },
# {
#         "name": "DNM_LINE_DET_FLYER",
#         "class": "LineDetectorFlyerDevice",
#         "dcs_nm": "CSTXM1610:Ci-D1C0:cntr:",
#         "con_chk_nm": "Run",
#         "stream_names": {"line_det_strm": "primary"},
#         "monitor_attrs": ["waveform_rbv"],
#         "pivot": True,
#     },
#     {
#         "name": "DNM_LINE_DET",
#         "class": "LineDetectorDevice",
#         "dcs_nm": "CSTXM1610:Ci-D1C0:cntr:",
#         "name": "DNM_LINE_DET",
#         "con_chk_nm": "Run",
#     },
#     {"name": "DNM_SIM_DET1", "class": "det1"},
#     {"name": "DNM_SIM_DET2", "class": "det2"},
#     {"name": "DNM_SIM_DET3", "class": "det3"},
#     {"name": "DNM_SIM_NOISYDET", "class": "noisy_det"},
#     {"name": "SIM_LINE_DET_1", "class": "SimLineDetectorDevice", "dcs_nm": "CSTXM1610:Ci:counter1:"},
#     {"name": "SIM_LINE_DET_2", "class": "SimLineDetectorDevice", "dcs_nm": "CSTXM1610:Ci:counter2:"},
#     {"name": "SIM_LINE_DET_3", "class": "SimLineDetectorDevice", "dcs_nm": "CSTXM1610:Ci:counter3:"},
#     {"name": "SIM_LINE_DET_4", "class": "SimLineDetectorDevice", "dcs_nm": "CSTXM1610:Ci:counter4:"},
#     {"name": "SIM_LINE_DET_5", "class": "SimLineDetectorDevice", "dcs_nm": "CSTXM1610:Ci:counter5:"},
#     {"name": "SIM_LINE_DET_FLYER_1", "class": "SimLineDetectorFlyerDevice", "dcs_nm": "CSTXM1610:Ci:counter11:","stream_names": {"line_fly_strm_1": "primary_1"}},
#     {"name": "SIM_LINE_DET_FLYER_2", "class": "SimLineDetectorFlyerDevice", "dcs_nm": "CSTXM1610:Ci:counter12:","stream_names": {"line_fly_strm_2": "primary_2"}},
#     {"name": "SIM_LINE_DET_FLYER_3", "class": "SimLineDetectorFlyerDevice", "dcs_nm": "CSTXM1610:Ci:counter13:","stream_names": {"line_fly_strm_3": "primary_3"}},
#     {"name": "SIM_LINE_DET_FLYER_4", "class": "SimLineDetectorFlyerDevice", "dcs_nm": "CSTXM1610:Ci:counter14:","stream_names": {"line_fly_strm_4": "primary_4"}},
#     {"name": "SIM_LINE_DET_FLYER_5", "class": "SimLineDetectorFlyerDevice", "dcs_nm": "CSTXM1610:Ci:counter15:","stream_names": {"line_fly_strm_5": "primary_5"}},
# ]

dev_dct["DETECTORS"] = [
    # daqmx_dev1 = DAQmxCounter("CSTXM1610:Ci-D2C0:cntr:", name='COUNTER_0', stream_names={"line_fly_strm_1": "primary"})
    # pxp_trig_src_pfi=3 #PFI for triggering point by point
    # lxl_trig_src_pfi=4 #PFI for triggering line by line
    # ci_clk_src_gate_pfi = 15 #PFI for the line gate
    # gate_clk_src_gate_pfi = 8 #PFI for the gate src clock
    # sig_src_term_pfi = 8 #PFI for pmt signal input

    # {
    #     "name": "DNM_DEFAULT_COUNTER",
    #     "class": "DAQmxCounter",
    #     "dcs_nm": "CSTXM1610:Ci-D1C0:cntr:",
    #     "scale_val": 1.0,
    #     "con_chk_nm": "Run",
    #     "stream_names": {"line_det_strm": "primary"},
    #     "pxp_trig_src_pfi": 3, #PFI for triggering point by point
    #     "lxl_trig_src_pfi": 4, #PFI for triggering line by line
    #     "ci_clk_src_gate_pfi": 15, #PFI for the line gate
    #     "gate_clk_src_gate_pfi": 8, #PFI for the gate src clock
    #     "sig_src_term_pfi":  8, #PFI for pmt signal input
    # },

    {
        "name": "DNM_SIS3820",
        "class": "SIS3820ScalarDevice",
        "dcs_nm": "MCS1610-310-01:",
        "con_chk_nm": "mcs:startScan",
        "sim": "False",
     },
    {
        "name": "DNM_PMT",
        "class": "make_basedevice",
        #"dcs_nm": "MCS1610-310-02:mcs09:fbk",
        #"dcs_nm": "CSTXM1610:Ci-D1C2:cntr:SingleValue_RBV",
        "dcs_nm": "uhvPMT:ctr:SingleValue_RBV",
        "sim": "False",
    },
    {
        "name": "DNM_CALIB_CAMERA_CLIENT",
        "class": "camera",
        "dcs_nm": "CCD1610-I10:uhv",
        "sim": "False",
    },

    # {
    #     "name": "DNM_TUCSEN_AD",
    #     "class": "TucsenDetector",
    #     "dcs_nm": "SCMOS1610-310:",
    #     "sim": "True",
    #  },
    # {
    #     "name": "DNM_SIM_CCD",
    #     "class": "SimDetector",
    #     "dcs_nm": "SIMCCD1610-I10-02:",
    # },

#     {"name": "DNM_SIM_DET1", "class": "det1"},
#     {"name": "DNM_SIM_DET2", "class": "det2"},
#     {"name": "DNM_SIM_DET3", "class": "det3"},
#     {"name": "DNM_SIM_NOISYDET", "class": "noisy_det"},
#     {"name": "SIM_LINE_DET_1", "class": "SimLineDetectorDevice", "dcs_nm": "CSTXM1610:Ci:counter1:"},
#     {"name": "SIM_LINE_DET_2", "class": "SimLineDetectorDevice", "dcs_nm": "CSTXM1610:Ci:counter2:"},
#     {"name": "SIM_LINE_DET_3", "class": "SimLineDetectorDevice", "dcs_nm": "CSTXM1610:Ci:counter3:"},
#     {"name": "SIM_LINE_DET_4", "class": "SimLineDetectorDevice", "dcs_nm": "CSTXM1610:Ci:counter4:"},
#     {"name": "SIM_LINE_DET_5", "class": "SimLineDetectorDevice", "dcs_nm": "CSTXM1610:Ci:counter5:"},
#     {"name": "SIM_LINE_DET_FLYER_1", "class": "SimLineDetectorFlyerDevice", "dcs_nm": "CSTXM1610:Ci:counter11:","stream_names": {"line_fly_strm_1": "primary_1"}},
#     {"name": "SIM_LINE_DET_FLYER_2", "class": "SimLineDetectorFlyerDevice", "dcs_nm": "CSTXM1610:Ci:counter12:","stream_names": {"line_fly_strm_2": "primary_2"}},
#     {"name": "SIM_LINE_DET_FLYER_3", "class": "SimLineDetectorFlyerDevice", "dcs_nm": "CSTXM1610:Ci:counter13:","stream_names": {"line_fly_strm_3": "primary_3"}},
#     {"name": "SIM_LINE_DET_FLYER_4", "class": "SimLineDetectorFlyerDevice", "dcs_nm": "CSTXM1610:Ci:counter14:","stream_names": {"line_fly_strm_4": "primary_4"}},
#     {"name": "SIM_LINE_DET_FLYER_5", "class": "SimLineDetectorFlyerDevice", "dcs_nm": "CSTXM1610:Ci:counter15:","stream_names": {"line_fly_strm_5": "primary_5"}},
]

dev_dct["PVS"] = [
    {
        "name": "DNM_FINE_ACCEL_DIST_PRCNT",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "SIM_FINEIMAGE:ACCEL_DIST_PRCNT",
        "sim": "False",
    },
    {
        "name": "DNM_FINE_DECCEL_DIST_PRCNT",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "SIM_FINEIMAGE:DECCEL_DIST_PRCNT",
        "sim": "False",
    },
    {
        "name": "DNM_CRS_ACCEL_DIST_PRCNT",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "SIM_COARSEIMAGE:ACCEL_DIST_PRCNT",
        "sim": "False",
    },
    {
        "name": "DNM_CRS_DECCEL_DIST_PRCNT",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "SIM_COARSEIMAGE:DECCEL_DIST_PRCNT",
        "sim": "False",
    },
    {
        "name": "DNM_CALCD_ZPZ",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "BL1610-I10:ENERGY:uhv:zp:fbk:tr.I",
        "sim": "False",
    },
    {
        "name": "DNM_RESET_INTERFERS",
        "class": "Bo",
        "cat": "PVS",
        "dcs_nm": "PSMTR1610-3-I12-00:reset_interfers",
        "sim": "False",
    },
    {
        "name": "DNM_SFX_AUTOZERO",
        "class": "Bo",
        "cat": "PVS",
        "dcs_nm": "IOC:m100:AutoZero",
        "sim": "False",
    },
    {
        "name": "DNM_SFY_AUTOZERO",
        "class": "Bo",
        "cat": "PVS",
        "dcs_nm": "IOC:m101:AutoZero",
        "sim": "False",
    },
    {
        "name": "DNM_ZPZ_ADJUST",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "BL1610-I10:ENERGY:uhv:zp:adjust_zpz",
        "sim": "False",
    },
    {
        "name": "DNM_ZONEPLATE_SCAN_MODE",
        "class": "Mbbo",
        "dcs_nm": "BL1610-I10:ENERGY:uhv:zp:scanselflag",
        "sim": "False",
    },
    # used to control which value gets sent to Zpz, fl or fl - A0
    # {'name': 'DNM_ZONEPLATE_INOUT', 'class': 'Bo', 'dcs_nm': 'BL1610-I12:zp_inout'},
    # {'name': 'DNM_ZONEPLATE_INOUT_FBK', 'class': 'Mbbi', 'dcs_nm': 'BL1610-I10:ENERGY:uhv:zp_inout:fbk'},
    # used to convieniently move zp z in and out
    {
        "name": "DNM_DELTA_A0",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "BL1610-I10:ENERGY:uhv:delta_A0",
        "sim": "False",
    },
    {
        "name": "DNM_IDEAL_A0",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "BL1610-I10:ENERGY:uhv:zp:fbk:tr.K",
        "sim": "False",
    },
    {
        "name": "DNM_CALCD_ZPZ",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "BL1610-I10:ENERGY:uhv:zp:fbk:tr.I",
        "sim": "False",
    },
    {
        "name": "DNM_ZPZ_ADJUST",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "BL1610-I10:ENERGY:uhv:zp:adjust_zpz",
        "sim": "False",
    },
    {
        "name": "DNM_FOCAL_LENGTH",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "BL1610-I10:ENERGY:uhv:zp:FL",
        "units": "um",
        "sim": "False",
    },
    {
        "name": "DNM_A0",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "BL1610-I10:ENERGY:uhv:A0",
        "sim": "False",
    },
    {
        "name": "DNM_A0MAX",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "BL1610-I10:ENERGY:uhv:A0Max",
        "sim": "False",
    },
    # {'name': 'DNM_A0_FOR_CALC', 'class': 'make_basedevice', 'cat': 'PVS', 'dcs_nm': 'BL1610-I10:ENERGY:uhv:A0:for_calc'},
    {
        "name": "DNM_ZPZ_POS",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "BL1610-I10:ENERGY:uhv:zp:zpz_pos",
        "sim": "False",
    },
    {
        "name": "DNM_ENERGY_ENABLE",
        "class": "Bo",
        "dcs_nm": "BL1610-I10:ENERGY:uhv:enabled",
        "sim": "False",
    },
    {
        "name": "DNM_ENERGY_RBV",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "BL1610-I10:ENERGY.RBV",
        "units": "um",
        "sim": "False",
    },
    {
        "name": "DNM_ZPZ_RBV",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "SMTR1610-3-I12-51.RBV",
        "units": "um",
        "sim": "False",
    },
    {
        "name": "DNM_ZP_DEF_A",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "BL1610-I10:ENERGY:uhv:zp:def.A",
        "sim": "False",
    },
    {
        "name": "DNM_ZP_DEF",
        "class": "Transform",
        "cat": "PVS",
        "dcs_nm": "BL1610-I10:ENERGY:uhv:zp:def",
        "sim": "False",
    },
    {
        "name": "DNM_OSA_DEF",
        "class": "Transform",
        "cat": "PVS",
        "dcs_nm": "BL1610-I10:ENERGY:uhv:osa:def",
        "sim": "False",
    },
    {
        "name": "DNM_SYSTEM_MODE_FBK",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "SYSTEM:mode:fbk",
        "sim": "False",
    },
    {
        "name": "DNM_SRSTATUS_SHUTTERS",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "SRStatus:shutters",
        "sim": "False",
    },
    # {'name': 'DNM_EPU_POL_FBK',  'class': 'Mbbo', 'dcs_nm': 'BL1610-I12UND1410-01:polarization'},
    # {'name': 'DNM_EPU_POL_ANGLE',  'class': 'make_basedevice', 'cat': 'PVS', 'dcs_nm': 'BL1610-I12:UND1410-01:polarAngle', 'units': 'udeg'},
    # {'name': 'DNM_EPU_GAP_FBK',  'class': 'make_basedevice', 'cat': 'PVS', 'dcs_nm': 'BL1610-I12:UND1410-01:gap:mm:fbk', 'units': 'mm'},
    # {'name': 'DNM_EPU_GAP_OFFSET',  'class': 'make_basedevice', 'cat': 'PVS', 'dcs_nm': 'BL1610-I12:UND1410-01:gap:offset', 'units': 'mm'},
    # {'name': 'DNM_EPU_HARMONIC_PV',  'class': 'make_basedevice', 'cat': 'PVS', 'dcs_nm': 'BL1610-I12:UND1410-01:harmonic'},
    # {'name': 'DNM_SYSTEM_MODE_FBK',  'class': 'Mbbi', 'dcs_nm': 'BL1610-I12SYSTEM:mode:fbk'},
    # {'name': 'DNM_EPU_POL_FBK',  'class': 'make_basedevice', 'dcs_nm': 'SIM_VBL1610-I12:epuPolarization.RBV', 'rd_only': True},
    # {'name': 'DNM_EPU_POL_ANGLE',  'class': 'make_basedevice', 'cat': 'PVS', 'dcs_nm': 'BLUND1410-01:polarAngle', 'units': 'udeg'},
    # {'name': 'DNM_EPU_GAP_FBK',  'class': 'make_basedevice', 'cat': 'PVS', 'dcs_nm': 'SIM_VBL1610-I12:epuGap', 'units': 'mm', 'rd_only': True},
    # {'name': 'DNM_EPU_GAP_OFFSET',  'class': 'make_basedevice', 'cat': 'PVS', 'dcs_nm': 'SIM_VBL1610-I12:epuOffset', 'units': 'mm'},
    # {'name': 'DNM_EPU_HARMONIC_PV',  'class': 'make_basedevice', 'cat': 'PVS', 'dcs_nm': 'SIM_VBL1610-I12:epuHarmonic'},
    #    {'name': 'DNM_SYSTEM_MODE_FBK',  'class': 'Mbbi', 'dcs_nm': 'BL1610-I12SYSTEM:mode:fbk'},
    {
        "name": "DNM_MONO_EV_FBK",
        "class": "make_basedevice",
        "cat": "PVS",
        #"dcs_nm": "SIM_SM01PGM01:ENERGY_MON",
        "dcs_nm": "SM01PGM01:ENERGY_MON",
        "units": "eV",
        "rd_only": True,
        "sim": "False",
    },
    {
        "name": "DNM_BEAM_DEFOCUS",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "BL1610-I10:ENERGY:uhv:zp:defocus",
        "units": "um",
        "sim": "False",
    },
    {
        "name": "DNM_AX1_INTERFER_VOLTS",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "uhvAi:ai:ai0_RBV",
        "rd_only": True,
        "sim": "False",
    },
    {
        "name": "DNM_SFX_PIEZO_VOLTS",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "IOC:m100:OutputVolt_RBV",
        "rd_only": True,
        "sim": "False",
    },
    {
        "name": "DNM_SFY_PIEZO_VOLTS",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "IOC:m101:OutputVolt_RBV",
        "rd_only": True,
        "sim": "False",
    },
    {
        "name": "DNM_AX2_INTERFER_VOLTS",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "uhvAi:ai:ai1_RBV",
        "rd_only": True,
        "sim": "False",
    },
    {
        "name": "DNM_RING_CURRENT",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "PCT1402-01:mA:fbk",
        "units": "mA",
        "sim": "False",
    },
    {
        "name": "DNM_BASELINE_RING_CURRENT",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "PCT1402-01:mA:fbk",
        "units": "mA",
        "sim": "False",
    },
    # {
    #     "name": "DNM_DFLT_PMT_DWELL",
    #     "class": "make_basedevice",
    #     "cat": "PVS",
    #     "dcs_nm": "MCS1610-310-02:mcs:delay",
    #     "sim": "True",
    # },
    # _pv: BaseDevice('BL1610-I12:MONO1610-I10-01:grating:select:fbk'}, _pv.get_position: _pv.get_enum_str_as_int[{'name': 'Mono_grating_fbk',  'class': _pv
]

dev_dct["PVS_DONT_RECORD"] = [
    {
        "name": "DNM_TICKER",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "TRG2400:cycles",
        "units": "counts",
        "sim": "False",
    }
]

dev_dct["HEARTBEATS"] = [
    # {
    #     "name": "DNM_BLAPI_HRTBT",
    #     "class": "Bo",
    #     "dcs_nm": "CSTXM1610:BlApi:hrtbt:alive",
    #     "desc": "BlApiApp",
    # },
    # {
    #     "name": "DNM_AI_HRTBT",
    #     "class": "Bo",
    #     "dcs_nm": "CSTXM1610:Ai:hrtbt:alive",
    #     "desc": "AnalogInputApp",
    # },
    # {
    #     "name": "DNM_CI_HRTBT",
    #     "class": "Bo",
    #     "dcs_nm": "CSTXM1610:Ci:hrtbt:alive",
    #     "desc": "CounterInputApp",
    # },
    # {
    #     "name": "DNM_CO_HRTBT",
    #     "class": "Bo",
    #     "dcs_nm": "CSTXM1610:Co:hrtbt:alive",
    #     "desc": "CounterOutputApp",
    # },
    # {
    #     "name": "DNM_DIO_HRTBT",
    #     "class": "Bo",
    #     "dcs_nm": "CSTXM1610:Dio:hrtbt:alive",
    #     "desc": "DigitalIOApp",
    # },
    # {
    #     "name": "DNM_MTRS_HRTBT",
    #     "class": "Bo",
    #     "dcs_nm": "CSTXM1610:AmbAbsMtrs:hrtbt:alive",
    #     "desc": "MainMotorsApp",
    # },
    # {
    #     "name": "DNM_MTR_CALIB_HRTBT",
    #     "class": "Bo",
    #     "dcs_nm": "CSTXM1610:MtrCal:hrtbt:alive",
    #     "desc": "MotorCalibrations",
    # },
    # {
    #     "name": "DNM_MTRS_OSA_HRTBT",
    #     "class": "Bo",
    #     "dcs_nm": "CSTXM1610:PiE873:hrtbt:alive",
    #     "desc": "OSAMotorsApp",
    # },
    #    {'name': 'DNM_MTRS_ZP_HRTBT',  'class': 'Bo', 'dcs_nm':'CSTXM1610:MtrZp:hrtbt:alive', 'desc': 'ZPzMotorsApp'},
    #    {'name': 'DNM_GATE_SCAN_CFG_HRTBT',  'class': 'Bo', 'dcs_nm':'CSTXM1610:hrtbt:alive', 'desc': 'Gate / CounterscancfgApp'}
]

dev_dct["PRESSURES"] = [
    {
        "name": "CCG1410-01:vac:p",
        "class": "make_basedevice",
        "cat": "PRESSURES",
        "dcs_nm": "CCG1410-01:vac:p",
        "desc": "Sec.1",
        "units": "torr",
        "pos_type": "POS_TYPE_BL",
        "sim": "False",
    },
    {
        "name": "CCG1410-I00-01:vac:p",
        "class": "make_basedevice",
        "cat": "PRESSURES",
        "dcs_nm": "CCG1410-I00-01:vac:p",
        "desc": "Sec.2",
        "units": "torr",
        "pos_type": "POS_TYPE_BL",
        "sim": "False",
    },
    {
        "name": "CCG1410-I00-02:vac:p",
        "class": "make_basedevice",
        "cat": "PRESSURES",
        "dcs_nm": "CCG1410-I00-02:vac:p",
        "desc": "Sec.4",
        "units": "torr",
        "pos_type": "POS_TYPE_BL",
        "sim": "False",
    },
    {
        "name": "CCG1610-1-I00-02:vac:p",
        "class": "make_basedevice",
        "cat": "PRESSURES",
        "dcs_nm": "CCG1610-1-I00-02:vac:p",
        "desc": "Sec.6",
        "units": "torr",
        "pos_type": "POS_TYPE_BL",
        "sim": "False",
    },
    {
        "name": "HCG1610-1-I00-01:vac:p",
        "class": "make_basedevice",
        "cat": "PRESSURES",
        "dcs_nm": "HCG1610-1-I00-01:vac:p",
        "desc": "Sec.7",
        "units": "torr",
        "pos_type": "POS_TYPE_BL",
        "sim": "False",
    },
    {
        "name": "CCG1610-1-I00-03:vac:p",
        "class": "make_basedevice",
        "cat": "PRESSURES",
        "dcs_nm": "CCG1610-1-I00-03:vac:p",
        "desc": "Sec.8",
        "units": "torr",
        "pos_type": "POS_TYPE_BL",
        "sim": "False",
    },
    {
        "name": "CCG1610-I10-01:vac:p",
        "class": "make_basedevice",
        "cat": "PRESSURES",
        "dcs_nm": "CCG1610-I10-01:vac:p",
        "desc": "Sec.10",
        "units": "torr",
        "pos_type": "POS_TYPE_BL",
        "sim": "False",
    },
    {
        "name": "CCG1610-I10-03:vac:p",
        "class": "make_basedevice",
        "cat": "PRESSURES",
        "dcs_nm": "CCG1610-I10-03:vac:p",
        "desc": "Sec.12",
        "units": "torr",
        "pos_type": "POS_TYPE_BL",
        "sim": "False",
    },
    {
        "name": "CCG1610-I10-04:vac:p",
        "class": "make_basedevice",
        "cat": "PRESSURES",
        "dcs_nm": "CCG1610-I10-04:vac:p",
        "desc": "Sec.13",
        "units": "torr",
        "pos_type": "POS_TYPE_BL",
        "sim": "False",
    },
    {
        "name": "CCG1610-I12-01:vac:p",
        "class": "make_basedevice",
        "cat": "PRESSURES",
        "dcs_nm": "CCG1610-I12-01:vac:p",
        "desc": "Sec.14",
        "units": "torr",
        "pos_type": "POS_TYPE_BL",
        "sim": "False",
    },
    {
        "name": "CCG1610-I12-02:vac:p",
        "class": "make_basedevice",
        "cat": "PRESSURES",
        "dcs_nm": "CCG1610-I12-02:vac:p",
        "desc": "Sec.15",
        "units": "torr",
        "pos_type": "POS_TYPE_BL",
        "sim": "False",
    },
    {
        "name": "CCG1610-3-I12-01:vac:p",
        "class": "make_basedevice",
        "cat": "PRESSURES",
        "dcs_nm": "CCG1610-3-I12-01:vac:p",
        "desc": "Sec.16",
        "units": "torr",
        "pos_type": "POS_TYPE_BL",
        "sim": "False",
    },
]


dev_dct["TEMPERATURES"] = [
    {
        "name": "TM1610-3-I12-01",
        "class": "make_basedevice",
        "cat": "TEMPERATURES",
        "dcs_nm": "TM1610-3-I12-01",
        "desc": "UVH Turbo cooling water",
        "units": "deg C",
        "pos_type": "POS_TYPE_ES",
        "sim": "False",
    },
    {
        "name": "TM1610-3-I12-30",
        "class": "make_basedevice",
        "cat": "TEMPERATURES",
        "dcs_nm": "TM1610-3-I12-30",
        "desc": "UVH Sample Coarse Y",
        "units": "deg C",
        "pos_type": "POS_TYPE_ES",
        "sim": "False",
    },
    {
        "name": "TM1610-3-I12-32",
        "class": "make_basedevice",
        "cat": "TEMPERATURES",
        "dcs_nm": "TM1610-3-I12-32",
        "desc": "UVH Detector Y",
        "units": "deg C",
        "pos_type": "POS_TYPE_ES",
        "sim": "False",
    },
    {
        "name": "TM1610-3-I12-21",
        "class": "make_basedevice",
        "cat": "TEMPERATURES",
        "dcs_nm": "TM1610-3-I12-21",
        "desc": "UVH Chamber temp #1",
        "units": "deg C",
        "pos_type": "POS_TYPE_ES",
        "sim": "False",
    },
    {
        "name": "TM1610-3-I12-22",
        "class": "make_basedevice",
        "cat": "TEMPERATURES",
        "dcs_nm": "TM1610-3-I12-22",
        "desc": "UVH Chamber temp #2",
        "units": "deg C",
        "pos_type": "POS_TYPE_ES",
        "sim": "False",
    },
    {
        "name": "TM1610-3-I12-23",
        "class": "make_basedevice",
        "cat": "TEMPERATURES",
        "dcs_nm": "TM1610-3-I12-23",
        "desc": "UVH Chamber temp #3",
        "units": "deg C",
        "pos_type": "POS_TYPE_ES",
        "sim": "False",
    },
    {
        "name": "TM1610-3-I12-24",
        "class": "make_basedevice",
        "cat": "TEMPERATURES",
        "dcs_nm": "TM1610-3-I12-24",
        "desc": "UVH Chamber temp #4",
        "units": "deg C",
        "pos_type": "POS_TYPE_ES",
        "sim": "False",
    },
]


dev_dct["E712"] = [
    # dev_dct['WIDGETS'][DNM_E712_WIDGET] = E712ControlWidget('%s%s:' % (DEVPRFX, e712_prfx), counter=dev_dct['DETECTORS'][DNM_COUNTER_APD], gate=dev_dct['DIO'][DNM_GATE])
    {
        "name": "DNM_E712_WIDGET",
        "class": "E712ControlWidget",
        "dcs_nm": "IOCE712:",
        "counter": "DETECTORS/DNM_DEFAULT_COUNTER",
        "gate": "DIO/DNM_GATE",
        "con_chk_nm": "CommStatus_RBV",
        "sim": "False",
    },
    {
        "name": "DNM_E712_OPHYD_DEV",
        "class": "E712WGDevice",
        "dcs_nm": "IOCE712:",
        "desc": "E712 wavgenerator flyer device",
        "con_chk_nm": "CommStatus_RBV",
        "sim": "False",
    },
    {
        "name": "DNM_E712_DWELLS",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:dwells",
        "units": "mA",
        "sim": "False",
    },
    {
        "name": "DNM_E712_XRESETPOSNS",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:xreset:posns",
        "units": "um",
        "sim": "False",
    },
    {
        "name": "DNM_E712_YRESETPOSNS",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:yreset:posns",
        "units": "um",
        "sim": "False",
    },
    {
        "name": "DNM_E712_SP_IDS",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:sp_roi:ids",
        "sim": "False",
    },
    {
        "name": "DNM_E712_CURRENT_SP_ID",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:sp_roi:current",
        "sim": "False",
    },
    {
        "name": "DNM_E712_X_START_POS",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:XStartPos",
        "sim": "False",
    },
    {
        "name": "DNM_E712_Y_START_POS",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:YStartPos",
        "sim": "False",
    },
    {
        "name": "DNM_E712_DDL_TBL_0",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:ddl:0",
        "sim": "False",
    },
    {
        "name": "DNM_E712_DDL_TBL_1",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:ddl:1",
        "sim": "False",
    },
    {
        "name": "DNM_E712_DDL_TBL_2",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:ddl:2",
        "sim": "False",
    },
    {
        "name": "DNM_E712_DDL_TBL_3",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:ddl:3",
        "sim": "False",
    },
    {
        "name": "DNM_E712_DDL_TBL_4",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:ddl:4",
        "sim": "False",
    },
    {
        "name": "DNM_E712_DDL_TBL_5",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:ddl:5",
        "sim": "False",
    },
    {
        "name": "DNM_E712_DDL_TBL_6",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:ddl:6",
        "sim": "False",
    },
    {
        "name": "DNM_E712_DDL_TBL_7",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:ddl:7",
        "sim": "False",
    },
    {
        "name": "DNM_E712_DDL_TBL_8",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:ddl:8",
        "sim": "False",
    },
    {
        "name": "DNM_E712_DDL_TBL_9",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:ddl:9",
        "sim": "False",
    },
    # the following are require args wvgen_x, wvgen_y which for astxm are 1,2 (sfx, sfy) and 3,4 for (zpx, zpy)
    {
        "name": "DNM_E712_IMAGE_IDX",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:image_idx",
        "sim": "False",
    },
    {
        "name": "DNM_E712_SCAN_MODE",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:ScanMode",
        "sim": "False",
    },
    {
        "name": "DNM_E712_X_START_MODE",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        #"dcs_nm": "IOCE712:wg1:startmode",
        "dcs_nm": "IOCE712:WavTbl1StartMode",
        "sim": "False",
    },
    {
        "name": "DNM_E712_Y_START_MODE",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        #"dcs_nm": "IOCE712:wg2:startmode",
        "dcs_nm": "IOCE712:WavTbl2StartMode",
        "sim": "False",
    },
    {
        "name": "DNM_E712_X_WAVTBL_IDS",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:wg1_tbl:ids",
        "sim": "False",
    },
    {
        "name": "DNM_E712_Y_WAVTBL_IDS",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:wg2_tbl:ids",
        "sim": "False",
    },
    # short PV's
    {
        "name": "DNM_E712_X_NPTS",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:wg1:npts",
        "sim": "False",
    },
    {
        "name": "DNM_E712_Y_NPTS",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:wg2:npts",
        "sim": "False",
    },
    # pvs that hold the flags for each waveformgenerator (4'}, for each supported sp_roi (max of 10'},
    {
        "name": "DNM_E712_X_USEDDL",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        #"dcs_nm": "IOCE712:wg1:useddl",
        "dcs_nm": "IOCE712:WavTbl1UseDDL",
        "sim": "False",
    },
    {
        "name": "DNM_E712_Y_USEDDL",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        #"dcs_nm": "IOCE712:wg2:useddl",
        "dcs_nm": "IOCE712:WavTbl2UseDDL",
        "sim": "False",
    },
    {
        "name": "DNM_E712_X_USEREINIT",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        #"dcs_nm": "IOCE712:wg1:usereinit",
        "dcs_nm": "IOCE712:WavTbl1UseReinitDDL",
        "sim": "False",
    },
    {
        "name": "DNM_E712_Y_USEREINIT",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        #"dcs_nm": "IOCE712:wg2:usereinit",
        "dcs_nm": "IOCE712:WavTbl2UseReinitDDL",
        "sim": "False",
    },
    {
        "name": "DNM_E712_X_STRT_AT_END",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        #"dcs_nm": "IOCE712:wg1:strtatend",
        "dcs_nm": "IOCE712:WavTbl1StartAtEndPos",
        "sim": "False",
    },
    {
        "name": "DNM_E712_Y_STRT_AT_END",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        #"dcs_nm": "IOCE712:wg2:strtatend",
        "dcs_nm": "IOCE712:WavTbl2StartAtEndPos",
        "sim": "False",
    },
    {
        "name": "DNM_E712_X_USE_TBL_NUM",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:WavGen1UseTblNum",
        "sim": "False",
    },
    {
        "name": "DNM_E712_Y_USE_TBL_NUM",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "IOCE712:WavGen2UseTblNum",
        "sim": "False",
    },
    # {
    #     "name": "DNM_E712_SSPND_CTRLR_FBK",
    #     "class": "make_basedevice",
    #     "cat": "PVS_DONT_RECORD",
    #     "dcs_nm": "IOCE712:SuspendCtrlrFbk",
    #     "sim": "True",
    #
    # },

]


def get_dev_names():
    from con_checker import con_check_many

    dev_nms = []
    for k in list(dev_dct.keys()):
        # get all the device names
        dlist = dev_dct[k]
        for sig_dct in dlist:
            if type(sig_dct) == dict:
                if "name" in sig_dct.keys():
                    dev_nms.append(sig_dct["name"])
            else:
                if sig_dct.find("POS_TYPE") > -1:
                    dlist = dev_dct[k][sig_dct]
                    for _dct in dlist:
                        if "name" in _dct.keys():
                            dev_nms.append(_dct["name"])
    return dev_nms


def get_connections_status(_dct=None):
    from con_checker import con_check_many

    dev_pvlist = []
    con_lst = []
    if _dct is None:
        keys = list(dev_dct.keys())
    else:
        keys = list(_dct.keys())

    for k in keys:
        # get all the signal names
        dlist = dev_dct[k]
        for sig_dct in dlist:
            if type(sig_dct) == dict:
                if "dcs_nm" in sig_dct.keys():
                    if "con_chk_nm" in sig_dct.keys():
                        con_lst.append(sig_dct["dcs_nm"] + sig_dct["con_chk_nm"])
                    else:
                        con_lst.append(sig_dct["dcs_nm"])
                    dev_pvlist.append(sig_dct["dcs_nm"])
            else:
                if sig_dct.find("POS_TYPE") > -1:
                    dlist = dev_dct[k][sig_dct]
                    for _dct in dlist:
                        if "dcs_nm" in _dct.keys():
                            if "con_chk_nm" in _dct.keys():
                                con_lst.append(_dct["dcs_nm"] + _dct["con_chk_nm"])
                            else:
                                con_lst.append(_dct["dcs_nm"])
                            dev_pvlist.append(_dct["dcs_nm"])
    # the list for connections might not be same as the sig_name required to create an instance of the device
    # so for purposes of finding out IS THERE A CONNECTION just make sure to specify an actual PV not just a prefix
    cons = con_check_many(con_lst)
    both = dict(zip(dev_pvlist, cons))
    return both


if __name__ == "__main__":
    cons = get_connections_status()
    for l in list(cons):
        print(l)
