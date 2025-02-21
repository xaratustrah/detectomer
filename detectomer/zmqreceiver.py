import zmq
import numpy as np
from pyqtgraph.Qt import QtCore, QtWidgets
from .mainwindow_ui import MainWindowUI

class ZMQReceiver(MainWindowUI):
    def __init__(self):
        super().__init__()

        self.context = zmq.Context()

        self.run_button.clicked.connect(self.start_receiving)
        self.stop_button.clicked.connect(self.stop_receiving)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        
        self.freqs = np.fft.fftfreq(1024, d=1.0/1024)

    def start_receiving(self):
        if not hasattr(self, 'zmq_url') or not hasattr(self, 'zmq_port'):
            QtWidgets.QMessageBox.warning(self, "Error", "Please load a valid config file with ZMQ address and port")
            return

        try:
            address = f"{self.zmq_url}:{self.zmq_port}"
            self.socket = self.context.socket(zmq.SUB)
            self.socket.connect(address)
            self.socket.setsockopt(zmq.SUBSCRIBE, b'')
            self.socket.setsockopt(zmq.CONFLATE, 1)  # Keep only the most recent message 
            self.timer.start(100)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Failed to connect: {e}")

    def stop_receiving(self):
        self.timer.stop()
        if hasattr(self, 'socket'):
            self.socket.close()
            del self.socket

    def update_plot(self):
        try:
            if not hasattr(self, 'socket'):
                raise AttributeError("'ZMQReceiver' object has no attribute 'socket'")

            data = self.socket.recv(flags=zmq.NOBLOCK)
            received_array = np.frombuffer(data, dtype=np.float32)
            fft_data = 20 * np.log10(np.abs(np.fft.fft(received_array)))
            self.graph_widget.plot(self.freqs[:512], fft_data[:512], pen='w', clear=True)
            self.graph_widget.addItem(self.red_line)
            self.graph_widget.addItem(self.green_line_1)
            self.graph_widget.addItem(self.green_line_2)
            
            graph_max = np.max(fft_data)
            self.graph_max_label.setText(f'Graph Max: {graph_max:.2f} dBm')

            if graph_max > self.vslider.value():
                self.statusBar().setStyleSheet("background-color: red; color: white; font-weight: bold;")
                self.statusBar().showMessage("Threshold crossed!")
                self.writeLog()

                if self.rest_checkbox.isChecked():
                    self.statusBar().setStyleSheet("background-color: purple; color: yellow; font-weight: bold;")
                    self.statusBar().showMessage("Threshold crossed, sending REST message!")

            else:
                self.statusBar().setStyleSheet("")
                self.statusBar().showMessage("Ready")

        except zmq.Again:
            pass
        except AttributeError:
            QtWidgets.QMessageBox.warning(self, "Error", "Please enter ZMQ address and port")
