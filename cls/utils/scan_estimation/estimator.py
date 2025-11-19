import os
from PyQt5.QtCore import QObject

import pprint
import pathlib
from collections import Counter
import simplejson as json
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
import numpy as np
import joblib

from cls.utils.json_utils import json_to_file, file_to_json, dict_to_json, json_to_dict
from cls.utils.log import get_module_logger
from cls.utils.cfgparser import ConfigClass
from cls.applications.pyStxm import abs_path_to_ini_file
from cls.data_io.stxm_data_io import STXMDataIo
from cls.utils.dirlist import get_files_with_extension
from cls.types.stxmTypes import scan_types

appConfig = ConfigClass(abs_path_to_ini_file)
BL_CFG_NM = appConfig.get_value("MAIN", "bl_config")
bl_scan_time_dir = os.path.join(os.getcwd(), "cls", "applications", "pyStxm", "bl_configs", BL_CFG_NM,
                                "scan_time_data")

_logger = get_module_logger(__name__)


class ScanTimeDataClass(QObject):
    fitted = False

    def __init__(self, data=(), scan_name='SCAN_NAME', degree=5, alpha=0.1, bl_scantime_dir=bl_scan_time_dir):
        super(ScanTimeDataClass, self).__init__()
        self.scan_name = scan_name
        self.degree = degree
        self.model_filename = os.path.join(bl_scantime_dir, scan_name + "_model.pkl")
        self.data_filename = os.path.join(bl_scantime_dir, scan_name + "_data.js")
        self.data = data

        if not os.path.exists(self.data_filename):
            self.data = [(1.0, 10, 10, 1.0)]
            self.fit_model(degree=self.degree)

        else:
            self.load_scan_time_data_from_disk()

        if not os.path.exists(self.model_filename):
            # print(f"creating model for [{scan_name}] with degree={self.degree}")
            self.model = make_pipeline(PolynomialFeatures(degree=self.degree), Ridge(alpha=alpha))
            self.fit_model(degree=self.degree)
        else:
            self.load_model()

        # print(f"creating model [{self.model_filename}] with degree={self.degree}")
        # self.model = make_pipeline(PolynomialFeatures(degree=self.degree), Ridge(alpha=alpha))
        # self.fit_model(degree=self.degree)

    def init_base_model(self):
        """

        """
        self.fit_model(degree=self.degree)

    def save_data_to_disk(self, data):
        """
        save the list of tuples as a json string to disk
        """
        with open(self.data_filename, 'w') as json_file:
            json.dump(data, json_file)

    def fit_model(self, degree=3, alpha=0.1):
        """
        expects data as a list of tuples conforming to:
            # (actual_time_sec, num_points_x, num_points_y, dwell_time_per_point_ms)
        """
        # Separate the data into features (X) and targets (y)
        if len(self.data) > 0:
            X = np.array([[points_x, points_y, dwell_time] for _, points_x, points_y, dwell_time in self.data])
            y = np.array([actual_time for actual_time, _, _, _, in self.data])

            # Initialize the Ridge regression model with polynomial features
            self.model = make_pipeline(PolynomialFeatures(degree=degree), Ridge(alpha=alpha))

            # Fit the model using the training data
            self.model.fit(X, y)
            self.fitted = True
            # Save the trained model to a file
            joblib.dump(self.model, self.model_filename)
            self.save_data_to_disk(self.data)
            #_logger.info(f"fit_model: model saved to [{self.model_filename}]")
            #_logger.info(f"model: data saved to [{self.data_filename}]")
        else:
            _logger.info("fit_model: Cannot fit model, self.data is empty")

    def load_scan_time_data_from_disk(self):
        """
        load the json string list of tuples of scan time data from disk and return it as a list
        """
        self.data = []
        if pathlib.Path(self.data_filename).exists():
            with open(self.data_filename, 'r') as json_file:
                self.data = json.load(json_file)
        else:
            print(f"load_scan_time_data_from_disk: the data file [{self.data_filename}] does not exist")

    def load_model(self):
        """
        load the trained model that was created with the fit_model() function
        """
        # Load the trained model from file
        self.model = None
        if pathlib.Path(self.model_filename).exists():
            self.model = joblib.load(self.model_filename)
        else:
            # data = self.init_base_data()
            self.fit_model(degree=self.degree)

    def estimate_scan_time(self, npoints_x, npoints_y, dwell_time):
        """
        loads the trained model from dis
        """

        # Function to predict time based on points X, points Y, and dwell time
        def predict_time(points_x, points_y, dwell_time):
            prediction = self.model.predict([[points_x, points_y, dwell_time]])
            return float(prediction[0])

        if len(self.data) > 0:
            estimated_time = predict_time(npoints_x, npoints_y, dwell_time)
            # print(f"Estimated time for points_x={npoints_x}, points_y={npoints_y}, dwell_time={dwell_time}: {estimated_time:.2f} seconds")
        else:
            estimated_time = None

        return estimated_time


