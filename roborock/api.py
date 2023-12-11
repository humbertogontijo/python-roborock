"""The Roborock api."""

from __future__ import annotations

import asyncio
import base64
import dataclasses
import hashlib
import hmac
import json
import logging
import math
import secrets
import struct
import time
from collections.abc import Callable, Coroutine
from random import randint
from typing import Any, TypeVar, final

import aiohttp

from .code_mappings import RoborockDockTypeCode
from .command_cache import CacheableAttribute, CommandType, RoborockAttribute, find_cacheable_attribute, get_cache_map
from .containers import (
    ChildLockStatus,
    CleanRecord,
    CleanSummary,
    Consumable,
    DeviceData,
    DnDTimer,
    DustCollectionMode,
    FlowLedStatus,
    HomeData,
    HomeDataRoom,
    ModelStatus,
    MultiMapsList,
    NetworkInfo,
    ProductResponse,
    RoborockBase,
    RoomMapping,
    RRiot,
    S7MaxVStatus,
    ServerTimer,
    SmartWashParams,
    Status,
    UserData,
    ValleyElectricityTimer,
    WashTowelMode,
)
from .exceptions import (
    RoborockAccountDoesNotExist,
    RoborockException,
    RoborockInvalidCode,
    RoborockInvalidCredentials,
    RoborockInvalidEmail,
    RoborockInvalidUserAgreement,
    RoborockMissingParameters,
    RoborockNoUserAgreement,
    RoborockTimeout,
    RoborockTooFrequentCodeRequests,
    RoborockUrlException,
    UnknownMethodError,
    VacuumError,
)
from .protocol import Utils
from .roborock_future import RoborockFuture
from .roborock_message import (
    ROBOROCK_DATA_CONSUMABLE_PROTOCOL,
    ROBOROCK_DATA_STATUS_PROTOCOL,
    RoborockDataProtocol,
    RoborockMessage,
    RoborockMessageProtocol,
)
from .roborock_typing import DeviceProp, DockSummary, RoborockCommand
from .util import RepeatableTask, RoborockLoggerAdapter, get_running_loop_or_create_one, unpack_list

_LOGGER = logging.getLogger(__name__)
KEEPALIVE = 60
COMMANDS_SECURED = [
    RoborockCommand.GET_MAP_V1,
    RoborockCommand.GET_MULTI_MAP,
]
RT = TypeVar("RT", bound=RoborockBase)
WASH_N_FILL_DOCK = [
    RoborockDockTypeCode.empty_wash_fill_dock,
    RoborockDockTypeCode.s8_dock,
    RoborockDockTypeCode.p10_dock,
]


def md5hex(message: str) -> str:
    md5 = hashlib.md5()
    md5.update(message.encode())
    return md5.hexdigest()


class PreparedRequest:
    def __init__(self, base_url: str, base_headers: dict | None = None) -> None:
        self.base_url = base_url
        self.base_headers = base_headers or {}

    async def request(self, method: str, url: str, params=None, data=None, headers=None) -> dict:
        _url = "/".join(s.strip("/") for s in [self.base_url, url])
        _headers = {**self.base_headers, **(headers or {})}
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method,
                _url,
                params=params,
                data=data,
                headers=_headers,
            ) as resp:
                return await resp.json()


EVICT_TIME = 60


