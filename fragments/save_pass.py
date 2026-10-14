import os
import sys
import uuid
import base64
import hashlib
import subprocess
from argon2.low_level import hash_secret_raw, Type
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def mad() -> str: # local id
    mex = f"{uuid.getnode():012x}"
    return ":".join(mex[i : i + 2] for i in range(0, 12, 2))

def mid() -> str: # local id
    for p in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
        if os.path.exists(p):
            with open(p, "r") as f:
                return f.read().strip()
    return "FallbackMachineID"

def ds() -> str: # local id
    try:
        r = subprocess.run(
            ["lsblk", "-n", "-o", "SERIAL"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
        )
        s = [l.strip() for l in r.stdout.split("\n") if l.strip()]
        return s[0] if s else "FallbackSerial"
    except Exception:
        return "FallbackSerial"

def hf() -> str: # combines local id
    r = f"{mid()}-{ds()}-{mad()}"
    return hashlib.sha256(r.encode('utf-8')).hexdigest()

def dk(r: bytes) -> bytes: # create the key
    h = hf()
    s = r + h.encode('utf-8')
    
    return hash_secret_raw(
        secret=s,
        salt=b"HydroTrackerSalt",
        time_cost=3,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        type=Type.ID
    )

def ep(p: str) -> str: # encrypt the password
    r = os.urandom(16)
    n = os.urandom(12)
    k = dk(r)
    a = AESGCM(k)
    c = a.encrypt(n, p.encode('utf-8'), None)
    b = r + n + c
    return base64.b64encode(b).decode('utf-8')

def dp(s: str) -> str: # decrypt the password
    b = base64.b64decode(s.encode('utf-8'))
    r = b[0:16]
    n = b[16:28]
    c = b[28:]
    k = dk(r)
    a = AESGCM(k)
    d = a.decrypt(n, c, None)
    return d.decode('utf-8')

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <password> [--encrypt|--decrypt]")
        exit(1)
        
    v = sys.argv[1]
    o = sys.argv[2]
    
    if o == "--encrypt":
        print(ep(v))
    elif o == "--decrypt":
        print(dp(v))
    else:
        print(f"Usage: {sys.argv[0]} <password> [--encrypt|--decrypt]")
        exit(1)
