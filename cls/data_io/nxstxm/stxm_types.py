"""
Created on Jan 4, 2019

@author: bergr
"""
from enum import Enum


class scan_types(Enum):
    DETECTOR_IMAGE = 0
    OSA_IMAGE = 1
    OSA_FOCUS = 2
    SAMPLE_FOCUS = 3
    SAMPLE_POINT_SPECTRUM = 4
    SAMPLE_LINE_SPECTRUM = 5
    SAMPLE_IMAGE = 6
    SAMPLE_IMAGE_STACK = 7
    GENERIC_SCAN = 8
    COARSE_IMAGE = 9
    COARSE_GONI = 10
    TOMOGRAPHY = 11
    PATTERN_GEN = 12
    PTYCHOGRAPHY = 13


two_posner_scans = [
    scan_types.DETECTOR_IMAGE.value,
    scan_types.OSA_IMAGE.value,
    scan_types.COARSE_IMAGE.value,
    scan_types.COARSE_GONI.value,
    scan_types.SAMPLE_IMAGE.value,
    scan_types.GENERIC_SCAN.value,
]
single_entry_scans = [
    scan_types.DETECTOR_IMAGE,
    scan_types.OSA_IMAGE,
    scan_types.OSA_FOCUS,
    scan_types.SAMPLE_FOCUS,
    scan_types.SAMPLE_LINE_SPECTRUM,
    scan_types.SAMPLE_IMAGE,
    scan_types.COARSE_IMAGE,
    scan_types.COARSE_GONI,
    scan_types.GENERIC_SCAN,
    scan_types.PATTERN_GEN,
]
multi_entry_scans = [
    scan_types.SAMPLE_IMAGE_STACK,
    scan_types.SAMPLE_POINT_SPECTRUM,
    scan_types.TOMOGRAPHY,
]
single_2d_scans = [
    scan_types.DETECTOR_IMAGE,
    scan_types.OSA_IMAGE,
    scan_types.SAMPLE_IMAGE,
    scan_types.COARSE_IMAGE,
    scan_types.COARSE_GONI,
]
focus_scans = [scan_types.SAMPLE_FOCUS, scan_types.OSA_FOCUS]
single_image_scans = [scan_types.SAMPLE_IMAGE, scan_types.PATTERN_GEN]
stack_type_scans = [
    scan_types.SAMPLE_IMAGE_STACK,
    scan_types.TOMOGRAPHY,
    scan_types.PTYCHOGRAPHY,
]
spectra_type_scans = [scan_types.SAMPLE_POINT_SPECTRUM, scan_types.GENERIC_SCAN]
line_spec_scans = [scan_types.SAMPLE_LINE_SPECTRUM]

sample_image_filetypes = [
    scan_types.SAMPLE_IMAGE,
    scan_types.COARSE_GONI,
    scan_types.COARSE_IMAGE,
    scan_types.TOMOGRAPHY,
]

#scan sub types
IS_PXP = 0
IS_LXL = 1
