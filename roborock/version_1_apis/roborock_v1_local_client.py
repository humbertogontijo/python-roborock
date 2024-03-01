from roborock.local_api import RoborockLocalClient

from .. import DeviceData, RoborockCommand
from ..roborock_message import MessageRetry, RoborockMessage, RoborockMessageProtocol
from .roborock_v1_client import COMMANDS_SECURED, RoborockV1Client


class RoborockV1LocalClient(RoborockLocalClient, RoborockV1Client):
    def __init__(self, device_data: DeviceData, queue_timeout: int = 4):
        RoborockLocalClient.__init__(self, device_data, queue_timeout)
        RoborockV1Client.__init__(self, device_data, self.cache, self._logger, "abc")

    def build_roborock_message(
        self, method: RoborockCommand | str, params: list | dict | int | None = None
    ) -> RoborockMessage:
        secured = True if method in COMMANDS_SECURED else False
        request_id, timestamp, payload = self._get_payload(method, params, secured)
        request_protocol = RoborockMessageProtocol.GENERAL_REQUEST
        message_retry: MessageRetry | None = None
        if method == RoborockCommand.RETRY_REQUEST and isinstance(params, dict):
            message_retry = MessageRetry(method=params["method"], retry_id=params["retry_id"])
        return RoborockMessage(
            timestamp=timestamp, protocol=request_protocol, payload=payload, message_retry=message_retry
        )

    async def _send_command(
        self,
        method: RoborockCommand | str,
        params: list | dict | int | None = None,
    ):
        roborock_message = self.build_roborock_message(method, params)
        return await self.send_message(roborock_message)
