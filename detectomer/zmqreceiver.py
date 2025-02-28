import zmq
import numpy as np
from pyqtgraph.Qt import QtCore, QtWidgets
import requests
from requests.exceptions import HTTPError
from .mainwindow_ui import MainWindowUI

class ZMQReceiver(MainWindowUI):
    def __init__(self):
        super().__init__()

        self.context = zmq.Context()

        self.run_button.clicked.connect(self.start_receiving)
        self.stop_button.clicked.connect(self.stop_receiving)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        
        self.rest_message_sent = False
        

    def start_receiving(self):
        if not hasattr(self, 'zmq_url') or not hasattr(self, 'zmq_port'):
            QtWidgets.QMessageBox.warning(self, "Error", "Please load a valid config file.")
            return

        self.freqs = np.fft.fftfreq(self.data_lframe, d=1.0/self.data_lframe)

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
            
            fft_data = 10 * np.log10(np.abs(np.fft.fft(received_array)))
            
            if self.inverse_checkbox.isChecked():
                fft_data = -fft_data - int(self.ref_value_spinbox.value())
            else:
                fft_data += int(self.ref_value_spinbox.value())
                
            self.graph_widget.plot(self.freqs[:int(self.data_lframe / 2)], fft_data[:int(self.data_lframe / 2)], pen='w', clear=True)
            self.graph_widget.addItem(self.red_line)
            self.graph_widget.addItem(self.green_line_1)
            self.graph_widget.addItem(self.green_line_2)
            
            pos1 = self.green_line_1.getPos()[0]
            pos2 = self.green_line_2.getPos()[0]
            
            index1 = 0 if pos1 < 0 else int(self.data_lframe / 2)-1 if pos1 > self.freqs[int(self.data_lframe / 2)-1] else pos1
            index2 = 0 if pos2 < 0 else int(self.data_lframe / 2)-1 if pos2 > self.freqs[int(self.data_lframe / 2)-1] else pos2
            start_index = min(index1, index2)
            end_index = max(index1, index2)
            
            graph_max = np.max(fft_data[start_index:end_index])
            graph_max_index = np.argmax(fft_data[start_index:end_index])

            graph_min = np.min(fft_data[start_index:end_index])
            graph_min_index = np.argmin(fft_data[start_index:end_index])

            self.graph_max_label.setText(f'Graph Max: {graph_max:.2f} dBm')

            if graph_max > self.vslider.value() and not self.inverse_checkbox.isChecked():
                if self.rest_checkbox.isChecked():
                    self.toggle_rest_message()
                else:
                    self.only_show_message()
                    self.writeLog()

            if graph_min < self.vslider.value() and self.inverse_checkbox.isChecked():
                if self.rest_checkbox.isChecked():
                    self.toggle_rest_message()
                else:
                    self.only_show_message()
                    self.writeLog()

        except zmq.Again:
            pass
        except ValueError:
            pass
        except AttributeError:
            QtWidgets.QMessageBox.warning(self, "Error", "Please enter ZMQ address and port")

    def toggle_rest_message(self):
        if self.rest_message_sent:
            self.actually_send_rest_message(False)
            self.rest_message_sent = False
        else:
            QtCore.QTimer.singleShot(self.rest_hold_time_spinbox.value()*1000, self.toggle_rest_message)
            self.rest_message_sent = True
            self.actually_send_rest_message(True)
    
    def only_show_message(self):
        self.statusBar().setStyleSheet("background-color: red; color: white; font-weight: bold;")
        self.statusBar().showMessage("Threshold crossed, no message sent.")
        QtCore.QTimer.singleShot(300, self.clear_up_statusbar)
    
    def clear_up_statusbar(self):
            self.statusBar().setStyleSheet("")
            self.statusBar().clearMessage()
        
    def actually_send_rest_message(self, status):
        if status:
            self.statusBar().setStyleSheet("background-color: purple; color: yellow; font-weight: bold;")
            self.statusBar().showMessage(f"Threshold crossed, holding REST message for {self.rest_hold_time_spinbox.value()} [s]")
            data = {
                "dynamicSignals": [
                    {
                        "enabled": status,
                        "id": self.rest_scid
                    }
                ],
                "staticSignals": []
            }
            headers = {
                "Content-Type": "application/json"
            }
            try:
                response = requests.put(self.rest_url, json=data, headers=headers)
                response.raise_for_status()  # Check for HTTP errors
                print(response.json())
        
            except HTTPError as http_err:
                print(f"HTTP error occurred: {http_err}")
        
            except Exception as err:
                print(f"Other error occurred: {err}")
        
        else:
            self.clear_up_statusbar()