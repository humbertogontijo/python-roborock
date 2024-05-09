import asyncio
import base64

import paho.mqtt.client as mqtt

from roborock.cloud_api import RoborockMqttClient

from ..containers import DeviceData, UserData
from ..exceptions import CommandVacuumError, RoborockException
from ..protocol import MessageParser, Utils
from ..roborock_message import (
    RoborockMessage,
    RoborockMessageProtocol,
)
from ..roborock_typing import RoborockCommand
from .roborock_client_v1 import COMMANDS_SECURED, RoborockClientV1


class RoborockMqttClientV1(RoborockMqttClient, RoborockClientV1):
    def __init__(self, user_data: UserData, device_info: DeviceData, queue_timeout: int = 10) -> None:
        rriot = user_data.rriot
        if rriot is None:
            raise RoborockException("Got no rriot data from user_data")
        endpoint = base64.b64encode(Utils.md5(rriot.k.encode())[8:14]).decode()

        RoborockMqttClient.__init__(self, user_data, device_info, queue_timeout)
        RoborockClientV1.__init__(self, device_info, self._logger, endpoint)

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
        request_id, timestamp, payload = self._get_payload(method, params, True)
        request_protocol = RoborockMessageProtocol.RPC_REQUEST
        roborock_message = RoborockMessage(timestamp=timestamp, protocol=request_protocol, payload=payload)
        return await self.send_message(roborock_message)

    async def get_map_v1(self) -> bytes | None:
        return await self.send_command(RoborockCommand.GET_MAP_V1)
