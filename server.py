import socket
import threading
import shlex

HOST = '127.0.0.1'
PORT = 14900

poll_question = None
poll_options = []
poll_votes = []
voted = set()
clients = []
lock = threading.Lock()


def broadcast(msg):
    with lock:
        for c in clients[:]:
            try:
                c.send((msg + '\n').encode())
            except:
                clients.remove(c)
                c.close()


def handle_client(conn, addr, cid):
    conn.send("Добро пожаловать!\n".encode())
    conn.send("Команды: VOTE 1..n   RESULTS   HELP\n\n".encode())

    while True:
        try:
            data = conn.recv(1024).decode().strip()
            if not data: break

            cmd, *args = data.upper().split()

            if cmd == "HELP":
                conn.send("VOTE <число> - голосовать\nRESULTS - результаты\nHELP - эта помощь\n".encode())

            elif cmd == "RESULTS":
                with lock:
                    if not poll_question:
                        conn.send("Опроса сейчас нет\n".encode())
                        continue
                    total = sum(poll_votes)
                    msg = f"{poll_question}\n"
                    for i, opt in enumerate(poll_options, 1):
                        perc = (poll_votes[i - 1] / total * 100) if total else 0
                        msg += f"{i}. {opt}  —  {poll_votes[i - 1]} ({perc:.0f}%)\n"
                    msg += f"Всего: {total}\n"
                conn.send(msg.encode())

            elif cmd == "VOTE":
                if len(args) != 1:
                    conn.send("Формат: VOTE <номер>\n".encode())
                    continue
                try:
                    choice = int(args[0]) - 1
                except:
                    conn.send("Номер должен быть числом\n".encode())
                    continue

                with lock:
                    if not poll_question:
                        conn.send("Нет активного опроса\n".encode())
                        continue
                    if cid in voted:
                        conn.send("Вы уже голосовали\n".encode())
                        continue
                    if not 0 <= choice < len(poll_options):
                        conn.send(f"Номер от 1 до {len(poll_options)}\n".encode())
                        continue

                    poll_votes[choice] += 1
                    voted.add(cid)
                    conn.send(f"Голос учтён: {poll_options[choice]}\n".encode())

            else:
                conn.send("Неизвестная команда. Напишите HELP\n".encode())

        except:
            break

    with lock:
        if conn in clients:
            clients.remove(conn)
    conn.close()
    print(f"Клиент {cid} отключился  ({len(clients)} онлайн)")


def admin_input():
    global poll_question, poll_options, poll_votes, voted

    while True:
        try:
            line = input("> ").strip()
            if line.lower() in ("q", "quit", "exit"): break
            if not line: continue

            parts = line.split(maxsplit=1)
            cmd = parts[0].upper()

            if cmd == "SHUTDOWN":
                broadcast("Сервер выключается")
                break

            if cmd != "POLL":
                print('Используйте: POLL "вопрос" "вариант1" "вариант2" ...')
                continue

            if len(parts) < 2:
                print('Пример: POLL "Любимый цвет?" "Красный" "Синий" "Зелёный"')
                continue

            args = shlex.split(parts[1])
            if len(args) < 3:
                print("Нужен вопрос + минимум 2 варианта")
                continue

            with lock:
                poll_question = args[0]
                poll_options = args[1:]
                poll_votes = [0] * len(poll_options)
                voted = set()

            broadcast(f"Новый опрос: {poll_question}")
            for i, opt in enumerate(poll_options, 1):
                broadcast(f"  {i}) {opt}")
            broadcast("Голосуйте:  VOTE 1  /  VOTE 2  ...")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print("Ошибка ввода:", e)

    print("Остановка...")
    with lock:
        for c in clients:
            try:
                c.close()
            except:
                pass
    exit(0)


def main():
    global clients

    threading.Thread(target=admin_input, daemon=True).start()

    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(10)
    print(f"Сервер {HOST}:{PORT}  (POLL для создания опроса)")

    cid = 0
    while True:
        try:
            conn, addr = s.accept()
            cid += 1
            with lock:
                clients.append(conn)
            print(f"Подключение {cid}  ({addr})  онлайн: {len(clients)}")
            threading.Thread(target=handle_client, args=(conn, addr, cid), daemon=True).start()
        except:
            break

    s.close()


if __name__ == "__main__":
    main()