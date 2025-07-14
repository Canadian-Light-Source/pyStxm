SIM = True
dev_dct = {}
dev_dct["POSITIONERS"] = [
    {
        "name": "DNM_CSX",
        "desc": "CSX",
        "class": "MotorQt",
        "dcs_nm": "CSX",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_CSY",
        "desc": "CSY",
        "class": "MotorQt",
        "dcs_nm": "CSY",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_MIRROR1_RY",
        "desc": "Mirror1_Ry",
        "class": "MotorQt",
        "dcs_nm": "Mirror1_Ry",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_MIRROR1_RX",
        "desc": "Mirror1_Rx",
        "class": "MotorQt",
        "dcs_nm": "Mirror1_Rx",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_HW_COARSE_Y",
        "desc": "HwCoarseY",
        "class": "MotorQt",
        "dcs_nm": "HwCoarseY",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_HW_COARSE_X",
        "desc": "HwCoarseX",
        "class": "MotorQt",
        "dcs_nm": "HwCoarseX",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_GIRDER_Y",
        "desc": "Girder_y",
        "class": "MotorQt",
        "dcs_nm": "Girder_y",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_SAMPLE_FINE_Z",
        "desc": "Fine_Z",
        "class": "MotorQt",
        "dcs_nm": "FineZ",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_EXIT_SLIT_V",
        "desc": "ExitSlit_V",
        "class": "MotorQt",
        "dcs_nm": "ExitSlit_V",
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "DNM_EXIT_SLIT_H",
        "desc": "ExitSlit_H",
        "class": "MotorQt",
        "dcs_nm": "ExitSlit_H",
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "DNM_ENTRANCE_SLIT",
        "desc": "EntranceSlit",
        "class": "MotorQt",
        "dcs_nm": "EntranceSlit",
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "DNM_SAMPLE_FINE_X",
        "desc": "Fine_X",
        "class": "MotorQt",
        "dcs_nm": "FineX",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_SAMPLE_FINE_Y",
        "desc": "Fine_Y",
        "class": "MotorQt",
        "dcs_nm": "FineY",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_OSA_X",
        "desc": "OSA_X",
        "class": "MotorQt",
        "dcs_nm": "OSAX",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_OSA_Y",
        "desc": "OSA_Y",
        "class": "MotorQt",
        "dcs_nm": "OSAY",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_ZONEPLATE_Z",
        "desc": "Zoneplate",
        "class": "MotorQt",
        "dcs_nm": "Zoneplate",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_COARSE_X",
        "desc": "Coarse_X",
        "class": "MotorQt",
        "dcs_nm": "CoarseX",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_COARSE_Y",
        "desc": "Coarse_Y",
        "class": "MotorQt",
        "dcs_nm": "CoarseY",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_COARSE_Z",
        "desc": "Coarse_Z",
        "class": "MotorQt",
        "dcs_nm": "CoarseZ",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_DETECTOR_X",
        "desc": "Detector_X",
        "class": "MotorQt",
        "dcs_nm": "DetectorX",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_DETECTOR_Y",
        "desc": "Detector_Y",
        "class": "MotorQt",
        "dcs_nm": "DetectorY",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_DETECTOR_Z",
        "desc": "Detector_Z",
        "class": "MotorQt",
        "dcs_nm": "DetectorZ",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_SAMPLE_X",
        "desc": "Sample_X",
        "class": "sample_abstract_motor",
        "dcs_nm": "SampleX",
        "pos_type": "POS_TYPE_ES",
        "fine_mtr_name": "DNM_SAMPLE_FINE_X",
        "coarse_mtr_name": "DNM_COARSE_X"
    },
    {
        "name": "DNM_SAMPLE_Y",
        "desc": "Sample_Y",
        "class": "sample_abstract_motor",
        "dcs_nm": "SampleY",
        "pos_type": "POS_TYPE_ES",
        "fine_mtr_name": "DNM_SAMPLE_FINE_Y",
        "coarse_mtr_name": "DNM_COARSE_Y"

    },
    {
        "name": "DNM_ENERGY",
        "desc": "Energy",
        "class": "MotorQt",
        "dcs_nm": "Energy" if SIM else "Energy",
        "abstract_mtr": True,
        "pos_type": "POS_TYPE_BL",
        "units": "eV",
    },
    {
        "name": "DNM_EPU_OFFSET",
        "desc": "ID1_Offset",
        "class": "MotorQt",
        "dcs_nm": "ID1Off" if SIM else "ID1Off",
        "abstract_mtr": True,
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "DNM_ID2_OFFSET",
        "desc": "ID2_Offset",
        "class": "MotorQt",
        "dcs_nm": "ID2Off" if SIM else "ID2Off",
        "abstract_mtr": True,
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "DNM_EPU_POLARIZATION",
        "desc": "Polarization",
        "class": "MotorQt",
        "dcs_nm": "Polarization" if SIM else "Polarization",
        "abstract_mtr": True,
        "pos_type": "POS_TYPE_BL",
        "enums": ["Off", "Pos", "Neg"],
        "enum_values": [0, -0.2, 0.2]
    },
    {
        "name": "DNM_EPU_ANGLE",
        "desc": "Epu_Angle",
        "class": "MotorQt",
        "dcs_nm": "PIXELATOR_DNM_EPU_ANGLE",
        "abstract_mtr": True,
        "pos_type": "POS_TYPE_BL",
    },
]
# if the sig_name is not itself a PV but is only a prefix, profide the con_chk_nm field
dev_dct["DIO"] = [
    {
        "name": "DNM_SHUTTER",
        "class": "DCSShutter",
        "dcs_nm": "BeamShutter",
        "ctrl_enum_strs": ["Auto", "Open", "Closed", "Auto Line"],
        "fbk_enum_strs": ["CLOSED", "OPEN"],

    },
    {
        "name": "DNM_SHUTTERTASKRUN",
        "class": "make_basedevice",
        # "dcs_nm": "ASTXM1610:Dio:shutter:Run",
        "dcs_nm": "PIXELATOR_SHUTTERTASKRUN",
    },
]

