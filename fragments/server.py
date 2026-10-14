import os
import base64
from pathlib import Path
from stem.control import Controller
from stem.process import launch_tor_with_config
import json
import hashlib
import uuid
import socket
import tempfile
from threading import Lock
from datetime import datetime
import subprocess as sp
from argon2.low_level import hash_secret_raw, Type
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SALTY = b"MySuperSecret_HydroTracker_Salt!420"
TTL_SECONDS = 10
SERVER_PORT = 5000
SERVER_HOST = '127.0.0.1' 
ONION_PORT = 80
KEY_FILE = Path("~/.hydro/secret.key").expanduser()
TOR_BIN_PATH = Path(__file__).parent / "bin/tor"


class Server:
    def __init__(self):
        self.nonces = {}
        self.nonce_lock = Lock()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tor_process = None
        self.start()

    def check_key(self, controller):
        if KEY_FILE.exists():
            with open(KEY_FILE, "r") as file:
                full_key = file.read().strip()

            if ":" in full_key:
                key_type, key_content = full_key.split(":", 1)
            else:
                key_type = "ED25519-V3"
                key_content = full_key
            print("Loading existing key...")
        else:
            key_type = "NEW"
            key_content = "ED25519-V3"
            print("Created a new key!")

        ephemeral = controller.create_ephemeral_hidden_service(
            {ONION_PORT: SERVER_PORT},
            key_type=key_type,
            key_content=key_content,
            await_publication=True
        )

        if key_type == "NEW":
            KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(KEY_FILE, "w") as file:
                file.write(ephemeral.private_key)
            print(f"Saved the key to file: {KEY_FILE}")

        print(f"Listening on address: {ephemeral.service_id}.onion")

    def start(self):
        if not TOR_BIN_PATH.exists():
            raise FileNotFoundError(
                f"Portable Tor binary not found at {TOR_BIN_PATH}. "
                "Please place a statically linked Linux tor binary inside the ./bin/ directory."
            )

        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((SERVER_HOST, SERVER_PORT))
        self.sock.listen()

        tor_data_dir = tempfile.mkdtemp(prefix="hydro_tor_")
        control_port = 9051

        print("Launching bundled Tor background process...")
        try:
            self.tor_process = launch_tor_with_config(
                config={
                    'ControlPort': str(control_port),
                    'DataDirectory': tor_data_dir,
                    'SocksPort': '0',
                },
                tor_cmd=str(TOR_BIN_PATH),
                take_ownership=True
            )
        except Exception as e:
            raise RuntimeError(f"Failed to start bundled Tor binary: {e}")

        with Controller.from_port(port=control_port) as controller:
            controller.authenticate()
            self.check_key(controller)
            
        self.start_listening()

    def get_nonce(self, hash: str) -> str:
        merged = hash + str(uuid.uuid4())
        merged_base = base64.b64encode(merged.encode('utf-8'))
        nonce = merged_base[69:]
        timestamp = datetime.now()
        print(nonce)
        print(timestamp)

        with self.nonce_lock:
            self.nonces[nonce.decode('utf-8')] = {"is_used": False, "created": timestamp}

        print(self.nonces)

        return nonce

    def start_listening(self):
        print("Starting the server listener loop...")

        try:
            while True:
                client, address = self.sock.accept()
                raw_data = client.recv(2048)

                if not raw_data:
                    client.close()
                    continue
                
                try:
                    data = json.loads(raw_data.decode('utf-8'))
                except json.JSONDecodeError:
                    client.close()
                    continue

                print(f"Received action: {data.get('action')}")

                if data.get('action') == "encrypt":
                    encrypted_val = self.encrypt_password(data['content'], data['hash'], data['nonce'])
                    client.sendall(encrypted_val.encode('utf-8'))

                elif data.get('action') == "decrypt":
                    decrypted_val = self.decrypt_password(data['content'], data['hash'], data['nonce'])
                    client.sendall(decrypted_val.encode('utf-8'))

                elif data.get('action') == "get_nonce":
                    nonce = self.get_nonce(data.get('hash'))
                    client.sendall(nonce.encode('utf-8'))
                
                client.close()
        finally:
            self.sock.close()
            if self.tor_process:
                self.tor_process.kill()

    def create_key(self, hash: str, random_bytes: bytes) -> bytes:
        secret = random_bytes + hash.encode('utf-8')
        return hash_secret_raw(
            secret=secret,
            salt=SALTY,
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            type=Type.ID
        )

    def nonce_expired(self, nonce: str) -> bool:
        created = self.nonces[nonce].get("created")
        current = datetime.now()
        deltatime = current - created
        print(deltatime)

        if deltatime.total_seconds() > 30:
            return True

        return False

    def valid_nonce(self, nonce: str) -> bool:
        if nonce not in list(self.nonces.keys()):
            print("Nonce does not exist!")
            return False

        is_used = self.nonces[nonce].get("is_used")

        if is_used:
            print("Nonce is used!")
            return False

        if self.nonce_expired(nonce):
            print("Nonce is expired!")
            return False

        return True

    def encrypt_password(self, password: str, hash: str, nonce: str) -> str:
        # print(f"DEBUG: {self.nonces}")
        # exit()
        print(f"DEBUG: {password} {hash} {nonce}")
        if not self.valid_nonce(nonce):
            return "ERROR"

        random_bytes = os.urandom(16)
        rand_nonce = os.urandom(12)
        key = self.create_key(hash, random_bytes)
        aesgcm = AESGCM(key)
        cipher = aesgcm.encrypt(rand_nonce, password.encode('utf-8'), None)
        password_bytes = random_bytes + rand_nonce + cipher

        self.nonces[nonce]["is_used"] = True

        return base64.b64encode(password_bytes).decode('utf-8')

    def decrypt_password(self, password: str, hash: str, nonce: str) -> str:
        if not self.valid_nonce(nonce):
            return "ERROR"

        password_bytes = base64.b64decode(password.encode('utf-8'))
        random_bytes = password_bytes[0:16]
        rand_nonce = password_bytes[16:28]
        cipher = password_bytes[28:]
        key = self.create_key(hash, random_bytes)
        aesgcm = AESGCM(key)
        decrypted = aesgcm.decrypt(rand_nonce, cipher, None)
        
        self.nonces[nonce]["is_used"] = True

        return decrypted.decode('utf-8')


if __name__ == '__main__':
    Server()