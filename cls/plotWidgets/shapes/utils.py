from plotpy.builder import make
#from plotpy.builder import make

import os


curDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "/")

MIN_SHAPE_Z = 1001

shape_cntr = MIN_SHAPE_Z

def create_segment(
    rect,
    title="None",
    plot=None,
    annotated=False,
    alpha=0.05,
    l_style="SolidLine",
    l_clr="#ffff00",
):
    """

    :param rect:
    :param xc:
    :param yc:
    :param title:
    :param plot:
    :return:
    """
    global shape_cntr
    # def segment(self, x0, y0, x1, y1, title=None):
    if annotated:
        # annotated_segment(self, x0, y0, x1, y1, title=None, subtitle=None
        r = make.annotated_segment(
            rect[0], rect[1], rect[2], rect[3], title=title, subtitle=None
        )
        sh = r.shape.shapeparam
    else:
        r = make.segment(rect[0], rect[1], rect[2], rect[3], title=title)
        sh = r.shapeparam

    r.set_resizable(False)
    sh._title = title
    sh.fill.alpha = alpha
    sh.sel_fill.alpha = alpha
    sh.symbol.alpha = alpha
    sh.sel_symbol.alpha = alpha
    sh.line._style = l_style
    sh.line._color = l_clr

    sh.symbol.marker = "NoSymbol"
    sh.sel_symbol.marker = "NoSymbol"

    r.set_item_parameters({"ShapeParam": sh})

    # self.plot.add_item(r, z=999999999)
    # z = 999999999
    shape_cntr += 1
    z = shape_cntr
    if plot:
        plot.add_item(r, z)
    return (r, z)


def create_polygon(x_pts, y_pts, title="None", plot=None):
    """
    self explanatory
    :param rect:
    :param xc:
    :param yc:
    :param title:
    :return:
    """

    pts = []
    for i in range(len(x_pts)):
        pts.append((x_pts[i], y_pts[i]))

    r = make.polygon(
        x_pts,
        y_pts,
        closed=True,
        title=title,
    )
    sh = r.shapeparam

    r.set_resizable(False)
    sh._title = title
    sh.fill.alpha = 0.2
    sh.sel_fill.alpha = 0.2
    sh.symbol.alpha = 0.2
    sh.sel_symbol.alpha = 0.2
    sh.line._style = "SolidLine"
    sh.line._color = "#ff5555"

    sh.symbol.marker = "NoSymbol"
    sh.sel_symbol.marker = "NoSymbol"

    r.set_item_parameters({"ShapeParam": sh})

    global shape_cntr
    shape_cntr += 1
    z = shape_cntr
    if plot:
        plot.add_item(r, z)

    return (r, z)


def create_rect_centerd_at(rect, xc, yc, title, plot=None):
    """
    self explanatory
    :param rect:
    :param xc:
    :param yc:
    :param title:
    :return:
    """

    dx = (rect[2] - rect[0]) * 0.5
    dy = (rect[1] - rect[3]) * 0.5
    r, z = create_rectangle((xc - dx, yc + dy, xc + dx, yc - dy), title=title, plot=plot)
    return (r, z)


def create_rectangle(
    rect,
    title="None",
    plot=None,
    annotated=False,
    alpha=0.2,
    l_style="SolidLine",
    l_clr="#55ff7f",
):
    """
    self explanatory
    :param rect:
    :param title:
    :return:
    """
    global shape_cntr
    if annotated:
        r = make.annotated_rectangle(rect[0], rect[1], rect[2], rect[3], title=title)
        sh = r.shape.shapeparam
    else:
        r = make.rectangle(rect[0], rect[1], rect[2], rect[3], title=title)
        sh = r.shapeparam

    r.set_resizable(False)
    sh._title = title
    # sh.fill.alpha = alpha
    sh.fill.alpha = 0.2
    sh.fill.color = l_clr
    sh.sel_fill.alpha = alpha
    sh.sel_fill.color = l_clr
    sh.symbol.alpha = alpha
    sh.sel_symbol.alpha = alpha
    sh.line._style = l_style
    sh.line._color = l_clr

    sh.symbol.marker = "NoSymbol"
    sh.sel_symbol.marker = "NoSymbol"

    # z = None
    shape_cntr += 1
    z = shape_cntr
    if plot:
        plot.add_item(r, z)
        r.set_item_parameters({"ShapeParam": sh})
    return (r, z)


def create_simple_circle(
    xc, yc, rad, title="None", clr=None, fill_alpha=0.05, plot=None
):
    """
    create_simple_circle(): description

    :param xc: xc description
    :type xc: xc type

    :param yc: yc description
    :type yc: yc type

    :param rad: rad description
    :type rad: rad type

    :returns: None
    """
    global shape_cntr
    from plotpy.styles import ShapeParam

    # circ = make.annotated_circle(x0, y0, x1, y1, ratio, title, subtitle)
    # rad = val/2.0
    circ = make.circle(xc, yc + rad, xc, yc - rad, title=title)
    circ.set_resizable(False)
    sh = circ.shapeparam
    sh._title = title
    if clr is not None:
        sh.sel_fill.color = clr
        sh.fill.color = clr

    sh.fill.alpha = fill_alpha
    sh.sel_fill.alpha = fill_alpha
    sh.symbol.alpha = fill_alpha
    sh.sel_symbol.alpha = fill_alpha
    sh.symbol.marker = "NoSymbol"
    sh.sel_symbol.marker = "NoSymbol"

    #         shape.shapeparam
    #         Shape:
    #             _styles:
    #               _ShapeParam___line:
    #                 LineStyleParam:
    #                   Style: Solid line
    #                   Color: black
    #                   Width: 1.0
    #                 LineStyleParam:
    #                   Style: Solid line
    #                   Color: black
    #                   Width: 1.0
    #               _ShapeParam___sym:
    #                 SymbolParam:
    #                   Style: No symbol
    #                   Size: 9
    #                   Border: gray
    #                   Background color: yellow
    #                   Background alpha: 1.0
    #                 SymbolParam:
    #                   Style: No symbol
    #                   Size: 9
    #                   Border: gray
    #                   Background color: yellow
    #                   Background alpha: 1.0
    #               _ShapeParam___fill:
    #                 BrushStyleParam:
    #                   Style: Uniform color
    #                   Color: black
    #                   Alpha: 1.0
    #                   Angle: 0.0
    #                   sx: 1.0
    #                   sy: 1.0
    #                 BrushStyleParam:
    #                   Style: Uniform color
    #                   Color: black
    #                   Alpha: 1.0
    #                   Angle: 0.0
    #                   sx: 1.0
    #                   sy: 1.0
    #             : False
    #             : False

    # circ.set_resizable(False)
    # offset teh annotation so that it is not on the center
    # circ.shape.shapeparam.fill = circ.shape.shapeparam.sel_fill
    # circ.shape.shapeparam.line = circ.shape.shapeparam.sel_line
    # circ.label.C = (50,50)
    # circ.set_label_visible(False)
    # print circ.curve_item.curveparam
    # circ.set_style(, option)
    circ.set_item_parameters({"ShapeParam": sh})
    # z = 999999999
    shape_cntr += 1
    z = shape_cntr
    if plot:
        plot.add_item(circ, z)

    return (circ, z)
