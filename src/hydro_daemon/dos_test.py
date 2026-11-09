import socket
import threading
from time import sleep
from password_client import PasswordClient

ONION_ADDR = "iockbh2qzuob2syjgqlk6xkmgse3rnylqr7llakxf3rn7bpxgtctmfid.onion"

def dangling_connection(index):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ONION_ADDR, 80))
        print(f"[Client {index}] Connected and hanging...")
        sock.send(b"PartialHashData")
        sleep(15) 
        sock.close()
    except Exception as e:
        print(f"[Client {index}] Connection dropped: {e}")

if __name__ == "__main__":
    print("[*] Starting test client and Tor proxy...")
    client = PasswordClient()

    try:
        threads = []
        for i in range(10):
            t = threading.Thread(target=dangling_connection, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
    finally:
        if client.tor_process:
            print("[*] Shutting down Tor process...")
            client.tor_process.kill()