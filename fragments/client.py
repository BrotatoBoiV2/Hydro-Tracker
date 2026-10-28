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


def print_bootstrap_lines(line):
    if "Bootstrapped" in line:
        print(line)


def get_machine_id() -> str:
    for pathname in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
        path = Path(pathname)
        if path.exists():
            try:
                return path.read_text().strip()
            except Exception:
                continue
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
    random_str = f"{mid}-{dsk}-{mac}"
    return hashlib.sha256(random_str.encode('utf-8')).hexdigest()

HASH = create_hash()
onion_port = 9090
ONION = "iockbh2qzuob2syjgqlk6xkmgse3rnylqr7llakxf3rn7bpxgtctmfid.onion"
tor_data = tempfile.mkdtemp()
tor_process = None
socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", onion_port, rdns=True)
socket.socket = socks.socksocket

def send_request(action, content):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(30)
    sock.connect((ONION, 80))
    sock.send(HASH.encode('utf-8'))
    nonce = sock.recv(2048).decode('utf-8')
    payload = {"action": action, "content": content, "hash": HASH, "nonce": nonce}
    sock.send(json.dumps(payload).encode('utf-8'))
    response = sock.recv(2048).decode('utf-8')
    sock.close()

    return response


try:
    print("Launching background Tor client... Please wait.")
    tor_process = stem.process.launch_tor_with_config(
        config={
            'SocksPort': str(onion_port),
            'DataDirectory': tor_data
        },
        init_msg_handler=print_bootstrap_lines,
        take_ownership=True
    )
    
    print("Tor connected. Waiting for circuits to stabilize...")
    sleep(20)

except Exception as e:
    print(f"Error with Tor: {e}")
    exit(1)

try:
    
    # nonce = get_nonce()
    # print(nonce)
    # enc_pass = send_request("encrypt", "TestPass123")
    # sleep(3)
    # dec_pass = send_request("decrypt", enc_pass)
    enc_pass = send_request("encrypt", "TestPass123")
    print(enc_pass)
    # sleep(1)
    
    dec_pass = send_request("decrypt", enc_pass)
    #sock.send(json.dumps({"action": "encrypt", "content": "TestPass123", "hash": HASH}).encode('utf-8'))
    #enc_data = sock.recv(2048).decode('utf-8')
    # sock.send(json.dumps({"action": "decrypt", "content": enc_data}))
    # dec_data = sock.recv(2048).decode('utf-8')
    # print(enc_data)

    
    print(dec_pass)

except Exception as e:
    print(f"Connection error: {e}")

finally:
    if tor_process:
        tor_process.kill()

    exit(0)

