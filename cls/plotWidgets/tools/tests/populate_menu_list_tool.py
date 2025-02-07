# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 CEA
# Pierre Raybaut
# Licensed under the terms of the CECILL License
# (see guiqwt/__init__.py for details)

"""All image and plot tools test"""



import os.path as osp
import numpy as np
import random

from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal, QObject, QTimer

import guiqwt
from guiqwt.plot import ImageDialog
from plotpy.tools import CommandTool, DefaultToolbarID
from plotpy.interfaces import (
    IColormapImageItemType, IImageItemType
)
from guiqwt.config import _
from guiqwt.builder import make

from cls.plotWidgets.tools.clsSigSelectionTool import clsSignalSelectTool

_dir = osp.dirname(osp.abspath(__file__))

def get_selected_detector_list():
    l = []
    l.append('Default_Counter')
    l.append("D2C0")
    l.append("D2C1")
    l.append("D2C2")
    l.append("D2C3")
    l.append("D2C4")
    l.append("D2C5")
    l.append("D2C6")
    l.append("D2C7")
    return(l)


def update_image_tool_status(tool, plot):
    from plotpy.items.annotation import ImagePlot

    enabled = isinstance(plot, ImagePlot)
    tool.action.setEnabled(enabled)
    return enabled

def reconnect_signal(obj, sig, cb):
    """
    This function takes the base object, the signal addr and the callback and checks first to see if the signal is still connected
    if it is it is disconnected before being connected to the callback
    ex:
        was:
            self.executingScan.sigs.changed.connect(self.add_line_to_plot)
        is:
            self.reconnect_signal(self.executingScan.sigs, self.executingScan.sigs.changed, self.add_line_to_plot)

    :param obj: base QObject
    :param sig: addr of signal instance
    :param cb: callback to attach signal to
    :return:
    """
    if obj.receivers(sig) > 0:
        sig.disconnect()
    sig.connect(cb)


def disconnect_signal(obj, sig):
    """
    This function takes the base object, the signal addr and checks first to see if the signal is still connected
    if it is it is disconnected

    :param obj: base QObject
    :param sig: addr of signal instance
    :return:
    """
    if obj.receivers(sig) > 0:
        sig.disconnect()


# class SignalSelectToolTool(CommandTool):
#     changed = pyqtSignal(object)
#
#     def __init__(self, manager, toolbar_id=DefaultToolbarID):
#         super(SignalSelectToolTool, self).__init__(
#             manager,
#             _("SignalSelectTool"),
#             tip=_("Select a signal to view"),
#             toolbar_id=toolbar_id
#         )
#         self.action.setEnabled(False)
#         self.action.setIconText("Signals  ")
#
#     def create_action_menu(self, manager):
#         """Create and return menu for the tool's action"""
#         dets = manager.get_selected_detectors()
#         #dets = get_selected_detector_list()
#         if len(dets) > 0:
#             #menu = QtWidgets.QMenu()
#             menu = self.menu
#             #clean menu
#             actions = menu.actions()
#             for a in actions:
#                 menu.removeAction(a)
#             disconnect_signal(menu, menu.triggered)
#
#             for signal_name in manager.get_selected_detectors():
#                 do_connect = True
#                 #icon = build_icon_from_signal_name(signal_name)
#                 action = menu.addAction(signal_name)
#                 action.setEnabled(True)
#                 #action.setCheckable(True)
#
#             menu.triggered.connect(self.activate_sigsel_tool)
#             return menu
#         print('create_action_menu: returning none')
#         return(QtWidgets.QMenu())
#
#     def update_menu(self, manager):
#         self.menu = self.create_action_menu(manager)
#         self.action.setMenu(self.menu)
#
#
#     def activate_command(self, plot, checked):
#         """Activate tool"""
#         pass
#
#     # def get_selected_images(self, plot):
#     #     items = [it for it in plot.get_selected_items(item_type=IColormapImageItemType)]
#     #     if not items:
#     #         active_image = plot.get_last_active_item(IColormapImageItemType)
#     #         if active_image:
#     #             items = [active_image]
#     #     return items
#
#     def get_image_items(self, plot):
#         i = []
#         items = plot.items
#         for item in items:
#             if type(item) == plotpy.items.ImageItem:
#                 i.append(item)
#         return (i)
#
#     def activate_sigsel_tool(self, action):
#         plot = self.get_active_plot()
#         xcs = self.manager.get_xcs_panel()
#         ycs = self.manager.get_ycs_panel()
#         xcs_plot = xcs.cs_plot
#         ycs_plot = ycs.cs_plot
#
#         if plot is not None:
#             items = self.get_image_items(plot)
#             signal_name = str(action.text())
#             self.action.setIconText(f'{signal_name}  ')
#             self.changed.emit(signal_name)
#             for item in items:
#             #     item.imageparam.colormap = signal_name
#             #     item.imageparam.update_image(item)
#                 if item.title().text().find(signal_name) > -1:
#                     #make sure this image item is in the cross sections known_items property
#                     xcs_plot.add_cross_section_item(item)
#                     ycs_plot.add_cross_section_item(item)
#                     item.setVisible(True)
#                     item.select()
#                 else:
#                     item.setVisible(False)
#             self.action.setText(signal_name)
#             plot.invalidate()
#             self.update_status(plot)
#
#     def update_status(self, plot):
#         if update_image_tool_status(self, plot):
#             item = plot.get_last_active_item(IColormapImageItemType)
#             #icon = self.default_icon
#             if item:
#                 self.action.setEnabled(True)
#                 # signal_name = item.get_color_map_name()
#                 # if signal_name:
#                 #     icon = build_icon_from_signal_name(signal_name)
#             else:
#                 self.action.setEnabled(False)
#             #self.action.setIcon(icon)


