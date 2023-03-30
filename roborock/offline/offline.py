import asyncio
import base64
import binascii
import json
import math
import secrets
import struct
import time

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad

from roborock import RoborockException
from roborock.api import md5bin, encode_timestamp
from roborock.offline.socket_listener import RoborockSocketListener
from roborock.typing import RoborockCommand

local_ip = "<device_ip>"
local_key = "<device_localkey>"

salt = "TXdfu$jyZ#TZHsg4"
seq = 1
random = 4711
request_id = 10000
counter = 1
endpoint = "abc"
nonce = secrets.token_bytes(16).hex().upper()

secured_prefix = 199
get_prefix = 119
app_prefix = 135
set_prefix = 151


async def send_command(
        method: RoborockCommand, params: list = None
):
    timestamp = math.floor(time.time())
    _request_id = request_id + 1
    inner = {
        "id": _request_id,
        "method": method,
        "params": params or [],
        "security": {
            "endpoint": endpoint,
            "nonce": nonce,
        }
    }
    payload = json.dumps(
        {
            "dps": {"101": json.dumps(inner, separators=(",", ":"))},
            "t": timestamp,
        },
        separators=(",", ":"),
    ).encode()
    print(f"id={_request_id} Requesting method {method} with {params}")
    _prefix = secured_prefix
    return await _send_msg_raw(timestamp, _prefix, payload)


async def _send_msg_raw(timestamp: int, prefix: int, payload: bytes):
    protocol = 4
    aes_key = md5bin(encode_timestamp(timestamp) + local_key + salt)
    cipher = AES.new(aes_key, AES.MODE_ECB)
    encrypted = cipher.encrypt(pad(payload, AES.block_size))
    encrypted_len = len(encrypted)
    msg = struct.pack(
        f"!I3sIIIHH{encrypted_len}s",
        prefix,
        "1.0".encode(),
        seq,
        random,
        timestamp,
        protocol,
        encrypted_len,
        encrypted,
    )
    crc32 = binascii.crc32(msg[4:])
    msg += struct.pack("!I", crc32)
    print(f"Requesting with prefix {prefix} and payload {payload}")
    # Send the command to the Roborock device
    return await listener.send_message(msg)


def _decode_msg(msg):
    prefix = int.from_bytes(msg[:4], 'big')
    msg = msg[4:]
    if msg[0:3] != "1.0".encode():
        raise RoborockException("Unknown protocol version")
    crc32 = binascii.crc32(msg[: len(msg) - 4])
    if len(msg) == 17 or len(msg) == 21:
        [version, _seq, _random, timestamp, protocol] = struct.unpack(
            "!3sIIIH", msg[0:17]
        )
        resp1 = {
            "version": version,
            "timestamp": timestamp,
            "protocol": protocol,
        }
        print(f"Response with prefix {prefix} and payload {resp1}")
        return resp1
    [version, _seq, _random, timestamp, protocol, payload_len] = struct.unpack(
        "!3sIIIHH", msg[0:19]
    )
    [payload, expected_crc32] = struct.unpack_from(f"!{payload_len}sI", msg, 19)
    if crc32 != expected_crc32:
        raise RoborockException(f"Wrong CRC32 {crc32}, expected {expected_crc32}")

    aes_key = md5bin(encode_timestamp(timestamp) + local_key + salt)
    decipher = AES.new(aes_key, AES.MODE_ECB)
    decrypted_payload = decipher.decrypt(payload)
    if len(decrypted_payload) > 0:
        decrypted_payload = unpad(decipher.decrypt(payload), AES.block_size)
    resp2 = {
        "version": version,
        "timestamp": timestamp,
        "protocol": protocol,
        "payload": decrypted_payload,
    }
    print(f"Response with prefix {prefix} and payload {resp2}")
    return resp2


listener = RoborockSocketListener(local_ip, asyncio.get_event_loop(), _decode_msg)
listener.connect()


async def main():
    response = await send_command(RoborockCommand.GET_STATUS)
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