dev_dct["DETECTORS"] = [
    # {
    #     "name": "DNM_SIS3820",
    #     #"class": "SIS3820ScalarDevice",
    #     "class": "make_basedevice",
    #     "dcs_nm": "PIXELATOR_SIS3820",
    #     "con_chk_nm": "mcs:startScan",
    # },
    # {
    #     "name": "DNM_PMT",
    #     "class": "Counter",
    #     "dcs_nm": "Counter1",
    # },
    {
        "name": "DNM_COUNTER1",
        "class": "Counter",
        "dcs_nm": "Counter1",
    },
    {
        "name": "DNM_COUNTER2",
        "class": "Counter",
        "dcs_nm": "Counter2",
    },
    {
        "name": "DNM_ANALOG0",
        "class": "Counter",
        "dcs_nm": "Bl AI 0",
    },

]
dev_dct["PVS"] = [
    {
        "name": "DNM_APD_VOLTAGE",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "APD Voltage",
    },
    {
        "name": "DNM_MAGNETIC_FIELD",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "Magnetic Field",
    },
    {
        "name": "DNM_ZMQ",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "ZMQ",
    },
    {
        "name": "DNM_MOENCH_NUM_FRAMES",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "MoenchNumFrames",
    },
    {
        "name": "DNM_FINE_ACCEL_DIST_PRCNT",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "PIXELATOR_FINE_ACCEL_DIST_PRCNT",
    },
    {
        "name": "DNM_FINE_DECCEL_DIST_PRCNT",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "PIXELATOR_FINE_DECCEL_DIST_PRCNT",
    },
    {
        "name": "DNM_CRS_ACCEL_DIST_PRCNT",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "PIXELATOR_CRS_ACCEL_DIST_PRCNT",
    },
    {
        "name": "DNM_CRS_DECCEL_DIST_PRCNT",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "PIXELATOR_CRS_DECCEL_DIST_PRCNT",
    },
    {
        "name": "DNM_CALCD_ZPZ",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "PIXELATOR_CALCD_ZPZ",
    },
    {
        "name": "DNM_RESET_INTERFERS",
        "class": "Bo",
        "cat": "PVS",
        "dcs_nm": "PIXELATOR_RESET_INTERFERS",
    },
    # {
    #     "name": "DNM_SFX_AUTOZERO",
    #     "class": "Bo",
    #     "cat": "PVS",
    #     "dcs_nm": "PIXELATOR_SFX_AUTOZERO",
    # },
    # {
    #     "name": "DNM_SFY_AUTOZERO",
    #     "class": "Bo",
    #     "cat": "PVS",
    #     "dcs_nm": "PIXELATOR_SFY_AUTOZERO",
    # },
    {
        "name": "DNM_ZPZ_ADJUST",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "PIXELATOR_ZPZ_ADJUST",
    },
    # {
    #     "name": "DNM_ZONEPLATE_SCAN_MODE",
    #     "class": "Mbbo",
    #     "dcs_nm": "PIXELATOR_ZONEPLATE_SCAN_MODE",
    # },
    # {
    #     "name": "DNM_ZONEPLATE_SCAN_MODE_RBV",
    #     "class": "Mbbo",
    #     "dcs_nm": "PIXELATOR_ZONEPLATE_SCAN_MODE_RBV",
    # },
    # used to control which value gets sent to Zpz, fl or fl - A0
    # {'name': 'DNM_ZONEPLATE_INOUT', 'class': 'Bo', 'dcs_nm': 'BL1610-I12:zp_inout'},
    # {'name': 'DNM_ZONEPLATE_INOUT_FBK', 'class': 'Mbbi', 'dcs_nm': 'ASTXM1610:bl_api:zp_inout:fbk'},
    # used to convieniently move zp z in and out
    {
        "name": "DNM_ZONEPLATE_INOUT",
        "class": "Bo",
        "dcs_nm": "PIXELATOR_ZONEPLATE_INOUT",
    },
    {
        "name": "DNM_OSA_INOUT",
        "class": "Bo",
        "dcs_nm": "PIXELATOR_OSA_INOUT",
    },
    {
        "name": "DNM_SAMPLE_OUT",
        "class": "Bo",
        "dcs_nm": "PIXELATOR_SAMPLE_OUT",
    },
    {
        "name": "DNM_DELTA_A0",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "PIXELATOR_DELTA_A0",
    },
    {
        "name": "DNM_IDEAL_A0",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "PIXELATOR_IDEAL_A0",
    },
    {
        "name": "DNM_CALCD_ZPZ",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "PIXELATOR_CALCD_ZPZ",
    },
    {
        "name": "DNM_ZPZ_ADJUST",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "PIXELATOR_ZPZ_ADJUST",
    },
    {
        "name": "DNM_FOCAL_LENGTH",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "PIXELATOR_FOCAL_LENGTH",
        "units": "um",
    },
    {
        "name": "DNM_A0",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "PIXELATOR_A0",
    },
    {
        "name": "DNM_A0MAX",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "PIXELATOR_A0MAX",
    },
    # {'name': 'DNM_A0_FOR_CALC', 'class': 'make_basedevice', 'cat': 'PVS', 'dcs_nm': 'ASTXM1610:bl_api:A0:for_calc'},
    {
        "name": "DNM_ZPZ_POS",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "PIXELATOR_ZPZ_POS",
    },
    # {
    #     "name": "DNM_ENERGY_ENABLE",
    #     "class": "Bo",
    #     "dcs_nm": "ASTXM1610:bl_api:enabled"
    # },
    # {
    #     "name": "DNM_ENERGY_RBV",
    #     "class": "make_basedevice",
    #     "cat": "PVS",
    #     "dcs_nm": "Energy" if SIM else "Energy",
    #     "units": "um",
    # },
    # {
    #     "name": "DNM_ZPZ_RBV",
    #     "class": "make_basedevice",
    #     "cat": "PVS",
    #     "dcs_nm": "Zoneplate",
    #     "units": "um",
    # },
    {
        "name": "DNM_ZP_DEF_A",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "PIXELATOR_ZP_DEF_A",
    },
    {
        "name": "DNM_ZP_DEF",
        "class": "Transform",
        "cat": "PVS",
        "dcs_nm": "PIXELATOR_ZP_DEF",
    },
    {
        "name": "DNM_OSA_DEF",
        "class": "Transform",
        "cat": "PVS",
        "dcs_nm": "PIXELATOR_OSA_DEF",
    },
    # {
    #     "name": "DNM_SYSTEM_MODE_FBK",
    #     "class": "make_basedevice",
    #     "cat": "PVS",
    #     "dcs_nm": "PIXELATOR_SYSTEM_MODE_FBK",
    # },
    {
        "name": "DNM_SRSTATUS_SHUTTERS",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "PIXELATOR_SRSTATUS_SHUTTERS",
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
    # {
    #     "name": "DNM_MONO_EV_FBK",
    #     "class": "make_basedevice",
    #     "cat": "PVS",
    #     # "dcs_nm": "SIM_SM01PGM01:ENERGY_MON",
    #     "dcs_nm": "Energy",
    #     "units": "eV",
    #     "rd_only": True,
    # },
    # {
    #     "name": "DNM_BEAM_DEFOCUS",
    #     "class": "make_basedevice",
    #     "cat": "PVS",
    #     "dcs_nm": "PIXELATOR_BEAM_DEFOCUS",
    #     "units": "um",
    # },
    # {
    #     "name": "DNM_AX1_INTERFER_VOLTS",
    #     "class": "make_basedevice",
    #     "cat": "PVS",
    #     "dcs_nm": "PIXELATOR_AX1_INTERFER_VOLTS",
    #     "rd_only": True,
    # },
    # {
    #     "name": "DNM_SFX_PIEZO_VOLTS",
    #     "class": "make_basedevice",
    #     "cat": "PVS",
    #     "dcs_nm": "PIXELATOR_SFX_PIEZO_VOLTS",
    #     "rd_only": True,
    # },
    # {
    #     "name": "DNM_SFY_PIEZO_VOLTS",
    #     "class": "make_basedevice",
    #     "cat": "PVS",
    #     "dcs_nm": "PIXELATOR_SFY_PIEZO_VOLTS",
    #     "rd_only": True,
    # },
    # {
    #     "name": "DNM_AX2_INTERFER_VOLTS",
    #     "class": "make_basedevice",
    #     "cat": "PVS",
    #     "dcs_nm": "PIXELATOR_AX2_INTERFER_VOLTS",
    #     "rd_only": True,
    # },
    # {
    #     "name": "DNM_RING_CURRENT",
    #     "class": "make_basedevice",
    #     "cat": "PVS",
    #     "dcs_nm": "PIXELATOR_RING_CURRENT" if SIM else "PIXELATOR_RING_CURRENT",
    #     "units": "mA",
    # },
    # {
    #     "name": "DNM_BASELINE_RING_CURRENT",
    #     "class": "make_basedevice",
    #     "cat": "PVS",
    #     "dcs_nm": "PIXELATOR_BASELINE_RING_CURRENT" if SIM else "PIXELATOR_BASELINE_RING_CURRENT",
    #     "units": "mA",
    # },
    {
        "name": "DNM_DFLT_PMT_DWELL",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "PIXELATOR_DFLT_PMT_DWELL",
    },
    {
        "name": "DNM_ALL_MOTORS_OFF",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "PIXELATOR_ALL_MOTORS_OFF",
    },
    {
        "name": "DNM_GATING",
        "class": "MultiSelectable",
        "dcs_nm": "PIXELATOR_GATING",
        "desc": "Pixelator Gating, connected to the rings top up mode",
        # the ctrl_enum_strs appear in teh pulldown for the combobox
        "ctrl_enum_strs": ["On", "Off", "No Repeat"],
        "fbk_enum_strs": ["On", "Off", "No Repeat"],
        #"fbk_enum_values": [0, 1, 2]
    },
    {
        "name": "DNM_FOCUS_MODE",
        "class": "MultiSelectable",
        "dcs_nm": "PIXELATOR_FOCUS_MODE",
        "desc": "Focus mode",
        # the ctrl_enum_strs appear in the pulldown for the combobox
        "ctrl_enum_strs": ["Static", "Auto"],
        "fbk_enum_strs": ["Static", "Auto"],
        #"fbk_enum_values": [0, 1]
    },
    {
        "name": "DNM_SHUTTER_MODE",
        "class": "MultiSelectable",
        "dcs_nm": "PIXELATOR_FOCUS_MODE",
        "desc": "Focus mode",
        # the ctrl_enum_strs appear in the pulldown for the combobox
        "ctrl_enum_strs": ["Static", "Auto"],
        "fbk_enum_strs": ["Static", "Auto"],
        #"fbk_enum_values": [0, 1]
    },



    # _pv: BaseDevice('BL1610-I12:MONO1610-I10-01:grating:select:fbk'}, _pv.get_position: _pv.get_enum_str_as_int[{'name': 'Mono_grating_fbk',  'class': _pv
]

dev_dct["PVS_DONT_RECORD"] = [
    {
        "name": "DNM_TICKER",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "PIXELATOR_TICKER",
        "units": "counts",
    }
]

dev_dct["HEARTBEATS"] = [
    # {
    #     "name": "DNM_BLAPI_HRTBT",
    #     "class": "Bo",
    #     "dcs_nm": "ASTXM1610:BlApi:hrtbt:alive",
    #     "desc": "BlApiApp",
    # },
    # {
    #     "name": "DNM_AI_HRTBT",
    #     "class": "Bo",
    #     "dcs_nm": "ASTXM1610:Ai:hrtbt:alive",
    #     "desc": "AnalogInputApp",
    # },
    # {
    #     "name": "DNM_CI_HRTBT",
    #     "class": "Bo",
    #     "dcs_nm": "ASTXM1610:Ci:hrtbt:alive",
    #     "desc": "CounterInputApp",
    # },
    # {
    #     "name": "DNM_CO_HRTBT",
    #     "class": "Bo",
    #     "dcs_nm": "ASTXM1610:Co:hrtbt:alive",
    #     "desc": "CounterOutputApp",
    # },
    # {
    #     "name": "DNM_DIO_HRTBT",
    #     "class": "Bo",
    #     "dcs_nm": "ASTXM1610:Dio:hrtbt:alive",
    #     "desc": "DigitalIOApp",
    # },
    # {
    #     "name": "DNM_MTRS_HRTBT",
    #     "class": "Bo",
    #     "dcs_nm": "ASTXM1610:AmbAbsMtrs:hrtbt:alive",
    #     "desc": "MainMotorsApp",
    # },
    # {
    #     "name": "DNM_MTR_CALIB_HRTBT",
    #     "class": "Bo",
    #     "dcs_nm": "ASTXM1610:MtrCal:hrtbt:alive",
    #     "desc": "MotorCalibrations",
    # },
    # {
    #     "name": "DNM_MTRS_OSA_HRTBT",
    #     "class": "Bo",
    #     "dcs_nm": "ASTXM1610:PiE873:hrtbt:alive",
    #     "desc": "OSAMotorsApp",
    # },
    #    {'name': 'DNM_MTRS_ZP_HRTBT',  'class': 'Bo', 'dcs_nm':'ASTXM1610:MtrZp:hrtbt:alive', 'desc': 'ZPzMotorsApp'},
    #    {'name': 'DNM_GATE_SCAN_CFG_HRTBT',  'class': 'Bo', 'dcs_nm':'ASTXM1610:hrtbt:alive', 'desc': 'Gate / CounterscancfgApp'}
]

dev_dct["PRESSURES"] = [
    # {
    #     "name": "CCG1410-01:vac:p",
    #     "class": "make_basedevice",
    #     "cat": "PRESSURES",
    #     "dcs_nm": "CCG1410-01:vac:p",
    #     "desc": "Sec.1",
    #     "units": "torr",
    #     "pos_type": "POS_TYPE_BL",
    # },
    # {
    #     "name": "CCG1410-I00-01:vac:p",
    #     "class": "make_basedevice",
    #     "cat": "PRESSURES",
    #     "dcs_nm": "CCG1410-I00-01:vac:p",
    #     "desc": "Sec.2",
    #     "units": "torr",
    #     "pos_type": "POS_TYPE_BL",
    # },
    # {
    #     "name": "CCG1410-I00-02:vac:p",
    #     "class": "make_basedevice",
    #     "cat": "PRESSURES",
    #     "dcs_nm": "CCG1410-I00-02:vac:p",
    #     "desc": "Sec.4",
    #     "units": "torr",
    #     "pos_type": "POS_TYPE_BL",
    # },
    # {
    #     "name": "CCG1610-1-I00-02:vac:p",
    #     "class": "make_basedevice",
    #     "cat": "PRESSURES",
    #     "dcs_nm": "CCG1610-1-I00-02:vac:p",
    #     "desc": "Sec.6",
    #     "units": "torr",
    #     "pos_type": "POS_TYPE_BL",
    # },
    # {
    #     "name": "HCG1610-1-I00-01:vac:p",
    #     "class": "make_basedevice",
    #     "cat": "PRESSURES",
    #     "dcs_nm": "HCG1610-1-I00-01:vac:p",
    #     "desc": "Sec.7",
    #     "units": "torr",
    #     "pos_type": "POS_TYPE_BL",
    # },
    # {
    #     "name": "CCG1610-1-I00-03:vac:p",
    #     "class": "make_basedevice",
    #     "cat": "PRESSURES",
    #     "dcs_nm": "CCG1610-1-I00-03:vac:p",
    #     "desc": "Sec.8",
    #     "units": "torr",
    #     "pos_type": "POS_TYPE_BL",
    # },
    # {
    #     "name": "CCG1610-I10-01:vac:p",
    #     "class": "make_basedevice",
    #     "cat": "PRESSURES",
    #     "dcs_nm": "CCG1610-I10-01:vac:p",
    #     "desc": "Sec.10",
    #     "units": "torr",
    #     "pos_type": "POS_TYPE_BL",
    # },
    # {
    #     "name": "CCG1610-I10-03:vac:p",
    #     "class": "make_basedevice",
    #     "cat": "PRESSURES",
    #     "dcs_nm": "CCG1610-I10-03:vac:p",
    #     "desc": "Sec.12",
    #     "units": "torr",
    #     "pos_type": "POS_TYPE_BL",
    # },
    # {
    #     "name": "CCG1610-I10-04:vac:p",
    #     "class": "make_basedevice",
    #     "cat": "PRESSURES",
    #     "dcs_nm": "CCG1610-I10-04:vac:p",
    #     "desc": "Sec.13",
    #     "units": "torr",
    #     "pos_type": "POS_TYPE_BL",
    # },
    # {
    #     "name": "CCG1610-I12-01:vac:p",
    #     "class": "make_basedevice",
    #     "cat": "PRESSURES",
    #     "dcs_nm": "CCG1610-I12-01:vac:p",
    #     "desc": "Sec.14",
    #     "units": "torr",
    #     "pos_type": "POS_TYPE_BL",
    # },
    # {
    #     "name": "CCG1610-I12-02:vac:p",
    #     "class": "make_basedevice",
    #     "cat": "PRESSURES",
    #     "dcs_nm": "CCG1610-I12-02:vac:p",
    #     "desc": "Sec.15",
    #     "units": "torr",
    #     "pos_type": "POS_TYPE_BL",
    # },
    # {
    #     "name": "CCG1610-3-I12-01:vac:p",
    #     "class": "make_basedevice",
    #     "cat": "PRESSURES",
    #     "dcs_nm": "CCG1610-3-I12-01:vac:p",
    #     "desc": "Sec.16",
    #     "units": "torr",
    #     "pos_type": "POS_TYPE_BL",
    #},
]

dev_dct["TEMPERATURES"] = [
    # {
    #     "name": "TM1610-3-I12-01",
    #     "class": "make_basedevice",
    #     "cat": "TEMPERATURES",
    #     "dcs_nm": "TM1610-3-I12-01",
    #     "desc": "UVH Turbo cooling water",
    #     "units": "deg C",
    #     "pos_type": "POS_TYPE_ES",
    # },
    # {
    #     "name": "TM1610-3-I12-30",
    #     "class": "make_basedevice",
    #     "cat": "TEMPERATURES",
    #     "dcs_nm": "TM1610-3-I12-30",
    #     "desc": "UVH Sample Coarse Y",
    #     "units": "deg C",
    #     "pos_type": "POS_TYPE_ES",
    # },
    # {
    #     "name": "TM1610-3-I12-32",
    #     "class": "make_basedevice",
    #     "cat": "TEMPERATURES",
    #     "dcs_nm": "TM1610-3-I12-32",
    #     "desc": "UVH Detector Y",
    #     "units": "deg C",
    #     "pos_type": "POS_TYPE_ES",
    # },
    # {
    #     "name": "TM1610-3-I12-21",
    #     "class": "make_basedevice",
    #     "cat": "TEMPERATURES",
    #     "dcs_nm": "TM1610-3-I12-21",
    #     "desc": "UVH Chamber temp #1",
    #     "units": "deg C",
    #     "pos_type": "POS_TYPE_ES",
    # },
    # {
    #     "name": "TM1610-3-I12-22",
    #     "class": "make_basedevice",
    #     "cat": "TEMPERATURES",
    #     "dcs_nm": "TM1610-3-I12-22",
    #     "desc": "UVH Chamber temp #2",
    #     "units": "deg C",
    #     "pos_type": "POS_TYPE_ES",
    # },
    # {
    #     "name": "TM1610-3-I12-23",
    #     "class": "make_basedevice",
    #     "cat": "TEMPERATURES",
    #     "dcs_nm": "TM1610-3-I12-23",
    #     "desc": "UVH Chamber temp #3",
    #     "units": "deg C",
    #     "pos_type": "POS_TYPE_ES",
    # },
    # {
    #     "name": "TM1610-3-I12-24",
    #     "class": "make_basedevice",
    #     "cat": "TEMPERATURES",
    #     "dcs_nm": "TM1610-3-I12-24",
    #     "desc": "UVH Chamber temp #4",
    #     "units": "deg C",
    #     "pos_type": "POS_TYPE_ES",
    # },
]



def get_dev_names():
    dev_nms = []
    for k in list(dev_dct.keys()):
        # get all the device names
        dlist = dev_dct[k]
        for sig_dct in dlist:
            if isinstance(sig_dct, dict):
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
    from cls.applications.pyStxm.bl_configs.device_configurator.con_checker import con_check_many

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
            if isinstance(sig_dct, dict):
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
    for conn in list(cons):
        print(conn)
