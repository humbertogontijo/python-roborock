from __future__ import annotations

import binascii
import hashlib
import json
import math
import struct
import time
from dataclasses import dataclass
from random import randint

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from .exceptions import RoborockException
from .roborock_typing import RoborockCommand


def md5bin(message: str) -> bytes:
    md5 = hashlib.md5()
    md5.update(message.encode())
    return md5.digest()


def encode_timestamp(_timestamp: int) -> str:
    hex_value = f"{_timestamp:x}".zfill(8)
    return "".join(list(map(lambda idx: hex_value[idx], [5, 6, 3, 7, 1, 2, 0, 4])))


salt = "TXdfu$jyZ#TZHsg4"

AP_CONFIG = 1
SOCK_DISCOVERY = 2


@dataclass
class RoborockMessage:
    protocol: int
    payload: bytes
    seq: int = randint(100000, 999999)
    prefix: bytes = b""
    version: bytes = b"1.0"
    random: int = randint(10000, 99999)
    timestamp: int = math.floor(time.time())

    def get_request_id(self) -> int | None:
        protocol = self.protocol
        if protocol in [4, 101, 102]:
            payload = json.loads(self.payload.decode())
            for data_point_number, data_point in payload.get("dps").items():
                if data_point_number in ["101", "102"]:
                    data_point_response = json.loads(data_point)
                    return data_point_response.get("id")
        return None

    def get_method(self) -> RoborockCommand | None:
        protocol = self.protocol
        if protocol in [4, 5, 101, 102]:
            payload = json.loads(self.payload.decode())
            for data_point_number, data_point in payload.get("dps").items():
                if data_point_number in ["101", "102"]:
                    data_point_response = json.loads(data_point)
                    return data_point_response.get("method")
        return None

    def get_params(self) -> list | dict | None:
        protocol = self.protocol
        if protocol in [4, 101, 102]:
            payload = json.loads(self.payload.decode())
            for data_point_number, data_point in payload.get("dps").items():
                if data_point_number in ["101", "102"]:
                    data_point_response = json.loads(data_point)
                    return data_point_response.get("params")
        return None


class RoborockParser:
    @staticmethod
    def encode(roborock_messages: list[RoborockMessage] | RoborockMessage, local_key: str):
        if isinstance(roborock_messages, RoborockMessage):
            roborock_messages = [roborock_messages]

        msg = b""
        for roborock_message in roborock_messages:
            if len(roborock_message.prefix) not in [0, 4]:
                raise RoborockException("Invalid prefix")
            aes_key = md5bin(encode_timestamp(roborock_message.timestamp) + local_key + salt)
            cipher = AES.new(aes_key, AES.MODE_ECB)
            payload = roborock_message.payload
            if payload:
                payload = pad(roborock_message.payload, AES.block_size)
            encrypted = cipher.encrypt(payload)
            encrypted_len = len(encrypted)
            _msg = struct.pack(
                f"!3sIIIHH{encrypted_len}s",
                "1.0".encode(),
                roborock_message.seq,
                roborock_message.random,
                roborock_message.timestamp,
                roborock_message.protocol,
                encrypted_len,
                encrypted,
            )
            if payload:
                crc32 = binascii.crc32(_msg)
                _msg += struct.pack("!I", crc32)
            else:
                _msg += b"\x00\x00"
            msg += roborock_message.prefix + _msg
        return msg

    @staticmethod
    def decode(msg: bytes, local_key: str, index=0) -> tuple[list[RoborockMessage], bytes]:
        prefix = b""
        original_index = index
        if len(msg) - index < 17:
            # broken message
            return [], msg[original_index:]

        if msg[index + 4 : index + 7] == "1.0".encode():
            prefix = msg[index : index + 4]
            index += 4
        elif msg[index : index + 3] != "1.0".encode():
            raise RoborockException(f"Unknown protocol version {msg[0:3]!r}")
        message_size = len(msg) - index
        if message_size == 17:
            [version, request_id, random, timestamp, protocol] = struct.unpack_from("!3sIIIH", msg, index)
            return [
                RoborockMessage(
                    prefix=prefix,
                    version=version,
                    seq=request_id,
                    random=random,
                    timestamp=timestamp,
                    protocol=protocol,
                    payload=b"",
                )
            ], b""

        if len(msg) - index < 19:
            # broken message
            return [], msg[original_index:]

        _format = "!3sIIIHH"
        [
            version,
            request_id,
            random,
            timestamp,
            protocol,
            payload_len,
        ] = struct.unpack_from(_format, msg, index)
        format_size = struct.calcsize(_format)
        index += format_size

        if payload_len + index + 4 > len(msg):
            ## broken message
            return [], msg[original_index:]

        payload = b""
        if payload_len == 0:
            index += 2
        else:
            [payload, expected_crc32] = struct.unpack_from(f"!{payload_len}sI", msg, index)
            crc32 = binascii.crc32(msg[index - format_size : index + payload_len])
            index += 4 + payload_len
            if crc32 != expected_crc32:
                raise RoborockException(f"Wrong CRC32 {crc32}, expected {expected_crc32}")

        if payload:
            aes_key = md5bin(encode_timestamp(timestamp) + local_key + salt)
            decipher = AES.new(aes_key, AES.MODE_ECB)
            payload = unpad(decipher.decrypt(payload), AES.block_size)

        [structs, remaining] = RoborockParser.decode(msg, local_key, index) if index < len(msg) else ([], b"")

        return [
            RoborockMessage(
                prefix=prefix,
                version=version,
                seq=request_id,
                random=random,
                timestamp=timestamp,
                protocol=protocol,
                payload=payload,
            )
        ] + structs, remaining
