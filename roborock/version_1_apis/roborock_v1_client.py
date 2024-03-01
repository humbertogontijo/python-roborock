import asyncio
import json
import math
import time
from collections.abc import Coroutine
from random import randint
from typing import Any

from roborock import DeviceProp, DockSummary, RoborockCommand, RoborockDockTypeCode
from roborock.api import RoborockClient
from roborock.command_cache import CacheableAttribute
from roborock.containers import (
    ChildLockStatus,
    CleanRecord,
    CleanSummary,
    Consumable,
    DeviceData,
    DnDTimer,
    DustCollectionMode,
    FlowLedStatus,
    ModelStatus,
    MultiMapsList,
    NetworkInfo,
    RoomMapping,
    S7MaxVStatus,
    ServerTimer,
    SmartWashParams,
    Status,
    ValleyElectricityTimer,
    WashTowelMode,
)
from roborock.util import unpack_list

COMMANDS_SECURED = [
    RoborockCommand.GET_MAP_V1,
    RoborockCommand.GET_MULTI_MAP,
]

WASH_N_FILL_DOCK = [
    RoborockDockTypeCode.empty_wash_fill_dock,
    RoborockDockTypeCode.s8_dock,
    RoborockDockTypeCode.p10_dock,
]


class RoborockV1Client(RoborockClient):
    def __init__(self, device_info: DeviceData, cache, logger, endpoint: str):
        super().__init__(endpoint, device_info)
        self._status_type: type[Status] = ModelStatus.get(device_info.model, S7MaxVStatus)
        self.cache = cache
        self._logger = logger

    @property
    def status_type(self) -> type[Status]:
        """Gets the status type for this device"""
        return self._status_type

    async def get_status(self) -> Status:
        data = self._status_type.from_dict(await self.cache[CacheableAttribute.status].async_value())
        if data is None:
            return self._status_type()
        return data

    async def get_dnd_timer(self) -> DnDTimer | None:
        return DnDTimer.from_dict(await self.cache[CacheableAttribute.dnd_timer].async_value())

    async def get_valley_electricity_timer(self) -> ValleyElectricityTimer | None:
        return ValleyElectricityTimer.from_dict(
            await self.cache[CacheableAttribute.valley_electricity_timer].async_value()
        )

    async def get_clean_summary(self) -> CleanSummary | None:
        clean_summary: dict | list | int = await self.send_command(RoborockCommand.GET_CLEAN_SUMMARY)
        if isinstance(clean_summary, dict):
            return CleanSummary.from_dict(clean_summary)
        elif isinstance(clean_summary, list):
            clean_time, clean_area, clean_count, records = unpack_list(clean_summary, 4)
            return CleanSummary(
                clean_time=clean_time,
                clean_area=clean_area,
                clean_count=clean_count,
                records=records,
            )
        elif isinstance(clean_summary, int):
            return CleanSummary(clean_time=clean_summary)
        return None

    async def get_clean_record(self, record_id: int) -> CleanRecord | None:
        record: dict | list = await self.send_command(RoborockCommand.GET_CLEAN_RECORD, [record_id])
        if isinstance(record, dict):
            return CleanRecord.from_dict(record)
        elif isinstance(record, list):
            # There are still a few unknown variables in this.
            begin, end, duration, area = unpack_list(record, 4)
            return CleanRecord(begin=begin, end=end, duration=duration, area=area)
        else:
            self._logger.warning("Clean record was of a new type, please submit an issue request: %s", record)
            return None

    async def get_consumable(self) -> Consumable:
        data = Consumable.from_dict(await self.cache[CacheableAttribute.consumable].async_value())
        if data is None:
            return Consumable()
        return data

    async def get_wash_towel_mode(self) -> WashTowelMode | None:
        return WashTowelMode.from_dict(await self.cache[CacheableAttribute.wash_towel_mode].async_value())

    async def get_dust_collection_mode(self) -> DustCollectionMode | None:
        return DustCollectionMode.from_dict(await self.cache[CacheableAttribute.dust_collection_mode].async_value())

    async def get_smart_wash_params(self) -> SmartWashParams | None:
        return SmartWashParams.from_dict(await self.cache[CacheableAttribute.smart_wash_params].async_value())

    async def get_dock_summary(self, dock_type: RoborockDockTypeCode) -> DockSummary:
        """Gets the status summary from the dock with the methods available for a given dock.

        :param dock_type: RoborockDockTypeCode"""
        commands: list[
            Coroutine[
                Any,
                Any,
                DustCollectionMode | WashTowelMode | SmartWashParams | None,
            ]
        ] = [self.get_dust_collection_mode()]
        if dock_type in WASH_N_FILL_DOCK:
            commands += [
                self.get_wash_towel_mode(),
                self.get_smart_wash_params(),
            ]
        [dust_collection_mode, wash_towel_mode, smart_wash_params] = unpack_list(
            list(await asyncio.gather(*commands)), 3
        )  # type: DustCollectionMode, WashTowelMode | None, SmartWashParams | None # type: ignore

        return DockSummary(dust_collection_mode, wash_towel_mode, smart_wash_params)

    async def get_prop(self) -> DeviceProp | None:
        """Gets device general properties."""
        # Mypy thinks that each one of these is typed as a union of all the others. so we do type ignore.
        status, clean_summary, consumable = await asyncio.gather(
            *[
                self.get_status(),
                self.get_clean_summary(),
                self.get_consumable(),
            ]
        )  # type: Status, CleanSummary, Consumable # type: ignore
        last_clean_record = None
        if clean_summary and clean_summary.records and len(clean_summary.records) > 0:
            last_clean_record = await self.get_clean_record(clean_summary.records[0])
        dock_summary = None
        if status and status.dock_type is not None and status.dock_type != RoborockDockTypeCode.no_dock:
            dock_summary = await self.get_dock_summary(status.dock_type)
        if any([status, clean_summary, consumable]):
            return DeviceProp(
                status,
                clean_summary,
                consumable,
                last_clean_record,
                dock_summary,
            )
        return None

    async def get_multi_maps_list(self) -> MultiMapsList | None:
        return await self.send_command(RoborockCommand.GET_MULTI_MAPS_LIST, return_type=MultiMapsList)

    async def get_networking(self) -> NetworkInfo | None:
        return await self.send_command(RoborockCommand.GET_NETWORK_INFO, return_type=NetworkInfo)

    async def get_room_mapping(self) -> list[RoomMapping] | None:
        """Gets the mapping from segment id -> iot id. Only works on local api."""
        mapping: list = await self.send_command(RoborockCommand.GET_ROOM_MAPPING)
        if isinstance(mapping, list):
            return [
                RoomMapping(segment_id=segment_id, iot_id=iot_id)  # type: ignore
                for segment_id, iot_id in [unpack_list(room, 2) for room in mapping if isinstance(room, list)]
            ]
        return None

    async def get_child_lock_status(self) -> ChildLockStatus:
        """Gets current child lock status."""
        return ChildLockStatus.from_dict(await self.cache[CacheableAttribute.child_lock_status].async_value())

    async def get_flow_led_status(self) -> FlowLedStatus:
        """Gets current flow led status."""
        return FlowLedStatus.from_dict(await self.cache[CacheableAttribute.flow_led_status].async_value())

    async def get_sound_volume(self) -> int | None:
        """Gets current volume level."""
        return await self.cache[CacheableAttribute.sound_volume].async_value()

    async def get_server_timer(self) -> list[ServerTimer]:
        """Gets current server timer."""
        server_timers = await self.cache[CacheableAttribute.server_timer].async_value()
        if server_timers:
            if isinstance(server_timers[0], list):
                return [ServerTimer(*server_timer) for server_timer in server_timers]
            return [ServerTimer(*server_timers)]
        return []

    def _get_payload(
        self,
        method: RoborockCommand | str,
        params: list | dict | int | None = None,
        secured=False,
    ):
        timestamp = math.floor(time.time())
        request_id = randint(10000, 32767)
        inner = {
            "id": request_id,
            "method": method,
            "params": params or [],
        }
        if secured:
            inner["security"] = {
                "endpoint": self._endpoint,
                "nonce": self._nonce.hex().lower(),
            }
        payload = bytes(
            json.dumps(
                {
                    "dps": {"101": json.dumps(inner, separators=(",", ":"))},
                    "t": timestamp,
                },
                separators=(",", ":"),
            ).encode()
        )
        return request_id, timestamp, payload
