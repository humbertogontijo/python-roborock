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
    RPC_REQUEST = 101
    RPC_RESPONSE = 102
    MAP_RESPONSE = 301


class RoborockDataProtocol(RoborockEnum):
    ERROR_CODE = 120
    STATE = 121
    BATTERY = 122
    FAN_POWER = 123
    WATER_BOX_MODE = 124
    MAIN_BRUSH_WORK_TIME = 125
    SIDE_BRUSH_WORK_TIME = 126
    FILTER_WORK_TIME = 127
    ADDITIONAL_PROPS = 128
    TASK_COMPLETE = 130
    TASK_CANCEL_LOW_POWER = 131
    TASK_CANCEL_IN_MOTION = 132
    CHARGE_STATUS = 133
    DRYING_STATUS = 134

    @classmethod
    def _missing_(cls: type[RoborockEnum], key) -> RoborockEnum:
        raise ValueError("%s not a valid key for Data Protocol", key)


class RoborockDyadDataProtocol(RoborockEnum):
    DRYING_STATUS = 134
    START = 200
    STATUS = 201
    SELF_CLEAN_MODE = 202
    SELF_CLEAN_LEVEL = 203
    WARM_LEVEL = 204
    CLEAN_MODE = 205
    SUCTION = 206
    WATER_LEVEL = 207
    BRUSH_SPEED = 208
    POWER = 209
    COUNTDOWN_TIME = 210
    AUTO_SELF_CLEAN_SET = 212
    AUTO_DRY = 213
    MESH_LEF = 214
    BRUSH_LEFT = 215
    ERROR = 216
    MESH_RESET = 218
    BRUSH_RESET = 219
    VOLUME_SET = 221
    STAND_LOCK_AUTO_RUN = 222
    AUTO_SELF_CLEAN_SET_MODE = 223
    AUTO_DRY_MODE = 224
    SILENT_DRY_DURATION = 225
    SILENT_MODE = 226
    SILENT_MODE_START_TIME = 227
    SILENT_MODE_END_TIME = 228
    RECENT_RUN_TIMe = 229
    TOTAL_RUN_TIME = 230
    FEATURE_INFO = 235
    RECOVER_SETTINGS = 236
    DRY_COUNTDOWN = 237
    ID_QUERY = 10000
    F_C = 10001
    SCHEDULE_TASK = 10002
    SND_SWITCH = 10003
    SND_STATE = 10004
    PRODUCT_INFO = 10005
    PRIVACY_INFO = 10006
    OTA_NFO = 10007
    RPC_REQUEST = 10101
    RPC_RESPONSE = 10102


ROBOROCK_DATA_STATUS_PROTOCOL = [
    RoborockDataProtocol.ERROR_CODE,
    RoborockDataProtocol.STATE,
    RoborockDataProtocol.BATTERY,
    RoborockDataProtocol.FAN_POWER,
    RoborockDataProtocol.WATER_BOX_MODE,
    RoborockDataProtocol.CHARGE_STATUS,
]

ROBOROCK_DATA_CONSUMABLE_PROTOCOL = [
    RoborockDataProtocol.MAIN_BRUSH_WORK_TIME,
    RoborockDataProtocol.SIDE_BRUSH_WORK_TIME,
    RoborockDataProtocol.FILTER_WORK_TIME,
]


@dataclass
class MessageRetry:
    method: str
    retry_id: int


@dataclass
class RoborockMessage:
    protocol: RoborockMessageProtocol
    payload: bytes | None = None
    seq: int = randint(100000, 999999)
    version: bytes = b"1.0"
    random: int = randint(10000, 99999)
    timestamp: int = math.floor(time.time())
    message_retry: MessageRetry | None = None

    def get_request_id(self) -> int | None:
        if self.payload:
            payload = json.loads(self.payload.decode())
            for data_point_number, data_point in payload.get("dps").items():
                if data_point_number in ["101", "102"]:
                    data_point_response = json.loads(data_point)
                    return data_point_response.get("id")
        return None

    def get_retry_id(self) -> int | None:
        if self.message_retry:
            return self.message_retry.retry_id
        return self.get_request_id()

    def get_method(self) -> str | None:
        if self.message_retry:
            return self.message_retry.method
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
