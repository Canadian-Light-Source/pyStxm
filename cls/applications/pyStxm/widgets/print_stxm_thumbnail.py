
import math
import sys

# import textile
import copy
import time

from PyQt5.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog

from PyQt5.QtCore import (
    Qt,
    QDate,
    QRectF,
    Qt,
    QSize,
    QRect,
    QPoint,
    pyqtSignal,
    QByteArray,
    QBuffer,
    QIODevice,
)
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from PyQt5.QtGui import (
    QFont,
    QFontMetrics,
    QGradient,
    QColor,
    QLinearGradient,
    QBrush,
    QPainter,
    QPixmap,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
    QTextOption,
    QTextTableFormat,
    QFont,
    QFontMetrics,
)

from cls.utils.fileUtils import get_file_path_as_parts
from cls.appWidgets.dialogs import excepthook, errorMessage
from cls.types.stxmTypes import spectra_type_scans, scan_types
from cls.utils.qt5_utils import dpi_scaled

sys.excepthook = excepthook


LEFT_MARGIN = dpi_scaled(20)
THMB_SIZE = dpi_scaled(128)
SP_LINE_LENGTH = dpi_scaled(5)

SPEC_THMB_WD = 200
SPEC_THMB_HT = 160

SINGLE_DATA_BOX = QSize(THMB_SIZE + dpi_scaled(150), THMB_SIZE + dpi_scaled(150))
SPEC_SINGLE_DATA_BOX = QSize(SPEC_THMB_WD + 125, SPEC_THMB_HT + 125)

DESCRIPTIVE_AXIS_LABELS = False


