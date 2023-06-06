from __future__ import annotations

import asyncio
import datetime
import functools
from asyncio import AbstractEventLoop
from typing import Callable, Coroutine, Optional, Tuple, TypeVar

T = TypeVar("T")
DEFAULT_TIME_ZONE: Optional[datetime.tzinfo] = datetime.datetime.now().astimezone().tzinfo


def unpack_list(value: list[T], size: int) -> list[Optional[T]]:
    return (value + [None] * size)[:size]  # type: ignore


def get_running_loop_or_create_one() -> AbstractEventLoop:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


def parse_datetime_to_roborock_datetime(
    start_datetime: datetime.datetime, end_datetime: datetime.datetime
) -> Tuple[datetime.datetime, datetime.datetime]:
    now = datetime.datetime.now(DEFAULT_TIME_ZONE)
    start_datetime = start_datetime.replace(
        year=now.year, month=now.month, day=now.day, second=0, microsecond=0, tzinfo=DEFAULT_TIME_ZONE
    )
    end_datetime = end_datetime.replace(
        year=now.year, month=now.month, day=now.day, second=0, microsecond=0, tzinfo=DEFAULT_TIME_ZONE
    )
    if start_datetime > end_datetime:
        end_datetime += datetime.timedelta(days=1)
    elif end_datetime < now:
        start_datetime += datetime.timedelta(days=1)
        end_datetime += datetime.timedelta(days=1)

    return start_datetime, end_datetime


def parse_time_to_datetime(
    start_time: datetime.time, end_time: datetime.time
) -> Tuple[datetime.datetime, datetime.datetime]:
    """Help to handle time data."""
    start_datetime = datetime.datetime.now(DEFAULT_TIME_ZONE).replace(
        hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0
    )
    end_datetime = datetime.datetime.now(DEFAULT_TIME_ZONE).replace(
        hour=end_time.hour, minute=end_time.minute, second=0, microsecond=0
    )

    return parse_datetime_to_roborock_datetime(start_datetime, end_datetime)


def run_sync():
    loop = get_running_loop_or_create_one()

    def decorator(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            return loop.run_until_complete(func(*args, **kwargs))

        return wrapped

    return decorator


class CacheableResult:
    last_run_result = None


RT = TypeVar("RT", bound=Callable[..., Coroutine])


def fallback_cache(func: RT) -> RT:
    cache = CacheableResult()

    @functools.wraps(func)
    async def wrapped(*args, **kwargs):
        try:
            last_run_result = await func(*args, **kwargs)
            cache.last_run_result = last_run_result
        except Exception as e:
            if cache.last_run_result is None:
                raise e
            last_run_result = cache.last_run_result
            cache.last_run_result = None
            return last_run_result
        return last_run_result

    return wrapped  # type: ignore
