from __future__ import annotations

import asyncio
from asyncio import BaseTransport
import binascii
import hashlib
import json
import logging
from typing import Callable

from construct import Adapter, Bytes, Checksum, Const, Int16ub, Int32ub, RawCopy, Struct
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from roborock.roborock_future import RoborockFuture

_LOGGER = logging.getLogger(__name__)


class RoborockProtocol(asyncio.DatagramProtocol):
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.transport: BaseTransport | None = None
        self.queue = RoborockFuture(0)

    def datagram_received(self, data, _):
        broadcast_message = BroadcastMessage.parse(data)
        self.queue.resolve((json.loads(broadcast_message.message.value.payload), None))
        self.close()

    async def discover(self):
        loop = asyncio.get_event_loop()
        self.transport, _ = await loop.create_datagram_endpoint(lambda: self, local_addr=("0.0.0.0", 58866))
        (response, exception) = await self.queue.async_get(self.timeout)
        if exception is not None:
            raise exception
        return response

    def close(self):
        self.transport.close() if self.transport else None


class Utils:
    """This class is adapted from the original xpn.py code by gst666."""

    @staticmethod
    def verify_token(token: bytes):
        """Checks if the given token is of correct type and length."""
        if not isinstance(token, bytes):
            raise TypeError("Token must be bytes")
        if len(token) != 16:
            raise ValueError("Wrong token length")

    @staticmethod
    def ensure_bytes(msg: bytes | str) -> bytes:
        if isinstance(msg, str):
            return msg.encode()
        return msg

    @staticmethod
    def encode_timestamp(_timestamp: int) -> bytes:
        hex_value = f"{_timestamp:x}".zfill(8)
        return "".join(list(map(lambda idx: hex_value[idx], [5, 6, 3, 7, 1, 2, 0, 4]))).encode()

    @staticmethod
    def md5(data: bytes) -> bytes:
        """Calculates a md5 hashsum for the given bytes object."""
        checksum = hashlib.md5()  # nosec
        checksum.update(data)
        return checksum.digest()

    @staticmethod
    def encrypt(plaintext: bytes, token: bytes) -> bytes:
        """Encrypt plaintext with a given token.

        :param bytes plaintext: Plaintext (json) to encrypt
        :param bytes token: Token to use
        :return: Encrypted bytes
        """
        if not isinstance(plaintext, bytes):
            raise TypeError("plaintext requires bytes")
        Utils.verify_token(token)
        cipher = AES.new(token, AES.MODE_ECB)
        if plaintext:
            plaintext = pad(plaintext, AES.block_size)
            return cipher.encrypt(plaintext)
        return plaintext

    @staticmethod
    def decrypt(ciphertext: bytes, token: bytes) -> bytes:
        """Decrypt ciphertext with a given token.

        :param bytes ciphertext: Ciphertext to decrypt
        :param bytes token: Token to use
        :return: Decrypted bytes object
        """
        if not isinstance(ciphertext, bytes):
            raise TypeError("ciphertext requires bytes")
        if ciphertext:
            Utils.verify_token(token)

            aes_key = token
            decipher = AES.new(aes_key, AES.MODE_ECB)
            return unpad(decipher.decrypt(ciphertext), AES.block_size)
        return ciphertext

    @staticmethod
    def crc(data: bytes) -> int:
        """Gather bytes for checksum calculation."""
        return binascii.crc32(data)

    @staticmethod
    def get_length(x) -> int:
        """Return total packet length."""
        datalen = x._.data.length  # type: int
        return datalen + 32

    @staticmethod
    def is_hello(x) -> bool:
        """Return if packet is a hello packet."""
        # not very nice, but we know that hellos are 32b of length
        val = x.get("length", x.header.value["length"])

        return val == 32


class EncryptionAdapter(Adapter):
    """Adapter to handle communication encryption."""

    def __init__(self, token_func: Callable, subcon):
        super().__init__(subcon)
        self.token_func = token_func
        self.flagbuildnone = True

    def _build(self, obj, stream, context, path):
        obj2 = self._encode(obj, context, path)
        return self.subcon._build(obj2, stream, context, path)

    def _encode(self, obj, context, path):
        """Encrypt the given payload with the token stored in the context.

        :param obj: JSON object to encrypt
        """
        token = self.token_func(context)
        encrypted = Utils.encrypt(obj, token)
        return encrypted

    def _decode(self, obj, context, path):
        """Decrypts the given payload with the token stored in the context."""
        token = self.token_func(context)
        decrypted = Utils.decrypt(obj, token)
        return decrypted


BROADCAST_TOKEN = "qWKYcdQWrbm9hPqe".encode()

BroadcastMessage = Struct(
    "message"
    / RawCopy(
        Struct(
            "version" / Const(b"1.0"),
            "seq" / Int32ub,
            "protocol" / Int16ub,
            "payload_len" / Int16ub,
            "payload" / EncryptionAdapter(lambda ctx: BROADCAST_TOKEN, Bytes(lambda ctx: ctx.payload_len)),
        )
    ),
    "checksum" / Checksum(Int32ub, Utils.crc, lambda ctx: ctx.message.data),
)
