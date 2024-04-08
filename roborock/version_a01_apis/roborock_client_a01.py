import dataclasses
import json
import typing
from collections.abc import Callable
from datetime import time

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from roborock import DeviceData
from roborock.api import RoborockClient
from roborock.code_mappings import (
    DyadBrushSpeed,
    DyadCleanMode,
    DyadError,
    DyadSelfCleanLevel,
    DyadSelfCleanMode,
    DyadSuction,
    DyadWarmLevel,
    DyadWaterLevel,
    RoborockDyadStateCode,
)
from roborock.containers import DyadProductInfo, DyadSndState
from roborock.roborock_message import (
    RoborockDyadDataProtocol,
    RoborockMessage,
    RoborockMessageProtocol,
)


@dataclasses.dataclass
class DyadProtocolCacheEntry:
    post_process_fn: Callable
    value: typing.Any | None = None


# Right now this cache is not active, it was too much complexity for the initial addition of dyad.
protocol_entries = {
    RoborockDyadDataProtocol.STATUS: DyadProtocolCacheEntry(lambda val: RoborockDyadStateCode(val).name),
    RoborockDyadDataProtocol.SELF_CLEAN_MODE: DyadProtocolCacheEntry(lambda val: DyadSelfCleanMode(val).name),
    RoborockDyadDataProtocol.SELF_CLEAN_LEVEL: DyadProtocolCacheEntry(lambda val: DyadSelfCleanLevel(val).name),
    RoborockDyadDataProtocol.WARM_LEVEL: DyadProtocolCacheEntry(lambda val: DyadWarmLevel(val).name),
    RoborockDyadDataProtocol.CLEAN_MODE: DyadProtocolCacheEntry(lambda val: DyadCleanMode(val).name),
    RoborockDyadDataProtocol.SUCTION: DyadProtocolCacheEntry(lambda val: DyadSuction(val).name),
    RoborockDyadDataProtocol.WATER_LEVEL: DyadProtocolCacheEntry(lambda val: DyadWaterLevel(val).name),
    RoborockDyadDataProtocol.BRUSH_SPEED: DyadProtocolCacheEntry(lambda val: DyadBrushSpeed(val).name),
    RoborockDyadDataProtocol.POWER: DyadProtocolCacheEntry(lambda val: int(val)),
    RoborockDyadDataProtocol.AUTO_DRY: DyadProtocolCacheEntry(lambda val: bool(val)),
    RoborockDyadDataProtocol.MESH_LEFT: DyadProtocolCacheEntry(lambda val: int(360000 - val * 60)),
    RoborockDyadDataProtocol.BRUSH_LEFT: DyadProtocolCacheEntry(lambda val: int(360000 - val * 60)),
    RoborockDyadDataProtocol.ERROR: DyadProtocolCacheEntry(lambda val: DyadError(val).name),
    RoborockDyadDataProtocol.VOLUME_SET: DyadProtocolCacheEntry(lambda val: int(val)),
    RoborockDyadDataProtocol.STAND_LOCK_AUTO_RUN: DyadProtocolCacheEntry(lambda val: bool(val)),
    RoborockDyadDataProtocol.AUTO_DRY_MODE: DyadProtocolCacheEntry(lambda val: bool(val)),
    RoborockDyadDataProtocol.SILENT_DRY_DURATION: DyadProtocolCacheEntry(lambda val: int(val)),  # in minutes
    RoborockDyadDataProtocol.SILENT_MODE: DyadProtocolCacheEntry(lambda val: bool(val)),
    RoborockDyadDataProtocol.SILENT_MODE_START_TIME: DyadProtocolCacheEntry(
        lambda val: time(hour=int(val / 60), minute=val % 60)
    ),  # in minutes since 00:00
    RoborockDyadDataProtocol.SILENT_MODE_END_TIME: DyadProtocolCacheEntry(
        lambda val: time(hour=int(val / 60), minute=val % 60)
    ),  # in minutes since 00:00
    RoborockDyadDataProtocol.RECENT_RUN_TIME: DyadProtocolCacheEntry(
        lambda val: [int(v) for v in val.split(",")]
    ),  # minutes of cleaning in past few days.
    RoborockDyadDataProtocol.TOTAL_RUN_TIME: DyadProtocolCacheEntry(lambda val: int(val)),
    RoborockDyadDataProtocol.SND_STATE: DyadProtocolCacheEntry(lambda val: DyadSndState.from_dict(val)),
    RoborockDyadDataProtocol.PRODUCT_INFO: DyadProtocolCacheEntry(lambda val: DyadProductInfo.from_dict(val)),
}


class RoborockClientA01(RoborockClient):
    def __init__(self, endpoint: str, device_info: DeviceData):
        super().__init__(endpoint, device_info)

    def on_message_received(self, messages: list[RoborockMessage]) -> None:
        for message in messages:
            protocol = message.protocol
            if message.payload and protocol in [
                RoborockMessageProtocol.RPC_RESPONSE,
                RoborockMessageProtocol.GENERAL_REQUEST,
            ]:
                payload = message.payload
                try:
                    payload = unpad(payload, AES.block_size)
                except Exception:
                    continue
                payload_json = json.loads(payload.decode())
                for data_point_number, data_point in payload_json.get("dps").items():
                    data_point_protocol = RoborockDyadDataProtocol(int(data_point_number))
                    if data_point_protocol in protocol_entries:
                        converted_response = protocol_entries[data_point_protocol].post_process_fn(data_point)
                        queue = self._waiting_queue.get(int(data_point_number))
                        if queue and queue.protocol == protocol:
                            queue.resolve((converted_response, None))

    async def update_values(self, dyad_data_protocols: list[RoborockDyadDataProtocol]):
        raise NotImplementedError
