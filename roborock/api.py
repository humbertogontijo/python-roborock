"""The Roborock api."""

from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json
import logging
import secrets
import struct
import time
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar, final

from .command_cache import CacheableAttribute, CommandType, RoborockAttribute, find_cacheable_attribute, get_cache_map
from .containers import (
    Consumable,
    DeviceData,
    ModelStatus,
    RoborockBase,
    S7MaxVStatus,
    Status,
)
from .exceptions import (
    RoborockException,
    RoborockTimeout,
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
from .roborock_typing import RoborockCommand
from .util import RepeatableTask, RoborockLoggerAdapter, get_running_loop_or_create_one

_LOGGER = logging.getLogger(__name__)
KEEPALIVE = 60
RT = TypeVar("RT", bound=RoborockBase)


def md5hex(message: str) -> str:
    md5 = hashlib.md5()
    md5.update(message.encode())
    return md5.hexdigest()


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

    async def async_release(self):
        await self.async_disconnect()
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
