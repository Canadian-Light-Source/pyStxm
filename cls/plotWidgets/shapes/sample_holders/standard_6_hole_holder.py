import os

from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QPainter
from plotpy.items.shape.polygon import PolygonShape
from plotpy.styles import ItemParameters

from cls.plotWidgets.shapes.base_shape import BaseShape


class Standard6HoleCompositeShape(PolygonShape):
    """Single plot item that draws the holder body and all six holes."""

    CLOSED = True

    def __init__(self, x_pts, y_pts, hole_centers, hole_radius, title):
        super().__init__()
        self.set_points(list(zip(x_pts, y_pts)))
        self.hole_radius = hole_radius

        # Keep holes in local coordinates so they follow item moves.
        xc = sum(x_pts) / len(x_pts)
        yc = sum(y_pts) / len(y_pts)
        self.hole_offsets = [(hx - xc, hy - yc) for hx, hy in hole_centers]
        self.set_resizable(False)

        sh = self.shapeparam
        sh._title = title
        sh.label = title
        sh.fill.alpha = 0.1
        sh.fill.color = "#55ff7f"
        sh.sel_fill.alpha = 0.2
        sh.sel_fill.color = "#55ff7f"
        sh.line._style = "SolidLine"
        sh.line._color = "#55ff7f"
        sh.sel_line._style = "SolidLine"
        sh.sel_line._color = "#55ff7f"
        sh.symbol.marker = "NoSymbol"
        sh.sel_symbol.marker = "NoSymbol"

        params = ItemParameters()
        params.add("ShapeParam", self, sh)  # type: ignore[arg-type]
        self.set_item_parameters(params)

    def draw(self, painter, xMap, yMap, canvasRect):
        points = self.transform_points(xMap, yMap)
        pen, brush, _symbol = self.get_pen_brush(xMap, yMap)

        xs = self.points[:, 0]
        ys = self.points[:, 1]
        xc = float(xs.mean())
        yc = float(ys.mean())

        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawPolygon(points)

        # Draw holes as part of the same selectable item.
        painter.save()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for dx, dy in self.hole_offsets:
            cx = xc + dx
            cy = yc + dy
            cpx = xMap.transform(cx)
            cpy = yMap.transform(cy)
            rx = abs(xMap.transform(cx + self.hole_radius) - cpx)
            ry = abs(yMap.transform(cy + self.hole_radius) - cpy)
            painter.drawEllipse(QPointF(cpx, cpy), rx, ry)
        painter.restore()

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

        # Build hole coordinates for composite draw
        hole_centers = []
        for row, y in enumerate([y_row1, y_row2]):
            for i in range(holes_per_row):
                x = x_start + i * (hole_diam + col_spacing)
                hole_centers.append((x, y))

        main_shape = Standard6HoleCompositeShape(
            x_pts=x_pts,
            y_pts=y_pts,
            hole_centers=hole_centers,
            hole_radius=hole_rad,
            title=f"{self.shape_prefix}rect",
        )
        self.parent.plot.add_item(main_shape)
        main_shape._shape_object = self
        main_shape.get_rect = self.get_rect
        main_shape.get_center = self.get_center
        self.shape_item = main_shape

