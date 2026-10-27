
"""
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Programmer: Aaron "A.J" Cassell. (@BrotatoBoi)
              Program Name: Secure Pass.
Description: A custom password encryption API server for 
             saving sensitive data to file.

File: nonce_handler.py             Date: 2026/10/19
                Version: 0.1.1-2026.10.27
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
import base64
from datetime import datetime
from threading import Lock, Thread
from time import sleep
import uuid


class NonceDatabase:
    """
        ~ The Database to handle what Nonce is valid and
          protect against malicious actors. ~

        Methods:
            __init__      : Initialize the database object.
            get_nonce     : Obtain random nonce for an
                            action.
            nonce_expired : Check if the nonce is expired.
            valid_nonce   : Ensure the nonce is valid to
                            use.
            cleanup_loop  : Remove used and expired nonces.
            use_nonce     : Mark a nonce as used to clean
                            it.
    """

    def __init__(self) -> None:
        """
            ~ Initialize the nonce database, and start the
              cleanup thread. ~

            Attributes:
                nonces     : A dictionary of existing
                             nonces.
                nonce_lock : Thread lock to ensure clean
                             nonce manipulation.
                ttl        : Time to live in seconds.

            Returns:
                None
        """

        # ~ Initialize the attributes. ~ #
        self.nonces = dict()
        self.nonce_lock = Lock()
        self.ttl = 10

        # ~ Start the cleanup thread. ~ #
        Thread(target=self.cleanup_loop, daemon=True).start()

    def get_nonce(self, hash: str) -> bytes:
        """
            ~ Obtain a nonce to send to the requesting
              client. ~

            Arguments:
                hash : A hash string created by the client.

            Variables:
                merged      : Merged the received hash with
                              a random V4 UUID.
                merged_base : Merged value encoded as
                              base64.
                nonce       : The created nonce from base64
                              value.
                timestamp   : The creation time for the
                              nonce.

            Returns:
                Bytes : The final nonce as bytes to send
                        via socket. 
        """

        # ~ Simple algorithm to generate nonce. ~ #
        merged = hash + str(uuid.uuid4())
        merged_base = base64.b64encode(merged.encode('utf-8'))
        nonce = merged_base[69:]
        timestamp = datetime.now()

        # ~ Update the nonce with its thread lock. ~ #
        with self.nonce_lock:
            self.nonces[nonce.decode('utf-8')] = {"created": timestamp, "is_used": False}

        return nonce

    def nonce_expired(self, nonce: str) -> bool:
        """
            ~ Check if a nonce has been expired. ~

            Arguments:
                nonce : A string of the nonce to verify.

            Variables:
                created   : Time of the nonces creation.
                current   : The current time to compare.
                deltatime : The amount of time that passed.

            Returns:
                Bool : The state of the nonces expiry.
        """

        # ~ Obtain the time variables. ~ #
        created = self.nonces[nonce].get('created')
        current = datetime.now()
        deltatime = current - created

        # ~ Check if nonce is older than 30 seconds. ~ #
        if deltatime.total_seconds() > 30:
            return True

        return False

    def valid_nonce(self, nonce: str) -> bool:
        """
            ~ Ensure the nonce being used is valid. ~

            Arguments:
                nonce : The nonce to verify validity.

            Returns:
                Bool : State of nonce being valid.
        """

        # ~ Check if the nonce exists. ~ #
        if nonce not in list(self.nonces.keys()):
            print("Nonce does not exist!")
            return False
        
        # ~ Check if the nonce is used. ~ #
        if self.nonces[nonce].get('is_used'):
            print("Nonce is already used!")
            return False
        
        # ~ Check if the nonce has expired. ~ #
        if self.nonce_expired(nonce):
            print("Nonce is expired!")
            return False

        return True
    
    def cleanup_loop(self) -> None:
        """
            ~ Endless cleanup loop to remove dead nonces. ~

            Variables:
                current    : The current time to check
                             against creation.
                nonce      : The nonce that is being
                             processed.
                nonce_data : The data of the nonce being
                             checked.
                            
            Returns:
                None
        """

        while True:
            # ~ Sleep for a bit then check time. ~ #
            sleep(self.ttl)
            current = datetime.now()

            # ~ Check each nonce and remove dead ones. ~ #
            with self.nonce_lock:
                for nonce, nonce_data in self.nonces:
                    if not self.valid_nonce(nonce):
                        del self.nonces[nonce]

    def use_nonce(self, nonce: str) -> None:
        """
            ~ Render the nonce as used to avoid reuse. ~

            Arguments:
                nonce : A string representing the nonce to
                        use.

            Returns:
                None
        """

        # ~ Update the used status of the nonce. ~ #
        with self.nonce_lock:
            if nonce in list(self.nonces.keys()):
                self.nonces[nonce]['is_used'] = True

