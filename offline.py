import binascii
import json
import math
import socket
import struct
import time

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad

from roborock import RoborockException
from roborock.api import md5bin, encode_timestamp
from roborock.typing import RoborockCommand

local_ip = "<device_ip>"
local_key = "<device_localkey>"

salt = "TXdfu$jyZ#TZHsg4"
seq = 1
random = 4711
request_id = 10000
counter = 1

get_prefix = 119
app_prefix = 135
set_prefix = 151

# example messages out of wireshark
msgs = [
    '00000087312e300000d1d5000198da6424b65900040070772b8ddc5645f5751d58d4a9805c37cc1c607e68d2a1e823c2f228841aed5489ccb0627ae677cea01203261df679d30d987a611e1460668f5aceacd2a4f9a94f95afad0f408768f28cff656e8a37657f831b25e579cea7bdc9b326e91c149012406eb417551668d82f57af0ee6ca113cb4369293',
    '00000087312e300000d1d5000198da6424b65900040070772b8ddc5645f5751d58d4a9805c37cc1c607e68d2a1e823c2f228841aed5489ccb0627ae677cea01203261df679d30d987a611e1460668f5aceacd2a4f9a94f95afad0f408768f28cff656e8a37657f831b25e579cea7bdc9b326e91c149012406eb417551668d82f57af0ee6ca113cb4369293',
    '00000077312e300000dde70001e4206424b65900040060772b8ddc5645f5751d58d4a9805c37ccb34713eb49547bc1b857a234f517d954a53ea8124688f0e58b8653bcaddc26e47a78f5e6e41e0f6af5dedf97599aba599471cc64c5ad7a95648287484963b87530068800ee12c23ce0aece65acb7047c1dcf29df',
    '00000097312e300000bdd0000068736424b65900040080772b8ddc5645f5751d58d4a9805c37cc5913ddddb0a61b3d24be9e857b201181a70bfbeae8768a2b514c9d5c9ff558423c007a32a856e96066c74c5453002cfb7f750c4d9f5c5ad5377bcb95f8298d919aa6968b8c1053a3bc1a2ce7f181d64d988306ad407e0c765a7d19a27ec9255e3fad02f352bab81c012feb8ea0104cd0a6a5218300000087312e300000f1d90001b4746424b65900040070772b8ddc5645f5751d58d4a9805c37ccdf2e18471bebd4bad04eeb563019355614fcc0f7a86a72a302a383c483e13442775c134021aa1f062c690c5e0780edc01e0718befd9e50b030c7cb02459741795a5b74edcf7346d79c045380257c393ecda8d9999868f0c835ad1c3b8730bcdffa0cd9c900000087312e30000187cf00020c2d6424b65900040070772b8ddc5645f5751d58d4a9805c37cc68ba4c061b90da4986b184fc28b8daef01c30401714d39128cf65bf2b74d40469735b3baa56e66c3e9059cb327f1b00c6c8ac4af88cd38b825a6e6c4d91fc6e264f60056fac4a16021160367b8d76981f668b2e2e6d8a60523261bfd046a53c3d58dfead'
]


def send_command(
        ip: str, method: RoborockCommand, params: list = None
):
    timestamp = math.floor(time.time())
    _request_id = request_id + 1
    inner = {
        "id": _request_id,
        "method": method,
        "params": params or [],
    }
    payload = json.dumps(
        {
            "dps": {"101": json.dumps(inner, separators=(",", ":"))},
            "t": timestamp,
        },
        separators=(",", ":"),
    ).encode()
    print(f"id={_request_id} Requesting method {method} with {params}")
    use_prefix = get_prefix
    # if method.startswith("app_"):
    #     use_prefix = app_prefix
    # # elif method.startswith("get_"):
    # #     use_prefix = get_prefix
    # elif method.startswith("set_"):
    #     use_prefix = set_prefix
    response1 = _send_msg_raw(ip, timestamp, use_prefix, payload)
    return _decode_msg(response1)


def _send_msg_raw(ip: str , timestamp: int, prefix: int, payload: bytes):
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
    # Send the command to the Roborock device
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((ip, 58867))
        s.send(msg)
        _response = s.recv(1024)

    return _response


def _decode_msg(msg):
    print(msg[:4])
    msg = msg[4:]
    if msg[0:3] != "1.0".encode():
        raise RoborockException("Unknown protocol version")
    # crc32 = binascii.crc32(msg[: len(msg) - 4])
    if len(msg) == 17:
        [version, _seq, _random, timestamp, protocol] = struct.unpack(
            "!3sIIIH", msg[0:17]
        )
        return {
            "version": version,
            "timestamp": timestamp,
            "protocol": protocol,
        }
    [version, _seq, _random, timestamp, protocol, payload_len] = struct.unpack(
        "!3sIIIHH", msg[0:19]
    )
    [payload, expected_crc32] = struct.unpack_from(f"!{payload_len}sI", msg, 19)
    # if crc32 != expected_crc32:
    #     raise RoborockException(f"Wrong CRC32 {crc32}, expected {expected_crc32}")

    aes_key = md5bin(encode_timestamp(timestamp) + local_key + salt)
    decipher = AES.new(aes_key, AES.MODE_ECB)
    decrypted_payload = unpad(decipher.decrypt(payload), AES.block_size)
    return {
        "version": version,
        "timestamp": timestamp,
        "protocol": protocol,
        "payload": decrypted_payload,
    }

for msg in msgs:
    print(_decode_msg(bytes.fromhex(msg)))

# Parse the response to get the current status of the device
response = send_command(local_ip, RoborockCommand.GET_STATUS)
# 4 = "app_get_init_status"
print(response)
