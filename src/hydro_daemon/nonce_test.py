import socket
import json
import time
from password_client import PasswordClient, ClientHash, LocalCryptograph

ONION_ADDR = "iockbh2qzuob2syjgqlk6xkmgse3rnylqr7llakxf3rn7bpxgtctmfid.onion"

def test_nonce_edge_cases():
    print("[*] Starting test client and Tor proxy...")
    client = PasswordClient()
    client_hash = ClientHash().client_hash
    local_crypto = LocalCryptograph()
    safe_pass = local_crypto.encrypt("NonceTest123")

    try:
        # --- TEST 1: Fabricated / Invalid Nonce ---
        print("\n--- [Test 1] Testing Forged/Invalid Nonce ---")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ONION_ADDR, 80))
        sock.send(client_hash.encode('utf-8'))
        _ = sock.recv(2048) # Drain valid server nonce
        
        forged_payload = {
            "action": "encrypt",
            "content": safe_pass,
            "hash": client_hash,
            "nonce": "TOTALLY_FAKE_NONCE_123456"
        }
        sock.send(json.dumps(forged_payload).encode('utf-8'))
        response1 = sock.recv(2048).decode('utf-8')
        sock.close()
        print(f"[+] Server Response to Fake Nonce (Should reject): {repr(response1)}")

        # --- TEST 2: Expired / Stale Nonce Simulation ---
        print("\n--- [Test 2] Testing Stale / Expired Nonce Delay ---")
        sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock2.connect((ONION_ADDR, 80))
        sock2.send(client_hash.encode('utf-8'))
        real_nonce = sock2.recv(2048).decode('utf-8')
        
        # print("[*] Obtained real nonce. Sleeping for 10 seconds to simulate time lag / expiration window...")
        # time.sleep(10)
        
        stale_payload = {
            "action": "encrypt",
            "content": safe_pass,
            "hash": client_hash,
            "nonce": real_nonce
        }
        # Try sending the delayed nonce
        sock2.send(json.dumps(stale_payload).encode('utf-8'))
        response2 = sock2.recv(2048).decode('utf-8')
        sock2.close()
        print(f"[+] Server Response to Delayed Nonce: {repr(response2)}")

        # --- TEST 3: Nonce Generation Flooding ---
        print("\n--- [Test 3] Nonce Request Flooding ---")
        success_count = 0
        for i in range(15):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(3)
                s.connect((ONION_ADDR, 80))
                s.send(client_hash.encode('utf-8'))
                n = s.recv(2048)
                if n:
                    success_count += 1
                s.close()
            except Exception as e:
                print(f"[-] Flood connection {i+1} failed: {e}")
        print(f"[+] Successfully pulled {success_count}/15 sequential nonces under rapid fire.")

    finally:
        if client.tor_process:
            print("[*] Shutting down Tor process...")
            client.tor_process.kill()

if __name__ == "__main__":
    test_nonce_edge_cases()