class EstimateScanTimeClass(QObject):

    def __init__(self, degree=2, alpha=0.1, bl_scantime_dir=bl_scan_time_dir):
        super(EstimateScanTimeClass, self).__init__()
        self.degree = degree
        self.alpha = alpha
        self.bl_scantime_dir = bl_scantime_dir
        self.scans_dct = {}
        self.scan_names = []
        self.scan_names_file = os.path.join(self.bl_scantime_dir, "scan_names.js")
        if os.path.exists(self.scan_names_file):
            with open(self.scan_names_file, 'r') as json_file:
                self.scan_names = json.load(json_file)

        for scan_name in self.scan_names:
            self.load_scan_data_and_models(scan_name)

    def load_scan_data_and_models(self, scan_name):
        """
        if they exist instanciate them
        """
        sdc = ScanTimeDataClass(data=[], scan_name=scan_name, degree=self.degree, alpha=self.alpha,
                                bl_scantime_dir=self.bl_scantime_dir)
        self.scans_dct[scan_name] = sdc

    def estimate_scan_time(self, scan_name, npoints_x, npoints_y, dwell_time):
        """
        estimate the scan time for a particular scan
        """
        sdc = self.get_scan_data_class(scan_name)
        if sdc:
            sdc.fit_model(sdc.degree)
            return sdc.estimate_scan_time(npoints_x, npoints_y, dwell_time)
        else:

            _logger.error(f"Scan name [{scan_name}] does not exist in the data")
            print(f"EstimateScanTimeClass: Scan name [{scan_name}] does not exist in the data")
            return None

    def get_scan_data_class(self, scan_name):
        """
        retriev ethe scan data class from the dict
        """
        if scan_name in self.scans_dct.keys():
            return self.scans_dct[scan_name]
        else:
            _logger.error(f"Scan name [{scan_name}] does not exist in the data")
            return None

    def add_scan(self, scan_name: str, data: tuple):
        """
        adds a new scan in the list of scans and adds the data and creates the model
        """
        if scan_name in self.scans_dct.keys():
            sdc = self.scans_dct[scan_name]
        else:
            sdc = ScanTimeDataClass(data=[], scan_name=scan_name, degree=self.degree,
                                    bl_scantime_dir=self.bl_scantime_dir)
            self.scans_dct[scan_name] = sdc

        sdc.data.append(data)
        # pprint.pprint(sdc.data)
        # update the model
        sdc.fit_model(self.degree)

        if scan_name not in self.scan_names:
            self.scan_names.append(scan_name)
            with open(self.scan_names_file, 'w') as json_file:
                json.dump(self.scan_names, json_file)
                # json_to_file(self.scan_names_file, js)

    def init_model_for_scan_type(self, scan_name: str, data: [()]):
        """
        adds a new scan in the list of scans and adds the data and creates the model
        """
        if scan_name in self.scans_dct.keys():
            sdc = self.scans_dct[scan_name]
        else:
            sdc = ScanTimeDataClass(data=[], scan_name=scan_name, degree=self.degree,
                                    bl_scantime_dir=self.bl_scantime_dir)
            self.scans_dct[scan_name] = sdc
        sdc.data = []
        sdc.data += data
        # pprint.pprint(sdc.data)
        # update the model
        sdc.fit_model(self.degree)

        if scan_name not in self.scan_names:
            self.scan_names.append(scan_name)
            with open(self.scan_names_file, 'w') as json_file:
                json.dump(self.scan_names, json_file)
                # json_to_file(self.scan_names_file, js)

    def remove_scan(self, scan_name):
        """
        remove a scan from the list of scans
        """
        if scan_name in self.scans_dct.keys():
            del self.scans_dct[scan_name]
        else:
            _logger.info(f"The scan [{scan_name}] does not exist in current list of scan data")

    def add_data_to_scan(self, scan_name, data_tpl):
        """
        adds a new scan in the list of scans and adds the data and creates the model
        """
        if scan_name in self.scans_dct.keys():
            sdc = self.scans_dct[scan_name]
        else:
            _logger.error(f"Scan data does not exist for scan name [{scan_name}]")
            return
        # dont add duplicates
        if data_tpl not in sdc.data:
            sdc.data.append(data_tpl)
            # update the model
            sdc.fit_model(self.degree)

    def get_dwell_from_entry(self, entry_dct):
        sp_keys = list(entry_dct['WDG_COM']['SPATIAL_ROIS'].keys())
        return entry_dct['WDG_COM']['SPATIAL_ROIS'][sp_keys[0]]['EV_ROIS'][0]['DWELL']
        # return entry_dct['WDG_COM']['SINGLE_LST']['DWELL'][0]

    def get_num_energies_from_entry(self, entry_dct):
        sp_keys = list(entry_dct['WDG_COM']['SPATIAL_ROIS'].keys())
        return len(entry_dct['WDG_COM']['SPATIAL_ROIS'][sp_keys[0]]['EV_ROIS'])

    def get_num_polarizations_from_entry(self, entry_dct):
        sp_keys = list(entry_dct['WDG_COM']['SPATIAL_ROIS'].keys())
        return len(entry_dct['WDG_COM']['SPATIAL_ROIS'][sp_keys[0]]['EV_ROIS'][0]['EPU_POL_PNTS'])

    def get_scan_range_from_entry(self, entry_dct, axis='X'):
        sp_keys = list(entry_dct['WDG_COM']['SPATIAL_ROIS'].keys())
        return entry_dct['WDG_COM']['SPATIAL_ROIS'][sp_keys[0]][axis]['RANGE']
        # return entry_dct['WDG_COM']['SINGLE_LST']['SP_ROIS'][0][axis]['RANGE']

    def get_num_points_from_entry(self, entry_dct, axis='X'):
        sp_keys = list(entry_dct['WDG_COM']['SPATIAL_ROIS'].keys())
        return int(entry_dct['WDG_COM']['SPATIAL_ROIS'][sp_keys[0]][axis]['NPOINTS'])
        # return entry_dct['WDG_COM']['SINGLE_LST']['SP_ROIS'][0][axis]['NPOINTS']

    def get_filename_from_spdb(self, sp_db):
        """
        Turn the start and stop time delta into (total seconds, hours:minutes:seconds)
        'END_TIME': b'2023-07-05T11:24:01',
        'START_TIME': b'2023-07-05T11:22:53',

        'ACTIVE_DATA_OBJ': {'CFG': {'CUR_EV_IDX': None,
           'CUR_SAMPLE_POS': None,
           'CUR_SEQ_NUM': None,
           'CUR_SPATIAL_ROI_IDX': None,
           'DATA_DIR': 'G:\\test_data\\guest\\0705',
           'DATA_EXT': 'hdf5',
           'DATA_FILE_NAME': 'C230705001.hdf5',
           'DATA_IMG_IDX': 0,
           'DATA_STATUS': 'NOT_FINISHED',
           'DATA_THUMB_NAME': 'C230705001',
           'PREFIX': 'C230705001',
           'PTYCHO_CAM_DATA_DIR': '/test_data/',
           'ROI': None,
           'SCAN_TYPE': None,
           'STACK_DIR': 'G:\\test_data\\guest\\0705\\C230705001',
           'THUMB_EXT': 'jpg',
           'UNIQUEID': None,
           'WDG_COM': None},
          'DATA': {'POINTS': None, 'SSCANS': {}},
          'DEVICES': None,
          'END_TIME': b'2023-07-05T11:24:01',
          'START_TIME': b'2023-07-05T11:22:53',
          'VERSION': b'1.0'}

        Parameters
        ----------
        sp_db
        axis

        Returns
        -------

        """

        ado = sp_db['ACTIVE_DATA_OBJ']
        return ado['CFG']['DATA_DIR'] + "\\" + ado['CFG']['DATA_FILE_NAME']

    def get_scan_type(self, entry_dct):
        spatial_keys = list(entry_dct['WDG_COM']['SPATIAL_ROIS'].keys())
        key = spatial_keys[0]
        scan_type_enum = entry_dct['WDG_COM']['SPATIAL_ROIS'][key]['SCAN_PLUGIN']['SCAN_TYPE']
        return scan_types[scan_type_enum]

    def make_scan_time_dct(self, data_io, entry_dct):
        """
        a convienience function to create a 'standard' dict for use by thumb widgets
        :param data_io:
        :param entry_dct:
        :return:
        """
        sp_db = data_io.get_first_sp_db_from_entry(entry_dct)
        ttl_scan_seconds = data_io.get_elapsed_time_from_sp_db(sp_db, axis='X')

        dct = {}
        dct['dwell'] = self.get_dwell_from_entry(entry_dct)
        # dct["ttl_scan_seconds"] = ttl_scan_seconds
        dct['scan_type'] = self.get_scan_type(entry_dct)
        dct['scan_range_x'] = self.get_scan_range_from_entry(entry_dct, axis='X')
        dct['num_points_x'] = self.get_num_points_from_entry(entry_dct, axis='X')
        dct['scan_range_y'] = self.get_scan_range_from_entry(entry_dct, axis='Y')
        dct['num_points_y'] = self.get_num_points_from_entry(entry_dct, axis='Y')

        dct["ttl_scan_seconds"] = ttl_scan_seconds
        dct["fpath"] = self.get_filename_from_spdb(sp_db)
        # dct['param_hash'] = hash(f"{dct['scan_type']}:{dct['dwell']}:{dct['num_points_x']}:{dct['num_points_y']}")
        # dct['unique_hash'] = hash(
        #  nev, npol
        dct['param_hash'] = self.gen_standard_key(dct['scan_type'], dct['dwell'], dct['num_points_x'],
                                                  dct['num_points_y'])
        dct['unique_hash'] = self.gen_standard_key(dct['scan_type'], dct['dwell'], dct['num_points_x'],
                                                   dct['num_points_y'], ttl_scan_seconds)
        # dct["entries"] = entry_dct
        # print(f"Total scan time = {ttl_scan_seconds} seconds")
        print(f"Processed: {dct['fpath']}")
        return dct

    def print_scan_time_dct(self, s_dct, i):
        print(f"[{i}] took {s_dct['ttl_scan_seconds']} seconds")

    def process_scans(self, crs_images_dct):
        for crs_parm, lst in crs_images_dct.items():
            i = 0
            for sct_dct in lst:
                self.print_scan_time_dct(sct_dct, i)

    def build_database(self, path):
        """
        build a list of dicts that represent information from a datafile regarding scan specifics and
        times of execution, this list of dicts
        """
        # path = r'G:/SM/test_data/guest'
        fpaths = get_files_with_extension(path, ext=".hdf5", skip_lst=[])

        dct = {}
        dct['scan_type'] = {}

        for fpath in fpaths:
            p = pathlib.Path(fpath)
            fname = p.name
            data_dir = p.as_posix().replace(fname, "")
            dataio = STXMDataIo(data_dir, fname.replace(".hdf5", ""))
            base_dct = dataio.load()
            if base_dct:
                if 'default' in list(base_dct.keys()):
                    ekey = base_dct['default']
                    edct = base_dct[ekey]
                    fdct = self.make_scan_time_dct(dataio, edct)
                    if fdct['scan_type'] not in dct['scan_type'].keys():
                        dct['scan_type'][fdct['scan_type']] = {}

                    # add this scan hashed by its params to the scan_types list
                    if fdct['param_hash'] not in dct['scan_type'][fdct['scan_type']].keys():
                        dct['scan_type'][fdct['scan_type']][fdct['param_hash']] = []

                    dct['scan_type'][fdct['scan_type']][fdct['param_hash']].append(fdct)
                else:
                    pprint.pprint(base_dct)
            else:
                print(f"something wrong with this file [{fname}")

        return dct

    def get_scan_name(self, scan_type_nm):
        for scan in scan_dirs:
            if scan.find(scan_type_nm) > -1:
                return scan
        return None

    def filter_majority_deadband(self, values, deadband=15):
        """
        based on the majority of the values reject all values that fall outside the absolute deadband of the
        majority value
        """
        # Step 1: Find the majority value
        count = Counter(values)
        majority_value = count.most_common(1)[0][0]
        # print(f"Most common value is: {majority_value}")

        # Step 2: Filter out values that fall outside the deadband
        filtered_values = [value for value in values if abs(value - majority_value) <= deadband]
        rejected_values = []
        for v in values:
            if abs(v - majority_value) <= deadband:
                filtered_values.append(v)
            else:
                rejected_values.append(v)

        return filtered_values, rejected_values

    def remove_outliers(self, arr, deadband=15.0):
        """
        remove all of the bogust values from the data,
        deadband: is an absolute value that that the data must fall within of the majority of the data values
        """
        filtered_data, rejected_values = self.filter_majority_deadband(arr, deadband)
        # print(f"filtered data: [{filtered_data}]")
        return filtered_data, rejected_values

    def gen_standard_key(self, scan_type, dwell, nx, ny, ttl_sec=None):
        """
        a function used in a couple of places to construct a key string based on scan type and parameters
        """
        if ttl_sec is None:
            return f"{scan_type}:{dwell}:{nx}:{ny}"
        else:
            return f"{scan_type}:{dwell}:{nx}:{ny}:{ttl_sec}"

    def build_training_data_from_datafiles(self, path, force=True):
        """
        prompt for a base directory name and then walk it building the adta base of all data files found
        """
        import os

        db_path = os.path.join(bl_scan_time_dir, 'time_dct.js')

        # load data instead
        if os.path.exists(db_path) and not force:
            js = file_to_json(db_path)
            dct = json_to_dict(js)
        else:
            # build it
            dct = self.build_database(path)
            js = dict_to_json(dct)
            json_to_file(db_path, js)

        # pprint.pprint(dct)
        styp_keys = dct["scan_type"].keys()
        scan_type_dct = {}
        for st in styp_keys:
            print(f"Processing ['{st}']")
            scan_type_dct[st] = {}
            # now walk each param set
            for hsh, hdct_lst in dct["scan_type"][st].items():
                sdct = hdct_lst[0]
                title = f"\t[{st}] Params: {sdct['dwell']} ms dwell and {sdct['num_points_x']}x{sdct['num_points_y']}x{sdct['dwell']}ms "
                print(title)
                scan_param_key = f"{sdct['num_points_x']}x{sdct['num_points_y']}x{sdct['dwell']}"
                for h in hdct_lst:

                    if scan_param_key not in scan_type_dct[st].keys():
                        scan_type_dct[st][scan_param_key] = []

                    # (actual_time_sec, num_points_x, num_points_y, dwell_time_per_point_ms)
                    scan_type_dct[st][scan_param_key].append(h['ttl_scan_seconds'])

                elements = np.array(scan_type_dct[st][scan_param_key])
                scan_type_dct[st][scan_param_key], rejected = self.remove_outliers(elements)
                print(f"data=[{scan_type_dct[st][scan_param_key]}]")
                print(f"rejected=[{rejected}]")

        # now create the models with the data
        for scan_type_nm, st_dct in scan_type_dct.items():
            param_keys = st_dct.keys()
            data_list = []
            for pk in param_keys:
                p_strs = pk.split('x')
                numX = int(p_strs[0])
                numY = int(p_strs[1])
                dwell = float(p_strs[2])
                data = st_dct[pk]
                data_list += self.create_tuples((numX, numY, dwell), data)
                # print(tuple_lst)
            # add all data for this scan type
            self.init_model_for_scan_type(scan_type_nm, data_list)

    def create_tuples(self, constant_values, values):
        # Create tuples by pairing each element in the values list with the constant values
        tuples_list = [(value,) + constant_values for value in values]
        return tuples_list


