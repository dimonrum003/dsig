import os
import tempfile

from uart.gost.gost341012 import CURVE_PARAMS, GOST3410Curve, prv_unmarshal, public_key
from uart.core import sign_file, verify_file, VerificationError, SigningError

# Параметры для кривой возьмём такие же, как в примере с do_genkeys
# Будем всегда использовать первый набор параметров
param_index = list(CURVE_PARAMS.keys())[0]
curve_params = CURVE_PARAMS[param_index]
curve = GOST3410Curve(*curve_params)

def generate_keypair():
    """
    Генерация ключевой пары:
    Приватный ключ: 512 бит (64 байта)
    Публичный ключ: 1024 бит (128 байт, первые 64 байта - X, следующие 64 - Y)
    """
    # Генерируем 64 случайных байт для приватного ключа
    priv_int = prv_unmarshal(os.urandom(64))
    # Генерируем публичный ключ (x, y)
    x, y = public_key(curve, priv_int)

    # Превращаем приватный ключ в 64-байтный массив:
    # priv_int - большое число, уместим его в 64 байта big-endian
    private_key_bytes = priv_int.to_bytes(64, 'big')

    # Превращаем публичный ключ (x, y) в 128-байтный массив
    # Каждое число (x, y) должно занять 64 байта
    x_bytes = x.to_bytes(64, 'big')
    y_bytes = y.to_bytes(64, 'big')
    public_key_bytes = x_bytes + y_bytes

    return private_key_bytes, public_key_bytes

def sign(private_key, message):
    print("Hi")
    """
    Подписывает сообщение, используя приватный ключ и кривую.
    Возвращает подпись в виде байтов.
    """
    # Конвертируем приватный ключ обратно в число
    priv_int = int.from_bytes(private_key, 'big')

    # Запишем message во временный файл
    with tempfile.NamedTemporaryFile(delete=False) as tmp_msg:
        print(message)
        tmp_msg.write(message)
        tmp_msg_path = tmp_msg.name

    try:
        print(curve)
        print(priv_int)
        # sign_file возвращает подпись
        
        signature = sign_file(tmp_msg_path, curve, priv_int)
        return bytes(''.join(map(str,signature)), 'utf-8')
    except SigningError as e:
        # В реальности нужно обработать ошибку
        return None
    finally:
        # Удаляем временный файл
        os.remove(tmp_msg_path)

def verify(public_key, message, signature):
    """
    Проверяет подпись, используя публичный ключ.
    Возвращает True, если подпись корректна, иначе False.
    """
    # Вытаскиваем x и y
    x = int.from_bytes(public_key[:64], 'big')
    y = int.from_bytes(public_key[64:], 'big')
    pub_key_tuple = (x, y)

    # Сохраняем сообщение во временный файл
    with tempfile.NamedTemporaryFile(delete=False) as tmp_msg:
        tmp_msg.write(message)
        tmp_msg_path = tmp_msg.name

    try:
        # verify_file бросает исключение VerificationError, если подпись неверна
        # или возвращает True/False?
        # Предположим, verify_file возвращает True при успешной проверке.
        verified = verify_file(curve, tmp_msg_path, signature, own_pubkey=pub_key_tuple)
        return verified
    except VerificationError:
        return False
    finally:
        os.remove(tmp_msg_path)