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
from roborock.containers import DeviceData, S7MaxVStatus
from roborock.version_1_apis.roborock_v1_mqtt_client import RoborockV1MqttClient
from roborock.web_api import PreparedRequest, RoborockApiClient
from tests.mock_data import BASE_URL_REQUEST, GET_CODE_RESPONSE, HOME_DATA_RAW, STATUS, USER_DATA


def test_can_create_roborock_client():
    RoborockApiClient("")


def test_can_create_prepared_request():
    PreparedRequest("https://sample.com")


def test_can_create_mqtt_roborock():
    home_data = HomeData.from_dict(HOME_DATA_RAW)
    device_info = DeviceData(device=home_data.devices[0], model=home_data.products[0].model)
    RoborockV1MqttClient(UserData.from_dict(USER_DATA), device_info)


@pytest.mark.asyncio
async def test_sync_connect(mqtt_client):
    with patch("paho.mqtt.client.Client.connect", return_value=mqtt.MQTT_ERR_SUCCESS):
        with patch("paho.mqtt.client.Client.loop_start", return_value=mqtt.MQTT_ERR_SUCCESS):
            connecting, connected_future = mqtt_client.sync_connect()
            assert connecting is True
            assert connected_future is not None

            connected_future.cancel()


@pytest.mark.asyncio
async def test_get_base_url_no_url():
    rc = RoborockApiClient("sample@gmail.com")
    with patch("roborock.web_api.PreparedRequest.request") as mock_request:
        mock_request.return_value = BASE_URL_REQUEST
        await rc._get_base_url()
    assert rc.base_url == "https://sample.com"


@pytest.mark.asyncio
async def test_request_code():
    rc = RoborockApiClient("sample@gmail.com")
    with patch("roborock.web_api.RoborockApiClient._get_base_url"), patch(
        "roborock.web_api.RoborockApiClient._get_header_client_id"
    ), patch("roborock.web_api.PreparedRequest.request") as mock_request:
        mock_request.return_value = GET_CODE_RESPONSE
        await rc.request_code()


@pytest.mark.asyncio
async def test_get_home_data():
    rc = RoborockApiClient("sample@gmail.com")
    with patch("roborock.web_api.RoborockApiClient._get_base_url"), patch(
        "roborock.web_api.RoborockApiClient._get_header_client_id"
    ), patch("roborock.web_api.PreparedRequest.request") as mock_prepared_request:
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
    device_info = DeviceData(device=home_data.devices[0], model=home_data.products[0].model)
    rmc = RoborockV1MqttClient(UserData.from_dict(USER_DATA), device_info)
    with patch("roborock.api.AttributeCache.async_value") as command:
        command.return_value = {"mode": 1}
        dust = await rmc.get_dust_collection_mode()
        assert dust is not None
        assert dust.mode == RoborockDockDustCollectionModeCode.light


@pytest.mark.asyncio
async def test_get_mop_wash_mode():
    home_data = HomeData.from_dict(HOME_DATA_RAW)
    device_info = DeviceData(device=home_data.devices[0], model=home_data.products[0].model)
    rmc = RoborockV1MqttClient(UserData.from_dict(USER_DATA), device_info)
    with patch("roborock.api.AttributeCache.async_value") as command:
        command.return_value = {"smart_wash": 0, "wash_interval": 1500}
        mop_wash = await rmc.get_smart_wash_params()
        assert mop_wash is not None
        assert mop_wash.smart_wash == 0
        assert mop_wash.wash_interval == 1500


@pytest.mark.asyncio
async def test_get_washing_mode():
    home_data = HomeData.from_dict(HOME_DATA_RAW)
    device_info = DeviceData(device=home_data.devices[0], model=home_data.products[0].model)
    rmc = RoborockV1MqttClient(UserData.from_dict(USER_DATA), device_info)
    with patch("roborock.api.AttributeCache.async_value") as command:
        command.return_value = {"wash_mode": 2}
        washing_mode = await rmc.get_wash_towel_mode()
        assert washing_mode is not None
        assert washing_mode.wash_mode == RoborockDockWashTowelModeCode.deep
        assert washing_mode.wash_mode == 2


@pytest.mark.asyncio
async def test_get_prop():
    home_data = HomeData.from_dict(HOME_DATA_RAW)
    device_info = DeviceData(device=home_data.devices[0], model=home_data.products[0].model)
    rmc = RoborockV1MqttClient(UserData.from_dict(USER_DATA), device_info)
    with patch("roborock.version_1_apis.roborock_v1_mqtt_client.RoborockV1MqttClient.get_status") as get_status, patch(
        "roborock.api.RoborockClient.send_command"
    ), patch("roborock.api.AttributeCache.async_value"), patch(
        "roborock.version_1_apis.roborock_v1_mqtt_client.RoborockV1MqttClient.get_dust_collection_mode"
    ):
        status = S7MaxVStatus.from_dict(STATUS)
        status.dock_type = RoborockDockTypeCode.auto_empty_dock_pure
        get_status.return_value = status

        props = await rmc.get_prop()
        assert props
        assert props.dock_summary
        assert props.dock_summary.wash_towel_mode is None
        assert props.dock_summary.smart_wash_params is None
        assert props.dock_summary.dust_collection_mode is not None
