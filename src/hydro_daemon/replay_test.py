import socket
import json
from password_client import PasswordClient, ClientHash, LocalCryptograph

ONION_ADDR = "iockbh2qzuob2syjgqlk6xkmgse3rnylqr7llakxf3rn7bpxgtctmfid.onion"

def test_replay_attack():
    # Initialize the client, which starts the background Tor SOCKS proxy on port 9090
    print("[*] Starting test client and Tor proxy...")
    client = PasswordClient()
    
    client_hash = ClientHash().client_hash
    local_crypto = LocalCryptograph()
    safe_pass = local_crypto.encrypt("ReplayTest123")

    try:
        print("[*] Sending initial legitimate request...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ONION_ADDR, 80))
        sock.send(client_hash.encode('utf-8'))
        
        nonce = sock.recv(2048).decode('utf-8')
        payload = {
            "action": "encrypt",
            "content": safe_pass,
            "hash": client_hash,
            "nonce": nonce
        }
        sock.send(json.dumps(payload).encode('utf-8'))
        response1 = sock.recv(2048).decode('utf-8')
        sock.close()
        print(f"[+] First Response: {response1}")

        print("[*] Attempting Replay Attack with the exact same nonce and payload...")
        sock_replay = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_replay.connect((ONION_ADDR, 80))
        sock_replay.send(client_hash.encode('utf-8'))
        
        # Drain the *new* nonce sent by server, but force-send the *old* payload/nonce combo
        _new_nonce_ignored = sock_replay.recv(2048).decode('utf-8')
        
        sock_replay.send(json.dumps(payload).encode('utf-8'))
        response2 = sock_replay.recv(2048).decode('utf-8')
        sock_replay.close()

        print(f"[+] Replay Response (Should be empty or rejected): {repr(response2)}")

    finally:
        if client.tor_process:
            print("[*] Shutting down Tor process...")
            client.tor_process.kill()

if __name__ == "__main__":
    test_replay_attack()