def run_estimations(estc, scan_name, scan_data, verbose=False):
    actuals = []
    estimateds = []
    for parms in scan_data:
        # print(f"\nTesting [{scan_name}]")
        est = estc.estimate_scan_time(scan_name, npoints_x=parms[1], npoints_y=parms[2], dwell_time=parms[3])
        if verbose:
            print(
                f"\tscan_type: {scan_name} {parms[1]} x {parms[2]} x {parms[3]} ms x =>  actual={parms[0]}sec, estimated={est:.2f}sec ")
        actuals.append(parms[0])
        estimateds.append(est)

    return actuals, estimateds


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    import numpy as np

    # Example data (list of tuples)
    scan_data = detector_scan_data = [
        (5, 5, 5, 1),  # (actual_time_sec, num_points_x, num_points_y, dwell_time_per_point_ms)
        (5, 5, 5, 10),
        (8, 5, 5, 100),
        (36, 15, 15, 1),
        (37, 15, 15, 10),
        (59, 15, 15, 100),
        (60, 30, 30, 1),
        (71, 30, 30, 10),
        (154, 30, 30, 100),
        (124, 40, 40, 10),
        (201, 50, 50, 10),
        (300, 50, 50, 50),
        (420, 50, 50, 100),
    ]

    # coarse_image_data = [[96.0, 200, 50, 5.0], [107.0, 200, 50, 5.0], [300.0, 100, 100, 10.0], [260.0, 100, 100, 10.0], [5.0, 100, 100, 10.0], [17.0, 100, 100, 10.0], [25.0, 100, 100, 10.0], [156.0, 100, 100, 10.0], [61.0, 100, 100, 10.0], [70.0, 100, 100, 10.0], [100.0, 100, 100, 10.0], [180.0, 100, 100, 10.0], [88.0, 100, 100, 10.0], [133.0, 100, 100, 4.0], [148.0, 100, 100, 4.0], [98.0, 220, 50, 2.0], [133.0, 100, 100, 2.5], [118.0, 100, 100, 2.5], [126.0, 100, 100, 2.5], [19.0, 100, 100, 2.5], [3.0, 100, 100, 2.5], [85.0, 100, 100, 2.5], [119.0, 100, 100, 2.5], [49.0, 100, 30, 10.0], [83.0, 100, 30, 10.0], [147.0, 100, 100, 4.5], [105.0, 100, 100, 2.0], [110.0, 100, 100, 2.0], [106.0, 100, 100, 2.0], [107.0, 100, 100, 2.0], [53.0, 100, 100, 2.0], [109.0, 100, 100, 2.0], [268.0, 100, 100, 2.0], [119.0, 100, 100, 2.0], [90.0, 100, 100, 5.0], [26.0, 100, 100, 5.0], [70.0, 100, 100, 5.0], [272.0, 100, 100, 5.0], [182.0, 100, 100, 5.0], [148.0, 100, 100, 5.0], [181.0, 100, 100, 5.0], [142.0, 100, 100, 5.0], [16.0, 100, 100, 5.0], [187.0, 100, 100, 5.0], [326.0, 100, 100, 5.0], [50.0, 100, 100, 5.0], [33.0, 100, 100, 5.0], [186.0, 100, 100, 5.0], [153.0, 100, 100, 5.0], [162.0, 100, 100, 5.0], [144.0, 100, 100, 5.0], [153.0, 100, 100, 5.0], [162.0, 100, 100, 5.0], [181.0, 100, 100, 5.0], [142.0, 100, 100, 5.0], [58.0, 100, 100, 5.0], [123.0, 100, 100, 5.0], [105.0, 100, 100, 5.0], [15.0, 150, 50, 2.0], [11.0, 150, 50, 2.0], [8.0, 150, 50, 2.0], [69.0, 150, 50, 2.0], [129.0, 150, 50, 2.0], [67.0, 150, 50, 2.0], [68.0, 150, 50, 2.0], [73.0, 150, 50, 2.0], [76.0, 150, 50, 2.0], [68.0, 150, 50, 2.0], [11.0, 150, 50, 2.0], [15.0, 150, 50, 2.0], [12.0, 150, 50, 2.0], [17.0, 150, 50, 2.0], [13.0, 150, 50, 2.0], [8.0, 150, 50, 2.0], [14.0, 150, 50, 2.0], [9.0, 150, 50, 2.0], [9.0, 150, 50, 2.0], [16.0, 150, 50, 2.0], [77.0, 150, 50, 2.0], [64.0, 150, 50, 2.0], [16.0, 150, 50, 2.0], [23.0, 150, 50, 2.0], [8.0, 150, 50, 2.0], [13.0, 150, 50, 2.0], [25.0, 150, 50, 2.0], [26.0, 150, 50, 2.0], [24.0, 150, 50, 2.0], [28.0, 150, 50, 2.0], [66.0, 150, 50, 2.0], [14.0, 150, 50, 2.0], [15.0, 150, 50, 2.0], [19.0, 150, 50, 2.0], [77.0, 150, 50, 2.0], [114.0, 150, 50, 2.0], [91.0, 150, 50, 2.0], [76.0, 150, 50, 2.0], [66.0, 150, 50, 2.0], [72.0, 150, 50, 2.0], [69.0, 150, 50, 2.0], [55.0, 150, 50, 2.0], [34.0, 150, 50, 2.0], [15.0, 150, 50, 2.0], [74.0, 150, 50, 2.0], [9.0, 150, 50, 2.0], [45.0, 150, 50, 2.0], [16.0, 150, 50, 2.0], [20.0, 150, 50, 2.0], [67.0, 150, 50, 2.0], [66.0, 150, 50, 2.0], [181.0, 150, 50, 2.0], [79.0, 150, 50, 2.0], [49.0, 150, 50, 2.0], [75.0, 150, 50, 2.0], [65.0, 150, 50, 2.0], [74.0, 150, 50, 2.0], [4.0, 150, 50, 2.0], [53.0, 150, 50, 2.0], [44.0, 150, 50, 2.0], [5.0, 150, 50, 2.0], [59.0, 150, 50, 2.0], [60.0, 150, 50, 2.0], [2.0, 150, 50, 2.0], [33.0, 150, 50, 2.0], [73.0, 150, 50, 2.0], [233.0, 150, 150, 2.0], [9.0, 100, 100, 16.0], [10.0, 100, 50, 5.0], [15.0, 100, 50, 5.0], [8.0, 100, 50, 5.0], [61.0, 100, 50, 5.0], [82.0, 100, 50, 5.0], [28.0, 100, 50, 5.0], [21.0, 100, 50, 5.0], [98.0, 100, 50, 5.0], [76.0, 100, 50, 5.0], [13.0, 100, 50, 5.0], [106.0, 100, 50, 5.0], [6.0, 100, 50, 5.0], [63.0, 100, 50, 5.0], [114.0, 100, 50, 5.0], [68.0, 100, 50, 5.0], [7.0, 100, 50, 5.0], [15.0, 100, 50, 5.0], [35.0, 100, 50, 5.0], [32.0, 100, 50, 5.0], [30.0, 100, 50, 5.0], [31.0, 100, 50, 5.0], [23.0, 100, 50, 5.0], [89.0, 100, 50, 5.0], [34.0, 100, 50, 5.0], [95.0, 100, 50, 5.0], [49.0, 100, 50, 5.0], [21.0, 100, 50, 5.0], [95.0, 100, 50, 5.0], [76.0, 100, 50, 5.0], [48.0, 100, 50, 5.0], [76.0, 100, 50, 5.0], [92.0, 100, 50, 5.0], [93.0, 100, 50, 5.0], [68.0, 100, 50, 5.0], [66.0, 100, 50, 5.0], [58.0, 100, 50, 5.0], [92.0, 100, 50, 5.0], [74.0, 100, 50, 5.0], [33.0, 100, 50, 5.0], [28.0, 100, 50, 5.0], [60.0, 100, 50, 5.0], [88.0, 100, 50, 5.0], [90.0, 100, 50, 5.0], [93.0, 100, 50, 5.0], [75.0, 100, 50, 5.0], [73.0, 100, 50, 5.0], [9.0, 100, 50, 5.0], [100.0, 100, 50, 5.0], [9.0, 100, 50, 5.0], [29.0, 100, 50, 5.0], [14.0, 100, 50, 5.0], [97.0, 100, 50, 5.0], [43.0, 100, 50, 5.0], [39.0, 100, 50, 5.0], [85.0, 100, 50, 5.0], [65.0, 100, 50, 5.0], [69.0, 100, 50, 5.0], [60.0, 100, 50, 5.0], [28.0, 100, 50, 5.0], [7.0, 100, 50, 5.0], [10.0, 100, 50, 5.0], [36.0, 100, 50, 5.0], [13.0, 100, 50, 5.0], [82.0, 100, 50, 5.0], [10.0, 100, 50, 5.0], [74.0, 100, 50, 5.0], [114.0, 100, 50, 5.0], [95.0, 100, 50, 5.0], [82.0, 100, 50, 5.0], [70.0, 100, 50, 5.0], [80.0, 100, 50, 5.0], [10.0, 100, 50, 5.0], [48.0, 100, 50, 5.0], [65.0, 100, 50, 5.0], [29.0, 100, 50, 5.0], [84.0, 100, 50, 5.0], [9.0, 100, 50, 5.0], [81.0, 100, 50, 5.0], [41.0, 100, 50, 5.0], [115.0, 100, 50, 5.0], [59.0, 100, 50, 5.0], [90.0, 100, 50, 5.0], [33.0, 100, 50, 5.0], [66.0, 100, 50, 5.0], [10.0, 100, 50, 5.0], [65.0, 100, 50, 5.0], [6.0, 100, 50, 5.0], [80.0, 100, 50, 5.0], [58.0, 100, 50, 5.0], [67.0, 100, 50, 5.0], [78.0, 100, 50, 5.0], [54.0, 100, 50, 5.0], [54.0, 100, 50, 5.0], [75.0, 100, 50, 5.0], [39.0, 100, 50, 5.0], [62.0, 100, 50, 5.0], [26.0, 100, 50, 5.0], [21.0, 100, 50, 5.0], [15.0, 100, 50, 5.0], [87.0, 100, 50, 5.0], [14.0, 100, 50, 5.0], [19.0, 100, 50, 5.0], [15.0, 100, 50, 5.0], [86.0, 100, 50, 5.0], [20.0, 100, 50, 5.0], [31.0, 100, 50, 5.0], [46.0, 100, 50, 10.0], [12.0, 100, 50, 10.0], [133.0, 100, 50, 10.0], [128.0, 100, 50, 10.0], [56.0, 100, 50, 10.0], [46.0, 100, 50, 10.0], [74.0, 100, 50, 10.0], [25.0, 100, 50, 10.0], [125.0, 100, 50, 10.0], [114.0, 100, 50, 10.0], [115.0, 100, 50, 10.0], [128.0, 100, 50, 10.0], [23.0, 100, 50, 10.0], [43.0, 100, 50, 10.0], [35.0, 100, 50, 10.0], [123.0, 100, 50, 10.0], [98.0, 100, 50, 10.0], [106.0, 100, 50, 10.0], [128.0, 100, 50, 10.0], [28.0, 100, 50, 10.0], [82.0, 100, 50, 10.0], [86.0, 100, 50, 10.0], [114.0, 100, 50, 10.0], [100.0, 100, 50, 10.0], [25.0, 100, 50, 10.0], [25.0, 100, 50, 10.0], [44.0, 100, 50, 10.0], [44.0, 100, 50, 10.0], [76.0, 100, 50, 10.0], [129.0, 100, 50, 10.0], [127.0, 100, 50, 10.0], [60.0, 100, 50, 10.0], [117.0, 100, 50, 10.0], [79.0, 100, 50, 10.0], [18.0, 100, 50, 10.0], [81.0, 100, 50, 10.0], [126.0, 100, 50, 10.0], [126.0, 100, 50, 10.0], [27.0, 100, 50, 10.0], [12.0, 100, 50, 10.0], [39.0, 100, 50, 10.0], [99.0, 100, 50, 10.0], [37.0, 100, 50, 10.0], [105.0, 100, 50, 10.0], [66.0, 100, 50, 10.0], [108.0, 100, 50, 10.0], [117.0, 100, 50, 10.0], [100.0, 100, 50, 10.0], [89.0, 100, 50, 10.0], [54.0, 100, 50, 10.0], [107.0, 100, 50, 10.0], [40.0, 100, 30, 2.5], [18.0, 75, 75, 2.0], [67.0, 100, 30, 5.0]]
    # scan_data = coarse_image_data
    # # Example usage
    test_points_x = 100
    test_points_y = 100
    test_dwell_time = 5.0
    # scan_data = [(181, 100, 100, 5)]
    estc = EstimateScanTimeClass(degree=2, alpha=0.1, bl_scantime_dir=os.getcwd())

    # build the database when starting from scratch, once built the data and model will just be reloaded from disk
    # estc.build_training_data_from_datafiles(r'T:/operations/STXM-data/ASTXM_upgrade_tmp/2024/guest/2024_05/0502',
    #                                         True)
    actual = []
    estimated = []
    final_data = {}

    scan_data = []
    scan_data.append(('detector_image', [128.0, 20, 20, 1.0]))
    scan_data.append(('sample_image', [75.0, 60, 70, 1.0]))
    scan_data.append(('sample_focus', [58.0, 300, 300, 1.0]))
    scan_data.append(('coarse_image', [69.0, 150, 50, 2.0]))
    scan_data.append(('generic_scan', [80.0, 150, 1, 200.0]))
    scan_data.append(('generic_scan', [0.0, 175, 1, 200.0]))
    scan_data.append(('generic_scan', [0.0, 275, 1, 200.0]))
    scan_data.append(('osa_focus', [6.0, 100, 100, 1.0]))
    scan_data.append(('osa_image', [99.0, 15, 15, 1.0]))
    scan_data.append(('sample_image_stack', [41.0, 150, 150, 1.0]))
    scan_data.append(('pattern_gen_scan', [424.0, 41, 27, 1000.0]))

    actual, estimated = run_estimations(estc, scan_data)

    # now test updating the model following the execution of a scan
    # generic scan ('generic_scan', [80.0, 150, 1, 200.0])
    estc.add_data_to_scan('generic_scan', [93.0, 200, 1, 200.0])

    # check that the generic scan is more accurate in estimating
    actual, estimated = run_estimations(estc, scan_data)

    #
    # plt.style.use('_mpl-gallery')
    # act_arr = np.array(actual)
    # est_arr = np.array(estimated)
    # x = np.linspace(0, 10, len(actual))
    #
    # # plot
    # fig, ax = plt.subplots()
    #
    # ax.plot(x, act_arr, 'x', markeredgewidth=2)
    # ax.plot(x, est_arr, linewidth=2.0)
    # #ax.plot(x2, y2 - 2.5, 'o-', linewidth=2)
    #
    # # ax.set(xlim=(0, 8), xticks=np.arange(1, 8),
    # #        ylim=(0, 8), yticks=np.arange(1, 8))
    # #
    # plt.show()
    #
