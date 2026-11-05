"""Test progressive-stack saving without beamline services.

Run from the repository root with:
    python -m pytest cls/utils/tests/test_prog_stack_utils.py

Requires pytest, numpy, and h5py. All output files use pytest's temporary
directories. Failure tests describe the current log-and-return behavior;
the writer does not roll back partially written files.
"""

import logging
import os
import stat

import h5py
import numpy as np
import pytest

from cls.utils import prog_stack_utils


@pytest.fixture
def metadata():
    """Return fresh metadata containing every required scan parameter."""
    return {
        'dwell': np.float64(0.5),
        'ev_setpoints': np.array([100.0, 101.0]),
        'x_roi': {'NPOINTS': np.int64(3), 'STEP': 0.25},
        'y_roi': {'NPOINTS': 2, 'STEP': 0.5},
        'is_pxp': 1,
        'default_det': 'detector_a',
        'rotation_angle': 12.5,
    }


@pytest.fixture
def image():
    """Return a fresh image containing an integer and a floating-point detector."""
    return {
        'img_idx': np.int64(0),
        'det_data': {
            'detector_a': np.arange(6, dtype=np.uint32).reshape(2, 3),
            'detector_b': np.array([[np.nan, np.inf, -np.inf], [1.5, 0, -2]]),
        },
    }


def test_creates_directory_file_detectors_and_all_metadata(tmp_path, metadata, image, caplog):
    """Verify the exact file layout, values, dtypes, and read permissions."""
    directory = tmp_path / 'new' / 'stack'
    with caplog.at_level(logging.WARNING):
        result = prog_stack_utils.save_progressive_stack_data_to_hdf5(
            image, directory, 'progressive-stack-scan', metadata
        )

    path = directory / 'progressive-stack-scan.hdf5'
    assert result is None
    assert not caplog.records
    with h5py.File(path, 'r') as saved:
        assert set(saved) == {'0', 'scan_parameters'}
        assert set(saved['0']) == set(image['det_data'])
        for name, data in image['det_data'].items():
            dataset = saved[f'0/{name}/data']
            assert dataset.shape == (2, 3)
            assert dataset.dtype == data.dtype
            np.testing.assert_array_equal(dataset[:], data)
        expected = {
            'ev_setpoints': metadata['ev_setpoints'],
            'dwell': metadata['dwell'],
            'is_pxp': metadata['is_pxp'],
            'rotation_angle': metadata['rotation_angle'],
            'numpoints_x': metadata['x_roi']['NPOINTS'],
            'numpoints_y': metadata['y_roi']['NPOINTS'],
            'step_size_x': metadata['x_roi']['STEP'],
            'step_size_y': metadata['y_roi']['STEP'],
        }
        assert set(saved['scan_parameters']) == set(expected) | {'default_det'}
        for name, value in expected.items():
            np.testing.assert_array_equal(saved[f'scan_parameters/{name}'][()], value)
        assert saved['scan_parameters/default_det'].asstr()[()] == 'detector_a'
    if os.name == 'posix':
        assert stat.S_IMODE(path.stat().st_mode) == 0o644


@pytest.mark.parametrize('previous_setting', [None, 'TRUE', 'FALSE'])
def test_saving_disables_file_locking(
    tmp_path, metadata, image, monkeypatch, previous_setting
):
    """Set the environment and file-open option even after h5py is imported."""
    if previous_setting is None:
        monkeypatch.delenv('HDF5_USE_FILE_LOCKING', raising=False)
    else:
        monkeypatch.setenv('HDF5_USE_FILE_LOCKING', previous_setting)
    real_file = h5py.File
    calls = []

    def open_without_locking(*args, **kwargs):
        """Check the environment and locking option at the actual file open."""
        calls.append(kwargs)
        assert os.environ['HDF5_USE_FILE_LOCKING'] == 'FALSE'
        assert kwargs['locking'] is False
        return real_file(*args, **kwargs)

    monkeypatch.setattr(prog_stack_utils.h5py, 'File', open_without_locking)
    prog_stack_utils.save_progressive_stack_data_to_hdf5(image, tmp_path, 'stack', metadata)
    assert len(calls) == 1
    assert os.environ['HDF5_USE_FILE_LOCKING'] == 'FALSE'
    with real_file(tmp_path / 'stack.hdf5', 'r', locking=False) as saved:
        np.testing.assert_array_equal(saved['0/detector_a/data'][:], image['det_data']['detector_a'])


