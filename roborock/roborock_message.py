from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from random import randint

from roborock import RoborockEnum


class RoborockMessageProtocol(RoborockEnum):
    HELLO_REQUEST = 0
    HELLO_RESPONSE = 1
    PING_REQUEST = 2
    PING_RESPONSE = 3
    GENERAL_REQUEST = 4
    GENERAL_RESPONSE = 5


@dataclass
class RoborockMessage:
    protocol: int
    payload: bytes | None
    seq: int = randint(100000, 999999)
    version: bytes = b"1.0"
    random: int = randint(10000, 99999)
    timestamp: int = math.floor(time.time())

    def get_request_id(self) -> int | None:
        protocol = self.protocol
        if self.payload and protocol in [4, 101, 102]:
            payload = json.loads(self.payload.decode())
            for data_point_number, data_point in payload.get("dps").items():
                if data_point_number in ["101", "102"]:
                    data_point_response = json.loads(data_point)
                    return data_point_response.get("id")
        return None

    def get_method(self) -> str | None:
        protocol = self.protocol
        if self.payload and protocol in [4, 5, 101, 102]:
            payload = json.loads(self.payload.decode())
            for data_point_number, data_point in payload.get("dps").items():
                if data_point_number in ["101", "102"]:
                    data_point_response = json.loads(data_point)
                    return data_point_response.get("method")
        return None

    def get_params(self) -> list | dict | None:
        protocol = self.protocol
        if self.payload and protocol in [4, 101, 102]:
            payload = json.loads(self.payload.decode())
            for data_point_number, data_point in payload.get("dps").items():
                if data_point_number in ["101", "102"]:
                    data_point_response = json.loads(data_point)
                    return data_point_response.get("params")
        return None
