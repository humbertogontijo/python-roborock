from __future__ import annotations

import asyncio
import base64
import logging
import threading
import uuid
from asyncio import Lock, Task
from typing import Any
from urllib.parse import urlparse

import paho.mqtt.client as mqtt

from .api import COMMANDS_SECURED, KEEPALIVE, RoborockClient, md5hex
from .containers import DeviceData, UserData
from .exceptions import CommandVacuumError, RoborockException, VacuumError
from .protocol import MessageParser, Utils
from .roborock_future import RoborockFuture
from .roborock_message import RoborockMessage, RoborockMessageProtocol
from .roborock_typing import RoborockCommand
from .util import RoborockLoggerAdapter

_LOGGER = logging.getLogger(__name__)
CONNECT_REQUEST_ID = 0
DISCONNECT_REQUEST_ID = 1


class RoborockMqttClient(RoborockClient, mqtt.Client):
    _thread: threading.Thread
    _client_id: str

    def __init__(self, user_data: UserData, device_info: DeviceData, queue_timeout: int = 10) -> None:
        rriot = user_data.rriot
        if rriot is None:
            raise RoborockException("Got no rriot data from user_data")
        endpoint = base64.b64encode(Utils.md5(rriot.k.encode())[8:14]).decode()
        RoborockClient.__init__(self, endpoint, device_info, queue_timeout)
        mqtt.Client.__init__(self, protocol=mqtt.MQTTv5)
        self._logger = RoborockLoggerAdapter(device_info.device.name, _LOGGER)
        self._mqtt_user = rriot.u
        self._hashed_user = md5hex(self._mqtt_user + ":" + rriot.k)[2:10]
        url = urlparse(rriot.r.m)
        if not isinstance(url.hostname, str):
            raise RoborockException("Url parsing returned an invalid hostname")
        self._mqtt_host = str(url.hostname)
        self._mqtt_port = url.port
        self._mqtt_ssl = url.scheme == "ssl"
        if self._mqtt_ssl:
            super().tls_set()
        self._mqtt_password = rriot.s
        self._hashed_password = md5hex(self._mqtt_password + ":" + rriot.k)[16:]
        super().username_pw_set(self._hashed_user, self._hashed_password)
        self._endpoint = base64.b64encode(Utils.md5(rriot.k.encode())[8:14]).decode()
        self._waiting_queue: dict[int, RoborockFuture] = {}
        self._mutex = Lock()
        self.update_client_id()

    def on_connect(self, *args, **kwargs):
        _, __, ___, rc, ____ = args
        connection_queue = self._waiting_queue.get(CONNECT_REQUEST_ID)
        if rc != mqtt.MQTT_ERR_SUCCESS:
            message = f"Failed to connect ({mqtt.error_string(rc)})"
            self._logger.error(message)
            if connection_queue:
                connection_queue.resolve((None, VacuumError(message)))
            return
        self._logger.info(f"Connected to mqtt {self._mqtt_host}:{self._mqtt_port}")
        topic = f"rr/m/o/{self._mqtt_user}/{self._hashed_user}/{self.device_info.device.duid}"
        (result, mid) = self.subscribe(topic)
        if result != 0:
            message = f"Failed to subscribe ({mqtt.error_string(rc)})"
            self._logger.error(message)
            if connection_queue:
                connection_queue.resolve((None, VacuumError(message)))
            return
        self._logger.info(f"Subscribed to topic {topic}")
        if connection_queue:
            connection_queue.resolve((True, None))

    def on_message(self, *args, **kwargs):
        _, __, msg = args
        try:
            messages, _ = MessageParser.parse(msg.payload, local_key=self.device_info.device.local_key)
            super().on_message_received(messages)
        except Exception as ex:
            self._logger.exception(ex)

    def on_disconnect(self, *args, **kwargs):
        _, __, rc, ___ = args
        try:
            exc = RoborockException(mqtt.error_string(rc)) if rc != mqtt.MQTT_ERR_SUCCESS else None
            super().on_connection_lost(exc)
            if rc == mqtt.MQTT_ERR_PROTOCOL:
                self.update_client_id()
            connection_queue = self._waiting_queue.get(DISCONNECT_REQUEST_ID)
            if connection_queue:
                connection_queue.resolve((True, None))
        except Exception as ex:
            self._logger.exception(ex)

    def update_client_id(self):
        self._client_id = mqtt.base62(uuid.uuid4().int, padding=22)

    def sync_stop_loop(self) -> None:
        if self._thread:
            self._logger.info("Stopping mqtt loop")
            super().loop_stop()

    def sync_start_loop(self) -> None:
        if not self._thread or not self._thread.is_alive():
            self.sync_stop_loop()
            self._logger.info("Starting mqtt loop")
            super().loop_start()

    def sync_disconnect(self) -> tuple[bool, Task[tuple[Any, VacuumError | None]] | None]:
        if not self.is_connected():
            return False, None

        self._logger.info("Disconnecting from mqtt")
        disconnected_future = asyncio.ensure_future(self._async_response(DISCONNECT_REQUEST_ID))
        rc = super().disconnect()

        if rc == mqtt.MQTT_ERR_NO_CONN:
            disconnected_future.cancel()
            return False, None

        if rc != mqtt.MQTT_ERR_SUCCESS:
            disconnected_future.cancel()
            raise RoborockException(f"Failed to disconnect ({mqtt.error_string(rc)})")

        return True, disconnected_future

    def sync_connect(self) -> tuple[bool, Task[tuple[Any, VacuumError | None]] | None]:
        if self.is_connected():
            self.sync_start_loop()
            return False, None

        if self._mqtt_port is None or self._mqtt_host is None:
            raise RoborockException("Mqtt information was not entered. Cannot connect.")

        self._logger.debug("Connecting to mqtt")
        connected_future = asyncio.ensure_future(self._async_response(CONNECT_REQUEST_ID))
        super().connect(host=self._mqtt_host, port=self._mqtt_port, keepalive=KEEPALIVE)

        self.sync_start_loop()
        return True, connected_future

    async def async_disconnect(self) -> None:
        async with self._mutex:
            (disconnecting, disconnected_future) = self.sync_disconnect()
            if disconnecting and disconnected_future:
                (_, err) = await disconnected_future
                if err:
                    raise RoborockException(err) from err

    async def async_connect(self) -> None:
        async with self._mutex:
            (connecting, connected_future) = self.sync_connect()
            if connecting and connected_future:
                (_, err) = await connected_future
                if err:
                    raise RoborockException(err) from err

    def _send_msg_raw(self, msg: bytes) -> None:
        info = self.publish(f"rr/m/i/{self._mqtt_user}/{self._hashed_user}/{self.device_info.device.duid}", msg)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RoborockException(f"Failed to publish ({mqtt.error_string(info.rc)})")

    async def send_message(self, roborock_message: RoborockMessage):
        await self.validate_connection()
        method = roborock_message.get_method()
        params = roborock_message.get_params()
        request_id = roborock_message.get_request_id()
        if request_id is None:
            raise RoborockException(f"Failed build message {roborock_message}")
        response_protocol = (
            RoborockMessageProtocol.MAP_RESPONSE if method in COMMANDS_SECURED else RoborockMessageProtocol.RPC_RESPONSE
        )

        local_key = self.device_info.device.local_key
        msg = MessageParser.build(roborock_message, local_key, False)
        self._logger.debug(f"id={request_id} Requesting method {method} with {params}")
        async_response = asyncio.ensure_future(self._async_response(request_id, response_protocol))
        self._send_msg_raw(msg)
        (response, err) = await async_response
        self._diagnostic_data[method if method is not None else "unknown"] = {
            "params": roborock_message.get_params(),
            "response": response,
            "error": err,
        }
        if err:
            raise CommandVacuumError(method, err) from err
        if response_protocol == RoborockMessageProtocol.MAP_RESPONSE:
            self._logger.debug(f"id={request_id} Response from {method}: {len(response)} bytes")
        else:
            self._logger.debug(f"id={request_id} Response from {method}: {response}")
        return response

    async def _send_command(
        self,
        method: RoborockCommand | str,
        params: list | dict | int | None = None,
    ):
        request_id, timestamp, payload = super()._get_payload(method, params, True)
        request_protocol = RoborockMessageProtocol.RPC_REQUEST
        roborock_message = RoborockMessage(timestamp=timestamp, protocol=request_protocol, payload=payload)
        return await self.send_message(roborock_message)

    async def get_map_v1(self):
        return await self.send_command(RoborockCommand.GET_MAP_V1)
