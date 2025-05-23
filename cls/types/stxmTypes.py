"""
Created on 2013-08-02

@author: bergr
"""
from cls.utils.enum_utils import Enum

H5_FILE_SUFFIX = "h5"
TIFF_FILE_SUFFIX = "tiff"
PLACEHOLDER_FILENAME="FILENAME"

endstation_id_types = Enum("AMB", "UHV", "BASIC")

# the following definitions are taken from the NXstxm data/stxm_scan_type section

spatial_type_prefix = Enum("ROI", "SEG", "PNT")

IMAGE_LXL = 100
IMAGE_PXP = 200

OSA_FOCUS_MODE = 0
SAMPLE_FOCUS_MODE = 1

SPEC_ROI_PREFIX = 'ROI_'

scan_status_types = Enum("STOPPED", "RUNNING", "PAUSED", "DONE", "ABORTED")
energy_scan_order_types = Enum("EV_THEN_POL", "POL_THEN_EV")
# the following positioning modes for the sample are mutually exclusive, the sample positioning mode will be set
# int the MAIN_OBJ configuration and used to select the positioners used for scanning samples
sample_positioning_modes = Enum("Coarse", "Goniometer")
sample_fine_positioning_modes = Enum("SampleFine", "Zoneplate")
scanning_mode = Enum("COARSE_SAMPLEFINE", "GONI_ZONEPLATE", "COARSE_ZONEPLATE")

# scan_panel_order = Enum('Detector_Scan','OSA_Scan','OSA_Focus_Scan','Focus_Scan','Point_Scan', 'Image_Scan', 'ZP_Image_Scan', 'Positioner_Scan', 'Line_Scan', 'Image_Scan_Mainobj')
# NOTE: that if a new scan pluggin is added to teh plugins directory there must be a corresponding entry into this enumeration so that
# its params page will appear in the gui scan toolbox
scan_panel_order = Enum(
    "detector_scan",
    "osa_scan",
    "osa_focus_scan",
    "coarse_image",
    "coarse_goni_image_scan",
    "image_scan",
    "tomography",
    "focus_scan",
    "point_scan",
    "line_scan",
    "positioner_scan",
    "pattern_gen",
    "ptychography",
    "two_variable_scan",
)

scan_types = Enum(
    "detector_image",
    "osa_image",
    "osa_focus",
    "sample_focus",
    "sample_point_spectrum",
    "sample_line_spectrum",
    "sample_image",
    "sample_image_stack",
    "generic_scan",
    "coarse_image",
    "coarse_goni",
    "tomography",
    "pattern_gen",
    "ptychography",
    "two_variable_image"
)

scan_type_to_panel_dct = {}
scan_type_to_panel_dct["detector_image"] = scan_panel_order.DETECTOR_SCAN
scan_type_to_panel_dct["osa_image"] = scan_panel_order.OSA_SCAN
scan_type_to_panel_dct["osa_focus"] = scan_panel_order.OSA_FOCUS_SCAN
scan_type_to_panel_dct["sample_focus"] = scan_panel_order.FOCUS_SCAN
scan_type_to_panel_dct["sample_point_spectrum"] = scan_panel_order.POINT_SCAN
scan_type_to_panel_dct["sample_line_spectrum"] = scan_panel_order.LINE_SCAN
scan_type_to_panel_dct["sample_image"] = scan_panel_order.IMAGE_SCAN
scan_type_to_panel_dct["sample_image_stack"] = scan_panel_order.IMAGE_SCAN
scan_type_to_panel_dct["generic_scan"] = scan_panel_order.POSITIONER_SCAN
scan_type_to_panel_dct["coarse_image"] = scan_panel_order.COARSE_IMAGE
scan_type_to_panel_dct["coarse_goni"] = scan_panel_order.COARSE_GONI_IMAGE_SCAN
scan_type_to_panel_dct["tomography"] = scan_panel_order.TOMOGRAPHY
scan_type_to_panel_dct["pattern_gen"] = scan_panel_order.PATTERN_GEN
scan_type_to_panel_dct["ptychography"] = scan_panel_order.PTYCHOGRAPHY
scan_type_to_panel_dct["two_variable_image"] = scan_panel_order.TWO_VARIABLE_SCAN

spectra_type_scans = [scan_types.SAMPLE_POINT_SPECTRUM, scan_types.GENERIC_SCAN]

image_type_scans = [
    scan_types.DETECTOR_IMAGE,
    scan_types.OSA_IMAGE,
    scan_types.OSA_FOCUS,
    scan_types.SAMPLE_FOCUS,
    scan_types.SAMPLE_LINE_SPECTRUM,
    scan_types.SAMPLE_IMAGE,
    scan_types.SAMPLE_IMAGE_STACK,
    scan_types.COARSE_IMAGE,
    scan_types.COARSE_GONI,
    scan_types.TOMOGRAPHY,
    scan_types.PATTERN_GEN,
    scan_types.PTYCHOGRAPHY,
    scan_types.TWO_VARIABLE_IMAGE,
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
    scan_types.PTYCHOGRAPHY,
    scan_types.TWO_VARIABLE_IMAGE,
]

multi_entry_scans = [
    scan_types.SAMPLE_IMAGE_STACK,
    scan_types.SAMPLE_POINT_SPECTRUM,
    scan_types.TOMOGRAPHY,
    scan_types.PTYCHOGRAPHY,
]

