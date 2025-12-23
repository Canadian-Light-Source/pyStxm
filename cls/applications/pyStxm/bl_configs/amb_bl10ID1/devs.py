
SIM = False
dev_dct = {}
dev_dct["POSITIONERS"] = [
    {
        "name": "DNM_SAMPLE_FINE_X",
        "desc": "Fine_X",
        "class": "e712_sample_motor",
        "dcs_nm": "PZAC1610-3-I12-40",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_SAMPLE_FINE_Y",
        "desc": "Fine_Y",
        "class": "e712_sample_motor",
        "dcs_nm": "PZAC1610-3-I12-41",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_OSA_X",
        "desc": "OSA_X",
        "class": "MotorQt",
        "dcs_nm": "PZAC1610-3-I12-43",
        "pos_type": "POS_TYPE_ES",
    },
    # {
    #     "name": "DNM_OSA_X",
    #     "desc": "OSA_X",
    #     "class": "make_baseZMQdevice",
    #     "dcs_nm": "PIXELATOR_OSA_X",
    #     "pos_type": "POS_TYPE_ES",
    # },
    {
        "name": "DNM_OSA_Y",
        "desc": "OSA_Y",
        "class": "MotorQt",
        "dcs_nm": "PZAC1610-3-I12-44",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_ZONEPLATE_Z",
        "Zoneplate_Z": "FineX",
        "class": "MotorQt",
        "dcs_nm": "SMTR1610-3-I12-51",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_COARSE_X",
        "desc": "Coarse_X",
        "class": "MotorQt",
        "dcs_nm": "SMTR1610-3-I12-45",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_COARSE_Y",
        "desc": "Coarse_Y",
        "class": "MotorQt",
        "dcs_nm": "SMTR1610-3-I12-46",
        "pos_type": "POS_TYPE_ES",
    },
    # {
    #     "name": "DNM_SCANCOARSE_X",
    #     "desc": "Scan_CX",
    #     "class": "EpicsMotor",
    #     "dcs_nm": "SMTR1610-3-I12-45",
    #     "pos_type": "POS_TYPE_ES",
    # },
    # {
    #     "name": "DNM_SCANCOARSE_Y",
    #     "desc": "Scan_CY",
    #     "class": "EpicsMotor",
    #     "dcs_nm": "SMTR1610-3-I12-46",
    #     "pos_type": "POS_TYPE_ES",
    # },
    {
        "name": "DNM_COARSE_Z",
        "desc": "Coarse_Z",
        "class": "MotorQt",
        "dcs_nm": "SMTR1610-3-I12-47",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_DETECTOR_X",
        "desc": "Detector_X",
        "class": "MotorQt",
        "dcs_nm": "SMTR1610-3-I12-48",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_DETECTOR_Y",
        "desc": "Detector_Y",
        "class": "MotorQt",
        "dcs_nm": "SMTR1610-3-I12-49",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_DETECTOR_Z",
        "desc": "Detector_Z",
        "class": "MotorQt",
        "dcs_nm": "SMTR1610-3-I12-50",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "DNM_SAMPLE_X",
        "desc": "Sample_X",
        "class": "sample_abstract_motor",
        "dcs_nm": "PSMTR1610-3-I12-00",
        "pos_type": "POS_TYPE_ES",
        "fine_mtr_name": "DNM_SAMPLE_FINE_X",
        "coarse_mtr_name": "DNM_COARSE_X"
    },
    {
        "name": "DNM_SAMPLE_Y",
        "desc": "Sample_Y",
        "class": "sample_abstract_motor",
        "dcs_nm": "PSMTR1610-3-I12-01",
        "pos_type": "POS_TYPE_ES",
        "fine_mtr_name": "DNM_SAMPLE_FINE_Y",
        "coarse_mtr_name": "DNM_COARSE_Y"

    },
    {
        "name": "DNM_ENERGY",
        "desc": "Energy",
        "class": "MotorQt",
        "dcs_nm": "SIM_VBL1610-I12:ENERGY" if SIM else "BL1610-I10:ENERGY",
        # "dcs_nm": "SIM_VBL1610-I12:ENERGY",
        # "dcs_nm": "BL1610-I10:ENERGY",
        "abstract_mtr": True,
        "pos_type": "POS_TYPE_BL",
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
        "abstract_mtr": True,
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "DNM_M3_PITCH",
        "desc": "M3_Pitch",
        "class": "MotorQt",
        "dcs_nm": "SIM_VBL1610-I12:m3STXMPitch" if SIM else "BL1610-I10:m3STXMPitch",
        "abstract_mtr": True,
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "DNM_EPU_GAP",
        "desc": "Epu_Gap",
        "class": "MotorQt",
        "dcs_nm": "SIM_VBL1610-I12:epuGap" if SIM else "BL1610-I10:epuGap",
        "abstract_mtr": True,
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "DNM_EPU_OFFSET",
        "desc": "Epu_Offset",
        "class": "MotorQt",
        "dcs_nm": "SIM_VBL1610-I12:epuOffset" if SIM else "BL1610-I10:epuOffset",
        "abstract_mtr": True,
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "DNM_EPU_HARMONIC",
        "desc": "Epu_Harmonic",
        "class": "MotorQt",
        "dcs_nm": "SIM_VBL1610-I12:epuHarmonic" if SIM else "BL1610-I10:epuHarmonic",
        "abstract_mtr": True,
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "DNM_EPU_POLARIZATION",
        "desc": "Polarization",
        "class": "MotorQt",
        "dcs_nm": "SIM_VBL1610-I12:epuPolarization" if SIM else "BL1610-I10:epuPolarization",
        "abstract_mtr": True,
        "pos_type": "POS_TYPE_BL",
        "enums": ["CircLeft", "CircRight", "LinHor", "IncVert-", "IncVert+", "LinInc"]
    },
    {
        "name": "DNM_EPU_ANGLE",
        "desc": "Epu_Angle",
        "class": "MotorQt",
        "dcs_nm": "SIM_VBL1610-I12:epuAngle" if SIM else "BL1610-I10:epuAngle",
        "abstract_mtr": True,
        "pos_type": "POS_TYPE_BL",
    },

]
# if the sig_name is not itself a PV but is only a prefix, profide the con_chk_nm field
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

