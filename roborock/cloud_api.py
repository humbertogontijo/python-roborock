from __future__ import annotations

import base64
import gzip
import json
import logging
import secrets
import struct
import threading
from asyncio import Lock
from asyncio.exceptions import TimeoutError, CancelledError
from typing import Any, Callable
from urllib.parse import urlparse

import paho.mqtt.client as mqtt
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from roborock.api import md5hex, md5bin, RoborockClient
from roborock.exceptions import (
    RoborockException,
    CommandVacuumError,
    VacuumError,
    RoborockTimeout,
)
from .code_mappings import STATE_CODE_TO_STATUS
from .containers import (
    UserData,
)
from .roborock_queue import RoborockQueue
from .typing import (
    RoborockCommand,
)
from .util import run_in_executor

_LOGGER = logging.getLogger(__name__)
QUEUE_TIMEOUT = 4
MQTT_KEEPALIVE = 60
COMMANDS_WITH_BINARY_RESPONSE = [
    RoborockCommand.GET_MAP_V1,
]


class RoborockMqttClient(RoborockClient, mqtt.Client):
    _thread: threading.Thread

    def __init__(self, user_data: UserData, device_localkey: dict[str, str]) -> None:
        rriot = user_data.rriot
        self._mqtt_user = rriot.user
        RoborockClient.__init__(self, rriot.endpoint, device_localkey)
        mqtt.Client.__init__(self, protocol=mqtt.MQTTv5)
        self._hashed_user = md5hex(self._mqtt_user + ":" + rriot.endpoint)[2:10]
        url = urlparse(rriot.reference.mqtt)
        self._mqtt_host = url.hostname
        self._mqtt_port = url.port
        self._mqtt_ssl = url.scheme == "ssl"
        if self._mqtt_ssl:
            super().tls_set()
        self._mqtt_password = rriot.password
        self._hashed_password = md5hex(self._mqtt_password + ":" + rriot.endpoint)[16:]
        super().username_pw_set(self._hashed_user, self._hashed_password)
        self._seq = 1
        self._random = 4711
        self._id_counter = 2
        self._salt = "TXdfu$jyZ#TZHsg4"
        self._endpoint = base64.b64encode(md5bin(rriot.endpoint)[8:14]).decode()
        self._nonce = secrets.token_bytes(16)
        self._waiting_queue: dict[int, RoborockQueue] = {}
        self._mutex = Lock()
        self._last_device_msg_in = mqtt.time_func()
        self._last_disconnection = mqtt.time_func()
        self._status_listeners: list[Callable[[str, str], None]] = []

    def __del__(self) -> None:
        self.sync_disconnect()

    @run_in_executor()
    async def on_connect(self, _client, _, __, rc, ___=None) -> None:
        connection_queue = self._waiting_queue.get(0)
        if rc != mqtt.MQTT_ERR_SUCCESS:
            message = f"Failed to connect (rc: {rc})"
            _LOGGER.error(message)
            if connection_queue:
                await connection_queue.async_put(
                    (None, VacuumError(rc, message)), timeout=QUEUE_TIMEOUT
                )
            return
        _LOGGER.info(f"Connected to mqtt {self._mqtt_host}:{self._mqtt_port}")
        topic = f"rr/m/o/{self._mqtt_user}/{self._hashed_user}/#"
        (result, mid) = self.subscribe(topic)
        if result != 0:
            message = f"Failed to subscribe (rc: {result})"
            _LOGGER.error(message)
            if connection_queue:
                await connection_queue.async_put(
                    (None, VacuumError(rc, message)), timeout=QUEUE_TIMEOUT
                )
            return
        _LOGGER.info(f"Subscribed to topic {topic}")
        if connection_queue:
            await connection_queue.async_put((True, None), timeout=QUEUE_TIMEOUT)

    @run_in_executor()
    async def on_message(self, _client, _, msg, __=None) -> None:
        try:
            async with self._mutex:
                self._last_device_msg_in = mqtt.time_func()
            device_id = msg.topic.split("/").pop()
            data = self._decode_msg(msg.payload, self.device_localkey[device_id])
            protocol = data.get("protocol")
            if protocol == 102:
                payload = json.loads(data.get("payload").decode())
                for data_point_number, data_point in payload.get("dps").items():
                    if data_point_number == "102":
                        data_point_response = json.loads(data_point)
                        request_id = data_point_response.get("id")
                        queue = self._waiting_queue.get(request_id)
                        if queue:
                            if queue.protocol == protocol:
                                error = data_point_response.get("error")
                                if error:
                                    await queue.async_put(
                                        (
                                            None,
                                            VacuumError(
                                                error.get("code"), error.get("message")
                                            ),
                                        ),
                                        timeout=QUEUE_TIMEOUT,
                                    )
                                else:
                                    result = data_point_response.get("result")
                                    if isinstance(result, list) and len(result) > 0:
                                        result = result[0]
                                    await queue.async_put(
                                        (result, None), timeout=QUEUE_TIMEOUT
                                    )
                        elif request_id < self._id_counter:
                            _LOGGER.debug(
                                f"id={request_id} Ignoring response: {data_point_response}"
                            )
                    elif data_point_number == "121":
                        status = STATE_CODE_TO_STATUS.get(data_point)
                        _LOGGER.debug(f"Status updated to {status}")
                        for listener in self._status_listeners:
                            listener(device_id, status)
                    else:
                        _LOGGER.debug(
                            f"Unknown data point number received {data_point_number} with {data_point}"
                        )
            elif protocol == 301:
                payload = data.get("payload")[0:24]
                [endpoint, _, request_id, _] = struct.unpack("<15sBH6s", payload)
                if endpoint.decode().startswith(self._endpoint):
                    iv = bytes(AES.block_size)
                    decipher = AES.new(self._nonce, AES.MODE_CBC, iv)
                    decrypted = unpad(
                        decipher.decrypt(data.get("payload")[24:]), AES.block_size
                    )
                    decrypted = gzip.decompress(decrypted)
                    queue = self._waiting_queue.get(request_id)
                    if queue:
                        if isinstance(decrypted, list):
                            decrypted = decrypted[0]
                        await queue.async_put((decrypted, None), timeout=QUEUE_TIMEOUT)
        except Exception as ex:
            _LOGGER.exception(ex)

    @run_in_executor()
    async def on_disconnect(self, _client: mqtt.Client, _, rc, __=None) -> None:
        try:
            self._last_disconnection = mqtt.time_func()
            message = f"Roborock mqtt client disconnected (rc: {rc})"
            _LOGGER.warning(message)
            connection_queue = self._waiting_queue.get(1)
            if connection_queue:
                await connection_queue.async_put(
                    (True, None), timeout=QUEUE_TIMEOUT
                )
        except Exception as ex:
            _LOGGER.exception(ex)

    @run_in_executor()
    async def _async_check_keepalive(self) -> None:
        async with self._mutex:
            now = mqtt.time_func()
            if now - self._last_disconnection > self._keepalive ** 2 and now - self._last_device_msg_in > self._keepalive:
                self._ping_t = self._last_device_msg_in

    def add_status_listener(self, callback: Callable[[str, str], None]):
        self._status_listeners.append(callback)

    def _check_keepalive(self) -> None:
        self._async_check_keepalive()
        super()._check_keepalive()

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
            if not rc in [mqtt.MQTT_ERR_SUCCESS, mqtt.MQTT_ERR_NO_CONN]:
                raise RoborockException(f"Failed to disconnect (rc:{rc})")
        return rc == mqtt.MQTT_ERR_SUCCESS

    def sync_connect(self) -> bool:
        rc = mqtt.MQTT_ERR_AGAIN
        self.sync_start_loop()
        if not self.is_connected():
            _LOGGER.info("Connecting to mqtt")
            rc = super().connect(
                host=self._mqtt_host,
                port=self._mqtt_port,
                keepalive=MQTT_KEEPALIVE
            )
            if rc != mqtt.MQTT_ERR_SUCCESS:
                raise RoborockException(f"Failed to connect (rc:{rc})")
        return rc == mqtt.MQTT_ERR_SUCCESS

    async def _async_response(self, request_id: int, protocol_id: int = 0) -> tuple[Any, VacuumError | None]:
        try:
            queue = RoborockQueue(protocol_id)
            self._waiting_queue[request_id] = queue
            (response, err) = await queue.async_get(QUEUE_TIMEOUT)
            return response, err
        except (TimeoutError, CancelledError):
            raise RoborockTimeout(
                f"Timeout after {QUEUE_TIMEOUT} seconds waiting for response"
            ) from None
        finally:
            del self._waiting_queue[request_id]

    async def async_disconnect(self) -> Any:
        async with self._mutex:
            disconnecting = self.sync_disconnect()
            if disconnecting:
                (response, err) = await self._async_response(1)
                if err:
                    raise RoborockException(err) from err
                return response

    async def async_connect(self) -> Any:
        async with self._mutex:
            connecting = self.sync_connect()
            if connecting:
                (response, err) = await self._async_response(0)
                if err:
                    raise RoborockException(err) from err
                return response

    async def validate_connection(self) -> None:
        await self.async_connect()

    def _send_msg_raw(self, device_id, msg) -> None:
        info = self.publish(
            f"rr/m/i/{self._mqtt_user}/{self._hashed_user}/{device_id}", msg
        )
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RoborockException(f"Failed to publish (rc: {info.rc})")

    async def send_command(
            self, device_id: str, method: RoborockCommand, params: list = None
    ):
        await self.validate_connection()
        request_id, timestamp, payload = super()._get_payload(method, params)
        _LOGGER.debug(f"id={request_id} Requesting method {method} with {params}")
        request_protocol = 101
        response_protocol = 301 if method in COMMANDS_WITH_BINARY_RESPONSE else 102
        msg = super()._get_msg_raw(device_id, request_protocol, timestamp, payload)
        self._send_msg_raw(device_id, msg)
        (response, err) = await self._async_response(request_id, response_protocol)
        if err:
            raise CommandVacuumError(method, err) from err
        if response_protocol == 301:
            _LOGGER.debug(
                f"id={request_id} Response from {method}: {len(response)} bytes"
            )
        else:
            _LOGGER.debug(f"id={request_id} Response from {method}: {response}")
        return response
