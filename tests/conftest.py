import pytest

from roborock import RoborockMqttClient, UserData, HomeData
from tests.mock_data import USER_DATA, HOME_DATA_RAW


@pytest.fixture(name="mqtt_client")
def mqtt_client():
    user_data = UserData.from_dict(USER_DATA)
    home_data = HomeData.from_dict(HOME_DATA_RAW)
    device_map = {home_data.devices[0].duid: home_data.devices[0].local_key}
    client = RoborockMqttClient(user_data, device_map)
    yield client
    # Clean up any resources after the test
