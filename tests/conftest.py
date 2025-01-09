import re

import pytest
from aioresponses import aioresponses

from roborock import HomeData, UserData
from roborock.containers import DeviceData
from roborock.version_1_apis.roborock_mqtt_client_v1 import RoborockMqttClientV1
from tests.mock_data import HOME_DATA_RAW, USER_DATA


@pytest.fixture(name="mqtt_client")
def mqtt_client():
    user_data = UserData.from_dict(USER_DATA)
    home_data = HomeData.from_dict(HOME_DATA_RAW)
    device_info = DeviceData(
        device=home_data.devices[0],
        model=home_data.products[0].model,
    )
    client = RoborockMqttClientV1(user_data, device_info)
    yield client
    # Clean up any resources after the test


@pytest.fixture(name="mock_rest", autouse=True)
def mock_rest() -> aioresponses:
    """Mock all rest endpoints so they won't hit real endpoints"""
    with aioresponses() as mocked:
        # Match the base URL and allow any query params
        mocked.post(
            re.compile(r"https://euiot\.roborock\.com/api/v1/getUrlByEmail.*"),
            status=200,
            payload={
                "code": 200,
                "data": {"country": "US", "countrycode": "1", "url": "https://usiot.roborock.com"},
                "msg": "success",
            },
        )
        mocked.post(
            re.compile(r"https://.*iot\.roborock\.com/api/v1/login.*"),
            status=200,
            payload={"code": 200, "data": USER_DATA, "msg": "success"},
        )
        mocked.post(
            re.compile(r"https://.*iot\.roborock\.com/api/v1/loginWithCode.*"),
            status=200,
            payload={"code": 200, "data": USER_DATA, "msg": "success"},
        )
        mocked.post(
            re.compile(r"https://.*iot\.roborock\.com/api/v1/sendEmailCode.*"),
            status=200,
            payload={"code": 200, "data": None, "msg": "success"},
        )
        mocked.get(
            re.compile(r"https://.*iot\.roborock\.com/api/v1/getHomeDetail.*"),
            status=200,
            payload={
                "code": 200,
                "data": {"deviceListOrder": None, "id": 123456, "name": "My Home", "rrHomeId": 123456, "tuyaHomeId": 0},
                "msg": "success",
            },
        )
        mocked.get(
            re.compile(r"https://api-.*\.roborock\.com/v2/user/homes*"),
            status=200,
            payload={"api": None, "code": 200, "result": HOME_DATA_RAW, "status": "ok", "success": True},
        )
        yield mocked