class AttributeCache:
    def __init__(self, attribute: RoborockAttribute, api: RoborockClient):
        self.attribute = attribute
        self.api = api
        self.attribute = attribute
        self.task = RepeatableTask(self.api.event_loop, self._async_value, EVICT_TIME)
        self._value: Any = None
        self._mutex = asyncio.Lock()
        self.unsupported: bool = False

    @property
    def value(self):
        return self._value

    async def _async_value(self):
        if self.unsupported:
            return None
        try:
            self._value = await self.api._send_command(self.attribute.get_command)
        except UnknownMethodError as err:
            # Limit the amount of times we call unsupported methods
            self.unsupported = True
            raise err
        return self._value

    async def async_value(self):
        async with self._mutex:
            if self._value is None:
                return await self.task.reset()
            return self._value

    def stop(self):
        self.task.cancel()

    async def update_value(self, params):
        if self.attribute.set_command is None:
            raise RoborockException(f"{self.attribute.attribute} have no set command")
        response = await self.api._send_command(self.attribute.set_command, params)
        await self._async_value()
        return response

    async def add_value(self, params):
        if self.attribute.add_command is None:
            raise RoborockException(f"{self.attribute.attribute} have no add command")
        response = await self.api._send_command(self.attribute.add_command, params)
        await self._async_value()
        return response

    async def close_value(self, params=None):
        if self.attribute.close_command is None:
            raise RoborockException(f"{self.attribute.attribute} have no close command")
        response = await self.api._send_command(self.attribute.close_command, params)
        await self._async_value()
        return response

    async def refresh_value(self):
        await self._async_value()


@dataclasses.dataclass
class ListenerModel:
    protocol_handlers: dict[RoborockDataProtocol, list[Callable[[Status | Consumable], None]]]
    cache: dict[CacheableAttribute, AttributeCache]


