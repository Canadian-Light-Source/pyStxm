"""
Created on Jan 30, 2017

@author: bergr
"""
e712_errors = {}
e712_errors[0] = ("PI_CNTR_NO_ERROR ", "No error")
e712_errors[1] = ("PI_CNTR_PARAM_SYNTAX", "Parameter syntax error")
e712_errors[2] = ("PI_CNTR_UNKNOWN_COMMAND", "Unknown command")
e712_errors[3] = (
    "PI_CNTR_COMMAND_TOO_LONG",
    "Command length out of limits or command buffer overrun",
)
e712_errors[4] = ("PI_CNTR_SCAN_ERROR", "Error while scanning")
e712_errors[5] = (
    "PI_CNTR_MOVE_WITHOUT_REF_OR_NO_SERVO",
    "Unallowable move attempted on unreferenced axis, or move attempted with servo off",
)
e712_errors[6] = ("PI_CNTR_INVALID_SGA_PARAM", "Parameter for SGA not valid")
e712_errors[7] = ("PI_CNTR_POS_OUT_OF_LIMITS", "Position out of limits")
e712_errors[8] = ("PI_CNTR_VEL_OUT_OF_LIMITS", "Velocity out of limits")
e712_errors[9] = (
    "PI_CNTR_SET_PIVOT_NOT_POSSIBLE",
    "Attempt to set pivot point while U,V and W not all 0",
)
e712_errors[10] = ("PI_CNTR_STOP", "Controller was stopped by command")
e712_errors[11] = (
    "PI_CNTR_SST_OR_SCAN_RANGE",
    "Parameter for SST or for one of the embedded scan algorithms out of range",
)
e712_errors[12] = (
    "PI_CNTR_INVALID_SCAN_AXES",
    "Invalid axis combination for fast scan",
)
e712_errors[13] = ("PI_CNTR_INVALID_NAV_PARAM", "Parameter for NAV out of range")
e712_errors[14] = ("PI_CNTR_INVALID_ANALOG_INPUT", "Invalid analog channel")
e712_errors[15] = ("PI_CNTR_INVALID_AXIS_IDENTIFIER", "Invalid axis identifier")
e712_errors[16] = ("PI_CNTR_INVALID_STAGE_NAME", "Unknown stage name")
e712_errors[17] = ("PI_CNTR_PARAM_OUT_OF_RANGE", "Parameter out of range")
e712_errors[18] = ("PI_CNTR_INVALID_MACRO_NAME", "Invalid macro name")
e712_errors[19] = ("PI_CNTR_MACRO_RECORD", "Error while recording macro")
e712_errors[20] = ("PI_CNTR_MACRO_NOT_FOUND", "Macro not found")
e712_errors[21] = ("PI_CNTR_AXIS_HAS_NO_BRAKE", "Axis has no brake")
e712_errors[22] = ("PI_CNTR_DOUBLE_AXIS", "Axis identifier specified more than once")
e712_errors[23] = ("PI_CNTR_ILLEGAL_AXIS", "Illegal axis")
e712_errors[24] = ("PI_CNTR_PARAM_NR", "Incorrect number of parameters")
e712_errors[25] = ("PI_CNTR_INVALID_REAL_NR", "Invalid floating point number")
e712_errors[26] = ("PI_CNTR_MISSING_PARAM", "Parameter missing")
e712_errors[27] = ("PI_CNTR_SOFT_LIMIT_OUT_OF_RANGE", "Soft limit out of range")
e712_errors[28] = ("PI_CNTR_NO_MANUAL_PAD", "No manual pad found")
e712_errors[29] = ("PI_CNTR_NO_JUMP", "No more step-response values")
e712_errors[30] = ("PI_CNTR_INVALID_JUMP", "No step-response values recorded")
e712_errors[31] = ("PI_CNTR_AXIS_HAS_NO_REFERENCE", "Axis has no reference sensor")
e712_errors[32] = ("PI_CNTR_STAGE_HAS_NO_LIM_SWITCH", "Axis has no limit switch")
e712_errors[33] = ("PI_CNTR_NO_RELAY_CARD", "No relay card installed")
e712_errors[34] = (
    "PI_CNTR_CMD_NOT_ALLOWED_FOR_STAGE",
    "Command not allowed for selected stage(s)",
)
e712_errors[35] = ("PI_CNTR_NO_DIGITAL_INPUT", "No digital input installed")
e712_errors[36] = ("PI_CNTR_NO_DIGITAL_OUTPUT", "No digital output configured")
e712_errors[37] = ("PI_CNTR_NO_MCM", "No more MCM responses")
e712_errors[38] = ("PI_CNTR_INVALID_MCM", "No MCM values recorded")
e712_errors[39] = ("PI_CNTR_INVALID_CNTR_NUMBER", "Controller number invalid")
e712_errors[40] = ("PI_CNTR_NO_JOYSTICK_CONNECTED", "No joystick configured")
e712_errors[41] = (
    "PI_CNTR_INVALID_EGE_AXIS",
    "Invalid axis for electronic gearing, axis can not be slave",
)
e712_errors[42] = (
    "PI_CNTR_SLAVE_POSITION_OUT_OF_RANGE",
    "Position of slave axis is out of range",
)
e712_errors[43] = (
    "PI_CNTR_COMMAND_EGE_SLAVE",
    "Slave axis cannot be commanded directly when electronic gearing is enabled",
)
e712_errors[44] = (
    "PI_CNTR_JOYSTICK_CALIBRATION_FAILED",
    "Calibration of joystick failed",
)
e712_errors[45] = ("PI_CNTR_REFERENCING_FAILED", "Referencing failed")
e712_errors[46] = ("PI_CNTR_OPM_MISSING", "OPM (Optical Power Meter) missing")
e712_errors[47] = (
    "PI_CNTR_OPM_NOT_INITIALIZED",
    "OPM (Optical Power Meter) not initialized or cannot be initialized",
)
e712_errors[48] = (
    "PI_CNTR_OPM_COM_ERROR",
    "OPM (Optical Power Meter) Communication Error",
)
e712_errors[49] = ("PI_CNTR_MOVE_TO_LIMIT_SWITCH_FAILED", "Move to limit switch failed")
e712_errors[50] = (
    "PI_CNTR_REF_WITH_REF_DISABLED",
    "Attempt to reference axis with referencing disabled",
)
e712_errors[51] = (
    "PI_CNTR_AXIS_UNDER_JOYSTICK_CONTROL",
    "Selected axis is controlled by joystick",
)
e712_errors[52] = (
    "PI_CNTR_COMMUNICATION_ERROR",
    "Controller detected communication error",
)
e712_errors[53] = ("PI_CNTR_DYNAMIC_MOVE_IN_PROCESS", "MOV! motion still in progress")
e712_errors[54] = ("PI_CNTR_UNKNOWN_PARAMETER", "Unknown parameter")
e712_errors[55] = ("PI_CNTR_NO_REP_RECORDED", "No commands were recorded with REP")
e712_errors[56] = ("PI_CNTR_INVALID_PASSWORD", "Password invalid")
e712_errors[57] = ("PI_CNTR_INVALID_RECORDER_CHAN", "Data Record Table does not exist")
e712_errors[58] = (
    "PI_CNTR_INVALID_RECORDER_SRC_OPT",
    "Source does not exist; number too low or too high",
)
e712_errors[59] = (
    "PI_CNTR_INVALID_RECORDER_SRC_CHAN",
    "Source Record Table number too low or too high",
)
e712_errors[60] = (
    "PI_CNTR_PARAM_PROTECTION",
    "Protected Param: current Command Level (CCL) too low",
)
e712_errors[61] = (
    "PI_CNTR_AUTOZERO_RUNNING",
    "Command execution not possible while Autozero is running",
)
e712_errors[62] = (
    "PI_CNTR_NO_LINEAR_AXIS",
    "Autozero requires at least one linear axis",
)
e712_errors[63] = ("PI_CNTR_INIT_RUNNING", "Initialization still in progress")
e712_errors[64] = ("PI_CNTR_READ_ONLY_PARAMETER", "Parameter is read-only")
e712_errors[65] = (
    "PI_CNTR_PAM_NOT_FOUND",
    "Parameter not found in non-volatile memory",
)
e712_errors[66] = ("PI_CNTR_VOL_OUT_OF_LIMITS", "Voltage out of limits")
e712_errors[67] = (
    "PI_CNTR_WAVE_TOO_LARGE",
    "Not enough memory available for requested wave curve",
)
e712_errors[68] = (
    "PI_CNTR_NOT_ENOUGH_DDL_MEMORY",
    "Not enough memory available for DDL table; DDL can not be started",
)
e712_errors[69] = (
    "PI_CNTR_DDL_TIME_DELAY_TOO_LARGE",
    "Time delay larger than DDL table; DDL can not be started",
)
e712_errors[70] = (
    "PI_CNTR_DIFFERENT_ARRAY_LENGTH",
    "The requested arrays have different lengths; query them separately",
)
e712_errors[71] = (
    "PI_CNTR_GEN_SINGLE_MODE_RESTART",
    "Attempt to restart the generator while it is running in single step mode",
)
e712_errors[72] = (
    "PI_CNTR_ANALOG_TARGET_ACTIVE",
    "Motion commands and wave generator activation are not allowed when analog target is active",
)
e712_errors[73] = (
    "PI_CNTR_WAVE_GENERATOR_ACTIVE",
    "Motion commands are not allowed when wave generator is active",
)
e712_errors[74] = (
    "PI_CNTR_AUTOZERO_DISABLED",
    "No sensor channel or no piezo channel connected to selected axis (sensor and piezo matrix)",
)
e712_errors[75] = (
    "PI_CNTR_NO_WAVE_SELECTED",
    "Generator started (WGO) without having selected a wave table (WSL).",
)
e712_errors[76] = (
    "PI_CNTR_IF_BUFFER_OVERRUN",
    "Interface buffer did overrun and command couldnt be received correctly",
)
e712_errors[77] = (
    "PI_CNTR_NOT_ENOUGH_RECORDED_DATA",
    "Data Record Table does not hold enough recorded data",
)
e712_errors[78] = (
    "PI_CNTR_TABLE_DEACTIVATED",
    "Data Record Table is not configured for recording",
)
e712_errors[79] = (
    "PI_CNTR_OPENLOOP_VALUE_SET_WHEN_SERVO_ON",
    "Open-loop commands (SVA, SVR) are not allowed when servo is on",
)
e712_errors[80] = ("PI_CNTR_RAM_ERROR", "Hardware error affecting RAM")
e712_errors[81] = ("PI_CNTR_MACRO_UNKNOWN_COMMAND", "Not macro command")
e712_errors[82] = ("PI_CNTR_MACRO_PC_ERROR", "Macro counter out of range")
e712_errors[83] = ("PI_CNTR_JOYSTICK_ACTIVE", "Joystick is active")
e712_errors[84] = ("PI_CNTR_MOTOR_IS_OFF", "Motor is off")
e712_errors[85] = ("PI_CNTR_ONLY_IN_MACRO", "Macro-only command")
e712_errors[86] = ("PI_CNTR_JOYSTICK_UNKNOWN_AXIS", "Invalid joystick axis")
e712_errors[87] = ("PI_CNTR_JOYSTICK_UNKNOWN_ID", "Joystick unknown")
e712_errors[88] = ("PI_CNTR_REF_MODE_IS_ON", "Move without referenced stage")
e712_errors[89] = (
    "PI_CNTR_NOT_ALLOWED_IN_CURRENT_MOTION_MODE",
    "Command not allowed in current motion mode",
)
e712_errors[90] = (
    "PI_CNTR_DIO_AND_TRACING_NOT_POSSIBLE",
    "No tracing possible while digital IOs are used on this HW revision. Reconnect to switch operation mode.",
)
e712_errors[91] = ("PI_CNTR_COLLISION", "Move not possible, would cause collision")
e712_errors[92] = (
    "PI_CNTR_SLAVE_NOT_FAST_ENOUGH",
    "Stage is not capable of following the master. Check the gear ratio(SRA).",
)
e712_errors[93] = (
    "PI_CNTR_CMD_NOT_ALLOWED_WHILE_AXIS_IN_MOTION",
    "This command is not allowed while the affected axis or its master is in motion.",
)
e712_errors[94] = (
    "PI_CNTR_OPEN_LOOP_JOYSTICK_ENABLED",
    "Servo cannot be switched on when open-loop joystick control is enabled.",
)
e712_errors[95] = (
    "PI_CNTR_INVALID_SERVO_STATE_FOR_PARAMETER",
    "This parameter cannot be changed in current servo mode.",
)
e712_errors[96] = ("PI_CNTR_UNKNOWN_STAGE_NAME", "Unknown stage name")
e712_errors[100] = (
    "PI_LABVIEW_ERROR",
    "PI LabVIEW driver reports error. See source control for details.",
)
e712_errors[200] = ("PI_CNTR_NO_AXIS", "No stage connected to axis")
e712_errors[201] = ("PI_CNTR_NO_AXIS_PARAM_FILE", "File with axis parameters not found")
e712_errors[202] = ("PI_CNTR_INVALID_AXIS_PARAM_FILE", "Invalid axis parameter file")
e712_errors[203] = (
    "PI_CNTR_NO_AXIS_PARAM_BACKUP",
    "Backup file with axis parameters not found",
)
e712_errors[204] = ("PI_CNTR_RESERVED_204", "PI internal error code 204")
e712_errors[205] = ("PI_CNTR_SMO_WITH_SERVO_ON", "SMO with servo on")
e712_errors[206] = ("PI_CNTR_UUDECODE_INCOMPLETE_HEADER", "uudecode: incomplete header")
e712_errors[207] = ("PI_CNTR_UUDECODE_NOTHING_TO_DECODE", "uudecode: nothing to decode")
e712_errors[208] = ("PI_CNTR_UUDECODE_ILLEGAL_FORMAT", "uudecode: illegal UUE format")
e712_errors[209] = ("PI_CNTR_CRC32_ERROR", "CRC32 error")
e712_errors[210] = (
    "PI_CNTR_ILLEGAL_FILENAME",
    "Illegal file name (must be 8-0 format)",
)
e712_errors[211] = ("PI_CNTR_FILE_NOT_FOUND", "File not found on controller")
e712_errors[212] = ("PI_CNTR_FILE_WRITE_ERROR", "Error writing file on controller")
e712_errors[213] = (
    "PI_CNTR_DTR_HINDERS_VELOCITY_CHANGE",
    "VEL command not allowed in DTR Command Mode",
)
e712_errors[214] = ("PI_CNTR_POSITION_UNKNOWN", "Position calculations failed")
e712_errors[215] = (
    "PI_CNTR_CONN_POSSIBLY_BROKEN",
    "The connection between controller and stage may be broken",
)
e712_errors[216] = (
    "PI_CNTR_ON_LIMIT_SWITCH",
    "The connected stage has driven into a limit switch, call CLR to resume operation",
)
e712_errors[217] = (
    "PI_CNTR_UNEXPECTED_STRUT_STOP",
    "Strut test command failed because of an unexpected strut stop",
)
e712_errors[218] = (
    "PI_CNTR_POSITION_BASED_ON_ESTIMATION",
    "While MOV! is running position can only be estimated!",
)
e712_errors[219] = (
    "PI_CNTR_POSITION_BASED_ON_INTERPOLATION",
    "Position was calculated during MOV motion",
)
e712_errors[230] = ("PI_CNTR_INVALID_HANDLE", "Invalid handle")
e712_errors[231] = ("PI_CNTR_NO_BIOS_FOUND", "No bios found")
e712_errors[232] = ("PI_CNTR_SAVE_SYS_CFG_FAILED", "Save system configuration failed")
e712_errors[233] = ("PI_CNTR_LOAD_SYS_CFG_FAILED", "Load system configuration failed")
e712_errors[301] = ("PI_CNTR_SEND_BUFFER_OVERFLOW", "Send buffer overflow")
e712_errors[302] = ("PI_CNTR_VOLTAGE_OUT_OF_LIMITS", "Voltage out of limits")
e712_errors[303] = (
    "PI_CNTR_OPEN_LOOP_MOTION_SET_WHEN_SERVO_ON",
    "Open-loop motion attempted when servo ON",
)
e712_errors[304] = ("PI_CNTR_RECEIVING_BUFFER_OVERFLOW", "Received command is too long")
e712_errors[305] = ("PI_CNTR_EEPROM_ERROR", "Error while reading/writing EEPROM")
e712_errors[306] = ("PI_CNTR_I2C_ERROR", "Error on I2C bus")
e712_errors[307] = ("PI_CNTR_RECEIVING_TIMEOUT", "Timeout while receiving command")
e712_errors[308] = (
    "PI_CNTR_TIMEOUT",
    "A lengthy operation has not finished in the expected time",
)
e712_errors[309] = ("PI_CNTR_MACRO_OUT_OF_SPACE", "Insufficient space to store macro")
e712_errors[310] = (
    "PI_CNTR_EUI_OLDVERSION_CFGDATA",
    "Configuration data has old version number",
)
e712_errors[311] = ("PI_CNTR_EUI_INVALID_CFGDATA", "Invalid configuration data")
e712_errors[333] = ("PI_CNTR_HARDWARE_ERROR", "Internal hardware error")
e712_errors[400] = ("PI_CNTR_WAV_INDEX_ERROR", "Wave generator index error")
e712_errors[401] = ("PI_CNTR_WAV_NOT_DEFINED", "Wave table not defined")
e712_errors[402] = ("PI_CNTR_WAV_TYPE_NOT_SUPPORTED", "Wave type not supported")
e712_errors[403] = ("PI_CNTR_WAV_LENGTH_EXCEEDS_LIMIT", "Wave length exceeds limit")
e712_errors[404] = ("PI_CNTR_WAV_PARAMETER_NR", "Wave parameter number error")
e712_errors[405] = ("PI_CNTR_WAV_PARAMETER_OUT_OF_LIMIT", "Wave parameter out of range")
e712_errors[406] = ("PI_CNTR_WGO_BIT_NOT_SUPPORTED", "WGO command bit not supported")
e712_errors[500] = (
    "PI_CNTR_EMERGENCY_STOP_BUTTON_ACTIVATED",
    'The "red knob" is still set and disables system',
)
e712_errors[501] = (
    "PI_CNTR_EMERGENCY_STOP_BUTTON_WAS_ACTIVATED",
    'The "red knob" was activated and still disables system - reanimation required',
)
e712_errors[502] = (
    "PI_CNTR_REDUNDANCY_LIMIT_EXCEEDED",
    "Position consistency check failed",
)
e712_errors[503] = (
    "PI_CNTR_COLLISION_SWITCH_ACTIVATED",
    "Hardware collision sensor(s) are activated",
)
e712_errors[504] = (
    "PI_CNTR_FOLLOWING_ERROR",
    "Strut following error occurred, e.g. caused by overload or encoder failure",
)
e712_errors[555] = ("PI_CNTR_UNKNOWN_ERROR", "BasMac: unknown controller error")
e712_errors[601] = ("PI_CNTR_NOT_ENOUGH_MEMORY", "not enough memory")
e712_errors[602] = ("PI_CNTR_HW_VOLTAGE_ERROR", "hardware voltage error")
e712_errors[603] = ("PI_CNTR_HW_TEMPERATURE_ERROR", "hardware temperature out of range")
e712_errors[604] = (
    "PI_CNTR_POSITION_ERROR_TOO_HIGH",
    "Position error of any axis in the system is too high",
)
e712_errors[606] = (
    "PI_CNTR_INPUT_OUT_OF_RANGE",
    "Maximum value of input signal has been exceeded",
)
e712_errors[1000] = ("PI_CNTR_TOO_MANY_NESTED_MACROS", "Too many nested macros")
e712_errors[1001] = ("PI_CNTR_MACRO_ALREADY_DEFINED", "Macro already defined")
e712_errors[1002] = ("PI_CNTR_NO_MACRO_RECORDING", "Macro recording not activated")
e712_errors[1003] = ("PI_CNTR_INVALID_MAC_PARAM", "Invalid parameter for MAC")
e712_errors[1004] = ("PI_CNTR_RESERVED_1004", "PI internal error code 1004")
e712_errors[1005] = (
    "PI_CNTR_CONTROLLER_BUSY",
    "Controller is busy with some lengthy operation (e.g. reference move, fast scan algorithm)",
)
e712_errors[1006] = (
    "PI_CNTR_INVALID_IDENTIFIER",
    "Invalid identifier (invalid special characters, ...)",
)
e712_errors[1007] = (
    "PI_CNTR_UNKNOWN_VARIABLE_OR_ARGUMENT",
    "Variable or argument not defined",
)
e712_errors[1008] = ("PI_CNTR_RUNNING_MACRO", "Controller is (already) running a macro")
e712_errors[1009] = (
    "PI_CNTR_MACRO_INVALID_OPERATOR",
    "Invalid or missing operator for condition. Check necessary spaces around operator.",
)
e712_errors[1063] = (
    "PI_CNTR_EXT_PROFILE_UNALLOWED_CMD",
    "User Profile Mode: Command is not allowed, check for required preparatory commands",
)
e712_errors[1064] = (
    "PI_CNTR_EXT_PROFILE_EXPECTING_MOTION_ERROR",
    "User Profile Mode: First target position in User Profile is too far from current position",
)
e712_errors[1065] = (
    "PI_CNTR_PROFILE_ACTIVE",
    "Controller is (already) in User Profile Mode",
)
e712_errors[1066] = (
    "PI_CNTR_PROFILE_INDEX_OUT_OF_RANGE",
    "User Profile Mode: Block or Data Set index out of allowed range",
)
e712_errors[1071] = (
    "PI_CNTR_PROFILE_OUT_OF_MEMORY",
    "User Profile Mode: Out of memory",
)
e712_errors[1072] = (
    "PI_CNTR_PROFILE_WRONG_CLUSTER",
    "User Profile Mode: Cluster is not assigned to this axis",
)
e712_errors[1073] = (
    "PI_CNTR_PROFILE_UNKNOWN_CLUSTER_IDENTIFIER",
    "Unknown cluster identifier",
)
e712_errors[2000] = (
    "PI_CNTR_ALREADY_HAS_SERIAL_NUMBER",
    "Controller already has a serial number",
)
e712_errors[4000] = ("PI_CNTR_SECTOR_ERASE_FAILED", "Sector erase failed")
e712_errors[4001] = ("PI_CNTR_FLASH_PROGRAM_FAILED", "Flash program failed")
e712_errors[4002] = ("PI_CNTR_FLASH_READ_FAILED", "Flash read failed")
e712_errors[4003] = ("PI_CNTR_HW_MATCHCODE_ERROR", "HW match code missing/invalid")
e712_errors[4004] = ("PI_CNTR_FW_MATCHCODE_ERROR", "FW match code missing/invalid")
e712_errors[4005] = ("PI_CNTR_HW_VERSION_ERROR", "HW version missing/invalid")
e712_errors[4006] = ("PI_CNTR_FW_VERSION_ERROR", "FW version missing/invalid")
e712_errors[4007] = ("PI_CNTR_FW_UPDATE_ERROR", "FW update failed")
e712_errors[4008] = ("PI_CNTR_FW_CRC_PAR_ERROR", "FW Parameter CRC wrong")
e712_errors[4009] = ("PI_CNTR_FW_CRC_FW_ERROR", "FW CRC wrong")
e712_errors[5000] = (
    "PI_CNTR_INVALID_PCC_SCAN_DATA",
    "PicoCompensation scan data is not valid",
)
e712_errors[5001] = (
    "PI_CNTR_PCC_SCAN_RUNNING",
    "PicoCompensation is running, some actions can not be executed during scanning/recording",
)
e712_errors[5002] = (
    "PI_CNTR_INVALID_PCC_AXIS",
    "Given axis can not be defined as PPC axis",
)
e712_errors[5003] = (
    "PI_CNTR_PCC_SCAN_OUT_OF_RANGE",
    "Defined scan area is larger than the travel range",
)
e712_errors[5004] = (
    "PI_CNTR_PCC_TYPE_NOT_EXISTING",
    "Given PicoCompensation type is not defined",
)
e712_errors[5005] = ("PI_CNTR_PCC_PAM_ERROR", "PicoCompensation parameter error")
e712_errors[5006] = (
    "PI_CNTR_PCC_TABLE_ARRAY_TOO_LARGE",
    "PicoCompensation table is larger than maximum table length",
)
e712_errors[5100] = ("PI_CNTR_NEXLINE_ERROR", "Common error in Nexline firmware module")
e712_errors[5101] = (
    "PI_CNTR_CHANNEL_ALREADY_USED",
    "Output channel for Nexline can not be redefined for other usage",
)
e712_errors[5102] = (
    "PI_CNTR_NEXLINE_TABLE_TOO_SMALL",
    "Memory for Nexline signals is too small",
)
e712_errors[5103] = (
    "PI_CNTR_RNP_WITH_SERVO_ON",
    "RNP can not be executed if axis is in closed loop",
)
e712_errors[5104] = ("PI_CNTR_RNP_NEEDED", "relax procedure (RNP) needed")
e712_errors[5200] = (
    "PI_CNTR_AXIS_NOT_CONFIGURED",
    "Axis must be configured for this action",
)
#### Interface Errors
e712_errors[0] = ("COM_NO_ERROR", "No error occurred during function call")
e712_errors[-1] = ("COM_ERROR", "Error during com operation (could not be specified)")
e712_errors[-2] = ("SEND_ERROR", "Error while sending data")
e712_errors[-3] = ("REC_ERROR", "Error while receiving data")
e712_errors[-4] = ("NOT_CONNECTED_ERROR", "Not connected (no port with given ID open)")
e712_errors[-5] = ("COM_BUFFER_OVERFLOW", "Buffer overflow")
e712_errors[-6] = ("CONNECTION_FAILED", "Error while opening port")
e712_errors[-7] = ("COM_TIMEOUT", "Timeout error")
e712_errors[-8] = ("COM_MULTILINE_RESPONSE", "There are more lines waiting in buffer")
e712_errors[-9] = (
    "COM_INVALID_ID",
    "There is no interface or DLL handle with the given ID",
)
e712_errors[-10] = (
    "COM_NOTIFY_EVENT_ERROR",
    "Event/message for notification could not be opened",
)
e712_errors[-11] = (
    "COM_NOT_IMPLEMENTED",
    "Function not supported by this interface type",
)
e712_errors[-12] = ("COM_ECHO_ERROR", 'Error while sending "echoed" data')
e712_errors[-13] = ("COM_GPIB_EDVR", "IEEE488: System error")
e712_errors[-14] = ("COM_GPIB_ECIC", "IEEE488: Function requires GPIB board to be CIC")
e712_errors[-15] = ("COM_GPIB_ENOL", "IEEE488: Write function detected no listeners")
e712_errors[-16] = ("COM_GPIB_EADR", "IEEE488: Interface board not addressed correctly")
e712_errors[-17] = ("COM_GPIB_EARG", "IEEE488: Invalid argument to function call")
e712_errors[-18] = ("COM_GPIB_ESAC", "IEEE488: Function requires GPIB board to be SAC")
e712_errors[-19] = ("COM_GPIB_EABO", "IEEE488: I/O operation aborted")
e712_errors[-20] = ("COM_GPIB_ENEB", "IEEE488: Interface board not found")
e712_errors[-21] = ("COM_GPIB_EDMA", "IEEE488: Error performing DMA")
e712_errors[-22] = (
    "COM_GPIB_EOIP",
    "IEEE488: I/O operation started before previous operation completed",
)
e712_errors[-23] = ("COM_GPIB_ECAP", "IEEE488: No capability for intended operation")
e712_errors[-24] = ("COM_GPIB_EFSO", "IEEE488: File system operation error")
e712_errors[-25] = ("COM_GPIB_EBUS", "IEEE488: Command error during device call")
e712_errors[-26] = ("COM_GPIB_ESTB", "IEEE488: Serial poll-status byte lost")
e712_errors[-27] = ("COM_GPIB_ESRQ", "IEEE488: SRQ remains asserted")
e712_errors[-28] = ("COM_GPIB_ETAB", "IEEE488: Return buffer full")
e712_errors[-29] = ("COM_GPIB_ELCK", "IEEE488: Address or board locked")
e712_errors[-30] = (
    "COM_RS_INVALID_DATA_BITS",
    "RS-232: 5 data bits with 2 stop bits is an invalid combination, as is 6, 7, or 8 data bits with 1.5 stop bits",
)
e712_errors[-31] = ("COM_ERROR_RS_SETTINGS", "RS-232: Error configuring the COM port")
e712_errors[-32] = (
    "COM_INTERNAL_RESOURCES_ERROR",
    "Error dealing with internal system resources (events, threads, ...)",
)
e712_errors[-33] = (
    "COM_DLL_FUNC_ERROR",
    "A DLL or one of the required functions could not be loaded",
)
e712_errors[-34] = ("COM_FTDIUSB_INVALID_HANDLE", "FTDIUSB: invalid handle")
e712_errors[-35] = ("COM_FTDIUSB_DEVICE_NOT_FOUND", "FTDIUSB: device not found")
e712_errors[-36] = ("COM_FTDIUSB_DEVICE_NOT_OPENED", "FTDIUSB: device not opened")
e712_errors[-37] = ("COM_FTDIUSB_IO_ERROR", "FTDIUSB: IO error")
e712_errors[-38] = (
    "COM_FTDIUSB_INSUFFICIENT_RESOURCES",
    "FTDIUSB: insufficient resources",
)
e712_errors[-39] = ("COM_FTDIUSB_INVALID_PARAMETER", "FTDIUSB: invalid parameter")
e712_errors[-40] = ("COM_FTDIUSB_INVALID_BAUD_RATE", "FTDIUSB: invalid baud rate")
e712_errors[-41] = (
    "COM_FTDIUSB_DEVICE_NOT_OPENED_FOR_ERASE",
    "FTDIUSB: device not opened for erase",
)
e712_errors[-42] = (
    "COM_FTDIUSB_DEVICE_NOT_OPENED_FOR_WRITE",
    "FTDIUSB: device not opened for write",
)
e712_errors[-43] = (
    "COM_FTDIUSB_FAILED_TO_WRITE_DEVICE",
    "FTDIUSB: failed to write device",
)
e712_errors[-44] = ("COM_FTDIUSB_EEPROM_READ_FAILED", "FTDIUSB: EEPROM read failed")
e712_errors[-45] = ("COM_FTDIUSB_EEPROM_WRITE_FAILED", "FTDIUSB: EEPROM write failed")
e712_errors[-46] = ("COM_FTDIUSB_EEPROM_ERASE_FAILED", "FTDIUSB: EEPROM erase failed")
e712_errors[-47] = ("COM_FTDIUSB_EEPROM_NOT_PRESENT", "FTDIUSB: EEPROM not present")
e712_errors[-48] = (
    "COM_FTDIUSB_EEPROM_NOT_PROGRAMMED",
    "FTDIUSB: EEPROM not programmed",
)
e712_errors[-49] = ("COM_FTDIUSB_INVALID_ARGS", "FTDIUSB: invalid arguments")
e712_errors[-50] = ("COM_FTDIUSB_NOT_SUPPORTED", "FTDIUSB: not supported")
e712_errors[-51] = ("COM_FTDIUSB_OTHER_ERROR", "FTDIUSB: other error")
e712_errors[-52] = (
    "COM_PORT_ALREADY_OPEN",
    "Error while opening the COM port: was already open",
)
e712_errors[-53] = (
    "COM_PORT_CHECKSUM_ERROR",
    "Checksum error in received data from COM port",
)
e712_errors[-54] = (
    "COM_SOCKET_NOT_READY",
    "Socket not ready, you should call the function again",
)
e712_errors[-55] = ("COM_SOCKET_PORT_IN_USE", "Port is used by another socket")
e712_errors[-56] = ("COM_SOCKET_NOT_CONNECTED", "Socket not connected (or not valid)")
e712_errors[-57] = ("COM_SOCKET_TERMINATED", "Connection terminated (by peer)")
e712_errors[-58] = ("COM_SOCKET_NO_RESPONSE", "Cant connect to peer")
e712_errors[-59] = (
    "COM_SOCKET_INTERRUPTED",
    "Operation was interrupted by a nonblocked signal",
)
e712_errors[-60] = ("COM_PCI_INVALID_ID", "No device with this ID is present")
e712_errors[-61] = (
    "COM_PCI_ACCESS_DENIED",
    "Driver could not be opened (on Vista: run as administrator!)",
)


