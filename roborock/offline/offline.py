import asyncio
import logging

from roborock.containers import HomeDataDevice, HomeDataDeviceField, HomeDataProduct, HomeDataProductField, NetworkInfo, \
    NetworkInfoField
from roborock.local_api import RoborockLocalClient
from roborock.typing import RoborockDeviceInfo

local_ip = "192.168.1.232"
local_key = "nXTBj42ej5WxQopO"
device_id = "1r9W0cAmDZ2COuVekgRhKA"


async def main():
    logging_config = {
        "level": logging.DEBUG
    }
    logging.basicConfig(**logging_config)
    client = RoborockLocalClient({
        device_id: RoborockDeviceInfo(HomeDataDevice({
            HomeDataDeviceField.DUID: device_id,
            HomeDataDeviceField.LOCAL_KEY: local_key
        }), HomeDataProduct({
            HomeDataProductField.MODEL: "test"
        }), NetworkInfo({
            NetworkInfoField.IP: local_ip
        }))
    })
    await client.async_connect()
    props = await client.get_prop(device_id)
    print(props)


if __name__ == "__main__":
    asyncio.run(main())
