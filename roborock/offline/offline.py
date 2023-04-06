import asyncio
import logging

import pyshark as pyshark
from pyshark.packet.packet import Packet

from roborock.containers import HomeDataDevice, NetworkInfo
from roborock.containers import RoborockLocalDeviceInfo
from roborock.local_api import RoborockLocalClient
from roborock.roborock_message import RoborockParser
from roborock.typing import CommandInfo, RoborockCommand

local_ip = "192.168.1.232"
local_key = "nXTBj42ej5WxQopO"
device_id = "1r9W0cAmDZ2COuVekgRhKa"

buffer = {0: bytes()}


def add_buffer(bytes):
    buffer[0] += bytes


async def main():
    logging_config = {
        "level": logging.DEBUG
    }
    logging.basicConfig(**logging_config)
    localdevices_info = RoborockLocalDeviceInfo(
        device=HomeDataDevice(
            duid=device_id,
            local_key=local_key,
            name = "test name",
            fv="1"
        ),
        network_info=NetworkInfo(
            ip=local_ip
        )
    )

    client = RoborockLocalClient({
        device_id: localdevices_info
    })
    await client.async_connect()
    commands = [
        RoborockCommand.APP_GET_DRYER_SETTING,
        RoborockCommand.APP_SET_DRYER_SETTING,
        RoborockCommand.GET_DUST_COLLECTION_MODE,
        RoborockCommand.SET_DUST_COLLECTION_MODE,
        RoborockCommand.GET_SMART_WASH_PARAMS,
        RoborockCommand.SET_SMART_WASH_PARAMS,
        RoborockCommand.GET_WASH_TOWEL_MODE,
        RoborockCommand.SET_WASH_TOWEL_MODE,
        RoborockCommand.START_WASH_THEN_CHARGE,
        RoborockCommand.GET_SOUND_PROGRESS,
        RoborockCommand.CHANGE_SOUND_VOLUME,
        RoborockCommand.SET_SERVER_TIMER,
    ]
    capture = pyshark.LiveCapture(interface='rvi0')

    await client.send_command(device_id, RoborockCommand.GET_MULTI_MAPS_LIST)

    prefix_map: dict[str, CommandInfo] = {}

    def on_package(packet: Packet):
        if hasattr(packet, "ip"):
            if packet.transport_layer == 'TCP' and (packet.ip.dst == local_ip or packet.ip.src == local_ip):
                if hasattr(packet, "DATA"):
                    if hasattr(packet.DATA, "data"):
                        if packet.ip.dst == local_ip:
                            print("Request")
                            try:
                                f, buffer[0] = RoborockParser.decode(
                                    buffer[0] + bytes.fromhex(
                                        packet.DATA.data
                                    ),
                                    local_key
                                )
                                for g in f:
                                    method = g.get_method()
                                    method_info = prefix_map.get(method)

                                    if method in commands:
                                        print(method, g.prefix)
                            except BaseException as e:
                                print(e)
                                pass

    while True:
        try:
            await capture.packets_from_tshark(on_package, close_tshark=False)
        except Exception as e:
            print(e)


if __name__ == "__main__":
    asyncio.run(main())
