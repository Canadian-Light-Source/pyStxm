from plotpy.plot.manager import PlotManager
def get_parent_who_has_attr(manager, func_nm):
    '''
    keeping looking up the parent chain until the one that contains the desired function is found
    and return it
    '''
    assert type(manager) == PlotManager, f"manager is wrong type, must be type PlotManager, [{type(manager)}] was passed instead"
    max_depth = 50
    p = manager.get_active_plot()
    i = 0
    while i < max_depth:
        if hasattr(p, func_nm):
            return p
        else:
            p = p.parent()
        i += 1


def get_widget_with_objectname(manager, objectname):
    '''
    this is a hack, when guiqwt changed to plotpy the manager used to be the parent plotter like CurveViewerWidget
    but after the change manager is now the PlotManager, so this function walks the parents of that PlotManager and
    returns when it finds the widget with the objectName we are looking for
    '''

    assert type(manager) == PlotManager, f"manager is wrong type, must be type PlotManager, [{type(manager)}] was passed instead"

    max_depth = 50
    p = manager.get_active_plot()
    i = 0
    while i < max_depth:
        if hasattr(p, 'objectName'):
            obj_nm = p.objectName()
            if obj_nm == objectname:
                return True
            else:
                if hasattr(p, 'parent'):
                    if callable(p.parent):
                        p = p.parent()
                    else:
                        break
                else:
                    break
        else:
            if hasattr(p, 'parent'):
                if callable(p.parent):
                    p = p.parent()
                else:
                    break
            else:
                break
        i += 1
    return False