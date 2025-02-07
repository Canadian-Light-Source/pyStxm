from PyQt5 import QtWidgets, QtCore

def make_label_tuple(dcs_devname):
    hbox = QtWidgets.QHBoxLayout()
    stopBtn = QtWidgets.QPushButton("STOP")
    fld = QtWidgets.QLineEdit("0")
    #fld.returnPressed.connect(self._on_dev_setpoint_changed)
    spacerItem = QtWidgets.QSpacerItem(
        30, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum
    )
    fld.setMaximumWidth(100)
    fld.setToolTip(dcs_devname)
    # add a new attribute to the pushButton so we can retrieve it later
    stopBtn._dcs_devname = dcs_devname
    name_lbl = QtWidgets.QLabel(f"{dcs_devname}: ")
    fbk_lbl = QtWidgets.QLabel("0")
    fbk_lbl.setAlignment(QtCore.Qt.AlignCenter)
    sts_lbl = QtWidgets.QLabel("STOPPED")
    sts_lbl.setAlignment(QtCore.Qt.AlignCenter)
    hbox.addWidget(name_lbl)
    hbox.addItem(spacerItem)
    hbox.addWidget(fld)
    hbox.addWidget(stopBtn)
    hbox.addWidget(fbk_lbl)
    hbox.addWidget(sts_lbl)
    dct = {'hbox':hbox, 'fbk_lbl': fbk_lbl, 'sts_lbl': sts_lbl, 'fld': fld, 'stopBtn':stopBtn}

    return dct

