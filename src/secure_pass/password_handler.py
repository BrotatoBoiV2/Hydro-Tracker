"""
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Programmer: Aaron "A.J" Cassell. (@BrotatoBoi)
              Program Name: Secure Pass.
Description: A custom password encryption API server for 
             saving sensitive data to file.

File: password_handler.py        Date: 2026/10/19
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
import os

# ~ Third-Party Imports. ~ #
from argon2.low_level import hash_secret_raw, Type
from dotenv import load_dotenv
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class SecurePass:
    """
        ~ Object that handles cryptography for passwords. ~

        Methods:
            __init__         : Initialize the password
                               cryptograper.
            encrypt_password : Encrypt password into hash.
            decrypt_password : Decrypt hash into password.
            create_key       : Create a cryptography key.
    """

    ### NOTE: Need to make the errors more robust.
    ### NOTE: Want to make en/de-cryption a single smart function.

    def __init__(self, nonce_handler: object) -> None:
        """
            ~ Initialize the password securing module. ~

            Arguments:
                nonce_handler : The original nonce handling
                                object.
            
            Attributes:
                nonce_handler : Inherits from the argument.
                salted        : The salt obtained form the
                                dotenv file. 

            Returns:
                None
        """

        # ~ Load the dotenv file. ~ #
        load_dotenv()

        # ~ Initialize the variables. ~ #
        self.nonce_handler = nonce_handler
        self.salted = str(os.getenv("SALTY")).encode('utf-8')

    def encrypt_password(self, password: str, hash: str, nonce: str) -> str:
        """
            ~ Encrypt the password into a hash. ~

            Arguments:
                password : The password to encrypt.
                hash     : The clients hash for key
                           creation.
                nonce    : The unique nonce for
                           verification.

            Variables:
                random_bytes : 16 random bytes to use.
                rand_nonce   : 12 random bytes for a nonce.
                key          : The generated key.
                aesgcm       : An instance of the AEGCM
                               cipher with the created key.
                cipher       : The encrypted string cipher.
                pass_bytes   : The final mashed password.

            Returns:
                String : Either a base64 encrypted version
                         of the password bytes or an error.
        """

        # ~ Throw an error if nonce is invalid. ~ #
        if not self.nonce_handler.valid_nonce(nonce):
            return "ERROR"

        # ~ Create the variables. ~ #
        random_bytes = os.urandom(16)
        rand_nonce = os.urandom(12)
        key = self.create_key(hash, random_bytes)
        aesgcm = AESGCM(key)
        cipher = aesgcm.encrypt(rand_nonce, password.encode('utf-8'), None)
        pass_bytes = random_bytes + rand_nonce + cipher

        # ~ Use the nonce. ~ #
        self.nonce_handler.use_nonce(nonce)

        return base64.b64encode(pass_bytes).decode('utf-8')

    def decrypt_password(self, password: str, hash: str, nonce: str) -> str:
        """
            ~ Decrypt the password into a hash. ~

            Arguments:
                password : The password to decrypt.
                hash     : The clients hash for key
                           creation.
                nonce    : The unique nonce for
                           verification.

            Variables:
                pass_bytes   : The password to decrypt.
                random_bytes : First 16 bytes of password.
                rand_nonce   : Next 12 bytes of password.
                cipher       : Final bytes of the password.
                key          : The generated key.
                aesgcm       : An instance of the AEGCM
                               cipher with the created key.
                decrypted    : The decrypted password.

            Returns:
                String : Either a base64 decrypted version
                         of the password bytes or an error.
        """

        # ~ Throw an error if nonce is invalid. ~ #
        if not self.nonce_handler.valid_nonce(nonce):
            return "ERROR"

        # ~ Create the variables. ~ #
        pass_bytes = base64.b64decode(password.encode('utf-8'))
        random_bytes = pass_bytes[0:16]
        rand_nonce = pass_bytes[16:28]
        cipher = pass_bytes[28:]
        key = self.create_key(hash, random_bytes)
        aesgcm = AESGCM(key)
        decrypted = aesgcm.decrypt(rand_nonce, cipher, None)
        
        # ~ Use the nonce. ~ #
        self.nonce_handler.use_nonce(nonce)

        return decrypted.decode('utf-8')

    def create_key(self, hash: str, random_bytes: bytes) -> bytes:
        """
            ~ Create the key for cryptography. ~

            Arguments:
                hash         : The clients hash string.
                random_bytes : Random bytes for the key.
            
            Variables:
                secret : Merged random bytes with the hash.

            Returns:
                Bytes : The secret raw hash created with
                        the special secret.
        """

        # ~ Create the key. ~ #
        secret = random_bytes + hash.encode('utf-8')
        return = hash_secret_raw(
            secret=secret,
            salt=self.salted,
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            type=Type.ID
        )
        
