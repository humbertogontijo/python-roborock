import asyncio
import logging

from roborock.local_api import RoborockLocalClient
from roborock.typing import RoborockCommand

local_ip = "192.168.1.232"
local_key = "nXTBj42ej5WxQopO"
endpoint = "abc"


async def main():
    logging_config = {
        "level": logging.DEBUG
    }
    logging.basicConfig(**logging_config)
    device_id = "1r9W0cAmDZ2COuVekgRhKA"
    client = RoborockLocalClient(local_ip, endpoint, {
        "1r9W0cAmDZ2COuVekgRhKA": local_key
    })
    # print(client._decode_msg(bytes.fromhex('000000c7312e300000cf6a0000bff56424b659000400b0772b8ddc5645f5751d58d4a9805c37cc7c1989a5c76ca69130ce6672cbf27d231d9fb0a85ddb8eb2a999cc1f630f18f05f5425d6a291319c88da0851a3811f2646b0b5a34bd26a4f83c118d48340302383c9c9ee3b0063f3ad5a773f606ffd0358fdb573afa774859bfc993eea8b2695f3a5af5938a2af03b6be6b559f4bc9601ca65617838efdbc8ac5e30b8e7bcc06218f3cc5eb279263c44de63b506bb7953baf9288963ee987270d01b1b9481df058b2f161'), local_key))
    await client.async_connect()
    dnd_timer = await client.get_clean_record(device_id, 1680313530)
    print(dnd_timer)
    # clean_summary = await client.get_clean_summary(device_id)
    # print(clean_summary)
    # consumable = await client.get_consumable(device_id)
    # print(consumable)


if __name__ == "__main__":
    asyncio.run(main())
