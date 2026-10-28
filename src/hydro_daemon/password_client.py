import tempfile
import socket
import socks
import stem.process
import json 
from time import sleep
from pathlib import Path
import uuid
import hashlib
import subprocess as sp

class ClientHash:
    def __init__(self) -> None:
        self.client_hash = self.create_hash()

    def get_machine_id(self) -> str:
        for pathname in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
            path = Path(pathname)

            if path.exists():
                try:
                    return path.read_text().strip()
                except Exception:
                    continue

        return "FallbackMachineID"

    def get_disk_serial(self) -> str:
        try:
            response = sp.run(["lsblk", "-n", "-o", "SERIAL"],
                            stdout=sp.PIPE, stderr=sp.PIPE, text=True, check=True)
            serial = [line.strip() for line in response.stdout.split("\n") if line.strip()]
            return serial[0] if serial else "FallbackDiskSerial"

        except Exception:
            return "FallbackDiskSerial"
    
    def create_hash(self) -> str:
        mid = self.get_machine_id()
        dsk = self.get_disk_serial()
        mac = f"{uuid.getnode():012x}"
        random_str = f"{mid}-{dsk}-{mac}"
        return hashlib.sha256(random_str.encode('utf-8')).hexdigest()


class PasswordClient:
    def __init__(self):
        self.onion_port = 9090
        self.onion = "iockbh2qzuob2syjgqlk6xkmgse3rnylqr7llakxf3rn7bpxgtctmfid.onion"
        self.tor_data = tempfile.mkdtemp()
        self.tor_process = self.start_client()

        socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", self.onion_port, rdns=True)
        socket.socket = socks.socksocket

    def start_client(self):
        try:
            print("Launching background Tor client... Please wait.")
            tor_process = stem.process.launch_tor_with_config(
                config={
                    'SocksPort': str(self.onion_port),
                    'DataDirectory': self.tor_data
                },
                take_ownership=True
            )
            
            print("Tor connected. Waiting for circuits to stabilize...")
            sleep(20)
            return tor_process

        except Exception as e:
            print(f"Error with Tor: {e}")
            exit(1)

    def send_request(self, action, content, client_hash):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect((self.onion, 80))
        sock.send(client_hash.encode('utf-8'))

        nonce = sock.recv(2048).decode('utf-8')
        payload = {
            "action": action,
            "content": content,
            "hash": client_hash,
            "nonce": nonce
        }

        sock.send(json.dumps(payload).encode('utf-8'))
        response = sock.recv(2048).decode('utf-8')

        sock.close()

        return response


if __name__ == '__main__':
    pass_clinet = PasswordClient()
    try:
        client_hash = ClientHash().client_hash
        enc_pass = pass_clinet.send_request("encrypt", "TestPass123", client_hash)
        print(enc_pass)
        client_hash = ClientHash().client_hash
        dec_pass = pass_clinet.send_request("decrypt", enc_pass, client_hash)
        print(dec_pass)

    except Exception as e:
        print(f"Connection error: {e}")

    finally:
        if pass_clinet.tor_process:
            pass_clinet.tor_process.kill()
