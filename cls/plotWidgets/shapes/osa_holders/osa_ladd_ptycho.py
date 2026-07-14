import os

from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QPainter
from plotpy.items.shape.polygon import PolygonShape
from plotpy.styles import ItemParameters

from cls.plotWidgets.shapes.base_shape import BaseShape


class OSALaddPtychoCompositeShape(PolygonShape):
    """Single plot item that draws the OSA body and all apertures."""

    CLOSED = True

    def __init__(self, x_pts, y_pts, hole_centers, hole_radii, title):
        super().__init__()
        self.set_points(list(zip(x_pts, y_pts)))
        self.hole_radii = hole_radii

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

        # Draw OSA apertures as part of the same selectable item.
        painter.save()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for (dx, dy), radius in zip(self.hole_offsets, self.hole_radii):
            cx = xc + dx
            cy = yc + dy
            cpx = xMap.transform(cx)
            cpy = yMap.transform(cy)
            rx = abs(xMap.transform(cx + radius) - cpx)
            ry = abs(yMap.transform(cy + radius) - cpy)
            painter.drawEllipse(QPointF(cpx, cpy), rx, ry)
        painter.restore()


class OSALaddPtychoHolderShape(BaseShape):
    """
    Ladd-OSA-order-ptychography.ppt
    """
    def __init__(self,parent=None, shp_id=None):
        name = "OSALaddPtychoHolderShape"
        if shp_id is not None:
            name = f"OSALaddPtychoHolderShape_{shp_id}"

        super().__init__(os.path.basename(os.path.dirname(__file__)), name, prefix='osa_', parent=parent)
        if parent is None:
            raise ValueError("parent must be provided")
        self.parent = parent

        # Define the base rectangle for the holder
        self.left = 0
        self.top = 0
        self.width = 3000
        self.height = 6000 * -1.0
        self.half_width = self.width / 2.0
        self.half_height = self.height / 2.0
        self.center = (self.half_width, self.half_height)
        self.base_rect = [0, 0, self.width, self.height]
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
        # print(f"OSALaddPtychoHolderShape: _create_shape called with do_it={do_it}")
        xc, yc = self.center
        # print(f"osa: center is {self.center}")
        # Use self.base_rect for width and height

        x0 = xc - self.half_width
        y0 = yc - self.half_height
        x1 = xc + self.half_width
        y1 = yc + self.half_height
        x_pts = [x0, x1, x1, x0]
        y_pts = [y0, y0, y1, y1]

        hole_centers = [
            (x0 + 1000, y0 - 1000),
            (x0 + 1000, y0 - 2000),
            (x0 + 1000, y0 - 3000),
            (x0 + 1000, y0 - 4000),
        ]
        hole_radii = [25, 30, 35, 40]

        main_shape = OSALaddPtychoCompositeShape(
            x_pts=x_pts,
            y_pts=y_pts,
            hole_centers=hole_centers,
            hole_radii=hole_radii,
            title=f"{self.shape_prefix}rect",
        )
        self.parent.plot.add_item(main_shape)
        # the following assignemnts are required for a shape otherwise the positions will not be tracked
        main_shape._shape_object = self
        main_shape.get_rect = self.get_rect
        main_shape.get_center = self.get_center
        self.shape_item = main_shape