class RoborockClient:
    _listeners: dict[str, ListenerModel] = {}

    def __init__(self, endpoint: str, device_info: DeviceData, queue_timeout: int = 4) -> None:
        self.event_loop = get_running_loop_or_create_one()
        self.device_info = device_info
        self._endpoint = endpoint
        self._nonce = secrets.token_bytes(16)
        self._waiting_queue: dict[int, RoborockFuture] = {}
        self._last_device_msg_in = self.time_func()
        self._last_disconnection = self.time_func()
        self.keep_alive = KEEPALIVE
        self._diagnostic_data: dict[str, dict[str, Any]] = {}
        self._logger = RoborockLoggerAdapter(device_info.device.name, _LOGGER)
        self.cache: dict[CacheableAttribute, AttributeCache] = {
            cacheable_attribute: AttributeCache(attr, self) for cacheable_attribute, attr in get_cache_map().items()
        }
        self.is_available: bool = True
        self.queue_timeout = queue_timeout
        self._status_type: type[Status] = ModelStatus.get(self.device_info.model, S7MaxVStatus)
        if device_info.device.duid not in self._listeners:
            self._listeners[device_info.device.duid] = ListenerModel({}, self.cache)
        self.listener_model = self._listeners[device_info.device.duid]

    def __del__(self) -> None:
        self.release()

    @property
    def status_type(self) -> type[Status]:
        """Gets the status type for this device"""
        return self._status_type

    def release(self):
        self.sync_disconnect()
        [item.stop() for item in self.cache.values()]

    @property
    def diagnostic_data(self) -> dict:
        return self._diagnostic_data

    @property
    def time_func(self) -> Callable[[], float]:
        try:
            # Use monotonic clock if available
            time_func = time.monotonic
        except AttributeError:
            time_func = time.time
        return time_func

    async def async_connect(self):
        raise NotImplementedError

    def sync_disconnect(self) -> Any:
        raise NotImplementedError

    async def async_disconnect(self) -> Any:
        raise NotImplementedError

    def on_message_received(self, messages: list[RoborockMessage]) -> None:
        try:
            self._last_device_msg_in = self.time_func()
            for data in messages:
                protocol = data.protocol
                if data.payload and protocol in [
                    RoborockMessageProtocol.RPC_RESPONSE,
                    RoborockMessageProtocol.GENERAL_REQUEST,
                ]:
                    payload = json.loads(data.payload.decode())
                    for data_point_number, data_point in payload.get("dps").items():
                        if data_point_number == "102":
                            data_point_response = json.loads(data_point)
                            request_id = data_point_response.get("id")
                            queue = self._waiting_queue.get(request_id)
                            if queue and queue.protocol == protocol:
                                error = data_point_response.get("error")
                                if error:
                                    queue.resolve(
                                        (
                                            None,
                                            VacuumError(
                                                error.get("code"),
                                                error.get("message"),
                                            ),
                                        )
                                    )
                                else:
                                    result = data_point_response.get("result")
                                    if isinstance(result, list) and len(result) == 1:
                                        result = result[0]
                                    queue.resolve((result, None))
                        else:
                            try:
                                data_protocol = RoborockDataProtocol(int(data_point_number))
                                self._logger.debug(f"Got device update for {data_protocol.name}: {data_point}")
                                if data_protocol in ROBOROCK_DATA_STATUS_PROTOCOL:
                                    if data_protocol not in self.listener_model.protocol_handlers:
                                        self._logger.debug(
                                            f"Got status update({data_protocol.name}) before get_status was called."
                                        )
                                        return
                                    value = self.listener_model.cache[CacheableAttribute.status].value
                                    value[data_protocol.name] = data_point
                                    status = self._status_type.from_dict(value)
                                    for listener in self.listener_model.protocol_handlers.get(data_protocol, []):
                                        listener(status)
                                elif data_protocol in ROBOROCK_DATA_CONSUMABLE_PROTOCOL:
                                    if data_protocol not in self.listener_model.protocol_handlers:
                                        self._logger.debug(
                                            f"Got consumable update({data_protocol.name})"
                                            + "before get_consumable was called."
                                        )
                                        return
                                    value = self.listener_model.cache[CacheableAttribute.consumable].value
                                    value[data_protocol.name] = data_point
                                    consumable = Consumable.from_dict(value)
                                    for listener in self.listener_model.protocol_handlers.get(data_protocol, []):
                                        listener(consumable)
                                return
                            except ValueError:
                                self._logger.warning(
                                    f"Got listener data for {data_point_number}, data: {data_point}. "
                                    f"This lets us update data quicker, please open an issue "
                                    f"at https://github.com/humbertogontijo/python-roborock/issues"
                                )

                                pass
                            dps = {data_point_number: data_point}
                            self._logger.debug(f"Got unknown data point {dps}")
                elif data.payload and protocol == RoborockMessageProtocol.MAP_RESPONSE:
                    payload = data.payload[0:24]
                    [endpoint, _, request_id, _] = struct.unpack("<8s8sH6s", payload)
                    if endpoint.decode().startswith(self._endpoint):
                        try:
                            decrypted = Utils.decrypt_cbc(data.payload[24:], self._nonce)
                        except ValueError as err:
                            raise RoborockException("Failed to decode %s for %s", data.payload, data.protocol) from err
                        decompressed = Utils.decompress(decrypted)
                        queue = self._waiting_queue.get(request_id)
                        if queue:
                            if isinstance(decompressed, list):
                                decompressed = decompressed[0]
                            queue.resolve((decompressed, None))
                else:
                    queue = self._waiting_queue.get(data.seq)
                    if queue:
                        queue.resolve((data.payload, None))
        except Exception as ex:
            self._logger.exception(ex)

    def on_connection_lost(self, exc: Exception | None) -> None:
        self._last_disconnection = self.time_func()
        self._logger.info("Roborock client disconnected")
        if exc is not None:
            self._logger.warning(exc)

    def should_keepalive(self) -> bool:
        now = self.time_func()
        # noinspection PyUnresolvedReferences
        if now - self._last_disconnection > self.keep_alive**2 and now - self._last_device_msg_in > self.keep_alive:
            return False
        return True

    async def validate_connection(self) -> None:
        if not self.should_keepalive():
            await self.async_disconnect()
        await self.async_connect()

    async def _wait_response(self, request_id: int, queue: RoborockFuture) -> tuple[Any, VacuumError | None]:
        try:
            (response, err) = await queue.async_get(self.queue_timeout)
            if response == "unknown_method":
                raise UnknownMethodError("Unknown method")
            return response, err
        except (asyncio.TimeoutError, asyncio.CancelledError):
            raise RoborockTimeout(f"id={request_id} Timeout after {self.queue_timeout} seconds") from None
        finally:
            self._waiting_queue.pop(request_id, None)

    def _async_response(
        self, request_id: int, protocol_id: int = 0
    ) -> Coroutine[Any, Any, tuple[Any, VacuumError | None]]:
        queue = RoborockFuture(protocol_id)
        self._waiting_queue[request_id] = queue
        return self._wait_response(request_id, queue)

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

    async def send_message(self, roborock_message: RoborockMessage):
        raise NotImplementedError

    async def _send_command(
        self,
        method: RoborockCommand | str,
        params: list | dict | int | None = None,
    ):
        raise NotImplementedError

    @final
    async def send_command(
        self,
        method: RoborockCommand | str,
        params: list | dict | int | None = None,
        return_type: type[RT] | None = None,
    ) -> RT:
        cacheable_attribute_result = find_cacheable_attribute(method)

        cache = None
        command_type = None
        if cacheable_attribute_result is not None:
            cache = self.cache[cacheable_attribute_result.attribute]
            command_type = cacheable_attribute_result.type

        response: Any = None
        if cache is not None and command_type == CommandType.GET:
            response = await cache.async_value()
        else:
            response = await self._send_command(method, params)
            if cache is not None and command_type == CommandType.CHANGE:
                await cache.refresh_value()

        if return_type:
            return return_type.from_dict(response)
        return response

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
            _LOGGER.warning("Clean record was of a new type, please submit an issue request: %s", record)
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

    def add_listener(
        self, protocol: RoborockDataProtocol, listener: Callable, cache: dict[CacheableAttribute, AttributeCache]
    ) -> None:
        self.listener_model.cache = cache
        if protocol not in self.listener_model.protocol_handlers:
            self.listener_model.protocol_handlers[protocol] = []
        self.listener_model.protocol_handlers[protocol].append(listener)

    def remove_listener(self, protocol: RoborockDataProtocol, listener: Callable) -> None:
        self.listener_model.protocol_handlers[protocol].remove(listener)

    async def get_from_cache(self, key: CacheableAttribute) -> AttributeCache | None:
        val = self.cache.get(key)
        if val is not None:
            return await val.async_value()
        return None


