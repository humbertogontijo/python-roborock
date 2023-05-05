import pytest

from roborock import HomeData, UserData
from roborock.cloud_api import RoborockMqttClient
from roborock.containers import DeviceData
from tests.mock_data import HOME_DATA_RAW, USER_DATA


@pytest.fixture(name="mqtt_client")
def mqtt_client():
    user_data = UserData.from_dict(USER_DATA)
    home_data = HomeData.from_dict(HOME_DATA_RAW)
    device_info = DeviceData(
        device=home_data.devices[0],
        model=home_data.products[0].model,
    )
    client = RoborockMqttClient(user_data, device_info)
    yield client
    # Clean up any resources after the test
