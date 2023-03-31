import asyncio

from roborock.local_api import RoborockLocalClient
from roborock.typing import RoborockCommand

local_ip = "<device_ip>"
local_key = "<device_localkey>"
endpoint = "abc"


async def main():
    device_id = "1r9W0cAmDZ2COuVekgRhKA"
    client = RoborockLocalClient(local_ip, endpoint, {
        "1r9W0cAmDZ2COuVekgRhKA": local_key
    })
    await client.async_connect()
    response = await client.send_command(device_id, RoborockCommand.GET_STATUS)
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
