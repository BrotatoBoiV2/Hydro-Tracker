import base64
import hashlib
import json
import os
import socket
import subprocess as sp
import sys
from time import time, sleep
import uuid
from threading import Thread, Lock
from pathlib import Path
import queue

from argon2.low_level import hash_secret_raw, Type
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SALTY = b"MySuperSecret_HydroTracker_Salt!420"
TTL_SECONDS = 10


class SecurePass:
    def __init__(self, hash: str) -> None:
        self.hash = hash
        self.nonces = {}
        self.nonce_lock = Lock()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        Thread(target=self.cleanup_nonces, daemon=True).start()
        # Thread(target=self.start_server, daemon=True).start()
        # self.start_server()

    def start_server(self):
        try:
            with Controller.from_port(port=9051) as controller:
                controller.authenticate()
                self.check_key(controller)
                self.start_listening()

        except Exception as e:
            print(f"Tor Controller Error: {e}. Ensure Tor is running with ControlPort enabled.")

    def check_key(self, controller: Controller):
        if KEY_FILE.exists():
            with open(KEY_FILE, "r") as file:
                full_key = file.read().strip()

            # Fix: Split 'ED25519-V3:xyz...' into type and the actual blob
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
            # Ensure the target directory ~/.hydro exists before writing
            KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(KEY_FILE, "w") as file:
                # This saves the full "ED25519-V3:BLOB" format
                file.write(ephemeral.private_key)
                print(f"Saved the key to file: {KEY_FILE}")

        print(f"Now listening with address: {ephemeral.service_id}.onion")

    def start_listening(self):
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((SERVER_HOST, SERVER_PORT))
        self.sock.listen(5)

        print("Now listening for requests...")

        while True:
            try:
                client, address = self.sock.accept()
                data = client.recv(4096)
                response = None

                if not data:
                    break

                if data['action'] == "encrypt":
                    response = self.encrypt_password(data['content'])

                elif data['action'] == "decrypt":
                    response = self.decrypt_password(data['content'])

                if response:
                    client.send(response.encode('utf-8'))

            except Exception as e:
                print(f"Error Occurred: {e}")


    def add_nonce(self, nonce):
        with self.nonce_lock:
            self.nonces[nonce] = time() + TTL_SECONDS

    def use_nonce(self, nonce) -> bool:
        with nonce_lock:
            if nonce in self.nonces:
                del self.nonces[nonce]
                return True

            return False
    
    def cleanup_nonces(self) -> None:
        while True:
            sleep(TTL_SECONDS)
            current_time = time()

            with self.nonce_lock:
                expired = [key for key, timestamp in self.nonces.items() if timestamp < current_time]

                for key in expired:
                    del self.nonces[key]

    def create_key(self, random: bytes) -> bytes:
        secret = random + self.hash.encode('utf-8')

        return hash_secret_raw(
            secret=secret,
            salt=SALTY,
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            type=Type.ID
        )

    def encrypt_password(self, password: str) -> str:
        random = os.urandom(16)
        nonce = os.urandom(12)
        key = self.create_key(random)
        aesgcm = AESGCM(key)
        cipher = aesgcm.encrypt(nonce, password.encode('utf-8'), None)
        password_bytes = random + nonce + cipher

        return base64.b64encode(password_bytes).decode('utf-8')

    def decrypt_password(self, password: str) -> str:
        password_bytes = base64.b64decode(password.encode('utf-8'))
        random = password_bytes[0:16]
        nonce = password_bytes[16:28]
        cipher = password_bytes[28:]
        key = self.create_key(random)
        aesgcm = AESGCM(key)
        decrypted = aesgcm.decrypt(nonce, cipher, None)

        return decrypted.decode('utf-8')


### Client-side
def get_machine_id() -> str:
    for pathname in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
        path = Path(pathname)
        
        if path.exists:
            with open(path, "r") as file:
                return file.read().strip()

    return "FallbackMachineID"

def get_disk_serial() -> str:
    try:
        response = sp.run(["lsblk", "-n", "-o", "SERIAL"],
        stdout=sp.PIPE, stderr=sp.PIPE, text=True, check=True)
        serial = [line.strip() for line in response.stdout.split("\n") if line.strip()]

        return serial[0] if serial else "FallbackDiskSerial"

    except Exception:
        return "FallbackDiskSerial"

def create_hash() -> str:
    mid = get_machine_id()
    dsk = get_disk_serial()
    mac = f"{uuid.getnode():012x}"
    random = f"{mid}-{dsk}-{mac}"

    return hashlib.sha256(random.encode('utf-8')).hexdigest()

import tempfile
import socks
import stem.process

if __name__ == '__main__':
    pass_secure = SecurePass(create_hash())
    # onion_port = 9090
    # onion = "unassigned"
    # tor_data = tempfile.mkdtemp()
    # tor_process = None
    # sock = None

    # try:
    #     tor_process = stem.process.launch_tor_with_config(
    #         config={
    #             'SocksPort': str(onion_port),
    #             'DataDirectory': tor_data
    #         },
    #         take_ownership=True
    #     )

    # except Exception as e:
    #     print(f"Error with Tor: {e}")
    #     exit(1)
        
    # socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", onion_port, rdns=True)
    # socket.socket = socks.socksocket
    # sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # try:
    #     sock.connect((onion, 80))
    #     sock.send(json.dumps({"action": "encrypt", "content": "TestPass123"}.encode('utf-8')))
    #     enc_data = sock.recv(2048).decode('utf-8')
    #     sock.send(json.dumps({"action": "decrypt", "content": enc_data}))
    #     dec_data = sock.recv(2048).decode('utf-8')
    #     print(enc_data)
    #     print(dec_data)

    # except Exception as e:
    #     print(f"Connection error: {e}")

    # finally:
    #     if sock:
    #         sock.close()
        
    #     if tor_process:
    #         tor_process.kill()

    #     exit(1)

