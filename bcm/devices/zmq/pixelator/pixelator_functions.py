import json
import pprint
from bcm.devices.zmq.pixelator.app_dcs_devnames import app_to_dcs_devname_map, dcs_to_app_devname_map

def PIXELATOR_initialize(parent, reply):
    """
    Function initialize description:
    returns: response.push_back(JsonUtils::response() )

    """
    print("PIXELATOR: function [initialize] called from ZMQ REQ/REP socket")
    if reply[0]['status'] == 'ok':
        parent.positioner_definition = reply[1]
        # for d in parent.positioner_definition:
        #     pprint.pprint(d)
        #     print()
        # response.push_back( JsonUtils::detectorDefinition() );
        parent.detector_definition = reply[2]
        # for d in parent.detector_definition:
        #     pprint.pprint(d)
        #     print()
        # response.push_back( Oscilloscope::getInstance().getDefinition() );
        parent.oscilloscope_definition = reply[3]
        # response.push_back( ZonePlate::getInstance().zonePlateDefinition() );
        parent.zone_plate_definition = reply[4]
        # for d in parent.zone_plate_definition:
        #     pprint.pprint(d)
        #     print()
        # # response.push_back( JsonUtils::value2string( NeXusFileReader::loadFile_getDefaults() ) );
        parent.remote_file_system_info = reply[5]

        for positioner_dct in parent.positioner_definition:
            dcs_devname = positioner_dct['axisName']
            if dcs_devname in dcs_to_app_devname_map.keys():
                app_devname = dcs_to_app_devname_map[dcs_devname]
                if app_devname in list(parent.devs.keys()):
                    dev = parent.devs[app_devname]['dev']
                    dev.set_connected(True)
                    dev.set_desc(positioner_dct['description'])
                    if hasattr(dev, 'set_low_limit'):
                        dev.set_low_limit(positioner_dct['lowerSoftLimit'])
                    if hasattr(dev, 'set_high_limit'):
                        dev.set_high_limit(positioner_dct['upperSoftLimit'])
                    if hasattr(dev, 'set_units'):
                        dev.set_units(positioner_dct['unit'])

                    # dev.set_readback(positioner_dct[dcs_devname]['position'])
        # # connect all the other devices that are not positioners
        # for dev_type in list(parent.devices_dct.keys()):
        #     if dev_type == 'POSITIONERS':
        #         pass
        #     else:
        #         for app_devname, dev in parent.devices_dct[dev_type].items():
        #             dev.set_connected(True)

        parent.print_all_devs("positionerDefinition", parent.positioner_definition)
        parent.print_all_devs("detectorDefinition", parent.detector_definition)
        parent.print_all_devs("oscilloscopeDefinition", parent.oscilloscope_definition)
        parent.print_all_devs("zonePlateDefinition", parent.zone_plate_definition)
        parent.print_all_devs("remoteFileSystemInfo", parent.remote_file_system_info)


