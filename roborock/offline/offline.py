import asyncio
import logging

from roborock.containers import HomeDataDevice, HomeDataDeviceField, HomeDataProduct, HomeDataProductField, NetworkInfo, \
    NetworkInfoField
from roborock.local_api import RoborockLocalClient
from roborock.typing import RoborockLocalDeviceInfo

local_ip = "<local_ip>"
local_key = "<local_key>"
device_id = "<device_id>"


async def main():
    logging_config = {
        "level": logging.DEBUG
    }
    logging.basicConfig(**logging_config)
    client = RoborockLocalClient({
        device_id: RoborockLocalDeviceInfo(HomeDataDevice({
            HomeDataDeviceField.NAME: "test_name",
            HomeDataDeviceField.DUID: device_id,
            HomeDataDeviceField.FV: "1",
            HomeDataDeviceField.LOCAL_KEY: local_key
        }), HomeDataProduct({
            HomeDataProductField.MODEL: "test_model"
        }), NetworkInfo({
            NetworkInfoField.IP: local_ip
        }))
    })
    await client.async_connect()
    props = await client.get_prop(device_id)
    print(props)


if __name__ == "__main__":
    asyncio.run(main())
