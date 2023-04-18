import asyncio

import pytest

from roborock.roborock_future import RoborockFuture


def test_can_create():
    RoborockFuture(1)


@pytest.mark.asyncio
async def test_put():
    rq = RoborockFuture(1)
    rq.resolve(("test", None))
    assert await rq.async_get(1) == ("test", None)


@pytest.mark.asyncio
async def test_get_timeout():
    rq = RoborockFuture(1)
    with pytest.raises(asyncio.TimeoutError):
        await rq.async_get(0.01)
