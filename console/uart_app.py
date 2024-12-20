import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox, QWidget, QFileDialog
)
from PyQt5.QtCore import QTimer
import serial
import serial.tools.list_ports

class UARTApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.serial_port = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.read_from_uart)

    def initUI(self):
        self.setWindowTitle("UART Communication")

        central_widget = QWidget()
        layout = QVBoxLayout()

        # Port selection
        self.port_label = QLabel("Select Port:")
        layout.addWidget(self.port_label)

        self.port_selector = QComboBox()
        self.refresh_ports()
        layout.addWidget(self.port_selector)

        self.refresh_button = QPushButton("Refresh Ports")
        self.refresh_button.clicked.connect(self.refresh_ports)
        layout.addWidget(self.refresh_button)

        # Baud rate selection
        self.baud_label = QLabel("Enter Baud Rate:")
        layout.addWidget(self.baud_label)

        self.baud_rate_input = QLineEdit("9600")
        layout.addWidget(self.baud_rate_input)

        # Connect and disconnect buttons
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_uart)
        layout.addWidget(self.connect_button)

        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.disconnect_uart)
        self.disconnect_button.setEnabled(False)
        layout.addWidget(self.disconnect_button)

        # Send data
        self.send_label = QLabel("Enter Data to Send:")
        layout.addWidget(self.send_label)

        self.send_input = QLineEdit()
        layout.addWidget(self.send_input)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_data)
        self.send_button.setEnabled(False)
        layout.addWidget(self.send_button)

        # Output display
        self.output_label = QLabel("Received Data:")
        layout.addWidget(self.output_label)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        layout.addWidget(self.output_text)

        # Display format
        self.format_label = QLabel("Display Format:")
        layout.addWidget(self.format_label)

        self.format_selector = QComboBox()
        self.format_selector.addItems(["ASCII", "Hexadecimal"])
        layout.addWidget(self.format_selector)

        # Save data button
        self.save_button = QPushButton("Save to File")
        self.save_button.clicked.connect(self.save_data)
        layout.addWidget(self.save_button)

        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def refresh_ports(self):
        ports = serial.tools.list_ports.comports()
        self.port_selector.clear()
        self.port_selector.addItems([port.device for port in ports])

    def connect_uart(self):
        port = self.port_selector.currentText()
        baud_rate = self.baud_rate_input.text()

        if not port or not baud_rate.isdigit():
            self.output_text.append("Error: Invalid port or baud rate.")
            return

        try:
            self.serial_port = serial.Serial(port, int(baud_rate), timeout=1)
            self.timer.start(100)  # Poll every 100 ms

            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
            self.send_button.setEnabled(True)

            self.output_text.append(f"Connected to {port} at {baud_rate} baud.")
        except Exception as e:
            self.output_text.append(f"Error: {str(e)}")

    def disconnect_uart(self):
        if self.serial_port:
            self.timer.stop()
            self.serial_port.close()
            self.serial_port = None

        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.send_button.setEnabled(False)

        self.output_text.append("Disconnected.")

    def send_data(self):
        if not self.serial_port:
            return

        data = self.send_input.text()
        try:
            self.serial_port.write(data.encode('utf-8'))
            self.output_text.append(f"Sent: {data}")
        except Exception as e:
            self.output_text.append(f"Error: {str(e)}")

    def read_from_uart(self):
        if not self.serial_port:
            return

        try:
            data = self.serial_port.read_all()
            if data:
                if self.format_selector.currentText() == "ASCII":
                    formatted_data = data.decode('utf-8', errors='replace')
                else:
                    formatted_data = ' '.join(f"{byte:02X}" for byte in data)
                self.output_text.append(f"Received: {formatted_data}")
        except Exception as e:
            self.output_text.append(f"Error: {str(e)}")

    def save_data(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Received Data", "", "Text Files (*.txt);;All Files (*)", options=options)
        if file_path:
            try:
                with open(file_path, 'w') as file:
                    file.write(self.output_text.toPlainText())
                self.output_text.append(f"Data saved to {file_path}")
            except Exception as e:
                self.output_text.append(f"Error: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    uart_app = UARTApp()
    uart_app.show()
    sys.exit(app.exec_())

