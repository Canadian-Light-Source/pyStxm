import os

from cls.plotWidgets.shapes.base_shape import BaseShape
from cls.plotWidgets.shapes.utils import create_rect_centerd_at

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

        # self.create_rectangle(new_rect, title='sh_rect')
        (main_shape, shp_id) = create_rect_centerd_at(frame, xc, yc, title="sh_rect", plot=self.parent.plot)
        # the following assignemnts are required for a shape otherwise the positions will not be tracked
        main_shape._shape_object = self
        main_shape.get_rect = self.get_rect
        main_shape.get_center = self.get_center
        self.shape_item = main_shape

        create_rect_centerd_at(
            hole, frame_outbrd_edge + 385.0, yc, title="sh_1", plot=self.parent.plot
        )
        create_rect_centerd_at(
            hole, frame_outbrd_edge + 660.0, yc, title="sh_1", plot=self.parent.plot
        )
        create_rect_centerd_at(
            hole, frame_outbrd_edge + 935.0, yc, title="sh_2", plot=self.parent.plot
        )
        create_rect_centerd_at(
            hole, frame_outbrd_edge + 1210.0, yc, title="sh_3", plot=self.parent.plot
        )
        create_rect_centerd_at(
            hole, frame_outbrd_edge + 1485.0, yc, title="sh_4", plot=self.parent.plot
        )
        create_rect_centerd_at(
            hole, frame_outbrd_edge + 1760.0, yc, title="sh_5", plot=self.parent.plot
        )
        create_rect_centerd_at(
            hole, frame_outbrd_edge + 2035.0, yc, title="sh_6", plot=self.parent.plot
        )
        create_rect_centerd_at(
            hole, frame_outbrd_edge + 2310.0, yc, title="sh_7", plot=self.parent.plot
        )
        create_rect_centerd_at(
            hole, frame_outbrd_edge + 2585.0, yc, title="sh_8", plot=self.parent.plot
        )

