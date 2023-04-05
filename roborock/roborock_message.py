from __future__ import annotations

import binascii
import hashlib
import json
import math
import struct
import time
from dataclasses import dataclass
from random import randint
from typing import Optional

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from roborock.typing import RoborockCommand

from roborock.exceptions import RoborockException


def md5bin(message: str) -> bytes:
    md5 = hashlib.md5()
    md5.update(message.encode())
    return md5.digest()


def encode_timestamp(_timestamp: int) -> str:
    hex_value = f"{_timestamp:x}".zfill(8)
    return "".join(list(map(lambda idx: hex_value[idx], [5, 6, 3, 7, 1, 2, 0, 4])))


salt = "TXdfu$jyZ#TZHsg4"


@dataclass
class RoborockMessage:
    protocol: int
    payload: bytes
    seq: Optional[int] = randint(100000, 999999)
    prefix: Optional[bytes] = b''
    version: Optional[bytes] = b'1.0'
    random: Optional[int] = randint(10000, 99999)
    timestamp: Optional[int] = math.floor(time.time())

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
        if protocol in [4, 101, 102]:
            payload = json.loads(self.payload.decode())
            for data_point_number, data_point in payload.get("dps").items():
                if data_point_number in ["101", "102"]:
                    data_point_response = json.loads(data_point)
                    return data_point_response.get("method")
        return None

    def get_params(self) -> list | None:
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

        msg = b''
        for roborock_message in roborock_messages:
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
                encrypted
            )
            if payload:
                crc32 = binascii.crc32(_msg)
                _msg += struct.pack("!I", crc32)
            else:
                _msg += b'\x00\x00'
            msg += roborock_message.prefix + _msg
        return msg

    @staticmethod
    def decode(msg: bytes, local_key: str, index=0) -> tuple[list[RoborockMessage], bytes]:
        prefix = None
        original_index = index
        if len(msg) - index < 17:
            ## broken message
            return [], msg[original_index:]

        if msg[index + 4:index + 7] == "1.0".encode():
            prefix = msg[index:index + 4]
            index += 4
        elif msg[index:index + 3] != "1.0".encode():
            raise RoborockException(f"Unknown protocol version {msg[0:3]}")

        if len(msg) - index in [17]:
            [version, request_id, random, timestamp, protocol] = struct.unpack_from(
                "!3sIIIH", msg, index
            )
            return [RoborockMessage(
                prefix=prefix,
                version=version,
                seq=request_id,
                random=random,
                timestamp=timestamp,
                protocol=protocol,
                payload=b''
            )], b''

        if len(msg) - index < 19:
            ## broken message
            return [], msg[original_index:]

        [version, request_id, random, timestamp, protocol, payload_len] = struct.unpack_from(
            "!3sIIIHH", msg, index
        )
        index += 19

        if payload_len + index + 4 > len(msg):
            ## broken message
            return [], msg[original_index:]

        payload = b''
        if payload_len == 0:
            index += 2
        else:
            [payload, expected_crc32] = struct.unpack_from(f"!{payload_len}sI", msg, index)
            crc32 = binascii.crc32(msg[index - 19: index + payload_len])
            index += 4 + payload_len
            if crc32 != expected_crc32:
                raise RoborockException(f"Wrong CRC32 {crc32}, expected {expected_crc32}")

        if payload:
            aes_key = md5bin(encode_timestamp(timestamp) + local_key + salt)
            decipher = AES.new(aes_key, AES.MODE_ECB)
            payload = unpad(decipher.decrypt(payload), AES.block_size)

        [structs, remaining] = RoborockParser.decode(msg, local_key, index) if index < len(msg) else ([], b'')

        return [RoborockMessage(
            prefix=prefix,
            version=version,
            seq=request_id,
            random=random,
            timestamp=timestamp,
            protocol=protocol,
            payload=payload
        )] + structs, remaining
