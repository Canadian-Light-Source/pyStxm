import simplejson as json

class LoadFileResponseClass(object):
    def __init__(self, response_str):
        super().__init__()

        response_dct = json.loads(response_str)
        # Define required keys
        required_keys = [
            'directory', 'filename', 'regionProfiles', 'scanData',
            'scanType', 'scanTypeArchive', 'signalList', 'scanRequest', 'pystxm_load'
        ]

        # Check for missing keys
        missing_keys = [key for key in required_keys if key not in response_dct]
        if missing_keys:
            raise KeyError(f"Missing required keys in response: {missing_keys}")

        # Validate nested scanData keys
        scan_data_keys = [
            'cntChannel', 'cntOuterRegion', 'cntPolarization',
            'polarizations', 'regionDims'
        ]

        if 'scanData' in response_dct:
            missing_scan_keys = [key for key in scan_data_keys if key not in response_dct['scanData']]
            if missing_scan_keys:
                raise KeyError(f"Missing required keys in scanData: {missing_scan_keys}")

        # Validate nested structure for data extraction
        try:
            # This will raise appropriate exceptions if the structure is invalid
            test_data = \
            response_dct["scanData"]["polarizations"][0]['outerRegions'][0]['scanDataRegionVec'][0]['channels']['channelData']
        except (KeyError, IndexError, TypeError) as e:
            raise ValueError(f"Invalid data structure for polarizations data path: {e}")

        # self.response_dct = response_dct
        # self.directory = response_dct.get("directory", None)
        # self.filename = response_dct.get("filename", None)
        # self.scan_type = response_dct.get("scanType", None)
        self.pystxm_load = response_dct.get("pystxm_load", None)