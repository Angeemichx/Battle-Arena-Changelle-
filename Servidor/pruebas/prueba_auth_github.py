import json, socket

s = socket.create_connection(("127.0.0.1", 5555), timeout=10)
s.sendall((json.dumps({"action": "oauth_start"}) + "\n").encode())
buf = ""
while True:
    buf += s.recv(4096).decode()
    for linea in buf.split("\n")[:-1]:
        msg = json.loads(linea)
        print(msg)
        if "ok" in msg:
            raise SystemExit
    buf = buf.split("\n")[-1]