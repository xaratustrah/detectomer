import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
import toml
import datetime
from .version import __version__

class MainWindowUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.graph_widget = pg.PlotWidget()
        self.graph_widget.setBackground('#1A237E')
        self.graph_widget.showGrid(x=True, y=True, alpha=0.3)
        self.graph_widget.addLegend()

        self.graph_widget.sigRangeChanged.connect(self.update_slider_range)

        self.vslider = QtWidgets.QSlider(QtCore.Qt.Vertical)
        self.vslider.valueChanged.connect(self.update_slider_label)

        self.hslider1 = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.hslider1.valueChanged.connect(self.update_hslider1_label)

        self.hslider2 = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.hslider2.valueChanged.connect(self.update_hslider2_label)

        self.vslider_label = QtWidgets.QLabel(f'Threshold: {self.vslider.value()} dBm')
        self.graph_max_label = QtWidgets.QLabel('Graph Max: -∞ dBm')

        self.hslider1_label = QtWidgets.QLabel(f'Freq 1: {self.hslider1.value()} Hz')
        self.hslider2_label = QtWidgets.QLabel(f'Freq 2: {self.hslider2.value()} Hz')

        self.inverse_checkbox = QtWidgets.QCheckBox("Inverse", self)

        self.log_checkbox = QtWidgets.QCheckBox("Log?", self)
        self.log_checkbox.stateChanged.connect(self.toggleLog)

        self.rest_checkbox = QtWidgets.QCheckBox('Send REST?')

        self.logFileName = QtWidgets.QLineEdit(self)
        self.logFileName.setPlaceholderText("Log file name")
        self.logFileName.setDisabled(True)
        self.setDefaultLogFileName()

        self.load_button = QtWidgets.QPushButton('Load Config File')
        self.load_button.clicked.connect(self.load_config_file)

        self.run_button = QtWidgets.QPushButton('Run')
        self.stop_button = QtWidgets.QPushButton('Stop')

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.run_button)
        button_layout.addWidget(self.stop_button)

        graph_layout = QtWidgets.QVBoxLayout()
        graph_layout.addWidget(self.graph_widget)

        label_layout = QtWidgets.QHBoxLayout()
        label_layout.addWidget(self.graph_max_label)
        label_layout.addWidget(self.vslider_label)
        label_layout.addWidget(self.hslider1_label)
        label_layout.addWidget(self.hslider2_label)
        label_layout.addWidget(self.inverse_checkbox)
        label_layout.addWidget(self.log_checkbox)
        label_layout.addWidget(self.logFileName)
        label_layout.addWidget(self.rest_checkbox)

        vslider_layout = QtWidgets.QVBoxLayout()
        vslider_layout.addWidget(self.vslider)

        hslider1_layout = QtWidgets.QHBoxLayout()
        hslider1_layout.addWidget(self.hslider1)

        hslider2_layout = QtWidgets.QHBoxLayout()
        hslider2_layout.addWidget(self.hslider2)

        hslider_layout = QtWidgets.QVBoxLayout()
        hslider_layout.addLayout(hslider1_layout)
        hslider_layout.addLayout(hslider2_layout)

        main_layout = QtWidgets.QHBoxLayout()
        main_layout.addLayout(graph_layout)
        main_layout.addLayout(vslider_layout)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(main_layout)
        layout.addLayout(hslider_layout)
        layout.addLayout(label_layout)
        layout.addLayout(button_layout)

        container = QtWidgets.QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        menubar = self.menuBar()

        color_menu = menubar.addMenu('Color Scheme')
        self.color_actions = []

        schemes = {
            '(Default) Navy Blue/Light Blue': ('#1A237E', '#BBDEFB'),
            'Black (Black/White)': ('k', 'w'),
            'Dark Grey/Light Grey': ('#2C2C2C', '#E0E0E0'),
            'Deep Purple/Lavender': ('#311B92', '#E1BEE7'),
            'Pale Yellow/Dark Brown': ('#FFF9C4', 'k'),
            'Mint Green/Dark Green': ('#C8E6C9', '#388E3C'),
            'Soft Pink/Deep Red': ('#F8BBD0', '#C2185B'),
            'Lime Green/Violet': ('#CDDC39', '#7B1FA2'),
            'Sky Blue/Orange': ('#81D4FA', '#F57C00')
        }

        for name, (bg, fg) in schemes.items():
            action = QtWidgets.QAction(name, self, checkable=True)
            action.triggered.connect(lambda checked, bg=bg, fg=fg, action=action: self.change_color_scheme(bg, fg, action))
            color_menu.addAction(action)
            self.color_actions.append(action)

        self.color_actions[0].setChecked(True)
        self.current_color_action = self.color_actions[0]

        about_menu = menubar.addMenu('About')
        about_action = QtWidgets.QAction('About', self)
        about_action.triggered.connect(self.show_about_dialog)
        about_menu.addAction(about_action)

        file_menu = menubar.addMenu('File')
        exit_action = QtWidgets.QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        self.statusBar().showMessage("Ready")

        self.setWindowTitle('DETECT-O-MER')
        self.resize(800, 600)

        self.red_line = self.graph_widget.addLine(y=self.vslider.value(), pen=pg.mkPen('r', width=1))
        self.green_line_1 = self.graph_widget.addLine(x=self.hslider1.value(), y=0, pen=pg.mkPen('g', width=1))
        self.green_line_2 = self.graph_widget.addLine(x=self.hslider2.value(), y=0, pen=pg.mkPen('g', width=1))

    def setDefaultLogFileName(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.logFileName.setText(f"{now}.log")

    def toggleLog(self, state):
        if state == 2:  # Checked
            self.logFileName.setDisabled(False)
        else:
            self.logFileName.setDisabled(True)

    def writeLog(self):
        if self.log_checkbox.isChecked():
            log_file = self.logFileName.text()
            if log_file:
                with open(log_file, "a") as f:
                    now = datetime.datetime.now()
                    f.write(f"{now}\n")
                            
    def update_slider_range(self):
        x_range, y_range = self.graph_widget.viewRange()
        min_x, max_x = x_range
        min_y, max_y = y_range
        self.vslider.setRange(int(min_y), int(max_y))
        self.hslider1.setRange(int(min_x), int(max_x))
        self.hslider2.setRange(int(min_x), int(max_x))
        
    def update_slider_label(self):
        self.vslider_label.setText(f'Threshold: {self.vslider.value()} dBm')
        self.red_line.setPos(self.vslider.value())

    def update_hslider1_label(self):
        self.hslider1_label.setText(f'Freq 1: {self.hslider1.value()} Hz')
        self.green_line_1.setPos(self.hslider1.value())

    def update_hslider2_label(self):
        self.hslider2_label.setText(f'Freq 2: {self.hslider2.value()} Hz')
        self.green_line_2.setPos(self.hslider2.value())

    def load_config_file(self):
        options = QtWidgets.QFileDialog.Options()
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load Config File", "", "TOML Files (*.toml);;All Files (*)", options=options)
        if file_name:
            try:
                with open(file_name, 'r') as file:
                    config = toml.load(file)

                self.zmq_url = config['zmq']['url']
                self.zmq_port = config['zmq']['port']
                self.data_lframe = config['data']['lframe']
                
                self.graph_xmin = config['graph']['xmin']
                self.graph_xmax = config['graph']['xmax']
                self.graph_ymin = config['graph']['ymin']
                self.graph_ymax = config['graph']['ymax']
                self.graph_xunit = config['graph']['xunit']
                self.graph_yunit = config['graph']['yunit']

                self.window_xsize = config['window']['xsize']
                self.window_ysize = config['window']['ysize']
                                
                self.hslider1.setRange(0, self.data_lframe - 1)
                self.hslider1.setValue(int(self.data_lframe / 4) - 5)
                self.hslider2.setRange(0, self.data_lframe - 1)
                self.hslider2.setValue(int(self.data_lframe / 4) + 5)

                self.graph_widget.setYRange(self.graph_ymin, self.graph_ymax)
                self.vslider.setRange(self.graph_ymin, self.graph_ymax)
                self.vslider.setValue(self.graph_ymax - 10)
                self.graph_widget.setXRange(self.graph_xmin, self.graph_xmax)

                self.graph_widget.setLabel('left', 'Amplitude', units=self.graph_yunit)
                self.graph_widget.setLabel('bottom', 'Frequency', units=self.graph_xunit)

                self.resize(self.window_xsize, self.window_ysize)

                self.statusBar().showMessage(f"Config Loaded: ZMQ URL - {self.zmq_url}, Port - {self.zmq_port}")
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Error", f"Failed to load config file: {e}")

    def change_color_scheme(self, bg_color, fg_color, action):
        self.graph_widget.setBackground(bg_color)
        left_axis = self.graph_widget.getPlotItem().getAxis('left')
        bottom_axis = self.graph_widget.getPlotItem().getAxis('bottom')
        left_axis.setPen(pg.mkPen(fg_color))
        bottom_axis.setPen(pg.mkPen(fg_color))
        left_axis.setTextPen(pg.mkPen(fg_color))
        bottom_axis.setTextPen(pg.mkPen(fg_color))
        left_axis.setLabel(fg_color)
        bottom_axis.setLabel(fg_color)

        if self.current_color_action:
            self.current_color_action.setChecked(False)
        action.setChecked(True)
        self.current_color_action = action

    def show_about_dialog(self):
        QtWidgets.QMessageBox.information(self, "About", f"DETECT-O-MER\n© xaratustrah@github, 2025\nVersion {__version__}\n")
