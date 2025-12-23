import os

from plotpy.interfaces import IShapeItemType
from cls.utils.json_utils import dict_to_json, json_to_dict, json_to_file, file_to_json

shapes_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "settings"))

class BaseShape(object):
    def __init__(self, category=None, name=None, prefix='', parent=None):
        if name is None:
            raise ValueError("name must be provided")
        self.category = category
        self.name = name
        self.shape_prefix = prefix
        #self.settings_fname = os.path.join(shapes_dir, f"{self.name}_settings.json")
        self.settings_fname = os.path.join(shapes_dir, "settings.json")
        self.shape_item = None
        self.center = (0, 0)
        self.size = (1, 1)
        self.rect = [0,0,0,0 ]
        self.color = (50, 50, 50)  # Blue color for the holder
        self.rotation = 0
        self.parent = parent
        self.init_settings()

    def init_settings(self):
        """
        initialize the shape parameters
        :return: None
        """
        try:
            self.load_settings()
        except Exception as e:
            # print(f"Could not load shape settings from {self.settings_fname}, using defaults. Error: {e}")
            self.save_settings()

    def save_settings(self):
        """
        Update the shape parameters in the settings file under self.category and self.name.
        :return: json string
        """
        # print(f"Saving settings for category [{self.category}] name [{self.name}] to {self.settings_fname}")
        if os.path.exists(self.settings_fname):
            js = file_to_json(self.settings_fname)
            settings = json_to_dict(js)
        else:
            # print(f"Settings file {self.settings_fname} does not exist. Creating a new one for "
            #      f"category=[{self.category}] name [{self.name}].")
            settings = {}

        # Ensure the category exists
        if self.category not in settings:
            print(f"Category [{self.category}] not found in settings. Creating new category.")
            settings[self.category] = {}


        # Update or add the shape under the category
        settings[self.category][self.name] = {
            "center": self.center,
            "rotation": self.rotation,
            "rect": self.rect,
            "name": self.name
        }

        js = dict_to_json(settings)
        json_to_file(self.settings_fname, js)
        # print(f"Settings saved successfully for category [{self.category}] name [{self.name}].")
        return js

    def load_settings(self):
        """
        Load the shape parameters from the settings file using self.category and self.name.
        """
        if not os.path.exists(self.settings_fname):
            return
        js = file_to_json(self.settings_fname)
        settings = json_to_dict(js)
        if self.category in settings and self.name in settings[self.category]:
            shape_dict = settings[self.category][self.name]
            self.center = tuple(shape_dict.get("center", self.center))
            self.rotation = shape_dict.get("rotation", self.rotation)
            self.rect = list(shape_dict.get("rect", self.rect))
            self.name = shape_dict.get("name", self.name)
        else:
            raise ValueError(f"Shape settings for category '{self.category}' and name '{self.name}' not found.")
        

    def create_shape(self, do_it=True):
        """
        create the shape(): description
        the main function _create_shape() to be implemented by inheriting class
        """
        if do_it:
            self._create_shape()
        else:

            # remove the shapes with shape_prefix
            self.parent.blockSignals(True)
            shapes = self.parent.plot.get_items(item_type=IShapeItemType)
            for shape in shapes:
                title = ""
                if hasattr(shape, "annotationparam"):
                    title = shape.annotationparam._title
                elif hasattr(shape, "shapeparam"):
                    title = shape.shapeparam._title
                if title.find(self.shape_prefix) > -1:
                    self.parent.delPlotItem(shape)
            self.parent.blockSignals(False)

    def set_color(self, color):
        """
        set the color of the shape
        :param color: tuple of (r,g,b)
        :return: None
        """
        self.color = color
        self.save_settings()

    def set_center_position(self, position):
        """
        set the position of the shape
        :param position: tuple of (x,y)
        """
        self.center = position
        self.save_settings()

    def set_rect(self, rect):
        """
        set the rect of the shape
        :param rect: list of [x0, y0, x1, y1]
        """
        self.rect = rect
        #self.save_settings()

    def set_rotation(self, rotation):
        """
        set the rotation of the shape
        :param rotation: rotation in degrees
        """
        self.rotation = rotation
        self.save_settings()

    def set_size(self, size):
        """
        set the size of the shape
        :param size: tuple of (width, height)
        """
        self.size = size
        #self.save_settings()

    def set_shapes_visible(self, prefix='', visible=True):
        shapes = self.parent.plot.get_items(item_type=IShapeItemType)
        for shape in shapes:
            title = ""
            if hasattr(shape, "annotationparam"):
                title = shape.annotationparam._title
            elif hasattr(shape, "shapeparam"):
                title = shape.shapeparam._title
            if title.find(prefix) > -1:
                # self.parent.delPlotItem(shape)
                shape.setVisible(visible)








