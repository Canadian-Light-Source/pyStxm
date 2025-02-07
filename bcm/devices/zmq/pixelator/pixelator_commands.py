import json

from .pixelator_functions import *
# this is a collection of commands to and responses from pixelator
# dcs_client_cmnds = {}
# dcs_client_cmnds['initialize'] = [
#                     json.dumps({'status':'ok'}),  # First part (JSON-encoded)
#                     json.dumps({"positionerDefinition": {'name':'PIXELATOR_SAMPLE_FINE_X'}}),
#                     json.dumps({"detectorDefinition": {'name':'SIS3820'}}) ,
#                     json.dumps({"oscilloscopeDefinition": {'name':'Agilent'}}) ,
#                     json.dumps({"zonePlateDefinition": {'name':'Zoneplate#4','a1':-6.792,'D':240.0, 'CsD':90.0, 'OZone': 35.0}}),
#                     json.dumps({"remoteFileSystemInfo": {'name':'Linux Debian 12'}}),
#                 ]
# dcs_client_cmnds['recordedChannels'] = 'ScanController::getInstance().recordedChannels(data); response.push_back( JsonUtils::response() )',
# dcs_client_cmnds['detectorSettings'] = 'Json::Value detectorSettings = DeviceHandler::getInstance().getDetector(data)->getSettingsProperties(); response.push_back( JsonUtils::response() ); response.push_back( JsonUtils::value2string(detectorSettings) )',
# dcs_client_cmnds['updateDetectorSettings'] = 'DeviceHandler::getInstance().getDetector(data)->updateSettings(data2); response.push_back( JsonUtils::response() ',
# dcs_client_cmnds['estimatedTime'] = 'std::string estimatedTime = ScanController::getInstance().getEstimatedTime(data); response.push_back( JsonUtils::response() ); response.push_back( JsonUtils::value2string(estimatedTime) ',
# dcs_client_cmnds['scanRequest'] = 'ScanController::getInstance().processScanRequest(data); response.push_back( JsonUtils::response() )',
# dcs_client_cmnds['abortScan'] = 'ScanController::getInstance().abortScan(); response.push_back( JsonUtils::response() )',
# dcs_client_cmnds['pauseScan'] = 'ScanController::getInstance().pauseScan(); response.push_back( JsonUtils::response() )',
# dcs_client_cmnds['resumeScan'] = 'ScanController::getInstance().resumeScan(); response.push_back( JsonUtils::response() )',
# dcs_client_cmnds['scanStatus'] = 'std::string status = ScanController::getInstance().getScanStatus(); response.push_back( JsonUtils::response() ); response.push_back( status )',
# dcs_client_cmnds['moveRequest'] = 'ScanController::getInstance().moveRequest(data); response.push_back( JsonUtils::response() )',
# dcs_client_cmnds['moveStatus'] = 'std::string status = ScanController::getInstance().getMoveStatus(data); response.push_back( JsonUtils::response() ); response.push_back( status )',
# dcs_client_cmnds['homeRequest'] = 'ScanController::getInstance().homeRequest(data); response.push_back( JsonUtils::response() )',
# dcs_client_cmnds['positionerStatus'] = 'std::string status = ScanController::getInstance().getPositionerStatus(data); response.push_back( JsonUtils::response() ); response.push_back( status )',
# dcs_client_cmnds['modified positioner definition'] = 'DeviceHandler::getInstance().modifyPositioner(data) }// publish new (complete) positioner definition TransferData positionerDefinition("positionerDefinition", JsonUtils::positionerDefinition() ); publish(positionerDefinition; response.push_back( JsonUtils::response() )',
# dcs_client_cmnds['modified zonePlate definition'] = 'ZonePlate::getInstance().modify(data);  publish(zonePlateDefinition); response.push_back( JsonUtils::response() )',
# dcs_client_cmnds['zonePlateFocus'] = 'double focusPosition = ZonePlate::getInstance().focusJson(data); response.push_back( JsonUtils::response() )',
# dcs_client_cmnds['oscilloscopeDefinition'] = 'Oscilloscope::getInstance().setDefinition(data); response.push_back( JsonUtils::response() )',
# dcs_client_cmnds['focusType'] = 'ScanController::getInstance().setFocusType(data); response.push_back( JsonUtils::response() )',
# dcs_client_cmnds['scanTypeArchive'] = 'ScanController::getInstance().setScanTypeArchiveAttr(data); response.push_back( JsonUtils::response() )',
# dcs_client_cmnds['localFileScanTypeArchive'] = 'NeXusFile::localFileScanTypeArchiveAttr(data); response.push_back( JsonUtils::response() )',
# dcs_client_cmnds['allMotorsOff'] = 'DeviceHandler::getInstance().allMotorsOff(true); response.push_back( JsonUtils::response() )',
# dcs_client_cmnds['resetInterferometer'] = 'DeviceHandler::getInstance().resetInterferometer(); response.push_back( JsonUtils::response() )',
# dcs_client_cmnds['OSA IN'] = 'DeviceHandler::getInstance().microscopeControlInOut("OSA", true); response.push_back( JsonUtils::response() )',
# dcs_client_cmnds['OSA OUT'] = 'DeviceHandler::getInstance().microscopeControlInOut("OSA", false); response.push_back( JsonUtils::response() )',
# dcs_client_cmnds['ZonePlate IN'] = 'DeviceHandler::getInstance().microscopeControlInOut("ZonePlate", true); response.push_back( JsonUtils::response() )',
# dcs_client_cmnds['ZonePlate OUT'] = 'DeviceHandler::getInstance().microscopeControlInOut("ZonePlate", false); response.push_back( JsonUtils::response() )',
# dcs_client_cmnds['Sample OUT'] = 'DeviceHandler::getInstance().microscopeControlInOut("Sample", false); response.push_back( JsonUtils::response() )',
# dcs_client_cmnds['topupMode'] = 'ScanController::getInstance().setTopupMode(data); response.push_back( JsonUtils::response() )',
# dcs_client_cmnds['beamShutterMode'] = 'ScanController::getInstance().setBeamShutterMode(data); response.push_back( JsonUtils::response() )',
# dcs_client_cmnds['loadFile directory'] = 'Json::Value loadFile = NeXusFileReader::loadFile_directory(data);  response.push_back( JsonUtils::response() ); response.push_back( JsonUtils::value2string(loadFile) )',
# dcs_client_cmnds['loadFile file'] = 'std::string msg = NeXusFileReader::loadFile_file(data); response.push_back( JsonUtils::response(msg) )',
# dcs_client_cmnds['loadDefinition'] = 'std::string scanDefinition = NeXusFileReader::loadDefinition(data, data2); // data2 is filename response.push_back( JsonUtils::response() ); response.push_back( scanDefinition ) ',
# dcs_client_cmnds['change user'] = 'Status::getInstance().changeUser(data); response.push_back( JsonUtils::response() )',
# dcs_client_cmnds['script info'] = 'MessageQueue::TransferData transferData("scriptInfo", data ); MessageQueue::getInstance().publish(transferData); response.push_back( JsonUtils::response() )',


