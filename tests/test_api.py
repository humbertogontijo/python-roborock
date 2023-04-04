from unittest.mock import patch

import paho.mqtt.client as mqtt
import pytest

from roborock import RoborockApiClient, UserData, HomeData, RoborockDockDustCollectionType, RoborockDockWashingModeType
from roborock.api import PreparedRequest
from roborock.cloud_api import RoborockMqttClient
from tests.mock_data import BASE_URL_REQUEST, GET_CODE_RESPONSE, USER_DATA, HOME_DATA_RAW


def test_can_create_roborock_client():
    RoborockApiClient("")


def test_can_create_prepared_request():
    PreparedRequest("https://sample.com")


def test_can_create_mqtt_roborock():
    home_data = HomeData(HOME_DATA_RAW)
    device_map = {home_data.devices[0].duid: home_data.devices[0]}
    RoborockMqttClient(UserData(USER_DATA), device_map)


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
    with patch("roborock.api.RoborockApiClient._get_base_url") as mock_url, patch(
        "roborock.api.RoborockApiClient._get_header_client_id") as mock_header_client, patch(
        "roborock.api.PreparedRequest.request") as mock_request:
        mock_request.return_value = GET_CODE_RESPONSE
        await rc.request_code()


@pytest.mark.asyncio
async def test_get_home_data():
    rc = RoborockApiClient("sample@gmail.com")
    with patch("roborock.api.RoborockApiClient._get_base_url") as mock_url, patch(
        "roborock.api.RoborockApiClient._get_header_client_id") as mock_header_client, patch(
        "roborock.api.PreparedRequest.request") as mock_prepared_request:
        mock_prepared_request.side_effect = [{'code': 200, 'msg': 'success', 'data': {"rrHomeId": 1}},
                                             {'code': 200, 'success': True, 'result': HOME_DATA_RAW}]

        user_data = UserData(USER_DATA)
        result = await rc.get_home_data(user_data)

        assert result == HomeData(HOME_DATA_RAW)


@pytest.mark.asyncio
async def test_get_dust_collection_mode():
    home_data = HomeData(HOME_DATA_RAW)
    device_map = {home_data.devices[0].duid: home_data.devices[0]}
    rmc = RoborockMqttClient(UserData(USER_DATA), device_map)
    with patch("roborock.cloud_api.RoborockMqttClient.send_command") as command:
        command.return_value = {"mode": 1}
        dust = await rmc.get_dust_collection_mode(home_data.devices[0].duid)
        assert dust.mode == RoborockDockDustCollectionType.LIGHT


@pytest.mark.asyncio
async def test_get_mop_wash_mode():
    home_data = HomeData(HOME_DATA_RAW)
    device_map = {home_data.devices[0].duid: home_data.devices[0]}
    rmc = RoborockMqttClient(UserData(USER_DATA), device_map)
    with patch("roborock.cloud_api.RoborockMqttClient.send_command") as command:
        command.return_value = {'smart_wash': 0, 'wash_interval': 1500}
        mop_wash = await rmc.get_smart_wash_params(home_data.devices[0].duid)
        assert mop_wash.smart_wash == 0
        assert mop_wash.wash_interval == 1500


@pytest.mark.asyncio
async def test_get_washing_mode():
    home_data = HomeData(HOME_DATA_RAW)
    device_map = {home_data.devices[0].duid: home_data.devices[0]}
    rmc = RoborockMqttClient(UserData(USER_DATA), device_map)
    with patch("roborock.cloud_api.RoborockMqttClient.send_command") as command:
        command.return_value = {'wash_mode': 2}
        washing_mode = await rmc.get_wash_towel_mode(home_data.devices[0].duid)
        assert washing_mode.wash_mode == RoborockDockWashingModeType.DEEP
