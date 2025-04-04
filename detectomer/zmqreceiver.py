import zmq
import numpy as np
from pyqtgraph.Qt import QtCore, QtWidgets
import requests
import warnings
import datetime
from requests.exceptions import HTTPError
from .mainwindow_ui import MainWindowUI


# Function to handle warnings as exceptions
def warn_handler(message, category, filename, lineno, file=None, line=None):
    raise category(message)

# Set the warning handler
warnings.showwarning = warn_handler

class ZMQReceiver(MainWindowUI):
    def __init__(self):
        super().__init__()

        self.zmq_context_sdr = zmq.Context()
        self.zmq_context_trigger = zmq.Context()
        
        self.run_button.clicked.connect(self.start_receiving)
        self.run_button.clicked.connect(self.start_trigger_server)
        
        self.stop_button.clicked.connect(self.stop_receiving)
        self.stop_button.clicked.connect(self.stop_trigger_server)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        
        self.busy_triggerbox = False
        self.busy_statusbar_show = False
        self.busy_rest_interface = False
        
    def get_moving_average(self, new_array):      
        if len(self.avg_buffer) < self.graph_avg_depth:
            self.avg_buffer = np.vstack((self.avg_buffer, new_array))
        else:
            # Discard the oldest value and append the new one
            self.avg_buffer = np.roll(self.avg_buffer, -1, axis = 0)  # Shift all elements to the left
            self.avg_buffer[-1] = new_array  # Add the new value at the end
        return np.mean(self.avg_buffer, axis=0)

    def start_receiving(self):
        if not hasattr(self, "zmq_sdr_url") or not hasattr(self, "zmq_sdr_port"):
            QtWidgets.QMessageBox.warning(
                self, "Error", "Please load a valid config file."
            )
            return

        self.freqs = (
            np.fft.fftfreq(self.data_lframe, d=1.0 / self.data_sample_rate)
            + self.data_center_freq
        )
        
        self.hslider1.setValue(int(self.freqs[0]))
        self.update_hslider1_label()
        self.hslider2.setValue(int(self.freqs[int(self.data_lframe / 2)]))
        self.update_hslider2_label()
        
        self.graph_widget.setXRange(np.min(self.freqs), np.max(self.freqs))

        try:
            address = f"{self.zmq_sdr_url}:{self.zmq_sdr_port}"
            self.socket_sdr = self.zmq_context_sdr.socket(zmq.SUB)
            self.socket_sdr.connect(address)
            self.socket_sdr.setsockopt(zmq.SUBSCRIBE, b"")
            self.socket_sdr.setsockopt(zmq.CONFLATE, 1)  # Keep only the most recent message
            self.timer.start(100)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Failed to connect: {e}")

    def stop_receiving(self):
        self.timer.stop()
        if hasattr(self, "socket_sdr"):
            self.socket_sdr.close()
            del self.socket_sdr

    def update_plot(self):
        try:
            if not hasattr(self, "socket_sdr"):
                raise AttributeError("'ZMQReceiver' object has no attribute 'socket_sdr'")

            data = self.socket_sdr.recv(flags=zmq.NOBLOCK)
            received_array = np.frombuffer(data, dtype=np.float32)
            
            fft_data = np.abs(np.fft.fftshift(np.fft.fft(received_array))) ** 2
            
            try:
                
                fft_data = 10 * np.log10(fft_data)
                
            except RuntimeWarning as e:
                pass
                #fft_data = np.where(np.isfinite(10 * np.log10(fft_data)), 10 * np.log10(fft_data), 1)

            fft_data = self.get_moving_average(fft_data)
            
            if self.invert_checkbox.isChecked():
                fft_data = -fft_data - int(self.ref_value_spinbox.value())
            else:
                fft_data += int(self.ref_value_spinbox.value())

            self.plot_curve = self.graph_widget.plot(
                self.freqs[: int(self.data_lframe / 2)],
                fft_data[: int(self.data_lframe / 2)],
                pen="w",
                clear=True,
            )
            self.graph_widget.addItem(self.red_line)
            self.graph_widget.addItem(self.green_line_1)
            self.graph_widget.addItem(self.green_line_2)

            pos1 = self.green_line_1.getPos()[0]
            pos2 = self.green_line_2.getPos()[0]

            lower_index = np.searchsorted(self.freqs[: int(self.data_lframe / 2)], pos1)
            upper_index = np.searchsorted(self.freqs[: int(self.data_lframe / 2)], pos2)

            if (
                lower_index < int(self.data_lframe / 2)
                and lower_index > 0
                and upper_index < int(self.data_lframe / 2)
                and upper_index > 0
            ):
                if lower_index > upper_index:
                    lower_index, upper_index = upper_index, lower_index
                graph_max = np.max(fft_data[lower_index:upper_index])
                graph_min = np.min(fft_data[lower_index:upper_index])
            else:
                graph_max = np.max(fft_data)
                graph_min = np.min(fft_data)

            self.graph_max_label.setText(f"Graph Max: {graph_max:.2f} dBm")

            # here comes all the triggering etc.
            
            if (
                graph_max > self.vslider.value()
                and not self.invert_checkbox.isChecked()
            ):
                if self.rest_checkbox.isChecked():
                    self.send_to_rest_interface()
                    if self.triggerbox_checkbox.isChecked():
                        self.send_to_triggerbox()
                else:
                    self.statusbar_show()
                    self.writeLog()
                    if self.triggerbox_checkbox.isChecked():
                        self.send_to_triggerbox()

            if graph_min < self.vslider.value() and self.invert_checkbox.isChecked():
                if self.rest_checkbox.isChecked():
                    self.send_to_rest_interface()
                else:
                    self.statusbar_show()
                    self.writeLog()

        except zmq.Again:
            pass
        except ValueError:
            pass
        except AttributeError:
            QtWidgets.QMessageBox.warning(self, "Error", "Please enter ZMQ address and port")

    # ------------ REST interface
    
    def send_to_rest_interface(self):
        if self.busy_rest_interface:
            print('REST interface is busy.')
        else:
            self.busy_rest_interface = True
            self.actually_send_rest_message(True)

            QtCore.QTimer.singleShot(self.hold_time_spinbox.value() * 1000, self.busy_rest_interface_reset)
            
    def busy_rest_interface_reset(self):
        self.busy_rest_interface = False
        self.actually_send_rest_message(False)
        self.rest_checkbox.setStyleSheet('')
        
    def actually_send_rest_message(self, status):
        headers = {"Content-Type": "application/json"}

        if status:
            self.rest_checkbox.setStyleSheet('background-color: purple')

            data = {
                "dynamicSignals": [{"enabled": True, "id": self.rest_scid}],
                "staticSignals": [],
            }
            try:
                response = requests.put(self.rest_url, json=data, headers=headers)
                response.raise_for_status()  # Check for HTTP errors
                # print(response.json())

            except HTTPError as http_err:
                pass
                print(f"HTTP error occurred: {http_err}")

            except Exception as err:
                pass
                print(f"Other error occurred: {err}")

        else:
            data = {
                "dynamicSignals": [{"enabled": False, "id": self.rest_scid}],
                "staticSignals": [],
            }
            try:
                response = requests.put(self.rest_url, json=data, headers=headers)
                response.raise_for_status()  # Check for HTTP errors
                # print(response.json())

            except HTTPError as http_err:
                pass
                print(f"HTTP error occurred: {http_err}")

            except Exception as err:
                pass
                print(f"Other error occurred: {err}")

            finally:
                # clear up anyways
                self.rest_checkbox.setStyleSheet('')

    # ------------ trigger box section

    def start_trigger_server(self):
        address = f"{self.zmq_trigger_url}:{self.zmq_trigger_port}"
        # print(f"Trigger server started on {address}")
        self.socket_trigger = self.zmq_context_trigger.socket(zmq.PUB)
        try:
            self.socket_trigger.bind(address)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Failed to connect: {e}")

    def stop_trigger_server(self):
        self.timer.stop()
        if hasattr(self, "socket_trigger"):
            self.socket_trigger.close()
            del self.socket_trigger
            # print(f"Trigger server stopped.")
            
    def send_to_triggerbox(self):
        if self.busy_triggerbox:
            print('Trigger box show is busy.')
        else:
            self.busy_triggerbox = True
            topic = '10002'  # just a number for identification
            current_time = datetime.datetime.now().strftime('%Y-%m-%d@%H:%M:%S.%f')
            self.socket_trigger.send_string("{} {}".format(topic, current_time))
            self.triggerbox_checkbox.setStyleSheet('background-color: green')
            QtCore.QTimer.singleShot(self.hold_time_spinbox.value() * 1000, self.busy_triggerbox_reset)
            
    def busy_triggerbox_reset(self):
        self.busy_triggerbox = False
        self.triggerbox_checkbox.setStyleSheet('')


    # ------------ Statusbar section

    def statusbar_show(self):
        if self.busy_statusbar_show:
            print('Status bar show is busy.')
        else:
            self.busy_statusbar_show = True
            self.statusBar().setStyleSheet(
                "background-color: red; color: white; font-weight: bold;"
            )
            self.statusBar().showMessage("Threshold crossed. Check button colors to see which messages were sent.")
            QtCore.QTimer.singleShot(2000, self.busy_statusbar_show_reset)
            
    def busy_statusbar_show_reset(self):
        self.busy_statusbar_show = False
        self.statusBar().setStyleSheet("")
        self.statusBar().clearMessage()
