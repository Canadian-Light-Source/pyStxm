import os

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter
from plotpy.items.shape.polygon import PolygonShape
from plotpy.styles import ItemParameters

from cls.plotWidgets.shapes.base_shape import BaseShape


class CryoGoniometerCompositeShape(PolygonShape):
    """Single plot item that draws frame and all slot rectangles."""

    CLOSED = True

    def __init__(self, frame_rect, slot_rects, title):
        super().__init__()
        x0, y0, x1, y1 = frame_rect
        self.set_points([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])

        fcx = (x0 + x1) * 0.5
        fcy = (y0 + y1) * 0.5
        self.slot_local_rects = []
        for sx0, sy0, sx1, sy1 in slot_rects:
            scx = (sx0 + sx1) * 0.5
            scy = (sy0 + sy1) * 0.5
            self.slot_local_rects.append(
                {
                    "offset": (scx - fcx, scy - fcy),
                    "size": (abs(sx1 - sx0), abs(sy1 - sy0)),
                }
            )

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
        fcx = float(xs.mean())
        fcy = float(ys.mean())

        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawPolygon(points)

        painter.save()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for slot in self.slot_local_rects:
            dx, dy = slot["offset"]
            w, h = slot["size"]
            cx = fcx + dx
            cy = fcy + dy
            x0 = cx - (w * 0.5)
            y0 = cy + (h * 0.5)
            x1 = cx + (w * 0.5)
            y1 = cy - (h * 0.5)

            px0 = xMap.transform(x0)
            py0 = yMap.transform(y0)
            px1 = xMap.transform(x1)
            py1 = yMap.transform(y1)
            left = float(px0 if px0 < px1 else px1)
            top = float(py0 if py0 < py1 else py1)
            width = float(abs(px1 - px0))
            height = float(abs(py1 - py0))
            painter.drawRect(
                QRectF(
                    left,
                    top,
                    width,
                    height,
                )
            )
        painter.restore()

class CryoGoniometerHolderShape(BaseShape):
    def __init__(self,parent=None, shp_id=None):
        name = "CryoGoniometerHolderShape"
        if shp_id is not None:
            name = f"CryoGoniometerHolderShape_{shp_id}"

        super().__init__(os.path.basename(os.path.dirname(__file__)), name, prefix='sh_',
                         parent=parent)
        if parent is None:
            raise ValueError("parent must be provided")

        self.parent = parent
        self.center = (0,0)
        self._circle_radius = 1250 #um
        # Define the base rectangle for the holder
        self.base_rect =  [0.0, 600.0, 3000.0, -600.0]
        self.set_rect(self.base_rect)
        self.color = (0, 0, 255)  # Blue color for the holder
        self.rotation = 0
        # Holder dimensions
        # self.bottom_width = 19000
        # self.top_width = 33000
        # self.height = 52000
        # self.bottom_width = 19000
        # self.top_width = 23000
        # self.height = 14000
        #
        # x0, y0 = (self.bottom_width/2)*-1, (self.height/2)*-1
        # x1, y1 = (self.top_width/2)*-1, (self.height/2)
        # x2, y2 = (self.top_width/2), (self.height/2)
        # x3, y3 = (self.bottom_width/2), (self.height/2)*-1
        #
        # self.holder_x_pts = [x0, x1, x2, x3]
        # self.holder_y_pts = [y0, y1, y2, y3]

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

        # rad = self.ss.get("%s.RADIUS" % SAMPLE_GONI)
        # rect = self.ss.get("%s.RECT" % SAMPLE_GONI)
        # xc, yc = self.ss.get("%s.CENTER" % SAMPLE_GONI)

        frame = (0.0, 600.0, 3000.0, -600.0)
        frame_outbrd_edge = xc - ((frame[0] + frame[2]) / 2.0)

        hole = (-100, 400, 100, -400)

        frame_rect = (
            xc - ((frame[2] - frame[0]) * 0.5),
            yc + ((frame[1] - frame[3]) * 0.5),
            xc + ((frame[2] - frame[0]) * 0.5),
            yc - ((frame[1] - frame[3]) * 0.5),
        )

        slot_centers = [385.0, 660.0, 935.0, 1210.0, 1485.0, 1760.0, 2035.0, 2310.0, 2585.0]
        hole_w = abs(hole[2] - hole[0])
        hole_h = abs(hole[1] - hole[3])
        slot_rects = []
        for xpos in slot_centers:
            cx_slot = frame_outbrd_edge + xpos
            slot_rects.append(
                (
                    cx_slot - (hole_w * 0.5),
                    yc + (hole_h * 0.5),
                    cx_slot + (hole_w * 0.5),
                    yc - (hole_h * 0.5),
                )
            )

        main_shape = CryoGoniometerCompositeShape(
            frame_rect=frame_rect,
            slot_rects=slot_rects,
            title="sh_rect",
        )
        self.parent.plot.add_item(main_shape)
        # the following assignemnts are required for a shape otherwise the positions will not be tracked
        main_shape._shape_object = self
        main_shape.get_rect = self.get_rect
        main_shape.get_center = self.get_center
        self.shape_item = main_shape


