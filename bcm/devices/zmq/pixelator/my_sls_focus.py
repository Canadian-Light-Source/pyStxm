#!/usr/bin/env python3
import pprint

import sys, zmq, json, os
from datetime import datetime, timedelta
from collections import OrderedDict
import numpy
import h5py

import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# from focusfinder import FocusOptimizer, Parameters
from matplotlib import pyplot

from scipy.stats import entropy
from scipy.ndimage import gaussian_filter1d

from PyQt5 import QtCore, QtWidgets, QtGui

CONFIG = {'REQ_adress': 'tcp://VOPI1610-005:56562',  # ZMQ Request port
          'SUB_adress': 'tcp://VOPI1610-005:56561',  # ZMQ subscription port
          'PluginID': 7}  # unsigned int ID for recognising broadcast data intended to satisfy our requests (i.e. when loading data from the server)


class ZMQ_Listener(QtCore.QObject):
    message = QtCore.pyqtSignal(list)

    def __init__(self):
        QtCore.QObject.__init__(self)

        # Socket to talk to server
        context = zmq.Context()
        self.SUBsocket = context.socket(zmq.SUB)
        self.SUBsocket.connect(CONFIG['SUB_adress'])
        self.SUBsocket.setsockopt_string(zmq.SUBSCRIBE, '')  # no filter means accepting all updates
        print('subscribed!')
        self.running = True

    def loop(self):
        while self.running:
            data = [x.decode() for x in self.SUBsocket.recv_multipart()]
            # print(len(data))
            self.message.emit(data)
        # print(data)


class RemoteFileDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(QtWidgets.QDialog, self).__init__()
        self.parent = parent
        self.filepath = None
        self.setDialogTitle()
        self.setMinimumSize(700, 400)
        self.move(parent.window().frameGeometry().topLeft() + parent.window().rect().center() - self.rect().center())

        # A vertical box layout containing rows
        self.MainSizer = QtWidgets.QVBoxLayout()
        hbox1 = QtWidgets.QHBoxLayout()
        vbox1_1 = QtWidgets.QVBoxLayout()
        vbox1_2 = QtWidgets.QVBoxLayout()
        # hbox2 = QtWidgets.QHBoxLayout()
        hbox3 = QtWidgets.QHBoxLayout()
        hbox4 = QtWidgets.QHBoxLayout()

        # Add the widgets to the left of the first row
        vbox1_1.addWidget(QtWidgets.QLabel("Bookmarks:"))
        self.BookmarkList = QtWidgets.QListWidget(self)
        for B in parent.remoteFileSystemInfo['bookmarks']:
            item = QtWidgets.QListWidgetItem(B['label']);
            item.setIcon(self.style().standardIcon(getattr(QtWidgets.QStyle, 'SP_DirLinkIcon')))
            item.setToolTip(B['target'])
            self.BookmarkList.addItem(item)
        self.BookmarkList.itemClicked.connect(self.selectBookmark)
        self.BookmarkList.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        # self.BookmarkList.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.BookmarkList.setSpacing(5)
        self.BookmarkList.setFixedWidth(
            self.BookmarkList.sizeHintForColumn(0) + 10 + 2 * self.BookmarkList.frameWidth())
        vbox1_1.addWidget(self.BookmarkList)
        hbox1.addLayout(vbox1_1)

        # Add the widgets to the right of the first row
        self.PathList = QtWidgets.QListWidget(self)
        self.PathList.setFlow(QtWidgets.QListView.LeftToRight)
        self.PathList.itemClicked.connect(self.selectBookmark)
        self.PathList.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        # self.PathList.setStyleSheet( "QListWidget::item { border-left: 1px solid grey; }" )
        self.PathList.setStyleSheet("QListWidget::item { background: grey; }")
        self.PathList.setSpacing(3)
        self.PathList.setFixedHeight(self.PathList.sizeHintForRow(0) + 30 + 2 * self.PathList.frameWidth())
        vbox1_2.addWidget(self.PathList)

        self.FileList = QtWidgets.QListWidget(self)
        self.FileList.itemDoubleClicked.connect(self.selectFileItem)
        vbox1_2.addWidget(self.FileList, stretch=1)
        hbox1.addLayout(vbox1_2, stretch=1)
        self.MainSizer.addLayout(hbox1)

        # Add the widgets to the third row
        self.showHiddenCheck = QtWidgets.QCheckBox("Show hidden")
        self.showHiddenCheck.clicked.connect(self.setShowHiddenChecked)
        hbox3.addWidget(self.showHiddenCheck)
        self.showHiddenCheck.setChecked(parent.remoteFileSystemInfo['showHidden'])
        hbox3.addStretch(1)
        self.FileTypeCombobox = QtWidgets.QComboBox(self)
        self.FileTypeCombobox.addItems([parent.remoteFileSystemInfo['fileExtension']])
        hbox3.addWidget(self.FileTypeCombobox)
        self.MainSizer.addLayout(hbox3)

        # Add widgets for the fourth row - just OK, cancel buttons
        hbox4.addStretch(1)
        self.button_ok = QtWidgets.QPushButton('Open')
        self.button_ok.clicked.connect(self.OnAccept)
        self.button_ok.setEnabled(False)
        self.FileList.itemClicked.connect(lambda: self.button_ok.setEnabled(True))
        hbox4.addWidget(self.button_ok)
        button_cancel = QtWidgets.QPushButton('Cancel')
        button_cancel.clicked.connect(self.close)
        hbox4.addWidget(button_cancel)
        self.MainSizer.addLayout(hbox4)

        # Set self.MainSizer as the layout for the window
        self.populateFileList()
        self.setLayout(self.MainSizer)
        self.setModal(True)

    def setDialogTitle(self):
        if self.parent.REQ_response:
            self.setWindowTitle('Open File')
        else:
            self.setWindowTitle('ERROR >> Pixelator is not responding!!!')

    def populateFileList(self):
        self.FileList.clear()
        self.PathList.clear()
        self.button_ok.setEnabled(False)
        # print(self.parent.remoteFileSystemInfo['directory'])
        response = self.parent.zmqRequest(["loadFile directory",
                                           '{{"directory":"{directory}", "showHidden":{showHidden}, "fileExtension":"{fileExtension}", "pluginNumber":0}}'.format(
                                               **self.parent.remoteFileSystemInfo)])
        # print(response)
        self.setDialogTitle()
        if response is not None:
            response = response[1]
            self.parent.remoteFileSystemInfo['directory'] = response['directory']
            more_path = response['directory']
            print(more_path)
            path_items = []
            tail = 'None'
            while len(tail) > 0:
                more_path, tail = os.path.split(more_path)
                path_items += [tail]
            path_items = [more_path] + path_items[-2::-1]
            # self.PathList.addItems(path_items)
            for i, P in enumerate(path_items):
                item = QtWidgets.QListWidgetItem(P);
                item.setToolTip('/'.join(path_items[:i + 1]))
                self.PathList.addItem(item)

            self.FileList_Dirs = sorted(response['directories'])
            for D in self.FileList_Dirs:
                item = QtWidgets.QListWidgetItem(D);
                item.setIcon(self.style().standardIcon(getattr(QtWidgets.QStyle, 'SP_DirIcon')))
                self.FileList.addItem(item)
            # if 'files' in response.keys():
            for F in sorted(response['files']):
                item = QtWidgets.QListWidgetItem(F);
                item.setIcon(self.style().standardIcon(getattr(QtWidgets.QStyle, 'SP_FileIcon')))
                self.FileList.addItem(item)
            # self.FileList.addItems(response['files'])

    def selectFileItem(self, item):
        self.setDialogTitle()
        # print(item)
        # print(item.text())
        if item.text() in self.FileList_Dirs:
            # print('is dir')
            self.parent.remoteFileSystemInfo['directory'] = os.path.normpath(
                '/'.join([self.parent.remoteFileSystemInfo['directory'], item.text()])).replace(os.sep, '/')
            print(f"constructed:\t{self.parent.remoteFileSystemInfo['directory']}")
            self.populateFileList()
        else:
            # print('is file')
            self.filepath = '/'.join([self.parent.remoteFileSystemInfo['directory'], item.text()])
            self.accept()

    def selectBookmark(self, item):
        print(item.toolTip())
        self.parent.remoteFileSystemInfo['directory'] = item.toolTip()
        self.populateFileList()

    def setShowHiddenChecked(self, value=True):
        # print(int(value))
        self.showHiddenCheck.setChecked(value)
        self.parent.remoteFileSystemInfo['showHidden'] = int(value)

    def OnAccept(self):
        # print(self.FileList.selectedItems())
        # self.filepath = [1]
        self.selectFileItem(self.FileList.selectedItems()[0])


