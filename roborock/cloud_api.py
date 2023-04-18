from __future__ import annotations

import base64
import logging
import threading
import uuid
from asyncio import Lock
from typing import Any, Mapping, Optional
from urllib.parse import urlparse

import paho.mqtt.client as mqtt

from .api import SPECIAL_COMMANDS, RoborockClient, md5hex
from .containers import RoborockDeviceInfo, UserData
from .exceptions import CommandVacuumError, RoborockException, VacuumError
from .roborock_future import RoborockFuture
from .roborock_message import RoborockMessage, RoborockParser, md5bin
from .typing import RoborockCommand

_LOGGER = logging.getLogger(__name__)
MQTT_KEEPALIVE = 60
CONNECT_REQUEST_ID = 0
DISCONNECT_REQUEST_ID = 1


class RoborockMqttClient(RoborockClient, mqtt.Client):
    _thread: threading.Thread

    def __init__(self, user_data: UserData, devices_info: Mapping[str, RoborockDeviceInfo]) -> None:
        rriot = user_data.rriot
        if rriot is None:
            raise RoborockException("Got no rriot data from user_data")
        endpoint = base64.b64encode(md5bin(rriot.k)[8:14]).decode()
        RoborockClient.__init__(self, endpoint, devices_info)
        mqtt.Client.__init__(self, protocol=mqtt.MQTTv5)
        self._mqtt_user = rriot.u
        self._hashed_user = md5hex(self._mqtt_user + ":" + rriot.k)[2:10]
        url = urlparse(rriot.r.m)
        if not isinstance(url.hostname, str):
            raise RoborockException("Url parsing returned an invalid hostname")
        self._mqtt_host = url.hostname
        self._mqtt_port = url.port
        self._mqtt_ssl = url.scheme == "ssl"
        if self._mqtt_ssl:
            super().tls_set()
        self._mqtt_password = rriot.s
        self._hashed_password = md5hex(self._mqtt_password + ":" + rriot.k)[16:]
        super().username_pw_set(self._hashed_user, self._hashed_password)
        self._endpoint = base64.b64encode(md5bin(rriot.k)[8:14]).decode()
        self._waiting_queue: dict[int, RoborockFuture] = {}
        self._mutex = Lock()
        self._last_device_msg_in = mqtt.time_func()
        self._last_disconnection = mqtt.time_func()
        self.update_client_id()

    def __del__(self) -> None:
        self.sync_disconnect()

    def on_connect(self, *args, **kwargs) -> None:
        _, __, ___, rc, ____ = args
        connection_queue = self._waiting_queue.get(CONNECT_REQUEST_ID)
        if rc != mqtt.MQTT_ERR_SUCCESS:
            message = f"Failed to connect (rc: {rc})"
            _LOGGER.error(message)
            if connection_queue:
                connection_queue.resolve((None, VacuumError(rc, message)))
            return
        _LOGGER.info(f"Connected to mqtt {self._mqtt_host}:{self._mqtt_port}")
        topic = f"rr/m/o/{self._mqtt_user}/{self._hashed_user}/#"
        (result, mid) = self.subscribe(topic)
        if result != 0:
            message = f"Failed to subscribe (rc: {result})"
            _LOGGER.error(message)
            if connection_queue:
                connection_queue.resolve((None, VacuumError(rc, message)))
            return
        _LOGGER.info(f"Subscribed to topic {topic}")
        if connection_queue:
            connection_queue.resolve((True, None))

    def on_message(self, *args, **kwargs) -> None:
        _, __, msg = args
        self._last_device_msg_in = mqtt.time_func()
        device_id = msg.topic.split("/").pop()
        messages, _ = RoborockParser.decode(msg.payload, self.devices_info[device_id].device.local_key)
        super().on_message(messages)

    def on_disconnect(self, *args, **kwargs) -> None:
        try:
            _, __, rc, ___ = args
            self._last_disconnection = mqtt.time_func()
            message = f"Roborock mqtt client disconnected (rc: {rc})"
            if rc == mqtt.MQTT_ERR_PROTOCOL:
                self.update_client_id()
            _LOGGER.warning(message)
            connection_queue = self._waiting_queue.get(DISCONNECT_REQUEST_ID)
            if connection_queue:
                connection_queue.resolve((True, None))
        except Exception as ex:
            _LOGGER.exception(ex)

    def update_client_id(self):
        self._client_id = mqtt.base62(uuid.uuid4().int, padding=22)

    def _async_check_keepalive(self) -> None:
        now = mqtt.time_func()
        # noinspection PyUnresolvedReferences
        if (
            now - self._last_disconnection > self._keepalive**2  # type: ignore[attr-defined]
            and now - self._last_device_msg_in > self._keepalive  # type: ignore[attr-defined]
        ):
            self._ping_t = self._last_device_msg_in

    def _check_keepalive(self) -> None:
        self._async_check_keepalive()
        # noinspection PyUnresolvedReferences
        super()._check_keepalive()  # type: ignore[misc]

    def sync_stop_loop(self) -> None:
        if self._thread:
            _LOGGER.info("Stopping mqtt loop")
            super().loop_stop()

    def sync_start_loop(self) -> None:
        if not self._thread or not self._thread.is_alive():
            self.sync_stop_loop()
            _LOGGER.info("Starting mqtt loop")
            super().loop_start()

    def sync_disconnect(self) -> bool:
        rc = mqtt.MQTT_ERR_AGAIN
        if self.is_connected():
            _LOGGER.info("Disconnecting from mqtt")
            rc = super().disconnect()
            if rc not in [mqtt.MQTT_ERR_SUCCESS, mqtt.MQTT_ERR_NO_CONN]:
                raise RoborockException(f"Failed to disconnect (rc:{rc})")
        return rc == mqtt.MQTT_ERR_SUCCESS

    def sync_connect(self) -> bool:
        rc = mqtt.MQTT_ERR_AGAIN
        self.sync_start_loop()
        if not self.is_connected():
            if self._mqtt_port is None or self._mqtt_host is None:
                raise RoborockException("Mqtt information was not entered. Cannot connect.")
            _LOGGER.info("Connecting to mqtt")
            rc = super().connect(host=self._mqtt_host, port=self._mqtt_port, keepalive=MQTT_KEEPALIVE)
            if rc != mqtt.MQTT_ERR_SUCCESS:
                raise RoborockException(f"Failed to connect (rc:{rc})")
        return rc == mqtt.MQTT_ERR_SUCCESS

    async def async_disconnect(self) -> Any:
        async with self._mutex:
            disconnecting = self.sync_disconnect()
            if disconnecting:
                (response, err) = await self._async_response(DISCONNECT_REQUEST_ID)
                if err:
                    raise RoborockException(err) from err
                return response

    async def async_connect(self) -> Any:
        async with self._mutex:
            connecting = self.sync_connect()
            if connecting:
                (response, err) = await self._async_response(CONNECT_REQUEST_ID)
                if err:
                    raise RoborockException(err) from err
                return response

    async def validate_connection(self) -> None:
        await self.async_connect()

    def _send_msg_raw(self, device_id, msg) -> None:
        info = self.publish(f"rr/m/i/{self._mqtt_user}/{self._hashed_user}/{device_id}", msg)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RoborockException(f"Failed to publish (rc: {info.rc})")

    async def send_command(self, device_id: str, method: RoborockCommand, params: Optional[list] = None):
        await self.validate_connection()
        request_id, timestamp, payload = super()._get_payload(method, params, True)
        _LOGGER.debug(f"id={request_id} Requesting method {method} with {params}")
        request_protocol = 101
        response_protocol = 301 if method in SPECIAL_COMMANDS else 102
        roborock_message = RoborockMessage(timestamp=timestamp, protocol=request_protocol, payload=payload)
        local_key = self.devices_info[device_id].device.local_key
        msg = RoborockParser.encode(roborock_message, local_key)
        self._send_msg_raw(device_id, msg)
        (response, err) = await self._async_response(request_id, response_protocol)
        if err:
            raise CommandVacuumError(method, err) from err
        if response_protocol == 301:
            _LOGGER.debug(f"id={request_id} Response from {method}: {len(response)} bytes")
        else:
            _LOGGER.debug(f"id={request_id} Response from {method}: {response}")
        return response

    async def get_map_v1(self, device_id):
        return await self.send_command(device_id, RoborockCommand.GET_MAP_V1)
