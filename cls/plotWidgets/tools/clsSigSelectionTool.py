"""
Created on Feb 3, 2023

@author: bergr
"""
from PyQt5.QtWidgets import QMenu
from PyQt5.QtCore import pyqtSignal

import plotpy
from plotpy.tools import CommandTool, DefaultToolbarID
from plotpy.interfaces import (
    IColormapImageItemType,
    ICurveItemType
)
from plotpy.config import _
from plotpy.plot import BasePlot

from cls.utils.sig_utils import disconnect_signal
from cls.plotWidgets.tools.utils import get_parent_who_has_attr, get_widget_with_objectname

def update_sigselect_tool_status(tool, plot):
    enabled = (isinstance(plot, BasePlot))
    tool.action.setEnabled(enabled)
    return enabled

#  This tool is dependant on the existance of a function called get_selected_detectors
# exists in the parent widget of this tool (typically the ImageWidget), this function returns
# a list of detector signal names that have been populated by the parent of the ImageWidget.
# the list of detector names returned from the function are used to populate the menu of the Tool button
class clsSignalSelectTool(CommandTool):
    changed = pyqtSignal(object)

    def __init__(self, manager, toolbar_id=DefaultToolbarID):
        super(clsSignalSelectTool, self).__init__(
            manager,
            _("clsSignalSelectTool"),
            tip=_("Select a signal to view"),
            toolbar_id=toolbar_id
        )
        self.action.setEnabled(True)
        self.action.setIconText("Signals  ")
        self.parent_obj_nm = "NONE"
        if get_widget_with_objectname(manager, "CurveViewerWidget"):
            self.parent_obj_nm = "CurveViewerWidget"
        elif get_widget_with_objectname(manager, "ImageWidgetPlot"):
            self.parent_obj_nm = "ImageWidgetPlot"

    def set_pulldown_title(self, title):
        self.action.setIconText(f"{title}  ")

    def create_action_menu(self, manager):
        """Create and return menu for the tool's action"""
        p = get_parent_who_has_attr(manager, 'get_selected_detectors')
        if p:
            dets = p.get_selected_detectors()
            if len(dets) > 0:
                menu = self.menu
                #clear previous menu
                actions = menu.actions()
                for a in actions:
                    menu.removeAction(a)
                disconnect_signal(menu, menu.triggered)

                for signal_name in p.get_selected_detectors():
                    action = menu.addAction(signal_name)
                    action.setEnabled(True)

                menu.triggered.connect(self.activate_sigsel_tool)
                return menu

        #print('create_action_menu: returning a blank')
        return QMenu()

    def update_menu(self, manager):
        self.menu = self.create_action_menu(manager)
        self.action.setMenu(self.menu)

    def activate_command(self, plot, checked):
        """Activate tool"""
        pass

    def get_plot_items(self, plot):
        """
        get all of the plot items from the plot searching for a specific type depending on the manager (parent widget)
        """
        i = []
        items = plot.items
        parent_plot_widget = get_parent_who_has_attr(self.manager, 'get_selected_detectors')
        if str(type(parent_plot_widget)).find("CurveViewerWidget") > -1:
            search_type = plotpy.items.CurveItem
        elif str(type(parent_plot_widget)).find("ImageWidgetPlot") > -1:
            search_type = plotpy.items.ImageItem
        else:
            search_type = None

        for item in items:
            if type(item) == search_type:
                i.append(item)
        return (i)

    def set_cross_section_curve_src_img(self, item, cs_plot):
        """
        a function to set the source image for cross section curves
        """
        curves = cs_plot.get_cross_section_curves()
        for curv in curves:
            curv.set_source_image(item)

    def activate_sigsel_tool(self, action):
        '''
        activate the tool and make sure that the current image item is registered with the
        x and y cross secction plots, also:
        - update the name displayed on the button to reflect the selection (setIconText)
        - set the selected image item to be visible and set all others to invisible
        '''
        ilp = self.manager.get_itemlist_panel()
        cntrst_pnl = self.manager.get_contrast_panel()
        xcs_plot = None
        ycs_plot = None
        plot = self.get_active_plot()
        xcs = self.manager.get_xcs_panel()
        ycs = self.manager.get_ycs_panel()
        if xcs:
            xcs_plot = xcs.cs_plot
        if ycs:
            ycs_plot = ycs.cs_plot

        if xcs_plot and ycs_plot:
            do_set_active = True
        else:
            do_set_active = False

        if plot is not None:
            #items = self.get_image_items(plot)
            items = self.get_plot_items(plot)
            signal_name = str(action.text()).replace("DNM_","")
            action.setEnabled(True)
            self.set_pulldown_title(signal_name)
            #self.changed.emit(signal_name)
            row = 0
            for item in items:
                if item.title().text().find(signal_name) > -1:
                    #make sure this image item is in the cross sections known_items property
                    if xcs_plot:
                        xcs_plot.add_cross_section_item(item)
                        self.set_cross_section_curve_src_img(item, xcs_plot)
                    if ycs_plot:
                        ycs_plot.add_cross_section_item(item)
                        self.set_cross_section_curve_src_img(item, ycs_plot)

                    ilp.listwidget.clearSelection()
                    item.setVisible(True)
                    item.select()
                    item.itemChanged()
                    ilp.listwidget.currentRowChanged.emit(row)
                    self.select_items_list_listwidget_item_by_name(ilp.listwidget, signal_name, True)
                    if do_set_active:
                        plot.set_active_item(item)

                else:

                    item.setVisible(False)
                    item.unselect()
                    item.itemChanged()
                    self.select_items_list_listwidget_item_by_name(ilp.listwidget, signal_name, False)
                row = row + 1

            if xcs_plot:
                xcs_plot.items_changed(plot)
            if ycs_plot:
                ycs_plot.items_changed(plot)

            plot.invalidate()
            self.update_status(plot)
            # this call causes the contrast histogram to update to the current
            ilp.listwidget.selection_changed()

    def select_items_list_listwidget_item_by_name(self, lw, name, select=True):
        """
        walk through list of items in item List Panel and select/deselect the one by name
        """
        #for item in lw.selectedItems():
        for item in lw.items:
            if item.title().text() == name:
                #item.setSelected(select)
                if select:
                    item.select()
                else:
                    item.unselect()

    def update_status(self, plot):
        if update_sigselect_tool_status(self, plot):
            if self.parent_obj_nm == "CurveViewerWidget":
                item = plot.get_last_active_item(ICurveItemType)
            elif self.parent_obj_nm == "ImageWidgetPlot":
                item = plot.get_last_active_item(IColormapImageItemType)

            #always make it enabled regardless if something is selected
            self.action.setEnabled(True)