#######  DLL Errors
e712_errors[-1001] = ("PI_UNKNOWN_AXIS_IDENTIFIER", "Unknown axis identifier")
e712_errors[-1002] = (
    "PI_NR_NAV_OUT_OF_RANGE",
    "Number for NAV out of range--must be in [1,10000]",
)
e712_errors[-1003] = (
    "PI_INVALID_SGA",
    "Invalid value for SGA--must be one of 1, 10, 100, 1000",
)
e712_errors[-1004] = ("PI_UNEXPECTED_RESPONSE", "Controller sent unexpected response")
e712_errors[-1005] = (
    "PI_NO_MANUAL_PAD",
    "No manual control pad installed, calls to SMA and related commands are not allowed",
)
e712_errors[-1006] = (
    "PI_INVALID_MANUAL_PAD_KNOB",
    "Invalid number for manual control pad knob",
)
e712_errors[-1007] = (
    "PI_INVALID_MANUAL_PAD_AXIS",
    "Axis not currently controlled by a manual control pad",
)
e712_errors[-1008] = (
    "PI_CONTROLLER_BUSY",
    "Controller is busy with some lengthy operation (e.g. reference move, fast scan algorithm)",
)
e712_errors[-1009] = ("PI_THREAD_ERROR", "Internal error--could not start thread")
e712_errors[-1010] = (
    "PI_IN_MACRO_MODE",
    "Controller is (already) in macro mode--command not valid in macro mode",
)
e712_errors[-1011] = (
    "PI_NOT_IN_MACRO_MODE",
    "Controller not in macro mode--command not valid unless macro mode active",
)
e712_errors[-1012] = (
    "PI_MACRO_FILE_ERROR",
    "Could not open file to write or read macro",
)
e712_errors[-1013] = (
    "PI_NO_MACRO_OR_EMPTY",
    "No macro with given name on controller, or macro is empty",
)
e712_errors[-1014] = ("PI_MACRO_EDITOR_ERROR", "Internal error in macro editor")
e712_errors[-1015] = (
    "PI_INVALID_ARGUMENT",
    "One or more arguments given to function is invalid (empty string, index out of range, ...)",
)
e712_errors[-1016] = (
    "PI_AXIS_ALREADY_EXISTS",
    "Axis identifier is already in use by a connected stage",
)
e712_errors[-1017] = ("PI_INVALID_AXIS_IDENTIFIER", "Invalid axis identifier")
e712_errors[-1018] = ("PI_COM_ARRAY_ERROR", "Could not access array data in COM server")
e712_errors[-1019] = (
    "PI_COM_ARRAY_RANGE_ERROR",
    "Range of array does not fit the number of parameters",
)
e712_errors[-1020] = (
    "PI_INVALID_SPA_CMD_ID",
    "Invalid parameter ID given to SPA or SPA?",
)
e712_errors[-1021] = (
    "PI_NR_AVG_OUT_OF_RANGE",
    "Number for AVG out of range--must be >0",
)
e712_errors[-1022] = (
    "PI_WAV_SAMPLES_OUT_OF_RANGE",
    "Incorrect number of samples given to WAV",
)
e712_errors[-1023] = ("PI_WAV_FAILED", "Generation of wave failed")
e712_errors[-1024] = (
    "PI_MOTION_ERROR",
    "Motion error while axis in motion, call CLR to resume operation",
)
e712_errors[-1025] = ("PI_RUNNING_MACRO", "Controller is (already) running a macro")
e712_errors[-1026] = (
    "PI_PZT_CONFIG_FAILED",
    "Configuration of PZT stage or amplifier failed",
)
e712_errors[-1027] = (
    "PI_PZT_CONFIG_INVALID_PARAMS",
    "Current settings are not valid for desired configuration",
)
e712_errors[-1028] = ("PI_UNKNOWN_CHANNEL_IDENTIFIER", "Unknown channel identifier")
e712_errors[-1029] = (
    "PI_WAVE_PARAM_FILE_ERROR",
    "Error while reading/writing wave generator parameter file",
)
e712_errors[-1030] = (
    "PI_UNKNOWN_WAVE_SET",
    "Could not find description of wave form. Maybe WG.INI is missing?",
)
e712_errors[-1031] = (
    "PI_WAVE_EDITOR_FUNC_NOT_LOADED",
    "The WGWaveEditor DLL function was not found at startup",
)
e712_errors[-1032] = ("PI_USER_CANCELLED", "The user cancelled a dialog")
e712_errors[-1033] = ("PI_C844_ERROR", "Error from C-844 Controller")
e712_errors[-1034] = (
    "PI_DLL_NOT_LOADED",
    "DLL necessary to call function not loaded, or function not found in DLL",
)
e712_errors[-1035] = (
    "PI_PARAMETER_FILE_PROTECTED",
    "The open parameter file is protected and cannot be edited",
)
e712_errors[-1036] = ("PI_NO_PARAMETER_FILE_OPENED", "There is no parameter file open")
e712_errors[-1037] = ("PI_STAGE_DOES_NOT_EXIST", "Selected stage does not exist")
e712_errors[-1038] = (
    "PI_PARAMETER_FILE_ALREADY_OPENED",
    "There is already a parameter file open. Close it before opening a new file",
)
e712_errors[-1039] = ("PI_PARAMETER_FILE_OPEN_ERROR", "Could not open parameter file")
e712_errors[-1040] = (
    "PI_INVALID_CONTROLLER_VERSION",
    "The version of the connected controller is invalid",
)
e712_errors[-1041] = (
    "PI_PARAM_SET_ERROR",
    "Parameter could not be set with SPA--parameter not defined for this controller!",
)
e712_errors[-1042] = (
    "PI_NUMBER_OF_POSSIBLE_WAVES_EXCEEDED",
    "The maximum number of wave definitions has been exceeded",
)
e712_errors[-1043] = (
    "PI_NUMBER_OF_POSSIBLE_GENERATORS_EXCEEDED",
    "The maximum number of wave generators has been exceeded",
)
e712_errors[-1044] = (
    "PI_NO_WAVE_FOR_AXIS_DEFINED",
    "No wave defined for specified axis",
)
e712_errors[-1045] = (
    "PI_CANT_STOP_OR_START_WAV",
    "Wave output to axis already stopped/started",
)
e712_errors[-1046] = ("PI_REFERENCE_ERROR", "Not all axes could be referenced")
e712_errors[-1047] = (
    "PI_REQUIRED_WAVE_NOT_FOUND",
    "Could not find parameter set required by frequency relation",
)
e712_errors[-1048] = (
    "PI_INVALID_SPP_CMD_ID",
    "Command ID given to SPP or SPP? is not valid",
)
e712_errors[-1049] = (
    "PI_STAGE_NAME_ISNT_UNIQUE",
    "A stage name given to CST is not unique",
)
e712_errors[-1050] = (
    "PI_FILE_TRANSFER_BEGIN_MISSING",
    'A uuencoded file transferred did not start with "begin" followed by the proper filename',
)
e712_errors[-1051] = (
    "PI_FILE_TRANSFER_ERROR_TEMP_FILE",
    "Could not create/read file on host PC",
)
e712_errors[-1052] = (
    "PI_FILE_TRANSFER_CRC_ERROR",
    "Checksum error when transferring a file to/from the controller",
)
e712_errors[-1053] = (
    "PI_COULDNT_FIND_PISTAGES_DAT",
    "The PiStages.dat database could not be found. This file is required to connect a stage with the CST command",
)
e712_errors[-1054] = ("PI_NO_WAVE_RUNNING", "No wave being output to specified axis")
e712_errors[-1055] = ("PI_INVALID_PASSWORD", "Invalid password")
e712_errors[-1056] = (
    "PI_OPM_COM_ERROR",
    "Error during communication with OPM (Optical Power Meter), maybe no OPM connected",
)
e712_errors[-1057] = (
    "PI_WAVE_EDITOR_WRONG_PARAMNUM",
    "WaveEditor: Error during wave creation, incorrect number of parameters",
)
e712_errors[-1058] = (
    "PI_WAVE_EDITOR_FREQUENCY_OUT_OF_RANGE",
    "WaveEditor: Frequency out of range",
)
e712_errors[-1059] = (
    "PI_WAVE_EDITOR_WRONG_IP_VALUE",
    "WaveEditor: Error during wave creation, incorrect index for integer parameter",
)
e712_errors[-1060] = (
    "PI_WAVE_EDITOR_WRONG_DP_VALUE",
    "WaveEditor: Error during wave creation, incorrect index for floating point parameter",
)
e712_errors[-1061] = (
    "PI_WAVE_EDITOR_WRONG_ITEM_VALUE",
    "WaveEditor: Error during wave creation, could not calculate value",
)
e712_errors[-1062] = (
    "PI_WAVE_EDITOR_MISSING_GRAPH_COMPONENT",
    "WaveEditor: Graph display component not installed",
)
e712_errors[-1063] = (
    "PI_EXT_PROFILE_UNALLOWED_CMD",
    "User Profile Mode: Command is not allowed, check for required preparatory commands",
)
e712_errors[-1064] = (
    "PI_EXT_PROFILE_EXPECTING_MOTION_ERROR",
    "User Profile Mode: First target position in User Profile is too far from current position",
)
e712_errors[-1065] = (
    "PI_EXT_PROFILE_ACTIVE",
    "Controller is (already) in User Profile Mode",
)
e712_errors[-1066] = (
    "PI_EXT_PROFILE_INDEX_OUT_OF_RANGE",
    "User Profile Mode: Block or Data Set index out of allowed range",
)
e712_errors[-1067] = (
    "PI_PROFILE_GENERATOR_NO_PROFILE",
    "ProfileGenerator: No profile has been created yet",
)
e712_errors[-1068] = (
    "PI_PROFILE_GENERATOR_OUT_OF_LIMITS",
    "ProfileGenerator: Generated profile exceeds limits of one or both axes",
)
e712_errors[-1069] = (
    "PI_PROFILE_GENERATOR_UNKNOWN_PARAMETER",
    "ProfileGenerator: Unknown parameter ID in Set/Get Parameter command",
)
e712_errors[-1070] = (
    "PI_PROFILE_GENERATOR_PAR_OUT_OF_RANGE",
    "ProfileGenerator: Parameter out of allowed range",
)
e712_errors[-1071] = (
    "PI_EXT_PROFILE_OUT_OF_MEMORY",
    "User Profile Mode: Out of memory",
)
e712_errors[-1072] = (
    "PI_EXT_PROFILE_WRONG_CLUSTER",
    "User Profile Mode: Cluster is not assigned to this axis",
)
e712_errors[-1073] = ("PI_UNKNOWN_CLUSTER_IDENTIFIER", "Unknown cluster identifier")
e712_errors[-1074] = (
    "PI_INVALID_DEVICE_DRIVER_VERSION",
    "The installed device driver doesnt match the required version. Please see the documentation to determine the required device driver version.",
)
e712_errors[-1075] = (
    "PI_INVALID_LIBRARY_VERSION",
    "The library used doesnt match the required version. Please see the documentation to determine the required library version.",
)
e712_errors[-1076] = (
    "PI_INTERFACE_LOCKED",
    "The interface is currently locked by another function. Please try again later.",
)
e712_errors[-1077] = (
    "PI_PARAM_DAT_FILE_INVALID_VERSION",
    "Version of parameter DAT file does not match the required version. Current files are available at www.pi.ws.",
)
e712_errors[-1078] = (
    "PI_CANNOT_WRITE_TO_PARAM_DAT_FILE",
    "Cannot write to parameter DAT file to store user defined stage type.",
)
e712_errors[-1079] = (
    "PI_CANNOT_CREATE_PARAM_DAT_FILE",
    "Cannot create parameter DAT file to store user defined stage type.",
)
e712_errors[-1080] = (
    "PI_PARAM_DAT_FILE_INVALID_REVISION",
    "Parameter DAT file does not have correct revision.",
)
e712_errors[-1081] = (
    "PI_USERSTAGES_DAT_FILE_INVALID_REVISION",
    "User stages DAT file does not have correct revision.",
)


if __name__ == "__main__":
    pass
