from __future__ import annotations

import base64
import logging
import threading
import uuid
from asyncio import Lock
from typing import Optional
from urllib.parse import urlparse

import paho.mqtt.client as mqtt

from .api import COMMANDS_SECURED, KEEPALIVE, RoborockClient, md5hex
from .containers import RoborockDeviceInfo, UserData
from .exceptions import CommandVacuumError, RoborockException, VacuumError
from .protocol import MessageParser, Utils
from .roborock_future import RoborockFuture
from .roborock_message import RoborockMessage
from .roborock_typing import RoborockCommand

_LOGGER = logging.getLogger(__name__)
CONNECT_REQUEST_ID = 0
DISCONNECT_REQUEST_ID = 1


class RoborockMqttClient(RoborockClient, mqtt.Client):
    _thread: threading.Thread
    _client_id: str

    def __init__(self, user_data: UserData, device_info: RoborockDeviceInfo) -> None:
        rriot = user_data.rriot
        if rriot is None:
            raise RoborockException("Got no rriot data from user_data")
        endpoint = base64.b64encode(Utils.md5(rriot.k.encode())[8:14]).decode()
        RoborockClient.__init__(self, endpoint, device_info)
        mqtt.Client.__init__(self, protocol=mqtt.MQTTv5)
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
            message = f"Failed to connect (rc: {rc})"
            _LOGGER.error(message)
            if connection_queue:
                connection_queue.resolve((None, VacuumError(rc, message)))
            return
        _LOGGER.info(f"Connected to mqtt {self._mqtt_host}:{self._mqtt_port}")
        topic = f"rr/m/o/{self._mqtt_user}/{self._hashed_user}/{self.device_info.device.duid}"
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

    def on_message(self, *args, **kwargs):
        _, __, msg = args
        try:
            messages, _ = MessageParser.parse(msg.payload, local_key=self.device_info.device.local_key)
            super().on_message_received(messages)
        except Exception as ex:
            _LOGGER.exception(ex)

    def on_disconnect(self, *args, **kwargs):
        _, __, rc, ___ = args
        try:
            super().on_connection_lost(RoborockException(f"(rc: {rc})"))
            if rc == mqtt.MQTT_ERR_PROTOCOL:
                self.update_client_id()
            connection_queue = self._waiting_queue.get(DISCONNECT_REQUEST_ID)
            if connection_queue:
                connection_queue.resolve((True, None))
        except Exception as ex:
            _LOGGER.exception(ex)

    def update_client_id(self):
        self._client_id = mqtt.base62(uuid.uuid4().int, padding=22)

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
        self.sync_start_loop()
        if not self.is_connected():
            if self._mqtt_port is None or self._mqtt_host is None:
                raise RoborockException("Mqtt information was not entered. Cannot connect.")
            _LOGGER.info("Connecting to mqtt")
            super().connect_async(host=self._mqtt_host, port=self._mqtt_port, keepalive=KEEPALIVE)
            return True
        return False

    async def async_disconnect(self) -> None:
        async with self._mutex:
            disconnecting = self.sync_disconnect()
            if disconnecting:
                (_, err) = await self._async_response(DISCONNECT_REQUEST_ID)
                if err:
                    raise RoborockException(err) from err

    async def async_connect(self) -> None:
        async with self._mutex:
            connecting = self.sync_connect()
            if connecting:
                (_, err) = await self._async_response(CONNECT_REQUEST_ID)
                if err:
                    raise RoborockException(err) from err

    def _send_msg_raw(self, msg: bytes) -> None:
        info = self.publish(f"rr/m/i/{self._mqtt_user}/{self._hashed_user}/{self.device_info.device.duid}", msg)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RoborockException(f"Failed to publish (rc: {info.rc})")

    async def send_command(self, method: RoborockCommand, params: Optional[list | dict] = None):
        await self.validate_connection()
        request_id, timestamp, payload = super()._get_payload(method, params, True)
        _LOGGER.debug(f"id={request_id} Requesting method {method} with {params}")
        request_protocol = 101
        response_protocol = 301 if method in COMMANDS_SECURED else 102
        roborock_message = RoborockMessage(timestamp=timestamp, protocol=request_protocol, payload=payload)
        local_key = self.device_info.device.local_key
        msg = MessageParser.build(roborock_message, local_key)
        self._send_msg_raw(msg)
        (response, err) = await self._async_response(request_id, response_protocol)
        if err:
            raise CommandVacuumError(method, err) from err
        if response_protocol == 301:
            _LOGGER.debug(f"id={request_id} Response from {method}: {len(response)} bytes")
        else:
            _LOGGER.debug(f"id={request_id} Response from {method}: {response}")
        return response

    async def get_map_v1(self):
        try:
            return await self.send_command(RoborockCommand.GET_MAP_V1)
        except RoborockException as e:
            _LOGGER.error(e)
        return None
