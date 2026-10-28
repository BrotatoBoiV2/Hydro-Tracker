
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


class ClientHash:
    """
        ~ Handle the clients local hash. ~

        Methods:
            __init__        : Initialize the hash.
            get_machine_id  : Obtain the ID from the
                              machine.
            get_disk_serial : Obtain the disks serial
                              number.
            create_hash     : Create clients full local
                              hash.
    """

    def __init__(self) -> None:
        """
            ~ Initialize the local hash. ~

            Attributes:
                client_hash : The clients final local hash.

            Returns:
                None
        """
        
        # ~ Initialize the attributes. ~ #
        self.client_hash = self.create_hash()

    def get_machine_id(self) -> str:
        """
            ~ Obtain the machines ID. ~

            Variables:
                pathname : The pathname to check for an ID.
                path : The path object of that pathname.

            Returns:
                String : The unique machine ID or a fallback one.
        """

        # ~ Check for the machine ID. ~ #
        for pathname in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
            path = Path(pathname)

            # ~ Return the ID if it exists. ~ #
            if path.exists():
                try:
                    return path.read_text().strip()
                except Exception:
                    continue

        return "FallbackMachineID"

    def get_disk_serial(self) -> str:
        """
            ~ Obtiain the disks serial number. ~

            Variables:
                response : The response of the `lsblk` command.
                serial   : The extracted serial number.
                line     : Each line returned form the command.

            Returns:
                String : Returns the disks serial number or
                         a fallback one.
        """

        # ~ Attempt to obtain the serial number. ~ #
        try:
            response = sp.run(["lsblk", "-n", "-o", "SERIAL"],
                            stdout=sp.PIPE, stderr=sp.PIPE, text=True, check=True)
            serial = [line.strip() for line in response.stdout.split("\n") if line.strip()]
            return serial[0] if serial else "FallbackDiskSerial"

        except Exception:
            return "FallbackDiskSerial"
    
    def create_hash(self) -> str:
        """
            ~ Create the clients local hash. ~ #

            Variables:
                mid : The machines ID.
                dsk : The disks serial number.
                mac : The MAC address.
                final_str : The final hash string

            Returns:
                String : A final hashed version of the
                         final string.
        """

        # ~ Obtain info and create hash string. ~ #
        mid = self.get_machine_id()
        dsk = self.get_disk_serial()
        mac = f"{uuid.getnode():012x}"
        random_str = f"{mid}-{dsk}-{mac}"

        return hashlib.sha256(random_str.encode('utf-8')).hexdigest()


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


# ~ Main test. ~ #
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
