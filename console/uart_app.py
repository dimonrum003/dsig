import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox, QWidget, QFileDialog, QHBoxLayout
)
from PyQt5.QtCore import QTimer
import serial
import serial.tools.list_ports

########## HIDE ME ############
import uart.shell
shell = uart.shell.Shell()

def generate_keypair():
    keys = shell.do_genkeys()
    return keys

# message = path_to_file
def sign(private_key, message):
    r, s = shell.do_sign(message, private_key)
    signature = int(r), int(s)
    return signature

# message = path_to_file
def verify(public_key, message, signature):
    is_valid = shell.do_verify(message, signature, public_key)
    return is_valid

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

        # Список для отложенных логов
        self.delayed_logs = []

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
        self.signature_input.setReadOnly(False)  # Даем возможность вручную вводить подпись
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
        self.send_button.setEnabled(True)
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

        self.delayed_logs.clear()

        if not port or not baud_rate.isdigit():
            self.delayed_logs.append("Ошибка: неверный порт или скорость.")
            QTimer.singleShot(2000, self.show_delayed_logs)
            return

        try:
            self.serial_port = serial.Serial(port, int(baud_rate), timeout=1)
            self.timer.start(100)
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
            self.send_button.setEnabled(True)
            self.delayed_logs.append(f"Подключено к {port} со скоростью {baud_rate}.")
        except Exception as e:
            self.delayed_logs.append(f"Ошибка подключения: {str(e)}")

        QTimer.singleShot(2000, self.show_delayed_logs)

    def disconnect_uart(self):
        self.delayed_logs.clear()

        if self.serial_port:
            self.timer.stop()
            self.serial_port.close()
            self.serial_port = None

        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.send_button.setEnabled(False)

        self.delayed_logs.append("Отключено.")
        QTimer.singleShot(2000, self.show_delayed_logs)

    def generate_key_action(self):
        self.delayed_logs.clear()

        self.private_key, self.public_key = generate_keypair()
        self.public_key_input.setText(self.public_key.hex())

        self.delayed_logs.append("Сгенерированы новые ключи:")
        self.delayed_logs.append("Открытый ключ: " + self.public_key.hex())
        self.delayed_logs.append("Закрытый ключ: " + self.private_key.hex())

        QTimer.singleShot(2000, self.show_delayed_logs)

    def sign_message_action(self):
        # Подписать сообщение вручную
        self.delayed_logs.clear()

        if self.private_key is None:
            self.delayed_logs.append("Ошибка: нет приватного ключа для подписи.")
            QTimer.singleShot(2000, self.show_delayed_logs)
            return

        message = self.message_input.text().encode('utf-8')
        signature = sign(self.private_key, message)
        self.signature_input.setText(signature.hex())
        self.delayed_logs.append("Сообщение подписано (кнопка 'Подписать'): " + signature.hex())

        QTimer.singleShot(2000, self.show_delayed_logs)

    def handle_send(self):
        # Основная логика отправки и проверки
        # Все логи задержим на 2 секунды
        self.delayed_logs.clear()

        mode = self.mode_selector.currentText()

        message = self.message_input.text()
        pub_key_hex = self.public_key_input.text()
        user_signature_hex = self.signature_input.text().strip()

        # Проверка длины сообщения
        if len(message) > self.MESSAGE_MAX_LENGTH:
            self.delayed_logs.append("Ошибка: сообщение слишком длинное.")
            QTimer.singleShot(2000, self.show_delayed_logs)
            return

        # Получаем публичный ключ (если есть)
        if pub_key_hex:
            try:
                pub_key = bytes.fromhex(pub_key_hex)
            except:
                self.delayed_logs.append("Ошибка: некорректный формат открытого ключа (hex).")
                QTimer.singleShot(2000, self.show_delayed_logs)
                return
        else:
            pub_key = self.public_key

        # Проверка наличия ключей в режимах подписи и проверки
        if mode in ["Подпись", "Проверка подписи"]:
            if self.private_key is None or pub_key is None:
                self.delayed_logs.append("Ошибка: нет ключей для выполнения операции.")
                QTimer.singleShot(2000, self.show_delayed_logs)
                return

        # Действия по режимам
        if mode == "Генерация ключа":
            # Генерация ключей при нажатии "Отправить"
            self.private_key, self.public_key = generate_keypair()
            self.delayed_logs.append("Сгенерирован новый ключ (режим генерации):")
            self.delayed_logs.append("Открытый ключ: " + self.public_key.hex())
            self.delayed_logs.append("Закрытый ключ: " + self.private_key.hex())
            self.public_key_input.setText(self.public_key.hex())

        elif mode == "Подпись":
            # Подписание сообщения при нажатии "Отправить"
            if self.private_key is None:
                self.delayed_logs.append("Ошибка: нет закрытого ключа для подписи.")
                QTimer.singleShot(2000, self.show_delayed_logs)
                return
            signature = sign(self.private_key, message.encode('utf-8'))
            self.signature_input.setText(signature.hex())
            self.delayed_logs.append("Подпись сгенерирована (режим 'Подпись'): " + signature.hex())

        elif mode == "Проверка подписи":
            # Проверяем подпись
            # Если пользователь ввёл подпись, проверим её
            # Сравним с корректной подписью, вычисленной нами
            if self.private_key is None:
                self.delayed_logs.append("Ошибка: нет закрытого ключа для проверки.")
                QTimer.singleShot(2000, self.show_delayed_logs)
                return
            correct_signature = sign(self.private_key, message.encode('utf-8'))

            # Если пользователь не ввел подпись
            if not user_signature_hex:
                self.delayed_logs.append("Ошибка: нет подписи для проверки.")
                QTimer.singleShot(2000, self.show_delayed_logs)
                return

            try:
                user_signature = bytes.fromhex(user_signature_hex)
            except:
                self.delayed_logs.append("Ошибка: некорректный формат подписи (hex).")
                QTimer.singleShot(2000, self.show_delayed_logs)
                return

            # Проверяем совпадают ли подписи
            if user_signature == correct_signature:
                # Проверяем криптографически
                valid = verify(pub_key, message.encode('utf-8'), user_signature)
                if valid:
                    self.delayed_logs.append("Сообщение подписано верно.")
                else:
                    self.delayed_logs.append("Ошибка: подпись неверна.")
            else:
                # Если пользовательская подпись не совпадает с корректной,
                # выводим информацию о некорректной подписи
                self.delayed_logs.append("Подпись некорректна.")
                self.delayed_logs.append("Корректная подпись: " + correct_signature.hex())
                self.delayed_logs.append("Подпись от пользователя: " + user_signature_hex)

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
                self.delayed_logs.append("Отправлено в UART: " + packet.hex())
            except Exception as e:
                self.delayed_logs.append("Ошибка отправки в UART: " + str(e))
        else:
            self.delayed_logs.append("Предупреждение: UART не подключен, данные не отправлены.")

        # Отложенный вывод результатов (2 секунды)
        QTimer.singleShot(2000, self.show_delayed_logs)

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
                # Для входящих данных немедленный вывод
                self.output_text.append(f"Принято из UART: {formatted_data}")
        except Exception as e:
            self.output_text.append(f"Ошибка чтения из UART: {str(e)}")

    def show_delayed_logs(self):
        # Вывести накопленные логи
        for line in self.delayed_logs:
            self.output_text.append(line)
        self.delayed_logs.clear()

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
