import pytest

from roborock import HomeData, UserData
from roborock.containers import DeviceData
from roborock.version_1_apis.roborock_v1_mqtt_client import RoborockV1MqttClient
from tests.mock_data import HOME_DATA_RAW, USER_DATA


@pytest.fixture(name="mqtt_client")
def mqtt_client():
    user_data = UserData.from_dict(USER_DATA)
    home_data = HomeData.from_dict(HOME_DATA_RAW)
    device_info = DeviceData(
        device=home_data.devices[0],
        model=home_data.products[0].model,
    )
    client = RoborockV1MqttClient(user_data, device_info)
    yield client
    # Clean up any resources after the test
