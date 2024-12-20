import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox, QWidget, QFileDialog, QHBoxLayout
)
from PyQt5.QtCore import QTimer
import serial
import serial.tools.list_ports

from gost3410_util import generate_keypair, sign, verify

class UARTApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        
        self.serial_port = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.read_from_uart)

        # Внутреннее хранение ключей
        self.private_key = None
        self.public_key = None

        # Параметры размеров
        self.CONTROL_SIZE = 1       # 8 бит -> 1 байт
        self.MESSAGE_SIZE = 64      # 512 бит -> 64 байта
        self.PUBLIC_KEY_SIZE = 32   # 256 бит -> 32 байта
        self.PRIVATE_KEY_SIZE = 32  # 256 бит -> 32 байта

        # Лимит длины сообщения
        self.MESSAGE_MAX_LENGTH = 64
        self.message_input.setMaxLength(self.MESSAGE_MAX_LENGTH)

        # Переменные для отложенной обработки
        self.delayed_mode = None
        self.delayed_message = None
        self.delayed_pub_key_hex = None
        self.delayed_user_signature_hex = None

        self.update_mode_ui()

    def initUI(self):
        self.setWindowTitle("UART Communication")

        central_widget = QWidget()
        main_layout = QVBoxLayout()

        # Режим работы
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Режим отправки:")
        mode_layout.addWidget(mode_label)

        self.mode_selector = QComboBox()
        self.mode_selector.addItems(["Генерация ключа", "Подпись", "Проверка подписи"])
        self.mode_selector.currentIndexChanged.connect(self.update_mode_ui)
        mode_layout.addWidget(self.mode_selector)
        main_layout.addLayout(mode_layout)

        # Поле открытого ключа
        key_layout = QHBoxLayout()
        self.key_label = QLabel("Открытый ключ (hex):")
        key_layout.addWidget(self.key_label)
        self.public_key_input = QLineEdit()
        key_layout.addWidget(self.public_key_input)

        # Кнопка сгенерировать ключ
        self.generate_key_button = QPushButton("Сгенерировать ключ")
        self.generate_key_button.clicked.connect(self.generate_key_action)
        key_layout.addWidget(self.generate_key_button)
        main_layout.addLayout(key_layout)

        # Поле сообщения
        msg_layout = QHBoxLayout()
        self.message_label = QLabel("Сообщение:")
        msg_layout.addWidget(self.message_label)
        self.message_input = QLineEdit()
        msg_layout.addWidget(self.message_input)
        main_layout.addLayout(msg_layout)

        # Поле подписи
        sig_layout = QHBoxLayout()
        self.signature_label = QLabel("Подпись (hex):")
        sig_layout.addWidget(self.signature_label)
        self.signature_input = QLineEdit()
        self.signature_input.setReadOnly(False)
        sig_layout.addWidget(self.signature_input)
        main_layout.addLayout(sig_layout)

        # Кнопка "Подписать"
        self.sign_button = QPushButton("Подписать")
        self.sign_button.clicked.connect(self.sign_message_action)
        main_layout.addWidget(self.sign_button)

        # Выбор порта
        self.port_label = QLabel("Выбор порта:")
        main_layout.addWidget(self.port_label)

        self.port_selector = QComboBox()
        self.refresh_ports()
        main_layout.addWidget(self.port_selector)

        self.refresh_button = QPushButton("Обновить порты")
        self.refresh_button.clicked.connect(self.refresh_ports)
        main_layout.addWidget(self.refresh_button)

        # Скорость
        self.baud_label = QLabel("Введите Baud Rate:")
        main_layout.addWidget(self.baud_label)

        self.baud_rate_input = QLineEdit("9600")
        main_layout.addWidget(self.baud_rate_input)

        # Кнопки подключения
        self.connect_button = QPushButton("Подключиться")
        self.connect_button.clicked.connect(self.connect_uart)
        main_layout.addWidget(self.connect_button)

        self.disconnect_button = QPushButton("Отключиться")
        self.disconnect_button.clicked.connect(self.disconnect_uart)
        self.disconnect_button.setEnabled(False)
        main_layout.addWidget(self.disconnect_button)

        # Кнопка отправки
        self.send_button = QPushButton("Отправить")
        self.send_button.clicked.connect(self.handle_send)
        self.send_button.setEnabled(False)
        main_layout.addWidget(self.send_button)

        # Формат отображения
        self.format_label = QLabel("Формат отображения:")
        main_layout.addWidget(self.format_label)

        self.format_selector = QComboBox()
        self.format_selector.addItems(["ASCII", "Hexadecimal"])
        main_layout.addWidget(self.format_selector)

        # Отображение входящих данных
        self.output_label = QLabel("Лог:")
        main_layout.addWidget(self.output_label)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        main_layout.addWidget(self.output_text)

        # Кнопка сохранить
        self.save_button = QPushButton("Сохранить в файл")
        self.save_button.clicked.connect(self.save_data)
        main_layout.addWidget(self.save_button)

        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def update_mode_ui(self):
        mode = self.mode_selector.currentText()
        # В режиме "Генерация ключа" кнопка "Сгенерировать ключ" неактивна
        if mode == "Генерация ключа":
            self.generate_key_button.setEnabled(False)
        else:
            self.generate_key_button.setEnabled(True)

        # Кнопка "Подписать" неактивна в режимах "Генерация ключа" и "Подпись"
        if mode == "Проверка подписи":
            self.sign_button.setEnabled(True)
        else:
            self.sign_button.setEnabled(False)

    def refresh_ports(self):
        ports = serial.tools.list_ports.comports()
        self.port_selector.clear()
        self.port_selector.addItems([port.device for port in ports])

    def connect_uart(self):
        port = self.port_selector.currentText()
        baud_rate = self.baud_rate_input.text()

        if not port or not baud_rate.isdigit():
            self.output_text.append("Ошибка: неверный порт или скорость.")
            return

        try:
            self.serial_port = serial.Serial(port, int(baud_rate), timeout=1)
            self.timer.start(100)
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
            self.send_button.setEnabled(True)
            self.output_text.append(f"Подключено к {port} со скоростью {baud_rate}.")
        except Exception as e:
            self.output_text.append(f"Ошибка подключения: {str(e)}")

    def disconnect_uart(self):
        if self.serial_port:
            self.timer.stop()
            self.serial_port.close()
            self.serial_port = None

        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.send_button.setEnabled(False)

        self.output_text.append("Отключено.")

    def generate_key_action(self):
        self.private_key, self.public_key = generate_keypair()
        self.public_key_input.setText(self.public_key.hex())
        self.output_text.append("Сгенерированы новые ключи:")
        self.output_text.append("Открытый ключ: " + self.public_key.hex())
        self.output_text.append("Закрытый ключ: " + self.private_key.hex())

    def sign_message_action(self):
        if self.private_key is None:
            self.output_text.append("Ошибка: нет приватного ключа для подписи.")
            return
        message = self.message_input.text().encode('utf-8')
        signature = sign(self.private_key, message)
        self.signature_input.setText(str(signature))
        self.output_text.append("Сообщение подписано (кнопка 'Подписать'): " + str(signature))

    def handle_send(self):
        # При нажатии "Отправить" мы не делаем ничего сразу, а запускаем таймер на 2 секунды
        # После 2 секунд вызываем do_actual_send
        self.delayed_mode = self.mode_selector.currentText()
        self.delayed_message = self.message_input.text()
        self.delayed_pub_key_hex = self.public_key_input.text()
        self.delayed_user_signature_hex = self.signature_input.text().strip()

        QTimer.singleShot(2000, self.do_actual_send)

    def do_actual_send(self):
        mode = self.delayed_mode
        message = self.delayed_message
        pub_key_hex = self.delayed_pub_key_hex
        user_signature_hex = self.delayed_user_signature_hex

        # Проверка длины сообщения
        if len(message) > self.MESSAGE_MAX_LENGTH:
            self.output_text.append("Ошибка: сообщение слишком длинное.")
            return

        # Получаем публичный ключ
        if pub_key_hex:
            try:
                pub_key = bytes.fromhex(pub_key_hex)
            except:
                self.output_text.append("Ошибка: некорректный формат открытого ключа (hex).")
                return
        else:
            pub_key = self.public_key

        # Проверка ключей в режимах подписи и проверки
        if mode in ["Подпись", "Проверка подписи"]:
            if self.private_key is None or pub_key is None:
                self.output_text.append("Ошибка: нет ключей для выполнения операции.")
                return

        if mode == "Генерация ключа":
            # Генерация ключей
            self.private_key, self.public_key = generate_keypair()
            self.public_key_input.setText(self.public_key.hex())
            self.output_text.append("Сгенерирован новый ключ (режим генерации):")
            self.output_text.append("Открытый ключ: " + self.public_key.hex())
            self.output_text.append("Закрытый ключ: " + self.private_key.hex())

        elif mode == "Подпись":
            # Подписание сообщения
            if self.private_key is None:
                self.output_text.append("Ошибка: нет закрытого ключа для подписи.")
                return
            signature = sign(self.private_key, message.encode('utf-8'))
            self.signature_input.setText(str(signature))
            self.output_text.append("Подпись сгенерирована (режим 'Подпись'): " + str(signature))

        elif mode == "Проверка подписи":
            # Проверка подписи
            if self.private_key is None:
                self.output_text.append("Ошибка: нет закрытого ключа для проверки.")
                return

            if not user_signature_hex:
                self.output_text.append("Ошибка: нет подписи для проверки.")
                return

            try:
                user_signature = user_signature_hex
            except:
                self.output_text.append("Ошибка: некорректный формат подписи (hex).")
                return

            if True:
                valid = verify(pub_key, message.encode('utf-8'), user_signature)
                if valid:
                    self.output_text.append("Сообщение подписано верно.")
                else:
                    self.output_text.append("Ошибка: подпись неверна.")
            else:
                self.output_text.append("Подпись некорректна.")
                self.output_text.append("Корректная подпись: " + correct_signature)
                self.output_text.append("Подпись от пользователя: " + user_signature)

        # Отправка по UART
        control_byte = b'\x01'
        msg_bytes = message.encode('utf-8')
        if len(msg_bytes) > self.MESSAGE_SIZE:
            msg_bytes = msg_bytes[:self.MESSAGE_SIZE]
        else:
            msg_bytes = msg_bytes.ljust(self.MESSAGE_SIZE, b'\x00')

        if pub_key is None:
            pub_key = b'\x00' * self.PUBLIC_KEY_SIZE
        if len(pub_key) > self.PUBLIC_KEY_SIZE:
            pub_key = pub_key[:self.PUBLIC_KEY_SIZE]
        else:
            pub_key = pub_key.ljust(self.PUBLIC_KEY_SIZE, b'\x00')

        priv_key = self.private_key
        if priv_key is None:
            priv_key = b'\x00' * self.PRIVATE_KEY_SIZE
        if len(priv_key) > self.PRIVATE_KEY_SIZE:
            priv_key = priv_key[:self.PRIVATE_KEY_SIZE]
        else:
            priv_key = priv_key.ljust(self.PRIVATE_KEY_SIZE, b'\x00')

        packet = control_byte + msg_bytes + pub_key + priv_key

        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(packet)
                self.output_text.append("Отправлено в UART: " + packet.hex())
            except Exception as e:
                self.output_text.append("Ошибка отправки в UART: " + str(e))
        else:
            self.output_text.append("Предупреждение: UART не подключен, данные не отправлены.")


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
                self.output_text.append(f"Принято из UART: {formatted_data}")
        except Exception as e:
            self.output_text.append(f"Ошибка чтения из UART: {str(e)}")

    def save_data(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить полученные данные", "", "Text Files (*.txt);;All Files (*)", options=options)
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(self.output_text.toPlainText())
                self.output_text.append(f"Данные сохранены в {file_path}")
            except Exception as e:
                self.output_text.append(f"Ошибка сохранения: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    uart_app = UARTApp()
    uart_app.show()
    sys.exit(app.exec_())