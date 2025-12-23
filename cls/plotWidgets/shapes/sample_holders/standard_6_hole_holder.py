import os

from cls.plotWidgets.shapes.base_shape import BaseShape
from cls.plotWidgets.shapes.utils import create_simple_circle, create_polygon

class Standard6HoleHolderShape(BaseShape):
    def __init__(self,parent=None, shp_id=None):
        name = "Standard6HoleHolderShape"
        if shp_id is not None:
            name = f"Standard6HoleHolderShape_{shp_id}"


        super().__init__(os.path.basename(os.path.dirname(__file__)), name, prefix='sh_',
                         parent=parent)
        if parent is None:
            raise ValueError("parent must be provided")

        self.parent = parent
        self.center = (0,0)
        self._circle_radius = 1250 #um
        # Define the base rectangle for the holder
        self.base_rect =  [-9500, 5000, 9500, -5000]
        self.set_rect(self.base_rect)
        self.color = (0, 0, 255)  # Blue color for the holder
        self.rotation = 0
        # Holder dimensions
        # self.bottom_width = 19000
        # self.top_width = 33000
        # self.height = 52000
        self.bottom_width = 19000
        self.top_width = 23000
        self.height = 14000

        x0, y0 = (self.bottom_width/2)*-1, (self.height/2)*-1
        x1, y1 = (self.top_width/2)*-1, (self.height/2)
        x2, y2 = (self.top_width/2), (self.height/2)
        x3, y3 = (self.bottom_width/2), (self.height/2)*-1

        self.holder_x_pts = [x0, x1, x2, x3]
        self.holder_y_pts = [y0, y1, y2, y3]

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
            return (point.x(), point.y())
        else:
            return self.center

    def _create_shape(self, do_it=True):
        """
        Create the sample holder shape and its 6 holes, all positioned relative to the current center.
        """

        if self.center is None:
            self.center = (0, 0)
        xc, yc = self.center

        # Polygon points (trapezoid), centered at (xc, yc)
        half_bottom = self.bottom_width / 2
        half_top = self.top_width / 2
        half_height = self.height / 2

        # Points: bottom left, top left, top right, bottom right
        x_pts = [
            xc - half_bottom,  # bottom left
            xc - half_top,  # top left
            xc + half_top,  # top right
            xc + half_bottom  # bottom right
        ]
        y_pts = [
            yc - half_height,  # bottom left
            yc + half_height,  # top left
            yc + half_height,  # top right
            yc - half_height  # bottom right
        ]

        (main_shape, shp_id) = create_polygon(x_pts=x_pts, y_pts=y_pts, title=f"{self.shape_prefix}rect", plot=self.parent.plot)
        # the following assignemnts are required for a shape otherwise the positions will not be tracked
        main_shape._shape_object = self
        main_shape.get_rect = self.get_rect
        main_shape.get_center = self.get_center
        self.shape_item = main_shape

        # Hole parameters
        hole_diam = 2500
        hole_rad = hole_diam / 2
        row_spacing = 2000  # vertical distance between rows
        col_spacing = 2000  # horizontal distance between holes
        holes_per_row = 3

        # Bottom edge y
        y_bottom = yc - half_height

        # First row (bottom), 2000um from bottom edge
        y_row1 = y_bottom + 2000 + hole_rad
        # Second row, above first row by (hole_diam + row_spacing)
        y_row2 = y_row1 + hole_diam + row_spacing

        # Center holes horizontally
        total_hole_width = (holes_per_row - 1) * (hole_diam + col_spacing)
        x_start = xc - total_hole_width / 2

        # Draw holes
        for row, y in enumerate([y_row1, y_row2]):
            for i in range(holes_per_row):
                x = x_start + i * (hole_diam + col_spacing)
                create_simple_circle(x, y, hole_rad, title=f"{self.shape_prefix}{row * 3 + i + 1}", plot=self.parent.plot)

