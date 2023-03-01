import asyncio

import pytest

from roborock.roborock_queue import RoborockQueue


def test_can_create():
    RoborockQueue(1)


@pytest.mark.asyncio
async def test_put():
    rq = RoborockQueue(1)
    await rq.async_put(("test", None), 1)
    assert await rq.get() == ("test", None)


@pytest.mark.asyncio
async def test_get_timeout():
    rq = RoborockQueue(1)
    with pytest.raises(asyncio.TimeoutError):
        await rq.async_get(.01)


@pytest.mark.asyncio
async def test_get():
    rq = RoborockQueue(1)
    await rq.async_put(("test", None), 1)
    assert await rq.async_get(1) == ("test", None)