def PIXELATOR_recordedChannels(parent, dct):
    """
    Function recordedChannels description:
    returns: ScanController::getInstance().recordedChannels(data); response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [recordedChannels] called from ZMQ REQ/REP socket")


def PIXELATOR_detectorSettings(parent, dct):
    """
    Function detectorSettings description:
    returns: Json::Value detectorSettings = DeviceHandler::getInstance().getDetector(data)->getSettingsProperties(); response.push_back( JsonUtils::response() ); response.push_back( JsonUtils::value2string(detectorSettings) )

    """
    print("PIXELATOR: function [detectorSettings] called from ZMQ REQ/REP socket")


def PIXELATOR_updateDetectorSettings(parent, dct):
    """
    Function updateDetectorSettings description:
    returns: DeviceHandler::getInstance().getDetector(data)->updateSettings(data2); response.push_back( JsonUtils::response()

    """
    print("PIXELATOR: function [updateDetectorSettings] called from ZMQ REQ/REP socket")


def PIXELATOR_estimatedTime(parent, dct):
    """
    Function estimatedTime description:
    returns: std::string estimatedTime = ScanController::getInstance().getEstimatedTime(data); response.push_back( JsonUtils::response() ); response.push_back( JsonUtils::value2string(estimatedTime)

    """
    print("PIXELATOR: function [estimatedTime] called from ZMQ REQ/REP socket")


def PIXELATOR_scanRequest(parent, dct):
    """
    Function scanRequest description:
    returns: ScanController::getInstance().processScanRequest(data); response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [scanRequest] called from ZMQ REQ/REP socket")


def PIXELATOR_abortScan(parent, dct):
    """
    Function abortScan description:
    returns: ScanController::getInstance().abortScan(); response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [abortScan] called from ZMQ REQ/REP socket")


def PIXELATOR_pauseScan(parent, dct):
    """
    Function pauseScan description:
    returns: ScanController::getInstance().pauseScan(); response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [pauseScan] called from ZMQ REQ/REP socket")


def PIXELATOR_resumeScan(parent, dct):
    """
    Function resumeScan description:
    returns: ScanController::getInstance().resumeScan(); response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [resumeScan] called from ZMQ REQ/REP socket")


def PIXELATOR_scanStatus(parent, dct):
    """
    Function scanStatus description:
    returns: std::string status = ScanController::getInstance().getScanStatus(); response.push_back( JsonUtils::response() ); response.push_back( status )

    """
    print("PIXELATOR: function [scanStatus] called from ZMQ REQ/REP socket")


def PIXELATOR_moveRequest(parent, dct):
    """
    Function moveRequest description:
    returns: ScanController::getInstance().moveRequest(data); response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [moveRequest] called from ZMQ REQ/REP socket")


def PIXELATOR_moveStatus(parent, dct):
    """
    Function moveStatus description:
    returns: std::string status = ScanController::getInstance().getMoveStatus(data); response.push_back( JsonUtils::response() ); response.push_back( status )

    """
    print("PIXELATOR: function [moveStatus] called from ZMQ REQ/REP socket")


def PIXELATOR_homeRequest(parent, dct):
    """
    Function homeRequest description:
    returns: ScanController::getInstance().homeRequest(data); response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [homeRequest] called from ZMQ REQ/REP socket")


def PIXELATOR_positionerStatus(parent, dct):
    """
    Function positionerStatus description:
    returns: std::string status = ScanController::getInstance().getPositionerStatus(data); response.push_back( JsonUtils::response() ); response.push_back( status )

    """
    print("PIXELATOR: function [positionerStatus] called from ZMQ REQ/REP socket")


def PIXELATOR_modified_positioner_definition(parent, dct):
    """
    Function modified_positioner_definition description:
    returns: DeviceHandler::getInstance().modifyPositioner(data) }// publish new (complete) positioner definition TransferData positionerDefinition("positionerDefinition", JsonUtils::positionerDefinition() ); publish(positionerDefinition; response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [modified positioner definition] called from ZMQ REQ/REP socket")


def PIXELATOR_modified_zonePlate_definition(parent, dct):
    """
    Function modified_zonePlate_definition description:
    returns: ZonePlate::getInstance().modify(data);  publish(zonePlateDefinition); response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [modified zonePlate definition] called from ZMQ REQ/REP socket")


def PIXELATOR_zonePlateFocus(parent, dct):
    """
    Function zonePlateFocus description:
    returns: double focusPosition = ZonePlate::getInstance().focusJson(data); response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [zonePlateFocus] called from ZMQ REQ/REP socket")


def PIXELATOR_oscilloscopeDefinition(parent, dct):
    """
    Function oscilloscopeDefinition description:
    returns: Oscilloscope::getInstance().setDefinition(data); response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [oscilloscopeDefinition] called from ZMQ REQ/REP socket")


def PIXELATOR_focusType(parent, dct):
    """
    Function focusType description:
    returns: ScanController::getInstance().setFocusType(data); response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [focusType] called from ZMQ REQ/REP socket")


def PIXELATOR_scanTypeArchive(parent, dct):
    """
    Function scanTypeArchive description:
    returns: ScanController::getInstance().setScanTypeArchiveAttr(data); response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [scanTypeArchive] called from ZMQ REQ/REP socket")


def PIXELATOR_localFileScanTypeArchive(parent, dct):
    """
    Function localFileScanTypeArchive description:
    returns: NeXusFile::localFileScanTypeArchiveAttr(data); response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [localFileScanTypeArchive] called from ZMQ REQ/REP socket")


def PIXELATOR_allMotorsOff(parent, dct):
    """
    Function allMotorsOff description:
    returns: DeviceHandler::getInstance().allMotorsOff(true); response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [allMotorsOff] called from ZMQ REQ/REP socket")


def PIXELATOR_resetInterferometer(parent, dct):
    """
    Function resetInterferometer description:
    returns: DeviceHandler::getInstance().resetInterferometer(); response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [resetInterferometer] called from ZMQ REQ/REP socket")


def PIXELATOR_OSA_IN(parent, dct):
    """
    Function OSA_IN description:
    returns: DeviceHandler::getInstance().microscopeControlInOut("OSA", true); response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [OSA IN] called from ZMQ REQ/REP socket")


def PIXELATOR_OSA_OUT(parent, dct):
    """
    Function OSA_OUT description:
    returns: DeviceHandler::getInstance().microscopeControlInOut("OSA", false); response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [OSA OUT] called from ZMQ REQ/REP socket")


def PIXELATOR_ZonePlate_IN(parent, dct):
    """
    Function ZonePlate_IN description:
    returns: DeviceHandler::getInstance().microscopeControlInOut("ZonePlate", true); response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [ZonePlate IN] called from ZMQ REQ/REP socket")


def PIXELATOR_ZonePlate_OUT(parent, dct):
    """
    Function ZonePlate_OUT description:
    returns: DeviceHandler::getInstance().microscopeControlInOut("ZonePlate", false); response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [ZonePlate OUT] called from ZMQ REQ/REP socket")


def PIXELATOR_Sample_OUT(parent, dct):
    """
    Function Sample_OUT description:
    returns: DeviceHandler::getInstance().microscopeControlInOut("Sample", false); response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [Sample OUT] called from ZMQ REQ/REP socket")


def PIXELATOR_topupMode(parent, dct):
    """
    Function topupMode description:
    returns: ScanController::getInstance().setTopupMode(data); response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [topupMode] called from ZMQ REQ/REP socket")


def PIXELATOR_beamShutterMode(parent, dct):
    """
    Function beamShutterMode description:
    returns: ScanController::getInstance().setBeamShutterMode(data); response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [beamShutterMode] called from ZMQ REQ/REP socket")


def PIXELATOR_loadFile_directory(parent, dct):
    """
    Function loadFile_directory description:
    returns: Json::Value loadFile = NeXusFileReader::loadFile_directory(data);  response.push_back( JsonUtils::response() ); response.push_back( JsonUtils::value2string(loadFile) )

    """
    print("PIXELATOR: function [loadFile directory] called from ZMQ REQ/REP socket")


def PIXELATOR_loadFile_file(parent, dct):
    """
    Function loadFile_file description:
    returns: std::string msg = NeXusFileReader::loadFile_file(data); response.push_back( JsonUtils::response(msg) )

    """
    print("PIXELATOR: function [loadFile file] called from ZMQ REQ/REP socket")


def PIXELATOR_loadDefinition(parent, dct):
    """
    Function loadDefinition description:
    returns: std::string scanDefinition = NeXusFileReader::loadDefinition(data, data2); // data2 is filename response.push_back( JsonUtils::response() ); response.push_back( scanDefinition )

    """
    print("PIXELATOR: function [loadDefinition] called from ZMQ REQ/REP socket")


def PIXELATOR_change_user(parent, dct):
    """
    Function change_user description:
    returns: Status::getInstance().changeUser(data); response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [change user] called from ZMQ REQ/REP socket")


def PIXELATOR_script_info(parent, dct):
    """
    Function script_info description:
    returns: MessageQueue::TransferData transferData("scriptInfo", data ); MessageQueue::getInstance().publish(transferData); response.push_back( JsonUtils::response() )

    """
    print("PIXELATOR: function [script info] called from ZMQ REQ/REP socket")
