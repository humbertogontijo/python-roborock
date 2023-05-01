from unittest.mock import patch

import paho.mqtt.client as mqtt
import pytest

from roborock import (
    HomeData,
    RoborockDockDustCollectionModeCode,
    RoborockDockTypeCode,
    RoborockDockWashTowelModeCode,
    UserData,
)
from roborock.api import PreparedRequest, RoborockApiClient
from roborock.cloud_api import RoborockMqttClient
from roborock.containers import RoborockDeviceInfo, Status
from tests.mock_data import BASE_URL_REQUEST, GET_CODE_RESPONSE, HOME_DATA_RAW, STATUS, USER_DATA


def test_can_create_roborock_client():
    RoborockApiClient("")


def test_can_create_prepared_request():
    PreparedRequest("https://sample.com")


def test_can_create_mqtt_roborock():
    home_data = HomeData.from_dict(HOME_DATA_RAW)
    device_info = RoborockDeviceInfo(
        device=home_data.devices[0], model_specification=home_data.products[0].model_specification
    )
    RoborockMqttClient(UserData.from_dict(USER_DATA), device_info)


def test_sync_connect(mqtt_client):
    with patch("paho.mqtt.client.Client.connect", return_value=mqtt.MQTT_ERR_SUCCESS):
        with patch("paho.mqtt.client.Client.loop_start", return_value=mqtt.MQTT_ERR_SUCCESS):
            mqtt_client.sync_connect()


@pytest.mark.asyncio
async def test_get_base_url_no_url():
    rc = RoborockApiClient("sample@gmail.com")
    with patch("roborock.api.PreparedRequest.request") as mock_request:
        mock_request.return_value = BASE_URL_REQUEST
        await rc._get_base_url()
    assert rc.base_url == "https://sample.com"


@pytest.mark.asyncio
async def test_request_code():
    rc = RoborockApiClient("sample@gmail.com")
    with patch("roborock.api.RoborockApiClient._get_base_url"), patch(
        "roborock.api.RoborockApiClient._get_header_client_id"
    ), patch("roborock.api.PreparedRequest.request") as mock_request:
        mock_request.return_value = GET_CODE_RESPONSE
        await rc.request_code()


@pytest.mark.asyncio
async def test_get_home_data():
    rc = RoborockApiClient("sample@gmail.com")
    with patch("roborock.api.RoborockApiClient._get_base_url"), patch(
        "roborock.api.RoborockApiClient._get_header_client_id"
    ), patch("roborock.api.PreparedRequest.request") as mock_prepared_request:
        mock_prepared_request.side_effect = [
            {"code": 200, "msg": "success", "data": {"rrHomeId": 1}},
            {"code": 200, "success": True, "result": HOME_DATA_RAW},
        ]

        user_data = UserData.from_dict(USER_DATA)
        result = await rc.get_home_data(user_data)

        assert result == HomeData.from_dict(HOME_DATA_RAW)


@pytest.mark.asyncio
async def test_get_dust_collection_mode():
    home_data = HomeData.from_dict(HOME_DATA_RAW)
    device_info = RoborockDeviceInfo(
        device=home_data.devices[0], model_specification=home_data.products[0].model_specification
    )
    rmc = RoborockMqttClient(UserData.from_dict(USER_DATA), device_info)
    with patch("roborock.cloud_api.RoborockMqttClient.send_command") as command:
        command.return_value = {"mode": 1}
        dust = await rmc.get_dust_collection_mode()
        assert dust is not None
        assert dust.mode == RoborockDockDustCollectionModeCode.light


@pytest.mark.asyncio
async def test_get_mop_wash_mode():
    home_data = HomeData.from_dict(HOME_DATA_RAW)
    device_info = RoborockDeviceInfo(
        device=home_data.devices[0], model_specification=home_data.products[0].model_specification
    )
    rmc = RoborockMqttClient(UserData.from_dict(USER_DATA), device_info)
    with patch("roborock.cloud_api.RoborockMqttClient.send_command") as command:
        command.return_value = {"smart_wash": 0, "wash_interval": 1500}
        mop_wash = await rmc.get_smart_wash_params()
        assert mop_wash is not None
        assert mop_wash.smart_wash == 0
        assert mop_wash.wash_interval == 1500


@pytest.mark.asyncio
async def test_get_washing_mode():
    home_data = HomeData.from_dict(HOME_DATA_RAW)
    device_info = RoborockDeviceInfo(
        device=home_data.devices[0], model_specification=home_data.products[0].model_specification
    )
    rmc = RoborockMqttClient(UserData.from_dict(USER_DATA), device_info)
    with patch("roborock.cloud_api.RoborockMqttClient.send_command") as command:
        command.return_value = {"wash_mode": 2}
        washing_mode = await rmc.get_wash_towel_mode()
        assert washing_mode is not None
        assert washing_mode.wash_mode == RoborockDockWashTowelModeCode.deep
        assert washing_mode.wash_mode == 2


@pytest.mark.asyncio
async def test_get_prop():
    home_data = HomeData.from_dict(HOME_DATA_RAW)
    device_info = RoborockDeviceInfo(
        device=home_data.devices[0], model_specification=home_data.products[0].model_specification
    )
    rmc = RoborockMqttClient(UserData.from_dict(USER_DATA), device_info)
    with patch("roborock.cloud_api.RoborockMqttClient.get_status") as get_status, patch(
        "roborock.cloud_api.RoborockMqttClient.send_command"
    ), patch("roborock.cloud_api.RoborockMqttClient.get_dust_collection_mode"):
        status = Status.from_dict(STATUS)
        status.update_status(home_data.products[0].model_specification)
        status.dock_type = RoborockDockTypeCode.auto_empty_dock_pure
        get_status.return_value = status

        props = await rmc.get_prop()
        assert props
        assert props.dock_summary
        assert props.dock_summary.wash_towel_mode is None
        assert props.dock_summary.smart_wash_params is None
        assert props.dock_summary.dust_collection_mode is not None
