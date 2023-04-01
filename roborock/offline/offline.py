import asyncio
import logging

from roborock.containers import HomeDataDevice, HomeDataDeviceField, HomeDataProduct, HomeDataProductField, NetworkInfo, \
    NetworkInfoField
from roborock.containers import RoborockLocalDeviceInfo
from roborock.local_api import RoborockLocalClient

local_ip = "<local_ip>"
local_key = "<local_key>"
device_id = "<device_id>"


async def main():
    logging_config = {
        "level": logging.DEBUG
    }
    logging.basicConfig(**logging_config)
    localdevices_info = RoborockLocalDeviceInfo({
        "device": HomeDataDevice({
            HomeDataDeviceField.NAME: "test_name",
            HomeDataDeviceField.DUID: device_id,
            HomeDataDeviceField.FV: "1",
            HomeDataDeviceField.LOCAL_KEY: local_key
        }),
        "product": HomeDataProduct({
            HomeDataProductField.MODEL: "test_model"
        }),
        "network_info": NetworkInfo({
            NetworkInfoField.IP: local_ip
        })})
    client = RoborockLocalClient({
        device_id: localdevices_info
    })
    await client.async_connect()
    props = await client.get_prop(device_id)
    print(props)


if __name__ == "__main__":
    asyncio.run(main())
