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
from threading import Thread

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
            ~ Initialize the API server. ~

            Attributes:
                nonce_handler : Object to handle nonces.
                sec_pass : Object to handle password cryptography
                key_file : Location of the servers secret key.
                onion_port : The port of the onion service.
                server_port : The servers port to binf the onion service to.
                server_host : Localhost to connect the onion server.
                sock : The socket object to listen for connections.
                tor_process : The executed Tor process.

            Returns:
                None
        """

        # ~ Declare attributes. ~ #
        self.nonce_handler = NonceDatabase()
        self.sec_pass = SecurePass(self.nonce_handler)
        self.key_file = Path("~/.hydro/secret.key").expanduser()
        self.onion_port = 80
        self.server_port = 5000
        self.server_host = '127.0.0.1'
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tor_process = None

        # ~ Start the API server. ~ #
        self.start()

    def start(self) -> None:
        """
            ~ Start the API server. ~

            Variables:
                controller : The stem controller object.
                err        : Caught error to notify.

            Returns:
                None
        """

        # ~ Attempt to start the server. ~ #
        try:
            with Controller.from_port(port=9051) as controller:
                controller.authenticate()

                self.load_key(controller)
                self.start_listening()

        # ~ An error has occurred! ~ #
        except Exception as err:
            print(f"Tor Controller Error: {err}")

    def load_key(self, controller: Controller) -> None:
        """
            ~ Load or create a secret key for the API
              server. ~

            Arguments:
                controller : The controller object to use.

            Variables:
                key_file    : The secret keys file.
                full_key    : The full content of the key.
                key_type    : The secret keys type.
                key_content : The content of the key.
                ephemeral   : An ephemeral hidden service
                              instance.

            Returns:
                None
        """

        # ~ Load the key if the file exists. ~ #
        if self.key_file.exists():
            with open(self.key_file, "r") as key_file:
                full_key = key_file.read().strip()

            # ~ Break up the key into type and content. ~ #
            if ":" in full_key:
                key_type, key_content = full_key.split(":", 1)
            else:
                key_type, key_content = ("ED25519-V3", full_key)

            print("Loading existing key...")

        else:
            key_type, key_content = ("NEW", "ED25519-V3")
            print("Created a new key!")

        # ~ Initialize the hidden service. ~ #
        ephemeral = controller.create_ephemeral_hidden_service(
            {self.onion_port: self.server_port},
            key_type=key_type,
            key_content=key_content,
            await_publication=True
        )

        # ~ Create a new secret key. ~ #
        if key_type == "NEW":
            self.key_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.key_file, "w") as key_file:
                key_file.write(ephemeral.private_key)

            print(f"Saved the key to file: {self.key_file}")

        print(f"Listening on address: {ephemeral.service_id}.onion")

    def start_listening(self) -> None:
        """
            ~ Begin listening for connections and requests
              to the server using threaded concurrency. ~
        """
        # ~ Set up listening for the server. ~ #
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.server_host, self.server_port))
        self.sock.listen(5)

        print("Listening for connections...")

        # ~ Start listening for connections. ~ #
        while True:
            try:
                client, address = self.sock.accept()
                
                # Spawn a separate thread for each client connection 
                # so the main loop can immediately accept new connections.
                client_thread = Thread(target=self.handle_client, args=(client,))
                client_thread.daemon = True
                client_thread.start()

            except Exception as err:
                print(f"Server socket accept error: {err}")
                break

        # ~ Close the server socket on exit. ~ #
        self.sock.close()
        if self.tor_process:
            self.tor_process.kill()

    def handle_client(self, client: socket.socket) -> None:
        """
            ~ Handle an individual client connection safely 
              without crashing the main server loop. ~
        """
        try:
            client.settimeout(15) # Prevent hanging connections forever
            raw_hash = client.recv(2048)

            if not raw_hash:
                client.close()
                return
                
            client_hash_str = raw_hash.decode('utf-8').strip()

            # --- RATE LIMIT CHECK ---
            # if self.nonce_handler.check_rate_limit(client_hash_str):
            #     print(f"[!] Rate limit exceeded for client hash: {client_hash_str[:8]}...")
            #     client.close()
            #     return

            # ~ Create a nonce and send it to the client. ~ #
            nonce = self.nonce_handler.get_nonce(raw_hash.decode('utf-8'))
            client.send(nonce)
            raw_data = client.recv(2048)
            
            if not raw_data:
                client.close()
                return

            # ~ Attempt to load the data. ~ #
            try:
                data = json.loads(raw_data.decode('utf-8'))
            except json.JSONDecodeError:
                client.close()
                return 

            if not data or not all(k in data for k in ('content', 'hash', 'nonce', 'action')):
                client.close()
                return

            # ~ Run the cryptographic data. ~ #
            payload = (data['content'], data['hash'], data['nonce'])

            if data.get('action') == "encrypt":
                enc_pass = self.sec_pass.encrypt_password(*payload)
                client.sendall(enc_pass.encode('utf-8'))
            
            elif data.get('action') == "decrypt":
                dec_pass = self.sec_pass.decrypt_password(*payload)
                client.sendall(dec_pass.encode('utf-8'))

        except socket.timeout:
            print("Client connection timed out.")
        except Exception as err:
            print(f"Error handling client request: {err}")
        finally:
            client.close()


# ~ Execute the main server. ~ #
if __name__ == '__main__':
    Server()