@pytest.mark.parametrize('img_idx', [2, np.int64(3), 'image_4'])
def test_appends_image_and_preserves_original_metadata(tmp_path, metadata, image, img_idx):
    """Appending must retain previous images and the first scan parameters."""
    prog_stack_utils.save_progressive_stack_data_to_hdf5(image, tmp_path, 'stack', metadata)
    metadata['dwell'] = 99
    metadata['ev_setpoints'][:] = 999
    next_image = {'img_idx': img_idx, 'det_data': {'detector_a': [[7, 8, 9], [10, 11, 12]]}}
    prog_stack_utils.save_progressive_stack_data_to_hdf5(next_image, tmp_path, 'stack', metadata)

    with h5py.File(tmp_path / 'stack.hdf5', 'r') as saved:
        assert set(saved) == {'0', str(img_idx), 'scan_parameters'}
        np.testing.assert_array_equal(saved['0/detector_a/data'][:], image['det_data']['detector_a'])
        np.testing.assert_array_equal(saved[f'{img_idx}/detector_a/data'][:], next_image['det_data']['detector_a'])
        assert saved['scan_parameters/dwell'][()] == 0.5
        np.testing.assert_array_equal(saved['scan_parameters/ev_setpoints'][:], [100, 101])


def test_replaces_detector_dataset_without_removing_other_data(tmp_path, metadata, image):
    """Repeated indices replace supplied detectors, including shape and dtype."""
    prog_stack_utils.save_progressive_stack_data_to_hdf5(image, tmp_path, 'stack', metadata)
    replacement = np.ones((1, 2), dtype=np.float32)
    update = {'img_idx': 0, 'det_data': {'detector_a': replacement, 'detector_c': [[42]]}}
    # Metadata is not consulted once the scan_parameters group exists.
    prog_stack_utils.save_progressive_stack_data_to_hdf5(update, tmp_path, 'stack', None)

    with h5py.File(tmp_path / 'stack.hdf5', 'r') as saved:
        assert set(saved['0']) == {'detector_a', 'detector_b', 'detector_c'}
        assert saved['0/detector_a/data'].dtype == replacement.dtype
        np.testing.assert_array_equal(saved['0/detector_a/data'][:], replacement)
        np.testing.assert_array_equal(saved['0/detector_b/data'][:], image['det_data']['detector_b'])
        np.testing.assert_array_equal(saved['0/detector_c/data'][:], [[42]])


def test_accepts_empty_detector_collection(tmp_path, metadata):
    """An empty detector dictionary produces an empty image group."""
    prog_stack_utils.save_progressive_stack_data_to_hdf5(
        {'img_idx': 0, 'det_data': {}}, tmp_path, 'stack', metadata
    )
    with h5py.File(tmp_path / 'stack.hdf5', 'r') as saved:
        assert set(saved) == {'0', 'scan_parameters'}
        assert len(saved['0']) == 0


@pytest.mark.parametrize('missing_key', [
    'dwell', 'ev_setpoints', 'x_roi', 'y_roi', 'is_pxp', 'default_det', 'rotation_angle',
])
def test_missing_metadata_warns_saves_image_and_can_be_retried(
    tmp_path, metadata, image, caplog, missing_key
):
    """A missing required key skips metadata, but does not discard image data."""
    incomplete = dict(metadata)
    del incomplete[missing_key]
    with caplog.at_level(logging.WARNING):
        prog_stack_utils.save_progressive_stack_data_to_hdf5(image, tmp_path, 'stack', incomplete)
    assert any(
        record.levelno == logging.WARNING
        and f'Missing required metadata key: {missing_key}' in record.message
        for record in caplog.records
    )
    assert not any(record.levelno >= logging.ERROR for record in caplog.records)
    with h5py.File(tmp_path / 'stack.hdf5', 'r') as saved:
        assert 'scan_parameters' not in saved
        np.testing.assert_array_equal(saved['0/detector_a/data'][:], image['det_data']['detector_a'])

    caplog.clear()
    prog_stack_utils.save_progressive_stack_data_to_hdf5(image, tmp_path, 'stack', metadata)
    assert not caplog.records
    with h5py.File(tmp_path / 'stack.hdf5', 'r') as saved:
        assert len(saved['scan_parameters']) == 9


@pytest.mark.parametrize('invalid_data', [
    None,
    {},
    {'img_idx': 0},
    {'img_idx': 0, 'det_data': None},
    {'img_idx': 0, 'det_data': {'detector': np.array([[object()]], dtype=object)}},
    {'img_idx': 0, 'det_data': {'detector': [[1, 2], [3]]}},
])
def test_invalid_image_logs_error(tmp_path, metadata, caplog, invalid_data):
    """Malformed images and unsupported arrays log errors rather than raising."""
    with caplog.at_level(logging.ERROR):
        result = prog_stack_utils.save_progressive_stack_data_to_hdf5(
            invalid_data, tmp_path, 'stack', metadata
        )
    assert result is None
    assert any(
        record.levelno == logging.ERROR
        and 'Error in save_progressive_stack_data_to_hdf5:' in record.message
        for record in caplog.records
    )