class Window(ImageDialog):

    def __init__(self, edit=False, toolbar=True,
                      wintitle="All image and plot tools test", numY=256, numX=256, is_line=False):
        super(Window, self).__init__(edit=edit, toolbar=toolbar, wintitle=wintitle,options=dict(
            lock_aspect_ratio=True,
            show_contrast=True,
            show_xsection=True,
            show_ysection=True,
            xlabel=("microns", ""),
            ylabel=("microns", ""),
            colormap="bone",
        ))
        self.selected_detectors = []
        self.sigsel_tool = self.add_tool(clsSignalSelectTool)
        self.on_change = self.det_sel_changed
        self.sigsel_tool.changed.connect(self.on_change)
        self.plot = self.get_plot()
        self.plot.setAutoReplot(True)
        #self.plot.SIG_MARKER_CHANGED.connect(self.on_marker_changed)
        self.setMinimumWidth(600)
        self.data_emitter = DataEmitter(detectors=get_selected_detector_list(),numY=numY,numX=numX, is_line=is_line)
        self.data_emitter.changed.connect(self.on_data_changed)
        self.toggle_dets_btn = QtWidgets.QPushButton("change dets")
        self.toggle_dets_btn.clicked.connect(self.change_sel_dets)
        layout = self.layout()
        layout.addWidget(self.toggle_dets_btn)

    def change_sel_dets(self):
        dets = self.get_selected_detectors()
        if len(dets) == 4:
            det_nums = random.sample(range(0, 7), 3)
        else:
            det_nums = random.sample(range(0, 7), 4)
        det_lst = []
        for d in det_nums:
            dstr = f'D2C{d}'
            det_lst.append(dstr)
        self.set_selected_detectors(det_lst)

    def set_selected_detectors(self, dets):
        self.selected_detectors = dets
        self.sigsel_tool.update_menu(self)

    def get_selected_detectors(self):
        return(self.selected_detectors)

    def on_marker_changed(self, dud):
        print(dud)

    def get_image_items(self):
        i = []
        items = self.plot.items
        for item in items:
            if type(item) == plotpy.items.ImageItem:
                i.append(item)
        return (i)

    def get_image_item_by_name(self, nm):
        items = self.get_image_items()
        for item in items:
            if item.title().text().find(nm) > -1:
                return(item)


    def det_sel_changed(self, s):
        print(f'det changed to [{s}]')
        item = self.get_image_item_by_name(s)

    def on_data_changed(self, dct):
        item = self.get_image_item_by_name(dct['det_nm'])
        y, x, data = dct['data']
        is_line = dct['is_line']
        #modify the data
        if not is_line:
            item.data[y,x] = data
        else:
            item.data[y] = data
        #invalidate the plot so it replots?
        self.plot.invalidate()



class DataEmitter(QObject):
    changed = pyqtSignal(object)

    def __init__(self, detectors=[], numY=1, numX=1, is_line=False):
        super(DataEmitter, self).__init__(None)
        self.is_line = is_line
        self.numY = numY
        self.numX = numX
        self.timer = QTimer()
        self.timer.timeout.connect(self.emit_data)
        self.timer.start(1000)
        self.dets = detectors
        self.row_cntr = numY - 1

    def emit_data(self):
        for d in self.dets:
            if(not self.is_line):
                data = np.random.randint(255, size=1, dtype=np.int32)
                #y = np.random.randint(self.numY, size=1, dtype=np.int32)
                x = np.random.randint(self.numX, size=1, dtype=np.int32)
                self.changed.emit({'det_nm': d, 'data': (self.row_cntr, x[0], data[0]),'is_line': self.is_line})
            else:
                data = np.random.randint(255, size=(1, self.numX), dtype=np.int32)
                #y = np.random.randint(self.numY, size=1, dtype=np.int32)
                x = np.random.randint(self.numX, size=1, dtype=np.int32)
                self.changed.emit({'det_nm': d, 'data': (self.row_cntr, x[0], data),'is_line': self.is_line})
        self.row_cntr = self.row_cntr - 1



def go():
    """Test"""
    # -- Create QApplication
    import guidata
    _app = guidata.qapplication()
    # --
    win = Window(edit=False, toolbar=True, wintitle="All image and plot tools test", numY=256, numX=256,is_line=True)
    win.set_selected_detectors(get_selected_detector_list())
    dets = win.get_selected_detectors()
    plot = win.get_plot()
    images = []
    for f in dets:

        filename = osp.join(osp.dirname(__file__), f"{f}.png")
        i = make.image(filename=filename, colormap="gist_gray")
        if len(images) == 0:
            i.setVisible(True)
        else:
            i.setVisible(False)
        images.append(i)
        plot.add_item(i)


    win.exec_()

if __name__ == "__main__":
    go()
