from PyQt5 import QtWidgets, QtCore, QtGui


class PersistentMenu(QtWidgets.QMenu):
    def __init__(self, parent=None):
        super(PersistentMenu, self).__init__(parent)

    def mouseReleaseEvent(self, event):
        action = self.actionAt(event.pos())
        if action and action.isCheckable():
            action.trigger()  # Trigger the action without closing the menu
        else:
            super(PersistentMenu, self).mouseReleaseEvent(event)


class CheckableListToolButton(QtWidgets.QWidget):
    def __init__(self, sigList, parent=None):
        super(CheckableListToolButton, self).__init__(parent)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.toolButton = QtWidgets.QToolButton(self)

        # Set a generic icon for the tool button
        icon = QtGui.QIcon.fromTheme("preferences-system")  # Use a system icon
        self.toolButton.setIcon(icon)
        self.toolButton.setPopupMode(QtWidgets.QToolButton.InstantPopup)

        # Remove the default downward triangle
        self.toolButton.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        self.toolButton.setArrowType(QtCore.Qt.NoArrow)

        # Create a PersistentMenu for the tool button
        self.menu = PersistentMenu(self.toolButton)

        # Add checkable actions for each item in sigList
        self.actions = []
        for sig in sigList:
            action = QtWidgets.QAction(sig, self.menu)
            action.setCheckable(True)
            self.menu.addAction(action)
            self.actions.append(action)

        self.toolButton.setMenu(self.menu)
        self.layout.addWidget(self.toolButton)

        # Install an