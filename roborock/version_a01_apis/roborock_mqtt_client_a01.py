import asyncio
import base64
import json
import typing

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from roborock.cloud_api import RoborockMqttClient
from roborock.containers import DeviceData, RoborockCategory, UserData
from roborock.exceptions import RoborockException
from roborock.protocol import MessageParser, Utils
from roborock.roborock_message import (
    RoborockDyadDataProtocol,
    RoborockMessage,
    RoborockMessageProtocol,
    RoborockZeoProtocol,
)

from .roborock_client_a01 import RoborockClientA01


class RoborockMqttClientA01(RoborockMqttClient, RoborockClientA01):
    def __init__(
        self, user_data: UserData, device_info: DeviceData, category: RoborockCategory, queue_timeout: int = 10
    ) -> None:
        rriot = user_data.rriot
        if rriot is None:
            raise RoborockException("Got no rriot data from user_data")
        endpoint = base64.b64encode(Utils.md5(rriot.k.encode())[8:14]).decode()

        RoborockMqttClient.__init__(self, user_data, device_info, queue_timeout)
        RoborockClientA01.__init__(self, endpoint, device_info, category, queue_timeout)

    async def send_message(self, roborock_message: RoborockMessage):
        await self.validate_connection()
        response_protocol = RoborockMessageProtocol.RPC_RESPONSE

        local_key = self.device_info.device.local_key
        m = MessageParser.build(roborock_message, local_key, prefixed=False)
        # self._logger.debug(f"id={request_id} Requesting method {method} with {params}")
        payload = json.loads(unpad(roborock_message.payload, AES.block_size))
        futures = []
        if "10000" in payload["dps"]:
            for dps in json.loads(payload["dps"]["10000"]):
                futures.append(asyncio.ensure_future(self._async_response(dps, response_protocol)))
        self._send_msg_raw(m)
        responses = await asyncio.gather(*futures, return_exceptions=True)
        dps_responses: dict[int, typing.Any] = {}
        if "10000" in payload["dps"]:
            for i, dps in enumerate(json.loads(payload["dps"]["10000"])):
                response = responses[i]
                if isinstance(response, BaseException):
                    self._logger.warning("Timed out get req for %s after %s s", dps, self.queue_timeout)
                    dps_responses[dps] = None
                else:
                    dps_responses[dps] = response[0]
        return dps_responses

    async def update_values(
        self, dyad_data_protocols: list[RoborockDyadDataProtocol | RoborockZeoProtocol]
    ) -> dict[RoborockDyadDataProtocol | RoborockZeoProtocol, typing.Any]:
        payload = {"dps": {RoborockDyadDataProtocol.ID_QUERY: str([int(protocol) for protocol in dyad_data_protocols])}}
        return await self.send_message(
            RoborockMessage(
                protocol=RoborockMessageProtocol.RPC_REQUEST,
                version=b"A01",
                payload=pad(json.dumps(payload).encode("utf-8"), AES.block_size),
            )
        )
