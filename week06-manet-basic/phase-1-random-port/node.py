import socket
import threading
import random
import sys
import importlib

# ==============================
# LOAD CONFIG
# ==============================
def load_node_config():
    try:
        node_idx = int(sys.argv[1])  # 0,1,2

        cfg = importlib.import_module("config")

        BASE_PORT = cfg.ALL_PORTS[node_idx]
        NEIGHBORS = [p for p in cfg.ALL_PORTS if p != BASE_PORT]

        return BASE_PORT, NEIGHBORS, cfg

    except (IndexError, ValueError):
        print("Usage: python node.py <0|1|2>")
        sys.exit(1)


BASE_PORT, NEIGHBORS, cfg = load_node_config()
neighbor_table = set(NEIGHBORS)

print(f"[NODE {BASE_PORT}] Neighbors: {NEIGHBORS}")

# ==============================
# RECEIVE
# ==============================
def handle_incoming(conn, addr):
    try:
        data = conn.recv(cfg.BUFFER_SIZE).decode()
        msg, ttl = data.split('|')
        ttl = int(ttl)

        print(f"[NODE {BASE_PORT}] From {addr}: {msg} (TTL={ttl})")

        # Forward
        if ttl > 0 and random.random() < cfg.FORWARD_PROBABILITY:
            forward_message(msg, ttl - 1, exclude=addr[1])

    except Exception as e:
        print(f"[NODE {BASE_PORT}] Error: {e}")

    finally:
        conn.close()

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
        threading.Thread(target=handle_incoming, args=(conn, addr), daemon=True).start()

# ==============================
# SEND
# ==============================
def forward_message(message, ttl, exclude=None):
    for peer_port in neighbor_table:
        if peer_port == exclude:
            continue

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((cfg.HOST, peer_port))

            payload = f"{message}|{ttl}"
            s.sendall(payload.encode())

            print(f"[NODE {BASE_PORT}] -> {peer_port}: {message} (TTL={ttl})")

            s.close()

        except ConnectionRefusedError:
            print(f"[NODE {BASE_PORT}] Peer {peer_port} unreachable")

# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    threading.Thread(target=start_server, daemon=True).start()

    # ส่ง message เริ่มต้น
    test_message = f"Hello from {BASE_PORT}"
    forward_message(test_message, cfg.TTL)

    # กันโปรแกรมปิด
    while True:
        threading.Event().wait(1)