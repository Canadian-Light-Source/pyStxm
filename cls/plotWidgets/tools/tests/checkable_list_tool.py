from PyQt5 import QtWidgets, QtCore


class PersistentMenu(QtWidgets.QMenu):
    def __init__(self, parent=None):
        super(PersistentMenu, self).__init__(parent)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)  # Ensure the menu can receive focus

    def mouseReleaseEvent(self, event):
        action = self.actionAt(event.pos())
        if action and action.isCheckable():
            action.trigger()  # Trigger the action without closing the menu
        else:
            super(PersistentMenu, self).mouseReleaseEvent(event)


class CheckableListToolButton(QtWidgets.QWidget):
    focusLost = QtCore.pyqtSignal(list)

    def __init__(self, sigList, parent=None):
        super(CheckableListToolButton, self).__init__(parent)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.toolButton = QtWidgets.QToolButton(self)

        self.toolButton.setText(" Signals  ")
        self.toolButton.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.toolButton.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        self.toolButton.setArrowType(QtCore.Qt.NoArrow)

        self.menu = PersistentMenu(self.toolButton)

        self.actions = []
        for sig in sigList:
            action = QtWidgets.QAction(sig, self.menu)
            action.setCheckable(True)
            self.menu.addAction(action)
            self.actions.append(action)

        self.toolButton.setMenu(self.menu)
        self.layout.addWidget(self.toolButton)

        self.menu.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.menu:
            if event.type() == QtCore.QEvent.FocusOut:
                print("FocusOut event detected")  # Debugging statement
                self.on_list_lose_focus()
                self.menu.hide()
        return super(CheckableListToolButton, self).eventFilter(obj, event)

    def on_list_lose_focus(self):
        selected_items = [action.text() for action in self.actions if action.isChecked()]
        print(f"on_list_lose_focus: emitting signal with {selected_items}")
        self.focusLost.emit(selected_items)


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)

    sigList = ["PMT", "Counter1", "Analog0", "Signal 4"]
    window = CheckableListToolButton(sigList)

    def handle_focus_lost(selected_items):
        print("Focus lost. Selected items:", selected_items)

    window.focusLost.connect(handle_focus_lost)
    window.show()

    sys.exit(app.exec_())