
import sys
import os
import simplejson as json
import numpy as np

#make sure that the applications modules can be found, used to depend on PYTHONPATH environ var
sys.path.append( os.path.join(os.path.dirname(os.path.abspath(__file__)), "..","..") )

from cls.utils.fileUtils import get_file_path_as_parts
from cls.data_io.stxm_data_io import STXMDataIo


def convert_numpy_to_python(obj):
    """Convert numpy types to standard Python types for JSON serialization"""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_numpy_to_python(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_to_python(i) for i in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    return obj

def load_nxstxm_file_to_h5_file_dct(filename, *, ret_as_dict=False, ret_as_jstr=False):
    """
    Load an HDF5 file and convert it to a dictionary.

    Parameters:
    h5_file (str): Path to the HDF5 file.

    Returns:
        if ret_as_dict is True:
            dict: Dictionary representation of the HDF5 file.
        else:
            None: It is assumed that this function was called by PixelatorController which is reading the output so
            the output is printed to stdout.
    dict: Dictionary representation of the HDF5 file.
    """
    # print(f"load_h5_file_to_dict called with filename={filename}")
    data_dir, fprefix, fsuffix = get_file_path_as_parts(filename)
    data_io = STXMDataIo(data_dir, fprefix)
    h5_file_dct = data_io.load()

    if ret_as_dict:
        # If ret_as_dict is True, return the dictionary
        return h5_file_dct
    elif ret_as_jstr:
        # Convert numpy arrays to Python lists before JSON serialization
        python_dict = convert_numpy_to_python(h5_file_dct)
        jstr = json.dumps(python_dict, indent=4)
        return jstr
    else:
        python_dict = convert_numpy_to_python(h5_file_dct)
        jstr = json.dumps(python_dict, indent=4)
        # by printing it it becomes the output of the function when called from PixelatorController
        # print(jstr)
        sys.stdout.write(jstr)



if __name__ == '__main__':
    #import pprint
    load_nxstxm_file_to_h5_file_dct(sys.argv[1])
    #dct = load_nxstxm_file_to_h5_file_dct('/tmp/2025-08-06/Motor_2025-08-06_021.hdf5', ret_as_dict=True)
    #pprint.pprint(dct)