two_posner_scans = [
    scan_types.DETECTOR_IMAGE,
    scan_types.OSA_IMAGE,
    scan_types.COARSE_IMAGE,
    scan_types.COARSE_GONI,
    scan_types.SAMPLE_IMAGE,
    scan_types.GENERIC_SCAN,
    scan_types.PTYCHOGRAPHY,
    scan_types.TWO_VARIABLE_IMAGE,
]

three_posner_scans = [
    scan_types.OSA_FOCUS,
    scan_types.SAMPLE_FOCUS,
    scan_types.SAMPLE_LINE_SPECTRUM,
    scan_types.SAMPLE_POINT_SPECTRUM,
    scan_types.TOMOGRAPHY,
    scan_types.SAMPLE_IMAGE_STACK,
]

acceptable_2dimages_list = [scan_types.COARSE_IMAGE, scan_types.SAMPLE_IMAGE, scan_types.COARSE_GONI, scan_types.PATTERN_GEN]

positioner_sub_types = Enum("SampleXY", "GoniometerXY")

scan_sub_types = Enum("Point_by_Point", "Line_Unidir")
detector_types = Enum("Point", "Line", "TWO_D", "Line_flyer")


scans_with_energy = [
    scan_types.SAMPLE_IMAGE,
    scan_types.SAMPLE_POINT_SPECTRUM,
    scan_types.GENERIC_SCAN,
]

image_types = Enum("focus", "osafocus", "image", "line_plot")

image_scan_secids = Enum("SAMPLE_LXL", "SAMPLE_PXP", "TOMO")

scan_image_types = {
    scan_types.DETECTOR_IMAGE: image_types.IMAGE,
    scan_types.OSA_IMAGE: image_types.IMAGE,
    scan_types.OSA_FOCUS: image_types.OSAFOCUS,
    scan_types.SAMPLE_FOCUS: image_types.FOCUS,
    scan_types.SAMPLE_IMAGE + IMAGE_LXL: image_types.IMAGE,
    scan_types.SAMPLE_IMAGE + IMAGE_PXP: image_types.IMAGE,
    scan_types.SAMPLE_IMAGE: image_types.IMAGE,
    scan_types.SAMPLE_POINT_SPECTRUM: image_types.LINE_PLOT,
    scan_types.GENERIC_SCAN: image_types.LINE_PLOT,
    scan_types.SAMPLE_LINE_SPECTRUM: image_types.LINE_PLOT,
    scan_types.COARSE_IMAGE + IMAGE_LXL: image_types.IMAGE,
    scan_types.COARSE_IMAGE + IMAGE_PXP: image_types.IMAGE,
    scan_types.COARSE_IMAGE: image_types.IMAGE,
    scan_types.SAMPLE_IMAGE_STACK: image_types.IMAGE,
    scan_types.TOMOGRAPHY: image_types.IMAGE,
    scan_types.COARSE_GONI: image_types.IMAGE,
    scan_types.PATTERN_GEN: image_types.IMAGE,
    scan_types.PTYCHOGRAPHY: image_types.IMAGE,
    scan_types.TWO_VARIABLE_IMAGE: image_types.IMAGE,
}

data_shapes = Enum(
    "NUME_NUMY_NUMX",
    "NUME_NUMZZ_NUMX",
    "ONE_NUMSPIDS_NUME",
    "NUMIMAGES_NUMY.NUMX",
    "NUMX_ONE_ONE",
    "NUMIMAGES_NUMY_NUMX",
    "NUMIMAGES_NUMY_NUME",
)

data_shape_types = {
    data_shapes.NUME_NUMY_NUMX: [
        scan_types.DETECTOR_IMAGE,
        scan_types.OSA_IMAGE,
        scan_types.COARSE_GONI,
        scan_types.PATTERN_GEN,
        scan_types.PTYCHOGRAPHY,
        scan_types.TWO_VARIABLE_IMAGE,

    ],
    data_shapes.NUME_NUMZZ_NUMX: [scan_types.OSA_FOCUS, scan_types.SAMPLE_FOCUS],
    data_shapes.ONE_NUMSPIDS_NUME: [scan_types.SAMPLE_POINT_SPECTRUM],
    data_shapes.NUMIMAGES_NUMY_NUMX: [
        scan_types.SAMPLE_IMAGE,
        scan_types.SAMPLE_IMAGE_STACK,
        scan_types.TOMOGRAPHY,
        scan_types.COARSE_IMAGE,
    ],
    data_shapes.NUMIMAGES_NUMY_NUME: [scan_types.SAMPLE_LINE_SPECTRUM],
    data_shapes.NUMX_ONE_ONE: [scan_types.GENERIC_SCAN],
}

non_zp_scans = [
    scan_types.DETECTOR_IMAGE,
    scan_types.OSA_IMAGE,
    scan_types.OSA_FOCUS,
    scan_types.SAMPLE_FOCUS,
    scan_types.GENERIC_SCAN,
    scan_types.COARSE_IMAGE,
    scan_types.COARSE_GONI,
    scan_types.TWO_VARIABLE_IMAGE,
]

focus_scans = [scan_types.OSA_FOCUS, scan_types.SAMPLE_FOCUS]
stack_scans = [scan_types.SAMPLE_IMAGE_STACK, scan_types.PTYCHOGRAPHY,  scan_types.TOMOGRAPHY]

__all__ = ["SPATIAL_TYPE_PREFIX", "TWO_D", "SEG", "PNT", scan_types, scans_with_energy]