class RoborockApiClient:
    def __init__(self, username: str, base_url=None) -> None:
        """Sample API Client."""
        self._username = username
        self._default_url = "https://euiot.roborock.com"
        self.base_url = base_url
        self._device_identifier = secrets.token_urlsafe(16)

    async def _get_base_url(self) -> str:
        if not self.base_url:
            url_request = PreparedRequest(self._default_url)
            response = await url_request.request(
                "post",
                "/api/v1/getUrlByEmail",
                params={"email": self._username, "needtwostepauth": "false"},
            )
            if response is None:
                raise RoborockUrlException("get url by email returned None")
            response_code = response.get("code")
            if response_code != 200:
                if response_code == 2003:
                    raise RoborockInvalidEmail("Your email was incorrectly formatted.")
                elif response_code == 1001:
                    raise RoborockMissingParameters(
                        "You are missing parameters for this request, are you sure you " "entered your username?"
                    )
                raise RoborockUrlException(response.get("error"))
            response_data = response.get("data")
            if response_data is None:
                raise RoborockUrlException("response does not have 'data'")
            self.base_url = response_data.get("url")
        return self.base_url

    def _get_header_client_id(self):
        md5 = hashlib.md5()
        md5.update(self._username.encode())
        md5.update(self._device_identifier.encode())
        return base64.b64encode(md5.digest()).decode()

    def _get_hawk_authentication(self, rriot: RRiot, url: str) -> str:
        timestamp = math.floor(time.time())
        nonce = secrets.token_urlsafe(6)
        prestr = ":".join(
            [
                rriot.u,
                rriot.s,
                nonce,
                str(timestamp),
                hashlib.md5(url.encode()).hexdigest(),
                "",
                "",
            ]
        )
        mac = base64.b64encode(hmac.new(rriot.h.encode(), prestr.encode(), hashlib.sha256).digest()).decode()
        return f'Hawk id="{rriot.u}", s="{rriot.s}", ts="{timestamp}", nonce="{nonce}", mac="{mac}"'

    async def request_code(self) -> None:
        base_url = await self._get_base_url()
        header_clientid = self._get_header_client_id()
        code_request = PreparedRequest(base_url, {"header_clientid": header_clientid})

        code_response = await code_request.request(
            "post",
            "/api/v1/sendEmailCode",
            params={
                "username": self._username,
                "type": "auth",
            },
        )
        if code_response is None:
            raise RoborockException("Failed to get a response from send email code")
        response_code = code_response.get("code")
        if response_code != 200:
            if response_code == 2008:
                raise RoborockAccountDoesNotExist("Account does not exist - check your login and try again.")
            elif response_code == 9002:
                raise RoborockTooFrequentCodeRequests("You have attempted to request too many codes. Try again later")
            else:
                raise RoborockException(f"{code_response.get('msg')} - response code: {code_response.get('code')}")

    async def pass_login(self, password: str) -> UserData:
        base_url = await self._get_base_url()
        header_clientid = self._get_header_client_id()

        login_request = PreparedRequest(base_url, {"header_clientid": header_clientid})
        login_response = await login_request.request(
            "post",
            "/api/v1/login",
            params={
                "username": self._username,
                "password": password,
                "needtwostepauth": "false",
            },
        )
        if login_response is None:
            raise RoborockException("Login response is none")
        if login_response.get("code") != 200:
            raise RoborockException(f"{login_response.get('msg')} - response code: {login_response.get('code')}")
        user_data = login_response.get("data")
        if not isinstance(user_data, dict):
            raise RoborockException("Got unexpected data type for user_data")
        return UserData.from_dict(user_data)

    async def pass_login_v3(self, password: str) -> UserData:
        """Seemingly it follows the format below, but password is encrypted in some manner.
        # login_response = await login_request.request(
        #     "post",
        #     "/api/v3/auth/email/login",
        #     params={
        #         "email": self._username,
        #         "password": password,
        #         "twoStep": 1,
        #         "version": 0
        #     },
        # )
        """
        raise NotImplementedError("Pass_login_v3 has not yet been implemented")

    async def code_login(self, code) -> UserData:
        base_url = await self._get_base_url()
        header_clientid = self._get_header_client_id()

        login_request = PreparedRequest(base_url, {"header_clientid": header_clientid})
        login_response = await login_request.request(
            "post",
            "/api/v1/loginWithCode",
            params={
                "username": self._username,
                "verifycode": code,
                "verifycodetype": "AUTH_EMAIL_CODE",
            },
        )
        if login_response is None:
            raise RoborockException("Login request response is None")
        response_code = login_response.get("code")
        if response_code != 200:
            if response_code == 2018:
                raise RoborockInvalidCode("Invalid code - check your code and try again.")
            if response_code == 3009:
                raise RoborockNoUserAgreement("You must accept the user agreement in the Roborock app to continue.")
            if response_code == 3006:
                raise RoborockInvalidUserAgreement(
                    "User agreement must be accepted again - or you are attempting to use the Mi Home app account."
                )
            raise RoborockException(f"{login_response.get('msg')} - response code: {response_code}")
        user_data = login_response.get("data")
        if not isinstance(user_data, dict):
            raise RoborockException("Got unexpected data type for user_data")
        return UserData.from_dict(user_data)

    async def _get_home_id(self, user_data: UserData):
        base_url = await self._get_base_url()
        header_clientid = self._get_header_client_id()
        home_id_request = PreparedRequest(base_url, {"header_clientid": header_clientid})
        home_id_response = await home_id_request.request(
            "get",
            "/api/v1/getHomeDetail",
            headers={"Authorization": user_data.token},
        )
        if home_id_response is None:
            raise RoborockException("home_id_response is None")
        if home_id_response.get("code") != 200:
            if home_id_response.get("code") == 2010:
                raise RoborockInvalidCredentials(
                    f"Invalid credentials ({home_id_response.get('msg')}) - check your login and try again."
                )
            raise RoborockException(f"{home_id_response.get('msg')} - response code: {home_id_response.get('code')}")

        return home_id_response["data"].get("rrHomeId")

    async def get_home_data(self, user_data: UserData) -> HomeData:
        rriot = user_data.rriot
        if rriot is None:
            raise RoborockException("rriot is none")
        home_id = await self._get_home_id(user_data)
        if rriot.r.a is None:
            raise RoborockException("Missing field 'a' in rriot reference")
        home_request = PreparedRequest(
            rriot.r.a,
            {
                "Authorization": self._get_hawk_authentication(rriot, f"/user/homes/{str(home_id)}"),
            },
        )
        home_response = await home_request.request("get", "/user/homes/" + str(home_id))
        if not home_response.get("success"):
            raise RoborockException(home_response)
        home_data = home_response.get("result")
        if isinstance(home_data, dict):
            return HomeData.from_dict(home_data)
        else:
            raise RoborockException("home_response result was an unexpected type")

    async def get_home_data_v2(self, user_data: UserData) -> HomeData:
        """This is the same as get_home_data, but uses a different endpoint and includes non-robotic vacuums."""
        rriot = user_data.rriot
        if rriot is None:
            raise RoborockException("rriot is none")
        home_id = await self._get_home_id(user_data)
        if rriot.r.a is None:
            raise RoborockException("Missing field 'a' in rriot reference")
        home_request = PreparedRequest(
            rriot.r.a,
            {
                "Authorization": self._get_hawk_authentication(rriot, "/v2/user/homes/" + str(home_id)),
            },
        )
        home_response = await home_request.request("get", "/v2/user/homes/" + str(home_id))
        if not home_response.get("success"):
            raise RoborockException(home_response)
        home_data = home_response.get("result")
        if isinstance(home_data, dict):
            return HomeData.from_dict(home_data)
        else:
            raise RoborockException("home_response result was an unexpected type")

    async def get_rooms(self, user_data: UserData, home_id: int | None = None) -> list[HomeDataRoom]:
        rriot = user_data.rriot
        if rriot is None:
            raise RoborockException("rriot is none")
        if home_id is None:
            home_id = await self._get_home_id(user_data)
        if rriot.r.a is None:
            raise RoborockException("Missing field 'a' in rriot reference")
        room_request = PreparedRequest(
            rriot.r.a,
            {
                "Authorization": self._get_hawk_authentication(rriot, "/v2/user/homes/" + str(home_id)),
            },
        )
        room_response = await room_request.request("get", f"/user/homes/{str(home_id)}/rooms" + str(home_id))
        if not room_response.get("success"):
            raise RoborockException(room_response)
        rooms = room_response.get("result")
        if isinstance(rooms, list):
            output_list = []
            for room in rooms:
                output_list.append(HomeDataRoom.from_dict(room))
            return output_list
        else:
            raise RoborockException("home_response result was an unexpected type")

    async def get_products(self, user_data: UserData) -> ProductResponse:
        """Gets all products and their schemas, good for determining status codes and model numbers."""
        base_url = await self._get_base_url()
        header_clientid = self._get_header_client_id()
        product_request = PreparedRequest(base_url, {"header_clientid": header_clientid})
        product_response = await product_request.request(
            "get",
            "/api/v3/product",
            headers={"Authorization": user_data.token},
        )
        if product_response is None:
            raise RoborockException("home_id_response is None")
        if product_response.get("code") != 200:
            raise RoborockException(f"{product_response.get('msg')} - response code: {product_response.get('code')}")
        result = product_response.get("data")
        if isinstance(result, dict):
            return ProductResponse.from_dict(result)
        raise RoborockException("product result was an unexpected type")