@pytest.mark.parametrize('invalid_metadata', [None, {'x_roi': {}}])
def test_invalid_metadata_logs_error_or_warning(tmp_path, image, caplog, invalid_metadata):
    """Absent metadata logs an error; incomplete dictionaries log a warning."""
    with caplog.at_level(logging.WARNING):
        prog_stack_utils.save_progressive_stack_data_to_hdf5(
            image, tmp_path, 'stack', invalid_metadata
        )
    expected_level = logging.ERROR if invalid_metadata is None else logging.WARNING
    assert any(record.levelno == expected_level for record in caplog.records)


@pytest.mark.parametrize('invalid_array', [
    pytest.param(np.array([[1, None]], dtype=object), id='none-in-array'),
    pytest.param(np.array([[1, 'invalid']], dtype=object), id='mixed-number-and-text'),
    pytest.param(np.array([[1, {'invalid': 2}]], dtype=object), id='dictionary-in-array'),
    pytest.param(np.array([['invalid', 'data']]), id='unicode-array'),
    pytest.param([[1, 2], [3]], id='ragged-array'),
])
def test_invalid_array_contents_log_error_without_creating_dataset(
    tmp_path, metadata, caplog, invalid_array
):
    """Invalid array contents must log a write failure, not create a data dataset."""
    image = {'img_idx': 0, 'det_data': {'invalid_detector': invalid_array}}
    with caplog.at_level(logging.ERROR):
        result = prog_stack_utils.save_progressive_stack_data_to_hdf5(
            image, tmp_path, 'stack', metadata
        )
    assert result is None
    assert any(
        record.levelno == logging.ERROR
        and 'Error in save_progressive_stack_data_to_hdf5:' in record.message
        for record in caplog.records
    )
    # Metadata or empty groups may remain, but no invalid detector data is saved.
    with h5py.File(tmp_path / 'stack.hdf5', 'r') as saved:
        assert '0/invalid_detector/data' not in saved


def test_invalid_roi_logs_error_and_leaves_partial_metadata(tmp_path, metadata, image, caplog):
    """Document that a nested metadata failure is not an atomic file write."""
    del metadata['x_roi']['NPOINTS']
    with caplog.at_level(logging.ERROR):
        prog_stack_utils.save_progressive_stack_data_to_hdf5(image, tmp_path, 'stack', metadata)
    assert any('NPOINTS' in record.message for record in caplog.records)
    with h5py.File(tmp_path / 'stack.hdf5', 'r') as saved:
        assert 'scan_parameters' in saved
        assert 'numpoints_x' not in saved['scan_parameters']
        assert '0' not in saved


@pytest.mark.parametrize('operation', ['makedirs', 'open', 'chmod', 'create_dataset'])
def test_io_failure_is_logged(tmp_path, metadata, image, caplog, monkeypatch, operation):
    """Simulate failures portably, without depending on host permissions."""
    def fail(*args, **kwargs):
        """Raise a recognizable filesystem error at the selected operation."""
        raise OSError(f'simulated {operation} failure')

    if operation == 'open':
        monkeypatch.setattr(prog_stack_utils.h5py, 'File', fail)
    elif operation == 'create_dataset':
        monkeypatch.setattr(prog_stack_utils.h5py.Group, 'create_dataset', fail)
    else:
        monkeypatch.setattr(prog_stack_utils.os, operation, fail)
    with caplog.at_level(logging.ERROR):
        result = prog_stack_utils.save_progressive_stack_data_to_hdf5(
            image, tmp_path, 'stack', metadata
        )
    assert result is None
    assert any(
        record.levelno == logging.ERROR
        and f'simulated {operation} failure' in record.message
        for record in caplog.records
    )


def test_corrupt_existing_file_is_not_overwritten(tmp_path, metadata, image, caplog):
    """Opening a non-HDF5 file must log failure and preserve its contents."""
    path = tmp_path / 'stack.hdf5'
    original = b'not an HDF5 file'
    path.write_bytes(original)
    with caplog.at_level(logging.ERROR):
        prog_stack_utils.save_progressive_stack_data_to_hdf5(image, tmp_path, 'stack', metadata)
    assert any(record.levelno == logging.ERROR for record in caplog.records)
    assert path.read_bytes() == original