dev_dct["DETECTORS"] = [
    {
        "name": "DNM_SIS3820",
        "class": "SIS3820ScalarDevice",
        "dcs_nm": "MCS1610-310-01:",
        "con_chk_nm": "mcs:startScan",
    },
    {
        "name": "DNM_PMT",
        "class": "make_basedevice",
        # "dcs_nm": "MCS1610-310-01:mcs09:fbk",
        "dcs_nm": "ASTXM1610:Ci-D1C2:cntr:SingleValue_RBV",
    },
    {
        "name": "DNM_TUCSEN_AD",
        "class": "TucsenDetector",
        "dcs_nm": "SCMOS1610-310:",
    },
    # {
    #     "name": "DNM_SIM_CCD",
    #     "class": "SimDetector",
    #     "dcs_nm": "SIMCCD1610-I10-02:",
    # },

    #     {"name": "DNM_SIM_DET1", "class": "det1"},
    #     {"name": "DNM_SIM_DET2", "class": "det2"},
    #     {"name": "DNM_SIM_DET3", "class": "det3"},
    #     {"name": "DNM_SIM_NOISYDET", "class": "noisy_det"},
    #     {"name": "SIM_LINE_DET_1", "class": "SimLineDetectorDevice", "dcs_nm": "ASTXM1610:Ci:counter1:"},
    #     {"name": "SIM_LINE_DET_2", "class": "SimLineDetectorDevice", "dcs_nm": "ASTXM1610:Ci:counter2:"},
    #     {"name": "SIM_LINE_DET_3", "class": "SimLineDetectorDevice", "dcs_nm": "ASTXM1610:Ci:counter3:"},
    #     {"name": "SIM_LINE_DET_4", "class": "SimLineDetectorDevice", "dcs_nm": "ASTXM1610:Ci:counter4:"},
    #     {"name": "SIM_LINE_DET_5", "class": "SimLineDetectorDevice", "dcs_nm": "ASTXM1610:Ci:counter5:"},
    #     {"name": "SIM_LINE_DET_FLYER_1", "class": "SimLineDetectorFlyerDevice", "dcs_nm": "ASTXM1610:Ci:counter11:","stream_names": {"line_fly_strm_1": "primary_1"}},
    #     {"name": "SIM_LINE_DET_FLYER_2", "class": "SimLineDetectorFlyerDevice", "dcs_nm": "ASTXM1610:Ci:counter12:","stream_names": {"line_fly_strm_2": "primary_2"}},
    #     {"name": "SIM_LINE_DET_FLYER_3", "class": "SimLineDetectorFlyerDevice", "dcs_nm": "ASTXM1610:Ci:counter13:","stream_names": {"line_fly_strm_3": "primary_3"}},
    #     {"name": "SIM_LINE_DET_FLYER_4", "class": "SimLineDetectorFlyerDevice", "dcs_nm": "ASTXM1610:Ci:counter14:","stream_names": {"line_fly_strm_4": "primary_4"}},
    #     {"name": "SIM_LINE_DET_FLYER_5", "class": "SimLineDetectorFlyerDevice", "dcs_nm": "ASTXM1610:Ci:counter15:","stream_names": {"line_fly_strm_5": "primary_5"}},
]

