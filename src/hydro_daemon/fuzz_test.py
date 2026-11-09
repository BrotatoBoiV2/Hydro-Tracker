import socket
import json
from password_client import PasswordClient, ClientHash

ONION_ADDR = "iockbh2qzuob2syjgqlk6xkmgse3rnylqr7llakxf3rn7bpxgtctmfid.onion"

MALFORMED_PAYLOADS = [
    "{not-even-json",  # Bad syntax
    json.dumps({"action": "encrypt"}),  # Missing keys
    json.dumps({"action": "drop_table", "content": "test", "hash": "abc", "nonce": "123"}), # Invalid action
    json.dumps({"action": "encrypt", "content": None, "hash": 12345, "nonce": {}}) # Wrong types
]

def fuzz_server():
    print("[*] Starting test client and Tor proxy...")
    client = PasswordClient()
    client_hash = ClientHash().client_hash

    try:
        for i, payload in enumerate(MALFORMED_PAYLOADS):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((ONION_ADDR, 80))
                sock.send(client_hash.encode('utf-8'))
                nonce = sock.recv(2048).decode('utf-8')
                
                sock.send(payload.encode('utf-8') if not payload.startswith("{not") else b"{not-even-json")
                response = sock.recv(2048).decode('utf-8')
                sock.close()
                print(f"[Test {i+1}] Handled gracefully. Server response: {repr(response)}")
            except Exception as e:
                print(f"[Test {i+1}] CRITICAL: Server crashed or dropped connection: {e}")
    finally:
        if client.tor_process:
            print("[*] Shutting down Tor process...")
            client.tor_process.kill()

if __name__ == "__main__":
    fuzz_server()