import pytest

from roborock import RoborockMqttClient, UserData, HomeData, RoborockDeviceInfo
from tests.mock_data import USER_DATA, HOME_DATA_RAW


@pytest.fixture(name="mqtt_client")
def mqtt_client():
    user_data = UserData(USER_DATA)
    home_data = HomeData(HOME_DATA_RAW)
    device = RoborockDeviceInfo(home_data.devices[0], home_data.products[0])
    device_map = {home_data.devices[0].duid: device}
    client = RoborockMqttClient(user_data, device_map)
    yield client
    # Clean up any resources after the test