class PrintSTXMThumbnailWidget(QDialog):
    do_print = pyqtSignal(object)
    do_preview = pyqtSignal(object)

    def __init__(self, parent=None):
        super(PrintSTXMThumbnailWidget, self).__init__(parent)

        self.printer = QPrinter()
        self.printer.setPageSize(QPrinter.Letter)
        self.do_print.connect(self.printViaQPainter)
        self.do_preview.connect(self.preview)
        self.dct = {}
        self.doc = None
        self.prev_pmap = None

    def preview(self):

        # Open preview dialog
        preview = QPrintPreviewDialog(self.printer, self)
        preview.setFixedWidth(700)
        preview.setFixedHeight(600)
        preview.paintRequested.connect(self.printPreview)

        # self.doc = self.getHtmlDoc()
        self.doc = QTextDocument()

        if self.dct["scan_type_num"] in spectra_type_scans:
            html = self.getQPainterSpecDoc()
        else:
            html = self.getQPainterDoc()
        self.doc.setHtml(html)
        # If a print is requested, open print dialog
        # self.preview.paintRequested.connect(self.printPreview)

        preview.exec_()

    def printPreview(self, printer):
        self.doc.print_(printer)

    def print_file(self, dct):
        self.do_print.emit(dct)

    def preview_file(self, dct):
        self.dct = copy.copy(dct)
        self.do_preview.emit(dct)

    def printViaQPainter(self, dct):
        """
        this appars to paint right to the printer
        as self.printer is the parent of the QPointer instance
        dct = {'self.info_jstr': '{"polarization": "CircLeft", "angle": 0.0, "center": [-1380.3554196143814, -119.63448659429068], "energy": 714.9979576566445, "step": [0.06733267796298362, 0.0680900257534698], "scan_type": "sample_image_stack Line_Unidir", "range": [10.032569016484558, 10.145413837267], "file": "S:\\\\STXM-data\\\\Cryo-STXM\\\\2017\\\\guest\\\\0817\\\\C170817057.hdf5", "offset": 0.0, "npoints": [150, 150], "dwell": 1.0, "scan_panel_idx": 5}', 'fname': 'S:\\STXM-data\\Cryo-STXM\\2017\\guest\\0817\\C170817057.hdf5'}
        """

        dialog = QPrintDialog(self.printer, self)
        if not dialog.exec_():
            return
        LeftMargin = LEFT_MARGIN
        sansFont = QFont("Arial", 8)
        sansLineHeight = QFontMetrics(sansFont).height()
        serifFont = QFont("Times", 11)
        serifLineHeight = QFontMetrics(sansFont).height()
        fm = QFontMetrics(serifFont)

        fname = dct["fname"]
        pnts = "%dx%d" % (dct["info_dct"]["npoints"][0], dct["info_dct"]["npoints"][1])
        scan_type = dct["info_dct"]["scan_type"]
        ev = "%.3f eV" % dct["info_dct"]["energy"]
        dwell = "%.2f ms Dwell" % dct["info_dct"]["dwell"]
        pol = "Polariz = %s" % dct["info_dct"]["polarization"]
        data_pm = dct["data_pmap"]
        xaxis_nm = "Sample X (um)"
        yaxis_nm = "counter0"

        # serifLineHeight = fm.height()
        # data_pm = QPixmap("data.png")
        data_pm = data_pm.scaled(QSize(THMB_SIZE, THMB_SIZE))
        hist_pm = QPixmap("hist.png")
        hist_pm = hist_pm.scaled(QSize(THMB_SIZE // 5, THMB_SIZE))
        painter = QPainter()
        painter.begin(self.printer)
        painter.setRenderHints(
            painter.renderHints()
            | QPainter.Antialiasing
            | QPainter.SmoothPixmapTransform
            | QPainter.HighQualityAntialiasing
        )

        pageRect = self.printer.pageRect()
        page = 1

        painter.save()
        y = 0
        # x = pageRect.width() - data_pm.width() - LeftMargin
        x = LeftMargin

        painter.setFont(serifFont)

        y += sansLineHeight
        y += sansLineHeight
        painter.drawText(x, y, "   %s" % fname)
        y += serifLineHeight
        painter.setFont(sansFont)
        painter.drawText(x, y, "%s " % (scan_type))
        y += sansLineHeight
        painter.drawText(x, y, "%s      %s " % (pnts, ev))
        y += sansLineHeight
        painter.drawText(x, y, "%s      %s " % (dwell, pol))
        y += sansLineHeight
        painter.drawPixmap(x, y, data_pm)
        # y += data_pm.height() + sansLineHeight

        ##############contrast gradient
        width = 20
        # QRectF(x,y,width, ht) Constructs a rectangle with (x, y) as its top-left corner and the given width and height.
        contrast_bounds = QRectF(x + data_pm.width() + 20, y, width, data_pm.height())
        # g = QLinearGradient(0.0, 0.0, 0.0, data_pm.height())
        g = QLinearGradient()
        g.setColorAt(0, Qt.white)
        g.setColorAt(1, Qt.black)

        g.setStart(contrast_bounds.topLeft())
        g.setFinalStop(contrast_bounds.bottomRight())
        # #top left
        # g.setStart(x + data_pm.width() + 10, data_pm.height())
        # #btm right
        # g.setFinalStop(width, y)
        # painter.fillRect(x + data_pm.width() + 10, y, width, data_pm.height(), QBrush(g))
        painter.fillRect(contrast_bounds, QBrush(g))
        painter.translate(x + data_pm.width(), y + 0.35 * THMB_SIZE)
        # rotate to place name of counter
        painter.rotate(90.0)
        painter.drawText(5, 0, " %s " % (yaxis_nm))
        painter.rotate(-90.0)
        painter.translate(-1.0 * (x + data_pm.width()), -1.0 * (y + 0.35 * THMB_SIZE))

        #########################en
        # painter.drawPixmap(x + data_pm.width() + 10, y, hist_pm)
        y += data_pm.height() + sansLineHeight
        painter.drawText(x + int(0.25 * data_pm.width()), y, "%s" % xaxis_nm)
        y += sansLineHeight
        painter.setFont(serifFont)
        x = LeftMargin

        # page += 1
        # if page <= len(self.statements):
        #     self.printer.newPage()
        painter.end()
        painter.restore()

    def getQPainterDoc(self):
        r"""Paints right to the printer, as self.printer is the parent of the QPointer instance"""
        self.prev_pmap = None

        title_font = QFont("Arial", 11)
        title_font_metrics = QFontMetrics(title_font)
        title_font_height = title_font_metrics.height()

        normal_font = QFont("Arial", 8)
        normal_font_metrics = QFontMetrics(normal_font)
        normal_font_height = normal_font_metrics.height()

        small_font = QFont("Arial", 7)
        small_font_metrics = QFontMetrics(small_font)
        small_font_height = small_font_metrics.height()

        dct = self.dct
        fname = dct["fname"]
        pnts = "{}x{}".format(*dct["info_dct"]["npoints"])
        scan_type = dct["scan_type"]
        scan_sub_type = "LxL" if dct["scan_sub_type"] == "Line_Unidir" else "PxP"
        if isinstance(dct["info_dct"]["energy"], list):
            ev = "{:.3f} eV".format(dct["info_dct"]["energy"][0])
        else:
            ev = "{:.3f} eV".format(dct["info_dct"]["energy"])
        dwell = "Dwell: {:.2f} ms".format(dct["info_dct"]["dwell"])
        pol = "Polariz: {}".format(dct["info_dct"]["polarization"])
        data_pm: QPixmap = dct["data_pmap"]
        xpositioner = str(dct["xpositioner"])
        ypositioner = str(dct["ypositioner"])
        xaxis_nm = str(dct.get("xaxis_nm", xpositioner))
        yaxis_nm = str(dct.get("yaxis_nm", ypositioner))
        counter_nm = dct['counter_nm']

        x_center = dct["xcenter"]
        x_range = dct["xrange"]
        if isinstance(x_center, (float, int)):
            x_lo = x_center - (x_range / 2)
            x_hi = x_center + (x_range / 2)
        else:  # (focus scans)
            x_lo = 0
            x_hi = x_range
            x_center = x_range / 2

        y_center = dct["ycenter"]
        y_range = dct["yrange"]
        if isinstance(y_center, (float, int)):
            y_lo = y_center - (y_range / 2)
            y_hi = y_center + (y_range / 2)
        else:  # (line spectrum scans)
            y_lo = 0
            y_hi = y_range
            y_center = y_range / 2

        scan_type_val = scan_types.get_value_by_name(scan_type)
        xunits_nm = "energy, eV" if scan_type_val in (scan_types.SAMPLE_LINE_SPECTRUM,) else "um"
        yunits_nm = "um"

        hist_pm = QPixmap("hist.png")
        hist_pm = hist_pm.scaled(QSize(int(THMB_SIZE / 5), THMB_SIZE))

        prev_pmap = QPixmap(SINGLE_DATA_BOX)
        self.prev_pmap = prev_pmap
        prev_pmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter()
        painter.begin(self.prev_pmap)
        painter.setRenderHints(painter.renderHints()
                               | QPainter.Antialiasing
                               | QPainter.SmoothPixmapTransform
                               | QPainter.HighQualityAntialiasing)

        painter.save()

        painter.fillRect(QRect(QPoint(0, 0), SINGLE_DATA_BOX), Qt.white)

        y = 0
        x = LEFT_MARGIN

        def _title_rect(x: int, y: int) -> QRectF:
            return QRectF(x, y, THMB_SIZE * 1.5, title_font_height)
        def _normal_rect(x: int, y: int) -> QRectF:
            return QRectF(x, y, THMB_SIZE * 1.5, normal_font_height)

        painter.setFont(title_font)

        y += normal_font_height * 2
        painter.drawText(_title_rect(x, y), Qt.AlignHCenter, fname)
        y += title_font_height
        painter.setFont(normal_font)
        painter.drawText(_normal_rect(x, y), Qt.AlignHCenter, f"{scan_type} {scan_sub_type}")
        y += normal_font_height
        painter.drawText(_normal_rect(x, y), Qt.AlignHCenter, f"{pnts}     {ev}")
        y += normal_font_height
        painter.drawText(_normal_rect(x, y), Qt.AlignHCenter, f"{dwell}    {pol}")
        if DESCRIPTIVE_AXIS_LABELS:
            y += normal_font_height
            painter.drawText(_normal_rect(x, y), Qt.AlignHCenter, f"X: {xaxis_nm} ({xunits_nm})")
            y += normal_font_height
            painter.drawText(_normal_rect(x, y), Qt.AlignHCenter, f"Y: {yaxis_nm} ({yunits_nm})")
        y += normal_font_height + dpi_scaled(10)

        painter.setFont(normal_font)

        ############################################
        # Y scale on data image
        _x = x
        tick_offset = 17

        if scan_type_val not in (scan_types.SAMPLE_LINE_SPECTRUM,) or DESCRIPTIVE_AXIS_LABELS:
            text_offset = tick_offset - normal_font_metrics.boundingRect(str(round(y_hi))).width() - 5
            painter.drawText(x + text_offset, y + 5, str(round(y_hi)))
            painter.drawLine(x + tick_offset,
                            y,
                            x + tick_offset + SP_LINE_LENGTH,
                            y)

            text_offset = tick_offset - normal_font_metrics.boundingRect(str(round(y_center))).width() - 5
            painter.drawText(x + text_offset, y + 3 + (THMB_SIZE // 2), str(round(y_center)))
            painter.drawLine(x + tick_offset,
                            y + (THMB_SIZE // 2),
                            x + tick_offset + SP_LINE_LENGTH,
                            y + (THMB_SIZE // 2))

            text_offset = tick_offset - normal_font_metrics.boundingRect(f"({yunits_nm})").width() - 5
            painter.drawText(x + text_offset, y + 3 + (THMB_SIZE // 2) + normal_font_height, f"({yunits_nm})")

            text_offset = tick_offset - normal_font_metrics.boundingRect(str(round(y_lo))).width() - 5
            painter.drawText(x + text_offset, y + 1 + THMB_SIZE, str(round(y_lo)))
            painter.drawLine(x + tick_offset,
                            y + THMB_SIZE,
                            x + tick_offset + SP_LINE_LENGTH,
                            y + THMB_SIZE)

        _x += 25
        ###################################

        grey_pm = QPixmap(THMB_SIZE, THMB_SIZE)
        grey_pm.fill(QColor(232, 232, 232))
        painter.drawPixmap(_x, y, grey_pm)

        # now see if the aspect ratio is equal or different, if so adjust image to sit in the center with a black border
        if data_pm.width() < data_pm.height():
            ratio = data_pm.width() / data_pm.height()
            data_pm = data_pm.scaled(QSize(int(ratio * THMB_SIZE), THMB_SIZE))
            newx = _x + (THMB_SIZE / 2) - (data_pm.width() / 2)
            painter.drawPixmap(int(newx), y, data_pm)

        elif data_pm.width() > data_pm.height():
            ratio = data_pm.height() / data_pm.width()
            data_pm = data_pm.scaled(QSize(THMB_SIZE, int(ratio * THMB_SIZE)))
            newy = y + (THMB_SIZE / 2) - (data_pm.height() / 2)
            painter.drawPixmap(_x, int(newy), data_pm)

        else:
            data_pm = data_pm.scaled(QSize(THMB_SIZE, THMB_SIZE))
            painter.drawPixmap(_x, y, data_pm)

        ##############contrast gradient
        width = 10
        # QRectF(x,y,width, ht) Constructs a rectangle with (x, y) as its top-left corner and the given width and height.
        contrast_bounds = QRect(_x + grey_pm.width() + dpi_scaled(20), y, width, grey_pm.height())
        contrast_gradient = QLinearGradient()
        contrast_gradient.setColorAt(0, Qt.white)
        contrast_gradient.setColorAt(1, Qt.black)

        contrast_gradient.setStart(contrast_bounds.topLeft())
        contrast_gradient.setFinalStop(contrast_bounds.bottomRight())
        painter.fillRect(contrast_bounds, QBrush(contrast_gradient))

        painter.drawText(contrast_bounds.right() + 7, contrast_bounds.top() + 5, str(int(dct["data_max"])))
        painter.drawLine(contrast_bounds.right(),
                         contrast_bounds.top(),
                         contrast_bounds.right() + SP_LINE_LENGTH,
                         contrast_bounds.top())

        painter.drawText(contrast_bounds.right() + 7, contrast_bounds.bottom() + 1, str(int(dct["data_min"])))
        painter.drawLine(contrast_bounds.right(),
                         contrast_bounds.bottom(),
                         contrast_bounds.right() + SP_LINE_LENGTH,
                         contrast_bounds.bottom())
        # end of contrast
        ###########################################
        # rotate to place name of counter
        painter.save()
        painter.translate(_x + grey_pm.width(), y + 0.25 * THMB_SIZE)
        painter.rotate(90.0)
        painter.drawText(dpi_scaled(5), -8, counter_nm)

        # UNDO TRANSFORMS
        painter.restore()

        ###########################
        # vertical bars across data image bottom
        y = contrast_bounds.bottom()

        tick_offset = 26
        text_offset = tick_offset - (normal_font_metrics.boundingRect(str(round(x_lo))).width() // 2)
        painter.drawText(x + text_offset,
                         y + 20 + normal_font.pixelSize() + SP_LINE_LENGTH,
                         str(round(x_lo)))
        painter.drawLine(x + tick_offset,
                         y + 5,
                         x + tick_offset,
                         y + 5 + SP_LINE_LENGTH)

        text_offset = tick_offset - (normal_font_metrics.boundingRect(str(round(x_center))).width() // 2)
        painter.drawText(x + text_offset + (THMB_SIZE // 2),
                         y + 20 + normal_font.pixelSize() + SP_LINE_LENGTH,
                         str(round(x_center)))
        text_offset = tick_offset - (normal_font_metrics.boundingRect(f"({xunits_nm})").width() // 2)
        painter.drawText(x + text_offset + (THMB_SIZE // 2),
                         y + 20 + normal_font.pixelSize() + normal_font_height + SP_LINE_LENGTH,
                         f"({xunits_nm})")
        painter.drawLine(x + tick_offset + (THMB_SIZE // 2),
                         y + 5,
                         x + tick_offset + (THMB_SIZE // 2),
                         y + 5 + SP_LINE_LENGTH)

        text_offset = tick_offset - (normal_font_metrics.boundingRect(str(round(x_hi))).width() // 2)
        painter.drawText(x + text_offset + THMB_SIZE,
                         y + 20 + normal_font.pixelSize() + SP_LINE_LENGTH,
                         str(round(x_hi)))
        painter.drawLine(x + tick_offset + THMB_SIZE,
                         y + 5,
                         x + tick_offset + THMB_SIZE,
                         y + 5 + SP_LINE_LENGTH)

        #########################
        y += 27 + normal_font_height * 2
        painter.restore()
        painter.end()

        html = self.create_html_for_pmap(prev_pmap)
        document = QTextDocument()
        document.setHtml(html)
        return html

    def getQPainterSpecDoc(self):
        """
        this appars to paint right to the printer
        as self.printer is the parent of the QPointer instance
        """
        self.prev_pmap = None

        LeftMargin = LEFT_MARGIN
        sansFont = QFont("Arial", 8)
        sansLineHeight = QFontMetrics(sansFont).height()
        serifFont = QFont("Times", 11)
        serifLineHeight = QFontMetrics(sansFont).height()

        arialFontSmall = QFont("Arial", 7)
        arialFontSmallHeight = QFontMetrics(arialFontSmall).height()

        fm = QFontMetrics(serifFont)

        dct = self.dct
        fname = dct["fname"]
        pnts = "%dx%d" % (dct["info_dct"]["npoints"][0], dct["info_dct"]["npoints"][1])
        scan_type = dct["scan_type"]
        scan_sub_type = dct["scan_sub_type"]
        if isinstance(dct["info_dct"]["energy"], list):
            ev = "%.3f eV" % dct["info_dct"]["energy"][0]
        else:
            ev = "%.3f eV" % dct["info_dct"]["energy"]
        dwell = "%.2f ms Dwell" % dct["info_dct"]["dwell"]
        pol = "Polariz = %s" % dct["info_dct"]["polarization"]
        data_pm = dct["data_pmap"]
        xaxis_nm = "%s" % dct["xpositioner"]
        yaxis_nm = dct["counter_nm"]
        units_nm = "um" "s"

        # serifLineHeight = fm.height()
        # data_pm = QPixmap("data.png")
        # data_pm= data_pm.scaled(QSize(THMB_SIZE, THMB_SIZE))

        prev_pmap = QPixmap(SPEC_SINGLE_DATA_BOX)
        self.prev_pmap = prev_pmap
        prev_pmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter()
        painter.begin(self.prev_pmap)
        #
        painter.setRenderHints(
            painter.renderHints()
            | QPainter.Antialiasing
            | QPainter.SmoothPixmapTransform
            | QPainter.HighQualityAntialiasing
        )
        #
        pageRect = self.printer.pageRect()
        page = 1

        painter.save()

        painter.fillRect(QRect(QPoint(0, 0), SPEC_SINGLE_DATA_BOX), Qt.white)

        y = 0
        # x = pageRect.width() - data_pm.width() - LeftMargin
        x = LeftMargin

        painter.setFont(serifFont)

        y += sansLineHeight
        y += sansLineHeight
        painter.drawText(x + 25, y, "   %s" % fname)
        y += serifLineHeight
        painter.setFont(sansFont)
        painter.drawText(x + 25, y, "%s      %s " % (pnts, scan_type))
        y += sansLineHeight
        painter.drawText(x + 25, y, "%s          %s " % (scan_sub_type, ev))
        y += sansLineHeight
        painter.drawText(x + 25, y, "%s      %s " % (dwell, pol))
        y += sansLineHeight

        _x = x + 25
        ###################################

        grey_pm = QPixmap(SPEC_THMB_WD, SPEC_THMB_HT)
        # grey_pm.fill(QColor(232,232,232))
        # painter.drawPixmap(_x, y, grey_pm)

        # # painter.drawPixmap(btm_rectF, self.pic, QtCore.QRectF(grey_pm.rect()))
        # pic_rectF = QRectF(data_pm.rect())
        cb = grey_pm.rect().center()
        # # now see if the aspect ratio is equal or different, if so adjust image to sit in the center with a black border
        if data_pm.width() < data_pm.height():
            r = float(data_pm.width()) / float(data_pm.height())
            # data_pm = data_pm.scaled(QSize(r * SPEC_THMB_WD, SPEC_THMB_HT))
            newx = int(_x + float((SPEC_THMB_WD / 2.0)) - float(data_pm.width()) / 2.0)
            painter.drawPixmap(newx, y, data_pm)

        elif data_pm.width() > data_pm.height():
            r = float(data_pm.height()) / float(data_pm.width())
            # data_pm = data_pm.scaled(QSize(SPEC_THMB_WD, r*SPEC_THMB_HT))
            newy = int(y + float((SPEC_THMB_HT / 2.0)) - float(data_pm.height()) / 2.0)
            painter.drawPixmap(_x, newy, data_pm)
        else:
            # data_pm = data_pm.scaled(QSize(SPEC_THMB_WD, SPEC_THMB_HT))
            painter.drawPixmap(_x, y, data_pm)

        painter.translate(_x + grey_pm.width() - 10, y + 0.25 * SPEC_THMB_HT)
        # rotate to place name of counter
        painter.rotate(90.0)
        painter.drawText(0, -5, " %s " % (yaxis_nm))
        # UNDO TRANSFORM
        painter.rotate(-90.0)
        painter.translate(
            -1.0 * (_x + grey_pm.width()), -1.0 * (y + 0.25 * SPEC_THMB_HT)
        )

        y += grey_pm.height() + 27 + sansLineHeight

        painter.setFont(arialFontSmall)
        painter.drawText(x + int(grey_pm.width() / 2), y - 25, "%s" % xaxis_nm)
        painter.setFont(serifFont)
        painter.restore()
        painter.end()

        html = self.create_html_for_pmap(prev_pmap)
        document = QTextDocument()
        document.setHtml(html)
        return html

    def create_html_for_pmap(self, pmap):
        text = "<html>"

        byteArray = QByteArray()
        buffer = QBuffer(byteArray)
        buffer.open(QIODevice.WriteOnly)
        pmap.save(buffer, "PNG")
        sdata = str(byteArray.toBase64())
        sdata = sdata.replace("b'", "")
        sdata = sdata.replace("'", "")
        url = '<img src="data:image/png;base64,' + sdata + '"/>'
        text += url
        text += "</html>"
        return text


if __name__ == "__main__":
    form = PrintSTXMThumbnailWidget(
        fname=r"S:\STXM-data\Cryo-STXM\2017\guest\1215\C171215077.hdf5"
    )
    form.show()
    app.exec_()