dev_dct["PVS"] = [
    {
        "name": "DNM_RETURN_VELO",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "SIM_SCAN:return_velo",
    },
    {
        "name": "DNM_FINE_ACCEL_DIST_PRCNT",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "SIM_FINEIMAGE:ACCEL_DIST_PRCNT",
    },
    {
        "name": "DNM_FINE_DECCEL_DIST_PRCNT",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "SIM_FINEIMAGE:DECCEL_DIST_PRCNT",
    },
    {
        "name": "DNM_CRS_ACCEL_DIST_PRCNT",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "SIM_COARSEIMAGE:ACCEL_DIST_PRCNT",
    },
    {
        "name": "DNM_CRS_DECCEL_DIST_PRCNT",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "SIM_COARSEIMAGE:DECCEL_DIST_PRCNT",
    },
    {
        "name": "DNM_RESET_INTERFERS",
        "class": "Bo",
        "cat": "PVS",
        "dcs_nm": "PSMTR1610-3-I12-00:reset_interfers",
    },
    {
        "name": "DNM_SFX_AUTOZERO",
        "class": "Bo",
        "cat": "PVS",
        "dcs_nm": "PZAC1610-3-I12-40:AutoZero",
    },
    {
        "name": "DNM_SFY_AUTOZERO",
        "class": "Bo",
        "cat": "PVS",
        "dcs_nm": "PZAC1610-3-I12-41:AutoZero",
    },
# used to control which value gets sent to Zpz, fl or fl - A0
    # {'name': 'DNM_ZONEPLATE_INOUT', 'class': 'Bo', 'dcs_nm': 'BL1610-I12:zp_inout'},
    # {'name': 'DNM_ZONEPLATE_INOUT_FBK', 'class': 'Mbbi', 'dcs_nm': 'ASTXM1610:bl_api:zp_inout:fbk'},
    # used to convieniently move zp z in and out

    {
        "name": "DNM_CALCD_ZPZ",
        "class": "make_base_simdevice",
        "cat": "PVS",
        "dcs_nm": "ASTXM1610:bl_api:zp:fbk:tr.I",
    },
    {
        "name": "DNM_ZPZ_ADJUST",
        "class": "make_base_simdevice",
        "cat": "PVS",
        "dcs_nm": "ASTXM1610:bl_api:zp:adjust_zpz",
    },
    {
        "name": "DNM_ZONEPLATE_FOCUS_MODE",
        "class": "make_base_simdevice",
        "dcs_nm": "ASTXM1610:bl_api:zp:scanselflag",
    },
    # {
    #     "name": "DNM_ZONEPLATE_SCAN_MODE_RBV",
    #     "class": "make_base_simdevice",
    #     "dcs_nm": "ASTXM1610:bl_api:zp:scanselflag",
    # },

    {
        "name": "DNM_DELTA_A0",
        "class": "make_base_simdevice",
        "cat": "PVS",
        "dcs_nm": "ASTXM1610:bl_api:delta_A0",
    },
    {
        "name": "DNM_IDEAL_A0",
        "class": "make_base_simdevice",
        "cat": "PVS",
        "dcs_nm": "ASTXM1610:bl_api:zp:fbk:tr.K",
    },
    {
        "name": "DNM_CALCD_ZPZ",
        "class": "make_base_simdevice",
        "cat": "PVS",
        "dcs_nm": "ASTXM1610:bl_api:zp:fbk:tr.I",
    },
    {
        "name": "DNM_ZPZ_ADJUST",
        "class": "make_base_simdevice",
        "cat": "PVS",
        "dcs_nm": "ASTXM1610:bl_api:zp:adjust_zpz",
    },
    {
        "name": "DNM_FOCAL_LENGTH",
        "class": "make_base_simdevice",
        "cat": "PVS",
        "dcs_nm": "ASTXM1610:bl_api:zp:FL",
        "units": "um",
    },
    {
        "name": "DNM_A0",
        "class": "make_base_simdevice",
        "cat": "PVS",
        "dcs_nm": "ASTXM1610:bl_api:A0",
    },
    {
        "name": "DNM_A0MAX",
        "class": "make_base_simdevice",
        "cat": "PVS",
        "dcs_nm": "ASTXM1610:bl_api:A0Max",
    },
    {
        "name": "DNM_ZPZ_POS",
        "class": "make_base_simdevice",
        "cat": "PVS",
        "dcs_nm": "ASTXM1610:bl_api:zp:zpz_pos",
    },
    {
        "name": "DNM_BEAM_DEFOCUS",
        "class": "make_base_simdevice",
        "cat": "PVS",
        "dcs_nm": "ASTXM1610:bl_api:zp:defocus",
        "units": "um",
    },
    {
        "name": "DNM_ZP_A1",
        "class": "make_base_simdevice",
        "cat": "PVS",
        "dcs_nm": "ASTXM1610:bl_api:zp:def.A",
    },
    {
        "name": "DNM_ZP_DEF",
        "class": "make_base_simdevice",
        "cat": "PVS",
        "dcs_nm": "ASTXM1610:bl_api:zp:def",
    },
    {
        "name": "DNM_OSA_DEF",
        "class": "make_base_simdevice",
        "cat": "PVS",
        "dcs_nm": "ASTXM1610:bl_api:osa:def",
    },
    {
        "name": "DNM_ENERGY_ENABLE",
        "class": "make_base_simdevice",
        "dcs_nm": "ASTXM1610:bl_api:enabled"
    },
    # {
    #     "name": "DNM_FOCUS_MODE",
    #     "class": "make_base_simdevice",
    #     "dcs_nm": "ASTXM1610:bl_api:enabled"
    # },
    {
        "name": "DNM_ENERGY_RBV",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "SIM_VBL1610-I12:ENERGY.RBV" if SIM else "BL1610-I10:ENERGY.RBV",
        "units": "um",
    },
    {
        "name": "DNM_ZPZ_RBV",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "SMTR1610-3-I12-51.RBV",
        "units": "um",
    },

    {
        "name": "DNM_SYSTEM_MODE_FBK",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "SYSTEM:mode:fbk",
    },
    {
        "name": "DNM_SRSTATUS_SHUTTERS",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "SRStatus:shutters",
    },
    {
        "name": "DNM_MONO_EV_FBK",
        "class": "make_basedevice",
        "cat": "PVS",
        # "dcs_nm": "SIM_SM01PGM01:ENERGY_MON",
        "dcs_nm": "SM01PGM01:ENERGY_MON",
        "units": "eV",
        "rd_only": True,
    },

    {
        "name": "DNM_AX1_INTERFER_VOLTS",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "ASTXM1610:Ai:ai0_RBV",
        "rd_only": True,
    },
    {
        "name": "DNM_SFX_PIEZO_VOLTS",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "PZAC1610-3-I12-40:OutputVolt_RBV",
        "rd_only": True,
    },
    {
        "name": "DNM_SFY_PIEZO_VOLTS",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "PZAC1610-3-I12-41:OutputVolt_RBV",
        "rd_only": True,
    },
    {
        "name": "DNM_AX2_INTERFER_VOLTS",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "ASTXM1610:Ai:ai1_RBV",
        "rd_only": True,
    },
    {
        "name": "DNM_RING_CURRENT",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "SIM_PCT1402-01:mA:fbk" if SIM else "PCT1402-01:mA:fbk",
        "units": "mA",
    },
    {
        "name": "DNM_BASELINE_RING_CURRENT",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "SIM_PCT1402-01:mA:fbk" if SIM else "PCT1402-01:mA:fbk",
        "units": "mA",
    },
    {
        "name": "DNM_DFLT_PMT_DWELL",
        "class": "make_basedevice",
        "cat": "PVS",
        "dcs_nm": "MCS1610-310-01:mcs:delay",
    },
    # _pv: BaseDevice('BL1610-I12:MONO1610-I10-01:grating:select:fbk'}, _pv.get_position: _pv.get_enum_str_as_int[{'name': 'Mono_grating_fbk',  'class': _pv

]
dev_dct["ENERGY_DEV"] = [
    {
        "name": "DNM_ENERGY_DEVICE",
        "desc": "Energy device that includes focussing",
        "class": "EnergyDevice",
        "dcs_nm": "SIM_VBL1610-I12:ENERGY" if SIM else "BL1610-I10:ENERGY",
        "energy_nm": "DNM_ENERGY",
        "zz_nm": "DNM_ZONEPLATE_Z",
        "cz_nm": "DNM_COARSE_Z",
        "pos_type": "POS_TYPE_BL",
    },
]

