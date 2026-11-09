"""HDF5 saving utilities shared by local and server progressive-stack writers."""

import logging
import os
import stat

# HDF5 may read this setting when its library is first loaded.
os.environ['HDF5_USE_FILE_LOCKING'] = 'FALSE'

import h5py
import numpy as np


def save_progressive_stack_data_to_hdf5(data_dct, data_dir, fprefix, metadata):
    """
    Save a progressive-stack image and its scan metadata to an HDF5 file.

    Create or update ``{data_dir}/{fprefix}.hdf5`` using native detector arrays.
    Each image is stored under its ``img_idx``, with a ``data`` dataset for each
    detector. Write scan parameters once, when the file has no metadata group.
    Callers must serialize writes to the same file. Write failures are logged.
    Set HDF5_USE_FILE_LOCKING=FALSE process-wide and explicitly disable locking
    on this file, including when h5py was initialized before this module.

    Parameters
    ----------
    data_dct : dict
        Dictionary containing 'img_idx' and 'det_data' with 2D arrays.
    data_dir : str
        Directory path to save the HDF5 file.
    fprefix : str
        Prefix for the HDF5 file name, without the .hdf5 extension.
    metadata : dict
        Scan parameters: dwell, ev_setpoints, x_roi, y_roi, is_pxp,
        default_det, and rotation_angle.

    Returns
    -------
    None
    """
    try:
        # Reassert the setting if application code changed it since module import.
        os.environ['HDF5_USE_FILE_LOCKING'] = 'FALSE'
        os.makedirs(data_dir, exist_ok=True)
        h5_path = os.path.join(data_dir, f"{fprefix}.hdf5")

        file_exists = os.path.exists(h5_path)
        mode = 'r+' if file_exists else 'w'
        # The explicit option also handles an already-initialized HDF5 library.
        kwargs = {'libver': 'latest', 'locking': False}

        with h5py.File(h5_path, mode, **kwargs) as h5f:
            os.chmod(h5_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
            h5f.swmr_mode = True

            # Scan parameters belong to the entire stack, not individual images.
            if 'scan_parameters' not in h5f:
                required_keys = ['dwell', 'ev_setpoints', 'x_roi', 'y_roi', 'is_pxp', 'default_det', 'rotation_angle']
                try:
                    for key in required_keys:
                        assert key in metadata, f"Missing required metadata key: {key}"

                    scan_grp = h5f.create_group('scan_parameters')
                    scan_grp.create_dataset('ev_setpoints', data=np.array(metadata['ev_setpoints']))
                    scan_grp.create_dataset('dwell', data=metadata['dwell'])
                    scan_grp.create_dataset('is_pxp', data=metadata['is_pxp'])
                    scan_grp.create_dataset('default_det', data=metadata['default_det'])
                    scan_grp.create_dataset('rotation_angle', data=metadata['rotation_angle'])
                    scan_grp.create_dataset('numpoints_x', data=metadata['x_roi']['NPOINTS'])
                    scan_grp.create_dataset('numpoints_y', data=metadata['y_roi']['NPOINTS'])
                    scan_grp.create_dataset('step_size_x', data=metadata['x_roi']['STEP'])
                    scan_grp.create_dataset('step_size_y', data=metadata['y_roi']['STEP'])
                except AssertionError as e:
                    logging.warning(f"Warning: {e}. scan_parameters group not written.")

            img_idx = str(data_dct['img_idx'])
            grp = h5f.require_group(img_idx)
            det_data = data_dct['det_data']
            for det_key, arr in det_data.items():
                det_grp = grp.require_group(det_key)
                arr_np = np.array(arr)
                # Replace an existing image dataset when the same index is saved again.
                if 'data' in det_grp:
                    del det_grp['data']
                det_grp.create_dataset('data', data=arr_np)
    except Exception as e:
        logging.error(f"Error in save_progressive_stack_data_to_hdf5: {e}")
