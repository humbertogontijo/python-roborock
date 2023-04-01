import asyncio
import logging

from roborock.local_api import RoborockLocalClient

local_ip = "<local_ip>"
local_key = "<local_key>"


async def main():
    logging_config = {
        "level": logging.DEBUG
    }
    logging.basicConfig(**logging_config)
    device_id = "1r9W0cAmDZ2COuVekgRhKA"
    client = RoborockLocalClient(local_ip, {
        "1r9W0cAmDZ2COuVekgRhKA": local_key
    })
    await client.async_connect()
    props = await client.get_prop(device_id)
    print(props)


if __name__ == "__main__":
    asyncio.run(main())
