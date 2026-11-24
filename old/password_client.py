
"""
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Programmer: Aaron "A.J" Cassell. (@BrotatoBoi)
              Program Name: Hydro Tracker.
Description: A tool for tracking hydro usage from the
             official Hydro Ottawa portal.

File: password_client.py             Date: 2026/10/28
                Version: 0.1.1-2026.10.28
===========================================================

        Copyright (C) 2026 BrotatoBoi.

This program is free software: you can redistribute it
and/or modify it under the terms of the GNU Affero 
General Public License as published by the Free
Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be
useful, but WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
PURPOSE.  See the GNU Affero General Public License for
more details.

You should have received a copy of the GNU Affero General
Public License along with this program.
If not, see <https://www.gnu.org/licenses/>
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""


# ~ Standard Imports. ~ #
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
import os
import base64
import keyring
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class ClientHash:
    """
        ~ Handle the client's stable, high-entropy local hash. ~

        Methods:
            __init__            : Initialize the hash and persistent salt.
            get_machine_id      : Obtain the stable OS machine ID.
            _get_or_create_salt : Load or generate a persistent cryptographic salt.
            create_hash         : Create client's full stable local hash.
    """

    def __init__(self) -> None:
        """
            ~ Initialize the local hash and salt storage. ~

            Attributes:
                salt_path   : Path to the persistent local salt file.
                client_hash : The client's final local hash.

            Returns:
                None
        """
        self.salt_path = Path("~/.hydro/client.salt").expanduser()
        self.client_hash = self.create_hash()

    def get_machine_id(self) -> str:
        """
            ~ Obtain the machine's persistent OS ID. ~

            Returns:
                String : The unique machine ID or a fallback one.
        """
        for pathname in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
            path = Path(pathname)
            if path.exists():
                try:
                    return path.read_text().strip()
                except Exception:
                    continue

        return "FallbackMachineID"

    def _get_or_create_salt(self) -> bytes:
        """
            ~ Retrieve or generate a high-entropy cryptographic salt. ~

            Returns:
                Bytes : 32 bytes of cryptographically secure random data.
        """
        if self.salt_path.exists():
            with open(self.salt_path, "rb") as f:
                return f.read()
        
        # Ensure parent directory exists with secure permissions
        self.salt_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate 256 bits of true random entropy
        salt = os.urandom(32)
        
        with open(self.salt_path, "wb") as f:
            os.chmod(self.salt_path, 0o600)
            f.write(salt)
            
        return salt

    def create_hash(self) -> str:
        """
            ~ Create the stable, high-entropy client hash. ~

            Returns:
                String : SHA-256 hash combining machine ID and random salt.
        """
        mid = self.get_machine_id()
        salt = self._get_or_create_salt()

        # Combine OS instance ID with 256 bits of persistent random entropy
        hasher = hashlib.sha256()
        hasher.update(mid.encode('utf-8'))
        hasher.update(salt)

        return hasher.hexdigest()


class PasswordClient:
    """
        ~ Handle the password cryptography. ~

        Methods:
            __init__     : Initialize the cryptographer.
            start_client : Start the client Tor connection.
            send_request : Send a cryptographic request to
                           the server.
    """

    def __init__(self) -> None:
        """
            ~ Initialize the password cryptographer. ~

            Attributes:
                onion_port  : The onion services port to
                              bind to.
                onion       : The onion address of the API
                              server.
                tor_data    : The etemporary Tor data
                              directory.
                tor_process : The clients Tor process to
                              for connection.

            Returns:
                None
        """

        # ~ Initialize the attributes. ~ #
        self.onion_port = 9090
        self.onion = "iockbh2qzuob2syjgqlk6xkmgse3rnylqr7llakxf3rn7bpxgtctmfid.onion" # Obtain dynamically.
        self.tor_data = tempfile.mkdtemp()
        self.tor_process = self.start_client()

        # ~ Setup the socket for connection. ~ #
        socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", self.onion_port, rdns=True)
        socket.socket = socks.socksocket

    def start_client(self) -> sp.Popen:
        """
            ~ Start the clients Tor process. ~

            Variables:
                tor_process : The Tor process service.

            Returns:
                Process : A process that runs the Tor
                          service.
        """

        # ~ Attempt to launch the Tor process. ~ #
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

    def send_request(self, action: str, content: str, client_hash: str) -> str:
        """
            ~ Send a request to the API server. ~

            Arguments:
                action      : The cryptographic action to
                              take.
                content     : The content to run the action
                              on.
                client_hash : The clients hahs to use for
                              cryptography.

            Variables:
                sock     : The clients socket to connect to
                           the server.
                nonce    : The unique nonce for
                           authorization.
                payload  : The cryptographic payload to
                           process.
                response : The final response from the API
                           server.
                    
            Returns:
                String : The result of the cryptographic
                         action on the content.
        """

        # ~ Create and setup the socket. ~ #
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect((self.onion, 80))
        sock.send(client_hash.encode('utf-8'))

        # ~ Obtain the nonce and send the cryptographic ~ #
        # ~ payload, receive the response and close the ~ #
        # ~ connection.                                 ~ #
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


class LocalCryptograph:
    def __init__(self):
        self.key_path = Path( "~/.hydro/device.key").expanduser()
        self._key = self._get_or_create_persistent_key()

    def _get_or_create_persistent_key(self) -> bytes:
        if self.key_path.exists():
            # Read the existing key
            with open(self.key_path, "rb") as f:
                return base64.b64decode(f.read())
        
        # Ensure parent directory exists with secure permissions
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate a cryptographically secure 256-bit AES key
        raw_key = AESGCM.generate_key(bit_length=256)
        
        # Write the key to disk with strict user-only read/write permissions (0600)
        with open(self.key_path, "wb") as f:
            os.chmod(self.key_path, 0o600)
            f.write(base64.b64encode(raw_key))
            
        return raw_key

    def encrypt(self, content: str) -> str:
        rand_nonce = os.urandom(12)
        aesgcm = AESGCM(self._key)
        ciphertext = aesgcm.encrypt(rand_nonce, content.encode('utf-8'), None)
        payload = rand_nonce + ciphertext
        return base64.b64encode(payload).decode('utf-8')

    def decrypt(self, content: str) -> str:
        payload = base64.b64decode(content.encode('utf-8'))
        rand_nonce = payload[:12]
        ciphertext = payload[12:]
        aesgcm = AESGCM(self._key)
        decrypted_bytes = aesgcm.decrypt(rand_nonce, ciphertext, None)
        return decrypted_bytes.decode('utf-8')

# ~ Main test. ~ #
if __name__ == '__main__':
    pass_clinet = PasswordClient()
    local_cryptographer = LocalCryptograph()

    try:
        client_hash = ClientHash().client_hash
        safe_pass = local_cryptographer.encrypt("TestPass123")
        print(f"Local Encrypted: {safe_pass}")
        enc_pass = pass_clinet.send_request("encrypt", safe_pass, client_hash)
        print(f"API Encrypted: {enc_pass}")
        dec_pass = pass_clinet.send_request("decrypt", enc_pass, client_hash)
        print(f"Server Decrypted: {dec_pass}")
        plain_pass = local_cryptographer.decrypt(dec_pass)
        print(f"Plaintext: {plain_pass}")

    except Exception as e:
        print(f"Connection error: {e}")

    finally:
        if pass_clinet.tor_process:
            pass_clinet.tor_process.kill()
