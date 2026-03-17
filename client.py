# client.py
import socket
import threading
import sys

HOST = '127.0.0.1'
PORT = 14900

def receive():
    """Поток для приёма сообщений от сервера"""
    while True:
        try:
            data = sock.recv(4096).decode('utf-8')
            if not data:
                print("\n[Соединение закрыто сервером]")
                break
            print(data, end='')  # выводим без лишних переносов
        except:
            print("\n[Ошибка соединения]")
            break
    sys.exit(0)


try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    print(f"Подключено к {HOST}:{PORT}")
    print("Можно вводить команды: VOTE 1, RESULTS, HELP")
    print("Для выхода: exit или ctrl+C\n")
except Exception as e:
    print(f"Не удалось подключиться: {e}")
    sys.exit(1)

# Запускаем поток приёма сообщений
threading.Thread(target=receive, daemon=True).start()

try:
    while True:
        msg = input().strip()
        if msg.lower() in ('exit', 'quit', 'q'):
            break
        if msg:
            try:
                sock.send((msg + '\n').encode('utf-8'))
            except:
                print("Не удалось отправить сообщение")
                break
except KeyboardInterrupt:
    print("\nКлиент завершает работу...")

sock.close()
print("До свидания!")