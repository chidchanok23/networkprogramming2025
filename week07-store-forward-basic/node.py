import socket
import threading
import time
import sys
import importlib
from message_queue import MessageQueue

# ==============================
# LOAD CONFIG
# ==============================
def load_node_config():
    try:
        node_idx = int(sys.argv[1])
        cfg = importlib.import_module("config")

        BASE_PORT = cfg.ALL_PORTS[node_idx]
        PEER_PORTS = [p for p in cfg.ALL_PORTS if p != BASE_PORT]

        return BASE_PORT, PEER_PORTS, cfg

    except (IndexError, ValueError):
        print("Usage: python node.py <0|1|2>")
        sys.exit(1)

BASE_PORT, PEER_PORTS, cfg = load_node_config()
print(f"[NODE {BASE_PORT}] Peers: {PEER_PORTS}")

queue = MessageQueue()

# ==============================
# SEND
# ==============================
def send_message(peer_port, message):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((cfg.HOST, peer_port))
        s.sendall(message.encode())
        s.close()
        return True

    except (ConnectionRefusedError, socket.timeout, OSError):
        return False

# ==============================
# RETRY LOOP (สำคัญมาก)
# ==============================
def retry_loop():
    while True:
        time.sleep(cfg.RETRY_INTERVAL)

        for msg in queue.get_messages():
            peer = msg["peer"]
            message = msg["message"]
            
            print(f"[NODE {BASE_PORT}] Retrying to {peer} (attempt {msg['attempts']+1})")

            if send_message(peer, message):
                print(f"[NODE {BASE_PORT}] Sent stored message to {peer}")
                queue.remove_message(msg)
            else:
                queue.inc_attempts(msg)

# ==============================
# SERVER
# ==============================
def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((cfg.HOST, BASE_PORT))
    server.listen()

    print(f"[NODE {BASE_PORT}] Listening...")

    while True:
        conn, addr = server.accept()
        try:
            data = conn.recv(cfg.BUFFER_SIZE).decode()
            print(f"[NODE {BASE_PORT}] Received: {data} from {addr}")
        finally:
            conn.close()

# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    threading.Thread(target=start_server, daemon=True).start()
    threading.Thread(target=retry_loop, daemon=True).start()

    # ส่งครั้งแรก
    for peer in PEER_PORTS:
        msg = f"Hello from {BASE_PORT}"

        if send_message(peer, msg):
            print(f"[NODE {BASE_PORT}] Sent to {peer}")
        else:
            print(f"[NODE {BASE_PORT}] Peer {peer} unavailable → store")
            queue.add_message(msg, peer)

    while True:
        time.sleep(1)