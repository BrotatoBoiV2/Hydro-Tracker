"""
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Programmer: Aaron "A.J" Cassell. (@BrotatoBoi)
              Program Name: Secure Pass.
Description: A custom password encryption API server for 
             saving sensitive data to file.

File: server.py                         Date: 2026/10/19
                Version: 0.1.0-2026.10.19
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
import socket
from pathlib import Path
import json

# ~ Third-Party Imports. ~ #
from stem.control import Controller

# ~ Custom Imports. ~ #
from password_handler import SecurePass
from nonce_handler import NonceDatabase


class Server:
    """
        ~ Handles the secure pass API server. ~

        Methods:
            __init__         : Initializr the server.
            start            : Start the API server.
            load_key         : Load the server private key.
            start_listenting : Begin listening for clients
                               on the server.
            get_data         : Obtain the data from the client.
    """

    def __init__(self) -> None:
        """

        """

        self.nonce_handler = NonceDatabase()
        self.sec_pass = SecurePass(self.nonce_handler)
        self.key_file = Path("~/.hydro/secret.key").expanduser()
        self.onion_port = 80
        self.server_port = 5000
        self.server_host = '127.0.0.1'
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tor_process = None
        self.start()

    def start(self) -> None:
        """

        """

        try:
            with Controller.from_port(port=9051) as controller:
                controller.authenticate()

                self.load_key(controller)
                self.start_listening()

        except Exception as err:
            print(f"Tor Controller Error: {err}")

    def load_key(self, controller: Controller) -> None:
        """

        """

        if self.key_file.exists():
            with open(self.key_file, "r") as key_file:
                full_key = key_file.read().strip()

            if ":" in full_key:
                key_type, key_content = full_key.split(":", 1)
            else:
                key_type, key_content = ("ED25519-V3", full_key)
            print("Loading existing key...")
        else:
            key_type, key_content = ("NEW", "ED25519-V3")
            print("Created a new key!")

        ephemeral = controller.create_ephemeral_hidden_service(
            {self.onion_port: self.server_port},
            key_type=key_type,
            key_content=key_content,
            await_publication=True
        )

        if key_type == "NEW":
            self.key_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.key_file, "w") as key_file:
                key_file.write(ephemeral.private_key)
            print(f"Saved the key to file: {self.key_file}")

        print(f"Listening on address: {ephemeral.service_id}.onion")

    def start_listening(self) -> None:
        """

        """

        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.server_host, self.server_port))
        self.sock.listen(5)

        print("Listening for connections...")

        while True:
            client, address = self.sock.accept()

            try:
                raw_hash = client.recv(2048)

                if not raw_hash:
                    continue
                    
                nonce = self.nonce_handler.get_nonce(raw_hash.decode('utf-8'))
                client.send(nonce)
                raw_data = client.recv(2048)
                
                if not raw_data:
                    continue

                data = None
                try:
                    data = json.loads(raw_data.decode('utf-8'))
                    print(type(data))

                except json.JSONDecodeError:
                    continue 

                if not data:
                    continue

                payload = (data['content'], data['hash'], data['nonce'])

                if data.get('action') == "encrypt":
                    enc_pass = self.sec_pass.encrypt_password(*payload)
                    client.sendall(enc_pass.encode('utf-8'))
                
                elif data.get('action') == "decrypt":
                    dec_pass = self.sec_pass.decrypt_password(*payload)
                    client.sendall(dec_pass.encode('utf-8'))

                else:
                    continue

            except:
                self.sock.close()

                if self.tor_process:
                    self.tor_process.kill()  

    def get_data(self) -> dict:
        """

        """

        raw_hash = client.recv(2048)
        print(raw_hash)

        if not raw_hash:
            return dict()

        nonce = self.nonce_handler.get_nonce(raw_hash.decode('utf-8'))
        client.send(nonce)
        raw_data = client.recv(2048)

        if not raw_data:
            return dict()

        try:
            data = json.loads(raw_data.decode('utf-8'))
        
        except json.JSONDecodeError:
            return dict()        

        return data


# ~ Execute the main server. ~ #
if __name__ == '__main__':
    Server()
