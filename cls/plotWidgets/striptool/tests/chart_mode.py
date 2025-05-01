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

        # Install an event filter to detect focus changes
        self.menu.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.menu and event.type() == QtCore.QEvent.FocusOut:
            # Close the menu when focus changes to something outside the menu
            self.menu.hide()
        return super(CheckableListToolButton, self).eventFilter(obj, event)

    def on_menu_closed(self):
        # Handle menu close event (e.g., print selected items)
        selected_items = [action.text() for action in self.actions if action.isChecked()]
        print("Selected items:", selected_items)


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)

    sigList = ["PMT", "Counter1", "Analog0", "Signal 4"]
    window = CheckableListToolButton(sigList)
    window.show()

    sys.exit(app.exec_())