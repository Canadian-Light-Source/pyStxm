import os

from cls.plotWidgets.shapes.base_shape import BaseShape
from cls.plotWidgets.shapes.utils import create_simple_circle, create_rectangle, create_polygon
from plotpy.interfaces import IShapeItemType

class OSAHorizontalRowHolderShape(BaseShape):
    def __init__(self,parent=None, shp_id=None):
        name = "OSAHorizontalRowHolderShape"
        if shp_id is not None:
            name = f"OSAHorizontalRowHolderShape_{shp_id}"

        super().__init__(os.path.basename(os.path.dirname(__file__)), name, prefix='osa_', parent=parent)
        if parent is None:
            raise ValueError("parent must be provided")
        self.parent = parent

        # Define the base rectangle for the holder
        self.left = 0
        self.top = 0
        self.width = 2500
        self.height = 10000 * -1.0
        self.half_width = self.width/2.0
        self.half_height = self.height/2.0
        self.center = (self.half_width, self.half_height)
        self.base_rect =   [0, 0, self.width, self.height]
        self.set_rect(self.base_rect)

        self.color = (0, 0, 255)  # Blue color for the holder
        self.rotation = 0


    def get_rect(self):
        """
        Return a rectangle with the same size as `base_rect`, but centered at the current center.

        Uses the current center (from `get_center()`) and the width/height from `base_rect`
        to compute the new rectangle coordinates.

        :return: List of rectangle coordinates [x0, y0, x1, y1]
        """
        cx, cy = self.get_center()
        x0, y0, x1, y1 = self.base_rect
        width = abs(x1 - x0)
        height = abs(y1 - y0)
        rect = [
            cx - width / 2,
            cy - height / 2,
            cx + width / 2,
            cy + height / 2
        ]
        return rect

    def get_center(self):
        if self.shape_item:
            point = self.shape_item.boundingRect().center()
            # print(f"osa: get_center: {(point.x(), point.y())}")
            return (point.x(), point.y())
        else:
            # print("osa: get_center: self.shape_item is None")
            return self.center

    def _create_shape(self, do_it=True):
        """
        create_osa(): description

        :returns: None
        """
        xc, yc = self.center
        print(f"osa: center is {self.center}")
        # Use self.base_rect for width and height

        x0 = xc - self.half_width
        y0 = yc - self.half_height
        x1 = xc + self.half_width
        y1 = yc + self.half_height
        rect = (x0, y0, x1, y1)
        #print(f"osa: _create_shape: rect is {rect}")
        # x0, y0, x1, y1 = rect = self.base_rect

        (main_shape, shp_id) = create_rectangle(rect, title=f"{self.shape_prefix}rect", plot=self.parent.plot)
        # the following assignemnts are required for a shape otherwise the positions will not be tracked
        main_shape._shape_object = self
        main_shape.get_rect = self.get_rect
        main_shape.get_center = self.get_center
        self.shape_item = main_shape

        create_simple_circle(x0 + 500, y0 - 500, 20, title=f"{self.shape_prefix}1", plot=self.parent.plot )
        create_simple_circle(x0 + 1000, y0 - 500, 25, title=f"{self.shape_prefix}2", plot=self.parent.plot )
        create_simple_circle(x0 + 1500, y0 - 500, 30, title=f"{self.shape_prefix}3", plot=self.parent.plot )
        create_simple_circle(x0 + 2000, y0 - 500, 35, title=f"{self.shape_prefix}4", plot=self.parent.plot )