class App(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.title = 'Focus Spy'
        self.time_last_message = datetime.now()
        self.zmq_timeout_warning = 25  # seconds

        ## User interface
        self.setWindowTitle(self.title)
        self.setGeometry(10, 10, 800, 600)
        self.statusBar()
        self.spinner = 0

        ## data
        self.scan_running = False
        self.scan_data_is_fresh = False
        self.scan_shape = None
        self.scan_extent = None
        self.scan_data = None
        self.scan_axis_titles = None
        # self.scan_data = numpy.full([10,10],numpy.nan)
        self.image_buffer = None
        self.tile_shapes = []
        self.scan_seq = 0

        self.line_entropy = None
        self.SignalNoiseRatio = 0

        ## Set up ZMQ listener in separate thread
        message = QtCore.pyqtSignal(list)
        self.thread = QtCore.QThread()
        self.zmq_listener = ZMQ_Listener()
        self.zmq_listener.moveToThread(self.thread)
        self.thread.started.connect(self.zmq_listener.loop)
        self.zmq_listener.message.connect(self.signal_received)
        QtCore.QTimer.singleShot(0, self.thread.start)
        self.REQcontext = zmq.Context()
        self.REQsocket = None
        self.REQ_response = False
        self.remoteFileSystemInfo = {'bookmarks': [], 'directory': '/tmp', 'fileExtension': '.hdf5', 'showHidden': 0}
        self.zmqREQconnect()

        ## request initial status and default settings of the Pixelator server
        self.initPixelatorStatus()  # This also causes Pixelator to publish some messages

        ## Regularly check time since last message
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.showTime)
        self.timer.start(1000)  # milliseconds

        ## GUI widgets
        FileLoadLocal = QtWidgets.QAction(QtGui.QIcon('open.png'), '&Load Local', self)
        FileLoadLocal.setShortcut('Ctrl+O')
        FileLoadLocal.setStatusTip('Load data from local file system')
        FileLoadLocal.triggered.connect(self.loadFileLocal)

        FileLoadRemote = QtWidgets.QAction(QtGui.QIcon('open.png'), '&Load Remote', self)
        FileLoadRemote.setStatusTip('Load data from server file system')
        FileLoadRemote.triggered.connect(self.loadFileRemote)

        exitAct = QtWidgets.QAction(QtGui.QIcon('exit.png'), '&Exit', self)
        exitAct.setShortcut('Ctrl+Q')
        exitAct.setStatusTip('Exit application')
        exitAct.triggered.connect(app.quit)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(FileLoadLocal)
        fileMenu.addAction(FileLoadRemote)
        fileMenu.addAction(exitAct)

        actionMenu = menubar.addMenu('&Action')
        self.autofocusSampleZ = QtWidgets.QAction('Autofocus Sample&Z', self)
        self.autofocusSampleZ.setStatusTip('Set SampleZ for autofocus')
        self.autofocusSampleZ.triggered.connect(self.setAutofocus)
        actionMenu.addAction(self.autofocusSampleZ)

        self.autofocusOSAgap = QtWidgets.QAction('Autofocus &OSA gap', self)
        self.autofocusOSAgap.setStatusTip('Set OSA gap for autofocus')
        self.autofocusOSAgap.triggered.connect(self.setAutofocusOSAgap)
        actionMenu.addAction(self.autofocusOSAgap)

        self._main = QtWidgets.QWidget()
        self.setCentralWidget(self._main)
        # layout = QtWidgets.QVBoxLayout(self._main)
        grid = QtWidgets.QGridLayout(self._main)

        self.canvas = self.PlotCanvas(self, width=5, height=4)
        # layout.addWidget(self.canvas)
        grid.addWidget(self.canvas, 0, 0, 1, 1)

        self.frame = QtWidgets.QFrame(self._main)
        self.frame.setFrameStyle(QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Sunken)
        self.frameLayout = QtWidgets.QVBoxLayout(self.frame)
        self.frame.setLayout(self.frameLayout)
        grid.addWidget(self.frame, 0, 0, 1, 1, alignment=QtCore.Qt.AlignLeft | QtCore.Qt.AlignBottom)
        self.frame.setVisible(False)
        self.button_setFocus = QtWidgets.QPushButton('Set Temporary Focus', parent=self.frame)
        self.button_setFocus.clicked.connect(self.setFocus)
        self.frameLayout.addWidget(self.button_setFocus)
        self.button_autofocusSampleZ = QtWidgets.QPushButton('SampleZ Autofocus', parent=self.frame)
        self.button_autofocusSampleZ.clicked.connect(self.setAutofocus)
        self.frameLayout.addWidget(self.button_autofocusSampleZ)
        self.button_autofocusOSAgap = QtWidgets.QPushButton('OSA Gap Autofocus', parent=self.frame)
        self.button_autofocusOSAgap.clicked.connect(self.setAutofocusOSAgap)
        self.frameLayout.addWidget(self.button_autofocusOSAgap)

        response = self.zmqRequest(['recordedChannels', json.dumps(['Counter1', 'Analog0'])])
        print(response)

        # response = self.zmqRequest(['detectorSettings'])
        # pprint.pprint(response)
        self.show()

    # self.loadFileRemote()

    def userFocusButtons(self, visible=True, enable=True):
        print('userFocusButtons')
        self.frame.setVisible(visible)
        if (None in self.canvas.crosshair.position) or not self.scan_data_is_fresh:
            enable = True  # False
        for item in [self.button_autofocusSampleZ, self.button_autofocusOSAgap, self.autofocusSampleZ,
                     self.autofocusOSAgap]:
            # print(item)
            # item.setParent(None) # this deletes the widget
            item.setEnabled(enable)

    # button = QtWidgets.QPushButton('Set Focus',parent=self.frame)
    # self.frameLayout.addWidget(button)
    # button2 = QtWidgets.QPushButton('Set Focus',parent=self.frame,height=50)
    # self.frameLayout.addWidget(button2)

    def zmqREQconnect(self):
        """
        Connect to the ZMQ server
        """
        ## Close any existing REQ socket
        if self.REQsocket is not None:
            self.REQsocket.close()
        ## Set up ZMQ request socket
        self.REQsocket = self.REQcontext.socket(zmq.REQ)
        self.REQsocket.connect(CONFIG['REQ_adress'])
        self.REQsocket.setsockopt(zmq.LINGER,
                                  0)  ## Important in case that the zmq server dies (otherwise it hangs until the message is sent or garbage collected...)

    def zmqRequest(self, command, timeout=500):
        """
        This function sends a command through the specified ZMQ request port
        and returns the response from the ZMQ server
        """

        def isListOfStrings(data):
            if type(data) != list:
                return False

            for d in data:
                if type(d) != str:  ## Python 3 str = unicode
                    return False
            return True

        # check data
        if not isListOfStrings(command):
            raise Exception("ERROR >> zmqRequest needs a list of strings (use json.dumps if you have a dictionary)")

        # something to send?
        if len(command) == 0:  # nothing to send
            print("WARNING >> zmqRequest called without data")
            return ''

        try:
            # send all but last part
            for i in range(len(command) - 1):
                self.REQsocket.send_string(command[i], flags=zmq.SNDMORE)
            # send last part
            self.REQsocket.send_string(command[-1])
        except zmq.error.ZMQError:
            self.zmqREQconnect()

        response = None
        if (self.REQsocket.poll(timeout) & zmq.POLLIN) != 0:
            response = [json.loads(x.decode()) for x in self.REQsocket.recv_multipart(zmq.NOBLOCK)]
            self.REQ_response = True
            self.time_last_message = datetime.now()
            if not (type(response) is list and response[0] == {'status': 'ok'}):  # responds with error message
                error_dialog = QtWidgets.QErrorMessage()
                error_dialog.showMessage(response[0]['message'])
                error_dialog.exec_()
                print(f"ZMQ ERROR >> {response[0]['message']}")
        else:  # when no response at all
            self.REQ_response = False
        self.showTime()
        return response

    def initPixelatorStatus(self):
        '''Request initial data from the Pixelator server.'''
        response = self.zmqRequest(['initialize'])

        pprint.pprint(response)

        if response is None:
            print("WARNING >> no zmq response from Pixelator server at {}".format(CONFIG['REQ_adress']))
        # raise Exception("ERROR >> no zmq response from Pixelator server at {}".format(CONFIG['REQ_adress']))
        else:
            # response.push_back( JsonUtils::response() ); #i.e. status
            # self.status = response[0]
            # response.push_back( JsonUtils::positionerDefinition() );
            self.positionerDefinition = response[1]
            # response.push_back( JsonUtils::detectorDefinition() );
            self.detectorDefinition = response[2]
            # response.push_back( Oscilloscope::getInstance().getDefinition() );
            self.oscilloscopeDefinition = response[3]
            # response.push_back( ZonePlate::getInstance().zonePlateDefinition() );
            self.zonePlateDefinition = response[4]
            # response.push_back( JsonUtils::value2string( NeXusFileReader::loadFile_getDefaults() ) );
            self.remoteFileSystemInfo = response[5]

        ##This also causes Pixelator to publish some messages
        # Status::getInstance().publishPositionerStatus(true);
        # Status::getInstance().publishFocalStatus(true);
        # Status::getInstance().publishScanStatus(true);
        # Status::getInstance().publishBeamShutterStatus(true);
        # Status::getInstance().publishTopupStatus(true);
        # Status::getInstance().publishUserStatus(true);
        # ScanController::getInstance().publishRecordedChannels();
        # ScanController::getInstance().publishFocusType();
        # ScanController::getInstance().publishScanTypeArchiveAttr();
        # ScanController::getInstance().publishBeamShutterMode();
        # ScanController::getInstance().publishTopupMode();

    def showTime(self):
        elapsed_time = (datetime.now() - self.time_last_message).total_seconds()
        # print(elapsed_time)
        if not self.REQ_response:
            self.statusBar().showMessage(
                f"Warning! {datetime.utcfromtimestamp(elapsed_time).strftime('%H:%M:%S')} since last message from Pixelator (failed request)")
        elif elapsed_time > self.zmq_timeout_warning:
            self.statusBar().showMessage(
                f"Warning! {datetime.utcfromtimestamp(elapsed_time).strftime('%H:%M:%S')} since last message from Pixelator")
        else:
            self.statusBar().showMessage(['|', '/', '-', '\\'][self.spinner])

    def signal_received(self, zmq_data):
        self.time_last_message = datetime.now()
        self.spinner = (self.spinner + 1) % 4
        self.showTime()
        if not self.REQ_response:  ##if Pixelator had failed to respond to a request
            print("PixelatorController has started")
            self.zmqREQconnect()
            self.initPixelatorStatus()
        if zmq_data[0] in ['scanStarted']:
            print("scanStarted")
            self.handle_scanStarted(json.loads(zmq_data[1], strict=False))
        elif self.scan_running and zmq_data[0] in ['scanLineData']:
            # print("signal_received: scanLineData")
            if self.scan_running:
                self.handle_scanLineData(zmq_data[1:])
        elif zmq_data[0] in ['scanFinished']:
            print("scanFinished")
            self.scan_running = False
            self.canvas.finalise_plot()
            self.userFocusButtons()
        elif zmq_data[0] in ['scanFileContent' + str(CONFIG['PluginID'])]:
            print("load remote data")
            self.readFileRemote(json.loads(zmq_data[1], strict=False))
        # print(zmq_data)
        elif zmq_data[0] in ['positionerDefinition']:
            self.scan_data_is_fresh = False
            self.userFocusButtons(enable=False)

        else:
            pass
        # print("Not handled:",zmq_data)

    def handle_scanStarted(self, scan_request):
        print(scan_request)
        self.scan_seq = 0
        if scan_request['scanType'] in ['Focus', 'OSA Focus', 'Sample', 'Detector','OSA']:
            # if scan_request['scanType'] in ['Focus','OSA Focus']:
            #     ax1_nm = 'Zoneplate'
            #     ax2_nm = 'FineX'
            # else:
            #     ax1_nm = 'FineY'
            #     ax2_nm = 'FineX'
            self.scan_running = True
            self.scan_data_is_fresh = True

            points_dict = {x["trajectories"][0]["positionerName"]: x["nPoints"] for x in scan_request["innerRegions"][0]["axes"]}

            ax1_nm = list(points_dict.keys())[0]
            ax2_nm = list(points_dict.keys())[1]

            extent_dict = {}
            for axis_info in scan_request["innerRegions"][0]["axes"]:
                # print(axis_info)
                if 'length' in axis_info:
                    extent_dict[axis_info["trajectories"][0]["positionerName"]] = [0, axis_info['length']]
                else:
                    axis_center = axis_info["trajectories"][0]['center']
                    axis_range = axis_info["trajectories"][0]['range']
                    extent_dict[axis_info["trajectories"][0]["positionerName"]] = [axis_center - .5 * axis_range,
                                                                                   axis_center + .5 * axis_range]
            self.scan_extent = [extent_dict[ax1_nm][0], extent_dict[ax2_nm][1], extent_dict[ax1_nm][0],
                                extent_dict[ax2_nm][1]]
            self.scan_shape = [0, 0, points_dict[ax1_nm], points_dict[ax2_nm]]
            self.scan_data = numpy.full(self.scan_shape[2:], numpy.nan)
            self.scan_axis_titles = [ax1_nm, ax2_nm]
            self.canvas.clear()
            self.canvas.plot()
            self.userFocusButtons(enable=False)

    # def handle_scanLineData(self, data):
    #     indices = [int(x) for x in data[0].split()]
    #     if indices[2] == len(self.tile_shapes):  # when starting a new tile
    #         self.tile_shapes.append(numpy.array([0, 0, 0, 0]))  # [Y0, X0, H, W]
    #         offset_wrap = numpy.divmod(self.tile_shapes[indices[2] - 1][1] + self.tile_shapes[indices[2] - 1][3],
    #                                    self.scan_shape[-1])
    #         self.tile_shapes[indices[2]][:2] = [
    #             self.tile_shapes[indices[2] - 1][0] + self.tile_shapes[indices[2] - 1][2] * offset_wrap[0],
    #             offset_wrap[1]]
    #     offset = self.tile_shapes[indices[2]][:2]
    #     chunk_start = numpy.array([int(x) for x in data[1].strip("\'b").split()])
    #     chunk_shape = numpy.array([int(x) for x in data[2].strip("\'b").split()])
    #     chunk_values = numpy.array([float(x) for x in data[3].strip().strip("\'b[]").split(',')])
    #     self.scan_data[ offset[0] + chunk_start[0]:offset[0] + chunk_start[0] + chunk_shape[0],              offset[1] + chunk_start[1]:offset[1] + chunk_start[1] + chunk_shape[1] ] = chunk_values
    #     self.tile_shapes[indices[2]][2:] = numpy.maximum(self.tile_shapes[indices[2]][2:], chunk_start + chunk_shape)
    #     self.canvas.update_plot()
    def handle_scanLineData(self, data):
        indices = [int(x) for x in data[0].split()]
        if indices[2] == len(self.tile_shapes):  # when starting a new tile
            self.tile_shapes.append(numpy.array([0, 0, 0, 0]))  # [Y0, X0, H, W]
            offset_wrap = numpy.divmod(self.tile_shapes[indices[2] - 1][1] + self.tile_shapes[indices[2] - 1][3],
                                       self.scan_shape[-1])
            self.tile_shapes[indices[2]][:2] = [
                self.tile_shapes[indices[2] - 1][0] + self.tile_shapes[indices[2] - 1][2] * offset_wrap[0],
                offset_wrap[1]]
        offset = self.tile_shapes[indices[2]][:2]
        chunk_start = numpy.array([int(x) for x in data[1].strip("\'b").split()])
        chunk_shape = numpy.array([int(x) for x in data[2].strip("\'b").split()])
        chunk_values = numpy.array([float(x) for x in data[3].strip().strip("\'b[]").split(',')])
        self.scan_data[ offset[0] + chunk_start[0]:offset[0] + chunk_start[0] + chunk_shape[0], offset[1] + chunk_start[1]:offset[1] + chunk_start[1] + chunk_shape[1] ] = chunk_values
        #print(f"scan_data[{offset[0] + chunk_start[0]} : {offset[0] + chunk_start[0] + chunk_shape[0]}, {offset[1] + chunk_start[1]} : {offset[1] + chunk_start[1] + chunk_shape[1]}]")
        row = offset[0] + chunk_start[0]
        col = offset[1] + chunk_start[1]
        #print(f"[{self.scan_seq}] scan_data[row={row}, col={col}] = length={len(chunk_values)} {chunk_values}")
        print(f"row={row} col={col}")

        self.scan_seq += 1
        self.tile_shapes[indices[2]][2:] = numpy.maximum(self.tile_shapes[indices[2]][2:], chunk_start + chunk_shape)

        self.canvas.update_plot()

    # def setFocus(self):
    # print("set focus")
    ## Just move the ZPZ positioner
    ##response = zmqRequest(self, ['zonePlateFocus','{"target":"Sample","action":"","defocus":,"cursorPosition":,"setDOsa":}'])
    ##print(response)
    # self.userFocusButtons(enable=False)

    # def setAutofocusSampleZ(self):
    # print("set SampleZ for Autofocus")
    # response = zmqRequest(self, ['zonePlateFocus','{"target":"Sample","action":"","defocus":,"cursorPosition":,"setDOsa":}'])
    # print(response)
    # self.userFocusButtons(enable=False)

    # def setAutofocusOSAgap(self):
    # print("set OSA_gap for Autofocus")
    # self.userFocusButtons(enable=False)

    def loadFileLocal(self):
        fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file')
        # fname = ['/home/watts/dev/hdf5_data/Focus_2021-03-16_051.hdf5','*.hdf5'] #for testing
        # fname = ['/home/watts/dev/FocusFinderGUI/focusfindergui/OSA Focus_2017-03-01_069.hdf5','*.hdf5'] #for testing
        print("Loading:\t", fname[0])
        self.readFileLocal(fname[0])
        # self.calculateEntropy()
        self.canvas.clear()
        self.canvas.plot()
        self.canvas.finalise_plot()
        self.userFocusButtons()

    def readFileLocal(self, fileName, selection=(0, 0), *args, **kwargs):
        try:
            with h5py.File(fileName, 'r') as NXfile:
                for NXentrygroup in list(NXfile):
                    if 'NX_class' in NXfile[NXentrygroup].attrs and NXfile[NXentrygroup].attrs['NX_class'] in [
                        'NXentry', b'NXentry']:
                        for NXdatagroup in list(NXfile[NXentrygroup]):
                            if 'NX_class' in NXfile[NXentrygroup][NXdatagroup].attrs and \
                                    NXfile[NXentrygroup][NXdatagroup].attrs['NX_class'] in ['NXdata', b'NXdata']:
                                # print(NXdatagroup, len(list(NXfile[NXentrygroup])))
                                stxm_scan_type = str(NXfile[NXentrygroup][NXdatagroup]['stxm_scan_type'][:],
                                                     encoding='utf-8')
                                # print(stxm_scan_type)
                                if stxm_scan_type in ['sample focus', 'osa focus']:
                                    data = numpy.array(NXfile[NXentrygroup][NXdatagroup]['data'])
                                    data_axes = NXfile[NXentrygroup][NXdatagroup].attrs['axes']
                                    data_span = []
                                    data_span_units = []
                                    for axis in data_axes:
                                        data_span.append(NXfile[NXentrygroup][NXdatagroup][axis][0])
                                        data_span.append(NXfile[NXentrygroup][NXdatagroup][axis][-1])
                                        if 'units' in NXfile[NXentrygroup][NXdatagroup][axis].attrs:
                                            data_span_units.append(
                                                str(NXfile[NXentrygroup][NXdatagroup][axis].attrs['units'],
                                                    encoding='utf-8'))
                                        elif axis in ['line_position', b'line_position']:
                                            if 'sample_x' in list(NXfile[NXentrygroup][NXdatagroup]):
                                                data_span_units.append(
                                                    str(NXfile[NXentrygroup][NXdatagroup]['sample_x'].attrs['units'],
                                                        encoding='utf-8'))
                                        else:
                                            data_span_units.append('?')
                                else:
                                    print(f'Scan type "{stxm_scan_type}" is not supported!')
        except OSError:
            print("Only HDF5 files (with NXstxm layout) are supported!")
        self.scan_shape = [0, 0, data.shape[0], data.shape[1]]
        self.scan_extent = data_span
        self.scan_data = data
        self.scan_axis_titles = [x.decode() for x in data_axes]

    def loadFileRemote(self):
        # pass
        print(self.remoteFileSystemInfo)
        # '{"bookmarks":[],"directory":"/tmp","fileExtension":".hdf5","showHidden":0}'
        dlg = RemoteFileDialog(parent=self)  # , initial_directory=self.remoteFileSystemInfo['directory'])
        if dlg.exec_():
            print("success!\t", dlg.filepath)
            response = self.zmqRequest(['loadFile file',
                                        '{{"directory":"{directory}","file":"{file}","showHidden":{showHidden}, "fileExtension":"{fileExtension}", "directories":[".."],"files":[""],"pluginNumber":{PluginID}}}'.format(
                                            file=dlg.filepath, **self.remoteFileSystemInfo, **CONFIG)])
        ## direct response is minimal, actual data comes via publisher port

    def readFileRemote(self, data):
        self.scan_shape = [0, 0, *data['scanData']['regionDims'][0]]
        self.scan_extent = [data['regionProfiles'][x] for x in ['minY', 'maxY', 'minX', 'maxX']]
        self.scan_data = numpy.reshape(
            data['scanData']['polarizations'][0]['outerRegions'][0]['scanDataRegionVec'][0]['channels']['channelData'][
                0], self.scan_shape[2:])
        self.scan_axis_titles = [data['regionProfiles']['displayedAxes']['displayedAxis' + x]['name'] for x in
                                 ['Y', 'X']]
        self.canvas.clear()
        self.canvas.plot()
        self.canvas.finalise_plot()

    def calculateEntropy(self):
        if self.scan_data is None:
            self.line_entropy = None
        elif numpy.isnan(self.scan_data).all():
            self.line_entropy = numpy.zeros(self.scan_data.shape[0])
        else:
            # self.scan_data
            # 1. Compute the ESF
            esf = (self.scan_data - numpy.nanmean(self.scan_data[:])) / numpy.nanstd(self.scan_data[:])
            esf = numpy.nan_to_num(esf, nan=0)
            # 2. Compute the LSF
            if True:
                # differential with smoothing
                lsf = gaussian_filter1d(esf, sigma=1.0, axis=1, order=1, mode='reflect')
            else:
                # simple forward difference without smoothing
                lsf = numpy.diff(esf, n=1)
            # 3. Perform the frequency analysis using a discrete FFT along the rows.
            lsf_fft = numpy.fft.fft(lsf, axis=1, norm='ortho')
            lsf_fft = numpy.fft.fftshift(lsf_fft, axes=1)

            # we could also use half of the spectrum, as it is symmetric
            # but it looks better in the graphs
            lsf_fft_mag = numpy.array_split(numpy.abs(lsf_fft), 2, axis=1)[1]
            # lsf_fft_mag = numpy.abs(lsf_fft)

            lsf_fft_mag = lsf_fft_mag ** 2

            # 4. Measure calculation

            # keep the bins and the range fixed
            hist_bins = 64
            hist_range = [lsf_fft_mag.min(), lsf_fft_mag.max()]

            line_entropy = numpy.zeros(lsf_fft_mag.shape[0])

            for i in range(lsf_fft_mag.shape[0]):
                try:
                    if True:
                        # parzen estimation of frequency density
                        [h_i, bins_i] = numpy.histogram(lsf_fft_mag[i][:], range=hist_range, bins=hist_bins,
                                                        density=True)
                        h_i_smooth = gaussian_filter1d(h_i, sigma=4., mode='nearest')
                        line_entropy[i] = entropy(h_i_smooth)
                    else:
                        # power spectral density
                        ps = lsf_fft_mag[i] ** 2
                        line_entropy[i] = entropy(ps / numpy.sum(ps))

                except ValueError:
                    print(f"Error in line {i}")
                    line_entropy[i] = 0
                    continue
            self.line_entropy = line_entropy
        m_g = gaussian_filter1d(self.line_entropy, sigma=3., mode="nearest")
        self.entropies_smoothed = m_g - min(self.line_entropy)
        self.maxEntropyIndex = numpy.argmax(self.entropies_smoothed)
        m = (self.line_entropy - m_g.min()) / max(1e-6, (m_g.max() - m_g.min()))
        m_g = (m_g - m_g.min()) / max(1e-6, (m_g.max() - m_g.min()))
        self.SignalNoiseRatio = numpy.sum(numpy.square(m)) / (numpy.sum(numpy.square(m - m_g)) + 0.0001)

    # print(self.SignalNoiseRatio)

    def setFocus(self):
        print('temp focus')
        if None not in self.canvas.crosshair.position:
            setFocusDict = {
                #							'axesNames':["SampleX,SampleY","Zoneplate"], #old GUI sends 'axesNames' but it doesn't seem to be required
                'positioners': ['Zoneplate'],
                'positions': [self.canvas.crosshair.position[1]],
            }
            response = self.zmqRequest(['moveRequest', json.dumps(setFocusDict)])
            print(response)
            self.userFocusButtons(enable=False)

    def setAutofocusOSAgap(self):
        self.setAutofocus(setDOSA=True)

    def setAutofocus(self, setDOSA=False):
        print('setFocusRequest')
        if None not in self.canvas.crosshair.position:
            setFocusDict = {
                'target': 'Sample',
                'action': 'calibrate',
                'cursorPosition': self.canvas.crosshair.position[1],
            }
            if setDOSA:
                setFocusDict['setDOsa'] = 1
            print(setFocusDict)
            distance = numpy.mean(self.scan_extent[:2]) - self.canvas.crosshair.position[1]
            print(f"Moving sample {['in', 'out'][int(distance > 0)]} by {abs(distance)} um.")
            response = self.zmqRequest(['zonePlateFocus', json.dumps(setFocusDict)])
            print(response)
            if type(response) is list and response[0] == {'status': 'ok'}:
                print("success")
                # self.statusBar().showMessage(f'Focus position adjusted by {distance} um')
                try:
                    self.text.remove()  # delete the old annotation if it already exists
                except:
                    pass
                self.text = self.canvas.axMain.text(numpy.mean(self.canvas.axMain.get_xlim()),
                                                    self.canvas.crosshair.position[1],
                                                    f'Focus position adjusted by {distance} um', ha='center',
                                                    va='center', backgroundcolor=[1, 1, 1, 0.6])
                self.scan_data_is_fresh = False
                self.userFocusButtons(enable=False)
                self.canvas.draw_idle()
                self.userFocusButtons(enable=False)

    class PlotCanvas(FigureCanvas):
        def __init__(self, parent=None, width=5, height=4, dpi=100):
            self.figure = Figure(figsize=(width, height), dpi=dpi)  # , layout='tight')
            self.parent = parent
            self.selectedObject = None
            self.signal_extremes = [None, None]
            FigureCanvas.__init__(self, self.figure)
            self.setParent(parent)

            FigureCanvas.setSizePolicy(self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            FigureCanvas.updateGeometry(self)

            self.setFocusPolicy(QtCore.Qt.ClickFocus)
            self.setFocus()

            spec = matplotlib.gridspec.GridSpec(2, 5, self.figure, wspace=0, hspace=0,
                                                width_ratios=[.1, .8, .03, .03, .04], height_ratios=[.9, .1])
            self.axMain = self.figure.add_subplot(spec[0, 1], facecolor='lightgrey')
            matplotlib.pyplot.setp(self.axMain.get_xticklabels(), visible=False)
            matplotlib.pyplot.setp(self.axMain.get_yticklabels(), visible=False)
            self.axMain.set_anchor('SW')

            self.axLeft = self.figure.add_subplot(spec[0, 0], sharey=self.axMain)
            self.axRight = self.figure.add_subplot(spec[0, 2])
            self.axBottom = self.figure.add_subplot(spec[1, 1], sharex=self.axMain)
            # self.axLeft.set_xticks([])
            self.axLeft.tick_params(axis='x', labelrotation=45)
            matplotlib.pyplot.setp(self.axRight.get_xticklabels(), visible=False)
            matplotlib.pyplot.setp(self.axRight.get_yticklabels(), visible=False)
            self.axRight.set_xticks([])
            self.axRight.set_yticks([])
            # self.axBottom.set_yticks([])
            self.axBottom.yaxis.tick_right()
            self.axBottom.tick_params(axis='x', labelrotation=45)

            self.axColor = ColorScale(ax=self.figure.add_subplot(spec[0, 4]), parent=self)
            self.crosshair = self.Crosshair(parent=self)
            self.SNR_text = self.figure.text(0.9, 0.1, 'S/N=0', backgroundcolor='lightblue')

            self.figure.canvas.mpl_connect("button_press_event", self.action_button_press)
            self.figure.canvas.mpl_connect("button_release_event", self.action_release)
            self.figure.canvas.mpl_connect("motion_notify_event", self.action_drag)
            self.figure.canvas.mpl_connect("pick_event", self.action_pick)

        # self.figure.canvas.mpl_connect("resize_event", self.resizeCanvas)
        # print(self.figure.canvas.callbacks.callbacks)

        class Crosshair():
            def __init__(self, parent=None, position=[None, None]):
                self.position = position
                self.parent = parent
                self.crosshair_H0 = self.parent.axLeft.axhline(numpy.inf, color='k', lw=0.8, ls='--')
                self.crosshair_H1 = self.parent.axMain.axhline(numpy.inf, color='k', lw=0.8, ls='--')
                self.crosshair_H2 = self.parent.axRight.axhline(numpy.inf, color='k', lw=0.8, ls='--')
                self.crosshair_V0 = self.parent.axBottom.axvline(numpy.inf, color='k', lw=0.8, ls='--')
                self.crosshair_V1 = self.parent.axMain.axvline(numpy.inf, color='k', lw=0.8, ls='--')

            def update(self):
                if self.position[1] is not None:
                    self.crosshair_H0.set_ydata([self.position[1]])
                    self.crosshair_H1.set_ydata([self.position[1]])
                    self.crosshair_H2.set_ydata([self.position[1]])
                if self.position[0] is not None:
                    self.crosshair_V0.set_xdata([self.position[0]])
                    self.crosshair_V1.set_xdata([self.position[0]])

        def action_button_press(self, event):
            # print(dir(event))
            if (self.parent.scan_data is not None) and (event.inaxes in [self.axMain, self.axLeft, self.axBottom]):
                if event.inaxes == self.axMain:
                    self.crosshair.position = [event.xdata, event.ydata]
                elif event.inaxes == self.axLeft:
                    self.crosshair.position[1] = event.ydata
                    if self.crosshair.position[0] is None:
                        self.crosshair.position[0] = self.axMain.get_xlim()[0]
                elif event.inaxes == self.axBottom:
                    self.crosshair.position[0] = event.xdata
                    if self.crosshair.position[1] is None:
                        self.crosshair.position[1] = self.axMain.get_ylim()[0]
                self.updateCrosshairTraces()
                self.parent.userFocusButtons(enable=True)
            elif event.inaxes in [self.axColor.ax] and event.dblclick:
                self.axColor.add_colorstop(event)

        # else:
        # print(event)

        def action_pick(self, event):
            print("action_pick ", event.artist, event.mouseevent)
            self.selectedObject = event.artist
            if event.mouseevent.button == 1:  # left click
                if event.mouseevent.dblclick:
                    self.axColor.stops[self.selectedObject]['object'].change_color(event)
                    self.selectedObject = None
            elif event.mouseevent.button == 3:  # right click
                self.axColor.stops[self.selectedObject]['object'].delete(event)

        def action_release(self, event):
            # print("action_release ", event)
            self.selectedObject = None

        def action_drag(self, event):
            if self.selectedObject is not None and self.axColor.stops[self.selectedObject]['status'] == 'movable':
                print("action_drag ", self.selectedObject, event)
                self.axColor.stops[self.selectedObject]['object'].move(event)
                self.figure.canvas.draw_idle()

        def updateCrosshairTraces(self):
            # print('updateCrosshairTraces',self.crosshair.position)
            if self.parent.scan_data is not None:
                if self.crosshair.position[1] is not None:
                    row = numpy.abs(
                        self.binsLeft + .5 * (self.binsLeft[1] - self.binsLeft[0]) - self.crosshair.position[
                            1]).argmin()
                    self.pointsBottom.set_data(values=self.parent.scan_data[row, :])
                if self.crosshair.position[0] is not None:
                    col = numpy.abs(
                        self.binsBottom + .5 * (self.binsBottom[1] - self.binsBottom[0]) - self.crosshair.position[
                            0]).argmin()
                    self.pointsLeft.set_data(values=self.parent.scan_data[:, col])
                self.crosshair.update()
                self.figure.canvas.draw_idle()

        def plot(self):
            if self.parent.scan_data is not None:
                if not numpy.isnan(self.parent.scan_data).all():
                    signal_min = numpy.nanmin(self.parent.scan_data)
                    signal_max = numpy.nanmax(self.parent.scan_data)
                else:
                    signal_min = 0
                    signal_max = 1
                extent = [self.parent.scan_extent[x] for x in [2, 3, 0, 1]]
                self.parent.image_buffer = self.axMain.imshow(self.parent.scan_data, origin='lower', extent=extent,
                                                              aspect='auto')  # , vmin=self.signal_extremes[0], vmax=self.signal_extremes[1], cmap=self.axColor.cmap)
                self.axMain.set_xlim(extent[:2])
                matplotlib.pyplot.setp(self.axMain.get_xticklabels(), visible=False)
                matplotlib.pyplot.setp(self.axMain.get_yticklabels(), visible=False)
                self.axColor.update_normal(self.parent.image_buffer)
                self.axBottom.set_xlabel(f"{self.parent.scan_axis_titles[-1]} ($\mu$m)")
                self.axLeft.set_ylabel(f"{self.parent.scan_axis_titles[-2]} ($\mu$m)")
                self.binsLeft = numpy.linspace(self.parent.scan_extent[0], self.parent.scan_extent[1],
                                               self.parent.scan_shape[2] + 1)
                self.binsBottom = numpy.linspace(self.parent.scan_extent[2], self.parent.scan_extent[3],
                                                 self.parent.scan_shape[3] + 1)

                self.pointsLeft = self.axLeft.stairs(self.parent.scan_data[:, 0], self.binsLeft,
                                                     orientation='horizontal')
                self.axLeft.set_xlim([signal_min, signal_max])
                self.pointsBottom = self.axBottom.stairs(self.parent.scan_data[0, :], self.binsBottom)
                self.axBottom.set_ylim([signal_min, signal_max])

                self.parent.calculateEntropy()
                self.barsRight = self.axRight.stairs(self.parent.line_entropy - min(self.parent.line_entropy),
                                                     self.binsLeft, orientation='horizontal', fill=True)
                self.dashRight = self.axRight.plot(self.parent.entropies_smoothed,
                                                   self.binsLeft[:-1] + .5 * (self.binsLeft[1] - self.binsLeft[0]),
                                                   'k--', visible=False)
                self.maxXRight = self.axRight.plot(self.parent.entropies_smoothed[self.parent.maxEntropyIndex],
                                                   self.binsLeft[self.parent.maxEntropyIndex] + .5 * (
                                                               self.binsLeft[1] - self.binsLeft[0]), 'rx',
                                                   visible=False)
                self.axRight.set_ylim(self.axLeft.get_ylim())
                self.axColor.make_colormap(update_stops=True)
            self.figure.canvas.draw()

        def update_plot(self):
            self.parent.image_buffer.set_data(self.parent.scan_data)
            temp_extremes = [numpy.nanmin(self.parent.scan_data), numpy.nanmax(self.parent.scan_data)]
            update_flag = not (
                        temp_extremes[0] == self.signal_extremes[0] and temp_extremes[1] == self.signal_extremes[1])
            self.signal_extremes = temp_extremes
            if update_flag:
                self.axColor.make_colormap(update_stops=True)
                self.parent.image_buffer.set_clim(vmin=self.signal_extremes[0], vmax=self.signal_extremes[1])
            self.axLeft.set_xlim(self.signal_extremes)
            self.axBottom.set_ylim(self.signal_extremes)
            self.updateCrosshairTraces()
            self.parent.calculateEntropy()
            self.updateSNRText()
            self.barsRight.set_data(values=self.parent.line_entropy - min(self.parent.line_entropy))
            self.axRight.set_xlim([0, max(self.parent.line_entropy) - min(self.parent.line_entropy)])
            self.dashRight[0].set_data(self.parent.entropies_smoothed,
                                       self.binsLeft[:-1] + .5 * (self.binsLeft[1] - self.binsLeft[0]))
            self.dashRight[0].set_visible(True)
            self.maxXRight[0].set_data([self.parent.entropies_smoothed[self.parent.maxEntropyIndex]],
                                       [self.binsLeft[self.parent.maxEntropyIndex]])
            self.maxXRight[0].set_visible(True)
            self.figure.canvas.draw()

        def finalise_plot(self):
            # print(numpy.sum(numpy.isfinite(self.parent.scan_data)))
            if self.parent.scan_data is None:
                return
            if numpy.sum(numpy.isfinite(self.parent.scan_data)) > 0:
                self.parent.calculateEntropy()
                self.updateSNRText()
                self.dashRight[0].set_data(self.parent.entropies_smoothed,
                                           self.binsLeft[:-1] + .5 * (self.binsLeft[1] - self.binsLeft[0]))
                self.dashRight[0].set_visible(True)
                self.maxXRight[0].set_data([self.parent.entropies_smoothed[self.parent.maxEntropyIndex]], [
                    self.binsLeft[self.parent.maxEntropyIndex] + .5 * (self.binsLeft[1] - self.binsLeft[0])])
                self.maxXRight[0].set_visible(True)
                focus_linestyle = [':', '-.', '--', '-'][numpy.clip(int(self.parent.SignalNoiseRatio * .3), 0, 3)]
                self.axMain.axhline(
                    self.binsLeft[self.parent.maxEntropyIndex] + .5 * (self.binsLeft[1] - self.binsLeft[0]), c='r',
                    ls=focus_linestyle)
            self.figure.canvas.draw()

        def clear(self):
            self.axLeft.clear()
            self.axMain.clear()
            self.axRight.clear()
            self.axBottom.clear()
            self.axRight.set_xticks([])
            self.axRight.set_yticks([])
            self.crosshair = self.Crosshair(parent=self)
            self.parent.userFocusButtons(visible=False)

        def updateSNRText(self):
            cScale = self.parent.SignalNoiseRatio * .1
            self.SNR_text.set(text=f"S/N={int(numpy.clip(self.parent.SignalNoiseRatio, 0, 99))}",
                              backgroundcolor=numpy.clip([2 - cScale ** 2, cScale ** 2, 0], 0, 1))


class ColorScale(matplotlib.colorbar.Colorbar):
    def __init__(self, *args, parent=None, **kwargs):
        super().__init__(*args, extend='both', extendrect=True, **kwargs)
        self.parent = parent
        self.ax.tick_params(width=0)
        self.ax.set_xlim([0, 1])
        self.set_ticks([])
        # matplotlib.pyplot.setp(self.ax.get_yticklabels(),visible=False)
        self.format_spec = "{:,.9g}"
        self.stop_pad = 0.02
        self.stops = OrderedDict()
        self.extreme_stops = [None, None]  # [bottom, top]; color scale limits. None means autoscale to data min/max
        self.colors = []
        self.ColorStop('under', [0, .5, 0], parent=self)
        self.ColorStop('over', [0, 1, 0], parent=self)
        self.ColorStop('bottom', [0, 0, 0], parent=self)
        self.ColorStop('top', [1, 1, 1], parent=self)
        self.ColorStop(0.5, [.4, .15, .05], parent=self)

    # self.ColorStop(0.8, [.9,.9,.15], parent=self)

    def add_colorstop(self, event):
        print("add stop at {}".format(event.ydata))
        pos = (event.ydata - self.vmin) / (self.vmax - self.vmin)
        print(pos)
        print(self.cmap(pos))
        new_color = QtWidgets.QColorDialog.getColor(QtGui.QColor.fromRgbF(*self.cmap(pos)))
        # print(new_color.isValid(),new_color.getRgbF()[:3])
        if new_color.isValid():
            self.ColorStop(pos, new_color.getRgbF()[:3], parent=self)

    def make_colormap(self, update_stops=False):
        # print("make colormap")
        self.colors = [(x['position'], x['color']) for x in self.stops.values()]
        if len(self.colors) > 4:
            cmap = matplotlib.colors.LinearSegmentedColormap.from_list('ScaleBar', self.colors[1:-1])
            cmap.set_over(self.colors[-1][1])
            cmap.set_under(self.colors[0][1])
            if self.parent.parent.image_buffer is None:
                self.update_normal(
                    matplotlib.cm.ScalarMappable(norm=matplotlib.colors.Normalize(vmin=0., vmax=1.), cmap=cmap))
            else:
                data_is_empty = self.parent.parent.image_buffer.get_array().count() == 0
                vlim = [0., 1.]
                if self.extreme_stops[0] is not None:
                    vlim[0] = self.extreme_stops[0]
                elif not data_is_empty:
                    vlim[0] = numpy.nanmin(self.parent.parent.image_buffer.get_array())
                if self.extreme_stops[1] is not None:
                    vlim[1] = self.extreme_stops[1]
                elif not data_is_empty:
                    vlim[1] = numpy.nanmax(self.parent.parent.image_buffer.get_array())
                self.stops[list(self.stops.keys())[1]]['text_obj'].text_disp.set_text(self.format_spec.format(vlim[0]))
                self.stops[list(self.stops.keys())[-2]]['text_obj'].text_disp.set_text(self.format_spec.format(vlim[1]))
                self.parent.parent.image_buffer.set(cmap=cmap, clim=vlim)
                self.update_normal(
                    matplotlib.cm.ScalarMappable(norm=matplotlib.colors.Normalize(vmin=vlim[0], vmax=vlim[1]),
                                                 cmap=cmap))
            self.set_ticks([])  # [x[0]*(self.vmax-self.vmin)+self.vmin for x in self.colors[2:-2]])
            if update_stops:
                for pick_obj, d in self.stops.items():
                    pick_obj.set_ydata([d['position'] * (self.vmax - self.vmin) + self.vmin])
                    if 1 > d['position'] > 0:
                        d['text_obj'].set_y(d['position'] * (self.vmax - self.vmin) + self.vmin)
                        d['text_obj'].set_text(
                            self.format_spec.format(d['position'] * (self.vmax - self.vmin) + self.vmin))
        self.parent.figure.canvas.draw()

    class ColorStop():
        def __init__(self, position, color, parent=None, **kwargs):
            self.parent = parent
            self.text_obj = None
            if type(position) is str:
                self.position = position
                if position in ['over']:
                    self.status = 'extreme'
                    position = 1.05
                    parent.color_over = color

                elif position in ['under']:
                    self.status = 'extreme'
                    position = -0.05
                    parent.color_under = color
                elif position in ['top']:
                    self.status = 'fixed'
                    position = 1.

                    self.parent.top_text_ax = parent.ax.figure.add_axes([.92, .835, .05, 0.025],
                                                                        transform=parent.ax.transAxes, frameon=False,
                                                                        label='', box_aspect=None)
                    self.parent.top_textbox = matplotlib.widgets.TextBox(self.parent.top_text_ax, None,
                                                                         initial=self.parent.format_spec.format(
                                                                             self.parent.ax.get_ylim()[1]), color='.1',
                                                                         hovercolor='1', label_pad=0,
                                                                         textalignment='left')
                    self.parent.top_textbox.on_submit(self.submit)
                    self.text_obj = self.parent.top_textbox

                elif position in ['bottom']:
                    self.status = 'fixed'
                    position = 0.
                    self.parent.bottom_text_ax = parent.ax.figure.add_axes([.92, .205, .05, 0.025],
                                                                           transform=parent.ax.transAxes, frameon=False,
                                                                           label='', box_aspect=None)
                    self.parent.bottom_textbox = matplotlib.widgets.TextBox(self.parent.bottom_text_ax, None,
                                                                            initial=self.parent.format_spec.format(
                                                                                self.parent.ax.get_ylim()[0]),
                                                                            color='.1', hovercolor='1', label_pad=0,
                                                                            textalignment='left')
                    self.parent.bottom_textbox.on_submit(self.submit)
                    self.text_obj = self.parent.bottom_textbox
            else:
                self.status = 'movable'
                self.text_obj = parent.ax.text(1.7, position, self.parent.format_spec.format(position), clip_on=False,
                                               va='center')
            self.pick_obj = \
            parent.ax.plot([1.3], [position], 'D', c=color, markeredgecolor='k', picker=True, clip_on=False)[0]
            # self.pick_obj = parent.ax.plot([1.3],[position],'D', c=color, transform=parent.ax.transAxes, markeredgecolor='k', picker=True, clip_on=False)[0]
            parent.stops[self.pick_obj] = {'object': self, 'color': color, 'position': position, 'status': self.status,
                                           'text_obj': self.text_obj}
            parent.stops = OrderedDict(sorted(parent.stops.items(), key=lambda t: t[1]['position']))
            if self.status != 'extreme':
                parent.colors.insert(sum([position > x[0] for x in parent.colors]), [position, color])
            self.parent.make_colormap(update_stops=True)

        def submit(self, text):
            print("submit: ", text)
            pos = ['bottom', 'top'].index(self.position)
            if self.parent.parent.parent.image_buffer is None:
                self.text_obj.text_disp.set_text(self.parent.format_spec.format([0.0, 1.0][pos]))
                self.text_obj.text_disp.set(fontweight='normal')
                self.parent.extreme_stops[pos] = None
            else:
                try:
                    value = float(text.replace(',', ''))
                except ValueError:
                    value = self.parent.parent.signal_extremes[pos]
                if value == self.parent.ax.get_ylim()[pos]:  # compare to previous value
                    self.text_obj.text_disp.set_text(
                        self.parent.format_spec.format(value))  # rewrite value to fix any comma issues
                    return
                elif value == self.parent.parent.signal_extremes[pos]:  # compare to min/max data values
                    self.text_obj.text_disp.set_text(
                        self.parent.format_spec.format(self.parent.parent.signal_extremes[pos]))
                    self.text_obj.text_disp.set(fontweight='normal')
                    self.parent.extreme_stops[pos] = None
                else:  # value is what user intended to set as new color scale limit
                    self.text_obj.text_disp.set(fontweight='bold')
                    self.parent.extreme_stops[pos] = value
            self.parent.make_colormap(update_stops=True)
            self.parent.parent.figure.canvas.draw()

        def move(self, event):
            print("move")
            data_coords = self.parent.ax.transData.inverted().transform((event.x, event.y))
            obj_list = list(self.parent.stops.keys())
            obj_ind = obj_list.index(self.pick_obj)
            plim = [self.parent.stops[obj_list[obj_ind - 1]]['position'] + self.parent.stop_pad,
                    self.parent.stops[obj_list[obj_ind + 1]]['position'] - self.parent.stop_pad]
            dlim = numpy.array(plim) * (self.parent.vmax - self.parent.vmin) + self.parent.vmin
            self.pick_obj.set_ydata(numpy.clip(data_coords[1], dlim[0], dlim[1]))
            self.text_obj.set_y(numpy.clip(data_coords[1], dlim[0], dlim[1]))
            self.text_obj.set_text(self.parent.format_spec.format(numpy.clip(data_coords[1], dlim[0], dlim[1])))
            self.parent.stops[self.pick_obj]['position'] = numpy.clip(
                (data_coords[1] - self.parent.vmin) / (self.parent.vmax - self.parent.vmin), plim[0], plim[1])
            self.parent.make_colormap()

        def delete(self, event):
            print("delete stop at {}".format(self.parent.stops[self.pick_obj]['position']))
            if self.status == 'movable':
                self.text_obj.remove()
                self.pick_obj.remove()
                # self.parent.stops.move_to_end(self.pick_obj)
                self.parent.stops.pop(self.pick_obj)  # remove entry from ordered dict
                self.parent.make_colormap()

        def change_color(self, event):
            print("change color at {}".format(self.parent.stops[self.pick_obj]['position']))
            new_color = QtWidgets.QColorDialog.getColor(
                QtGui.QColor.fromRgbF(*self.parent.stops[self.pick_obj]['color']))
            # print(new_color.isValid(),new_color.getRgbF()[:3])
            if new_color.isValid():  # is not None:
                self.parent.stops[self.pick_obj]['color'] = new_color.getRgbF()[:3]
                self.pick_obj.set_mfc(new_color.getRgbF()[:3])
                self.parent.make_colormap()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())