cmd_func_map_dct = {}
cmd_func_map_dct['initialize'] = PIXELATOR_initialize
cmd_func_map_dct['recordedChannels'] = PIXELATOR_recordedChannels
cmd_func_map_dct['detectorSettings'] = PIXELATOR_detectorSettings
cmd_func_map_dct['updateDetectorSettings'] = PIXELATOR_updateDetectorSettings
cmd_func_map_dct['estimatedTime'] = PIXELATOR_estimatedTime
cmd_func_map_dct['scanRequest'] = PIXELATOR_scanRequest
cmd_func_map_dct['abortScan'] = PIXELATOR_abortScan
cmd_func_map_dct['pauseScan'] = PIXELATOR_pauseScan
cmd_func_map_dct['resumeScan'] = PIXELATOR_resumeScan
cmd_func_map_dct['scanStatus'] = PIXELATOR_scanStatus
cmd_func_map_dct['moveRequest'] = PIXELATOR_moveRequest
cmd_func_map_dct['moveStatus'] = PIXELATOR_moveStatus
cmd_func_map_dct['homeRequest'] = PIXELATOR_homeRequest
cmd_func_map_dct['positionerStatus'] = PIXELATOR_positionerStatus
cmd_func_map_dct['modified_positioner_definition'] = PIXELATOR_modified_positioner_definition
cmd_func_map_dct['modified_zonePlate_definition'] = PIXELATOR_modified_zonePlate_definition
cmd_func_map_dct['zonePlateFocus'] = PIXELATOR_zonePlateFocus
cmd_func_map_dct['oscilloscopeDefinition'] = PIXELATOR_oscilloscopeDefinition
cmd_func_map_dct['focusType'] = PIXELATOR_focusType
cmd_func_map_dct['scanTypeArchive'] = PIXELATOR_scanTypeArchive
cmd_func_map_dct['localFileScanTypeArchive'] = PIXELATOR_localFileScanTypeArchive
cmd_func_map_dct['allMotorsOff'] = PIXELATOR_allMotorsOff
cmd_func_map_dct['resetInterferometer'] = PIXELATOR_resetInterferometer
cmd_func_map_dct['OSA_IN'] = PIXELATOR_OSA_IN
cmd_func_map_dct['OSA_OUT'] = PIXELATOR_OSA_OUT
cmd_func_map_dct['ZonePlate_IN'] = PIXELATOR_ZonePlate_IN
cmd_func_map_dct['ZonePlate_OUT'] = PIXELATOR_ZonePlate_OUT
cmd_func_map_dct['Sample_OUT'] = PIXELATOR_Sample_OUT
cmd_func_map_dct['topupMode'] = PIXELATOR_topupMode
cmd_func_map_dct['beamShutterMode'] = PIXELATOR_beamShutterMode
cmd_func_map_dct['loadFile_directory'] = PIXELATOR_loadFile_directory
cmd_func_map_dct['loadFile_file'] = PIXELATOR_loadFile_file
cmd_func_map_dct['loadDefinition'] = PIXELATOR_loadDefinition
cmd_func_map_dct['change_user'] = PIXELATOR_change_user
cmd_func_map_dct['script_info'] = PIXELATOR_script_info
