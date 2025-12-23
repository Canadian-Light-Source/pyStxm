

from cls.applications.pyStxm.widgets.dict_based_contact_sheet.utils import *
from cls.applications.pyStxm.widgets.dict_based_contact_sheet.build_tooltip_info import dict_based_build_image_params
from cls.applications.pyStxm.widgets.dict_based_contact_sheet.thumbnail_widget import ThumbnailWidget
from cls.utils.fileUtils import get_file_path_as_parts

def create_thumbnail(h5_file_dct, is_folder=False, data=None, energy=None, ev_idx=0, ev_pnt=0, pol_idx=0, stack_idx=None,
                     is_stack=False):
    """
    Create a thumbnail QGraphicsWidget from sp_db_dict data

    :param h5_file_dct: Dictionary containing sp_db data structure
    :param is_folder: thumbwidget is a folder image
    :param data: Optional data array for the thumbnail, used to create stack thumbs
    :param energy: Optional energy value for the thumbnail, used to create stack thumbs
    :return: QGraphicsWidget thumbnail
    """
    file_path = h5_file_dct[h5_file_dct['default']]['sp_db_dct']['file_path']
    data_dir, fprefix, fsuffix = get_file_path_as_parts(file_path)

    if stack_idx is None:
        th_wdg = ThumbnailWidget(h5_file_dct, fprefix + fsuffix, is_folder=is_folder, data=data, energy=energy,
                                 is_stack=is_stack)
    else:
        # change the filename sp that in the location of the filename the energy value of this stack widget is shown
        th_wdg = ThumbnailWidget(h5_file_dct, f'{energy:.2f} eV', is_folder=is_folder, data=data, energy=energy,
                                 is_stack=is_stack)

    if th_wdg.valid_file:
        s, jstr = dict_based_build_image_params(h5_file_dct, energy=energy, ev_idx=ev_idx, ev_pnt=ev_pnt, pol_idx=pol_idx,
                                                stack_idx=stack_idx)
        th_wdg.info_jstr = jstr
        th_wdg.setToolTip(s)
        return th_wdg
    return None
