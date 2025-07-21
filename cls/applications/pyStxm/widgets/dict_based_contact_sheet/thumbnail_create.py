

from cls.applications.pyStxm.widgets.dict_based_contact_sheet.utils import *
from cls.applications.pyStxm.widgets.dict_based_contact_sheet.build_tooltip_info import dict_based_build_image_params
from cls.applications.pyStxm.widgets.dict_based_contact_sheet.thumbnail_widget import ThumbnailWidget
from cls.utils.fileUtils import get_file_path_as_parts

def create_thumbnail(data_dct, is_folder=False):
    """
    Create a thumbnail QGraphicsWidget from sp_db_dict data

    :param data_dct: Dictionary containing sp_db data structure
    :param filename: Filename to display at bottom
    :return: QGraphicsWidget thumbnail
    """

    if not is_folder:
        file_path = data_dct['entry1']['sp_db_dct']['file_path']
        data_dir, fprefix, fsuffix = get_file_path_as_parts(file_path)
        th_wdg = ThumbnailWidget(data_dct, fprefix+fsuffix, is_folder=is_folder)
        #th_wdg.setToolTip(gpt_build_image_params(data_dct))

        s, jstr = dict_based_build_image_params(data_dct)
        th_wdg.info_jstr = jstr
        th_wdg.setToolTip(s)
    else:
        th_wdg = ThumbnailWidget({}, '..', is_folder=is_folder)

    return th_wdg