dev_dct["PVS_DONT_RECORD"] = [
    {
        "name": "DNM_TICKER",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": "TRG2400:cycles",
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
    {
        "name": "CCG1410-01:vac:p",
        "class": "make_basedevice",
        "cat": "PRESSURES",
        "dcs_nm": "CCG1410-01:vac:p",
        "desc": "Sec.1",
        "units": "torr",
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "CCG1410-I00-01:vac:p",
        "class": "make_basedevice",
        "cat": "PRESSURES",
        "dcs_nm": "CCG1410-I00-01:vac:p",
        "desc": "Sec.2",
        "units": "torr",
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "CCG1410-I00-02:vac:p",
        "class": "make_basedevice",
        "cat": "PRESSURES",
        "dcs_nm": "CCG1410-I00-02:vac:p",
        "desc": "Sec.4",
        "units": "torr",
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "CCG1610-1-I00-02:vac:p",
        "class": "make_basedevice",
        "cat": "PRESSURES",
        "dcs_nm": "CCG1610-1-I00-02:vac:p",
        "desc": "Sec.6",
        "units": "torr",
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "HCG1610-1-I00-01:vac:p",
        "class": "make_basedevice",
        "cat": "PRESSURES",
        "dcs_nm": "HCG1610-1-I00-01:vac:p",
        "desc": "Sec.7",
        "units": "torr",
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "CCG1610-1-I00-03:vac:p",
        "class": "make_basedevice",
        "cat": "PRESSURES",
        "dcs_nm": "CCG1610-1-I00-03:vac:p",
        "desc": "Sec.8",
        "units": "torr",
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "CCG1610-I10-01:vac:p",
        "class": "make_basedevice",
        "cat": "PRESSURES",
        "dcs_nm": "CCG1610-I10-01:vac:p",
        "desc": "Sec.10",
        "units": "torr",
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "CCG1610-I10-03:vac:p",
        "class": "make_basedevice",
        "cat": "PRESSURES",
        "dcs_nm": "CCG1610-I10-03:vac:p",
        "desc": "Sec.12",
        "units": "torr",
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "CCG1610-I10-04:vac:p",
        "class": "make_basedevice",
        "cat": "PRESSURES",
        "dcs_nm": "CCG1610-I10-04:vac:p",
        "desc": "Sec.13",
        "units": "torr",
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "CCG1610-I12-01:vac:p",
        "class": "make_basedevice",
        "cat": "PRESSURES",
        "dcs_nm": "CCG1610-I12-01:vac:p",
        "desc": "Sec.14",
        "units": "torr",
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "CCG1610-I12-02:vac:p",
        "class": "make_basedevice",
        "cat": "PRESSURES",
        "dcs_nm": "CCG1610-I12-02:vac:p",
        "desc": "Sec.15",
        "units": "torr",
        "pos_type": "POS_TYPE_BL",
    },
    {
        "name": "CCG1610-3-I12-01:vac:p",
        "class": "make_basedevice",
        "cat": "PRESSURES",
        "dcs_nm": "CCG1610-3-I12-01:vac:p",
        "desc": "Sec.16",
        "units": "torr",
        "pos_type": "POS_TYPE_BL",
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
    },
    {
        "name": "TM1610-3-I12-30",
        "class": "make_basedevice",
        "cat": "TEMPERATURES",
        "dcs_nm": "TM1610-3-I12-30",
        "desc": "UVH Sample Coarse Y",
        "units": "deg C",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "TM1610-3-I12-32",
        "class": "make_basedevice",
        "cat": "TEMPERATURES",
        "dcs_nm": "TM1610-3-I12-32",
        "desc": "UVH Detector Y",
        "units": "deg C",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "TM1610-3-I12-21",
        "class": "make_basedevice",
        "cat": "TEMPERATURES",
        "dcs_nm": "TM1610-3-I12-21",
        "desc": "UVH Chamber temp #1",
        "units": "deg C",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "TM1610-3-I12-22",
        "class": "make_basedevice",
        "cat": "TEMPERATURES",
        "dcs_nm": "TM1610-3-I12-22",
        "desc": "UVH Chamber temp #2",
        "units": "deg C",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "TM1610-3-I12-23",
        "class": "make_basedevice",
        "cat": "TEMPERATURES",
        "dcs_nm": "TM1610-3-I12-23",
        "desc": "UVH Chamber temp #3",
        "units": "deg C",
        "pos_type": "POS_TYPE_ES",
    },
    {
        "name": "TM1610-3-I12-24",
        "class": "make_basedevice",
        "cat": "TEMPERATURES",
        "dcs_nm": "TM1610-3-I12-24",
        "desc": "UVH Chamber temp #4",
        "units": "deg C",
        "pos_type": "POS_TYPE_ES",
    },
]


#E712_NAME = "BL2022:E712:" if SIM else "ASTXM1610:E712:",
E712_NAME = "ASTXM1610:E712:"

dev_dct["E712"] = [
    # dev_dct['WIDGETS'][DNM_E712_WIDGET] = E712ControlWidget('%s%s:' % (DEVPRFX, e712_prfx), counter=dev_dct['DETECTORS'][DNM_COUNTER_APD], gate=dev_dct['DIO'][DNM_GATE])
    {
        "name": "DNM_E712_WIDGET",
        "class": "E712ControlWidget",
        "dcs_nm": f"{E712_NAME}",
        "counter": "DETECTORS/DNM_DEFAULT_COUNTER",
        "gate": "DIO/DNM_GATE",
        "con_chk_nm": "CommStatus_RBV",
    },
    {
        "name": "DNM_E712_OPHYD_DEV",
        "class": "E712WGDevice",
        "dcs_nm": f"{E712_NAME}",
        "desc": "E712 wavgenerator flyer device",
        "con_chk_nm": "CommStatus_RBV",
    },
    {
        "name": "DNM_E712_DWELLS",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}dwells",
        "units": "mA",
    },
    {
        "name": "DNM_E712_XRESETPOSNS",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}xreset:posns",
        "units": "um",
    },
    {
        "name": "DNM_E712_YRESETPOSNS",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}yreset:posns",
        "units": "um",
    },
    {
        "name": "DNM_E712_SP_IDS",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}sp_roi:ids",
    },
    {
        "name": "DNM_E712_CURRENT_SP_ID",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}sp_roi:current",
    },
    {
        "name": "DNM_E712_X_START_POS",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}XStartPos",
    },
    {
        "name": "DNM_E712_Y_START_POS",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}YStartPos",
    },
    {
        "name": "DNM_E712_DDL_TBL_0",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}ddl:0",
    },
    {
        "name": "DNM_E712_DDL_TBL_1",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}ddl:1",
    },
    {
        "name": "DNM_E712_DDL_TBL_2",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}ddl:2",
    },
    {
        "name": "DNM_E712_DDL_TBL_3",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}ddl:3",
    },
    {
        "name": "DNM_E712_DDL_TBL_4",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}ddl:4",
    },
    {
        "name": "DNM_E712_DDL_TBL_5",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}ddl:5",
    },
    {
        "name": "DNM_E712_DDL_TBL_6",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}ddl:6",
    },
    {
        "name": "DNM_E712_DDL_TBL_7",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}ddl:7",
    },
    {
        "name": "DNM_E712_DDL_TBL_8",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}ddl:8",
    },
    {
        "name": "DNM_E712_DDL_TBL_9",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}ddl:9",
    },
    # the following are require args wvgen_x, wvgen_y which for astxm are 1,2 (sfx, sfy) and 3,4 for (zpx, zpy)
    {
        "name": "DNM_E712_IMAGE_IDX",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}image_idx",
    },
    {
        "name": "DNM_E712_SCAN_MODE",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}ScanMode",
    },
    {
        "name": "DNM_E712_X_START_MODE",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        # "dcs_nm": f"{E712_NAME}wg1:startmode",
        "dcs_nm": f"{E712_NAME}WavTbl1StartMode",
    },
    {
        "name": "DNM_E712_Y_START_MODE",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        # "dcs_nm": f"{E712_NAME}wg2:startmode",
        "dcs_nm": f"{E712_NAME}WavTbl2StartMode",
    },
    {
        "name": "DNM_E712_X_WAVTBL_IDS",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}wg1_tbl:ids",
    },
    {
        "name": "DNM_E712_Y_WAVTBL_IDS",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}wg2_tbl:ids",
    },
    # short PV's
    {
        "name": "DNM_E712_X_NPTS",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}wg1:npts",
    },
    {
        "name": "DNM_E712_Y_NPTS",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}wg2:npts",
    },
    # pvs that hold the flags for each waveformgenerator (4'}, for each supported sp_roi (max of 10'},
    {
        "name": "DNM_E712_X_USEDDL",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        # "dcs_nm": f"{E712_NAME}wg1:useddl",
        "dcs_nm": f"{E712_NAME}WavTbl1UseDDL",
    },
    {
        "name": "DNM_E712_Y_USEDDL",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        # "dcs_nm": f"{E712_NAME}wg2:useddl",
        "dcs_nm": f"{E712_NAME}WavTbl2UseDDL",
    },
    {
        "name": "DNM_E712_X_USEREINIT",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        # "dcs_nm": f"{E712_NAME}wg1:usereinit",
        "dcs_nm": f"{E712_NAME}WavTbl1UseReinitDDL",
    },
    {
        "name": "DNM_E712_Y_USEREINIT",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        # "dcs_nm": f"{E712_NAME}wg2:usereinit",
        "dcs_nm": f"{E712_NAME}WavTbl2UseReinitDDL",
    },
    {
        "name": "DNM_E712_X_STRT_AT_END",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        # "dcs_nm": f"{E712_NAME}wg1:strtatend",
        "dcs_nm": f"{E712_NAME}WavTbl1StartAtEndPos",
    },
    {
        "name": "DNM_E712_Y_STRT_AT_END",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        # "dcs_nm": f"{E712_NAME}wg2:strtatend",
        "dcs_nm": f"{E712_NAME}WavTbl2StartAtEndPos",
    },
    {
        "name": "DNM_E712_X_USE_TBL_NUM",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}WavGen1UseTblNum",
    },
    {
        "name": "DNM_E712_Y_USE_TBL_NUM",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}WavGen2UseTblNum",
    },
    {
        "name": "DNM_E712_SSPND_CTRLR_FBK",
        "class": "make_basedevice",
        "cat": "PVS_DONT_RECORD",
        "dcs_nm": f"{E712_NAME}SuspendCtrlrFbk",
    },

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
