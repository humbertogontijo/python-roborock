from unittest.mock import patch

import pytest

from roborock import RoborockClient, UserData, HomeData
from roborock.api import PreparedRequest
from tests.mock_data import BASE_URL_REQUEST, GET_CODE_RESPONSE, USER_DATA, HOME_DATA_RAW


def test_can_create_roborock_client():
    RoborockClient("")


def test_can_create_prepared_request():
    PreparedRequest("https://sample.com")


@pytest.mark.asyncio
async def test_get_base_url_no_url():
    rc = RoborockClient("sample@gmail.com")
    with patch("roborock.api.PreparedRequest.request") as mock_request:
        mock_request.return_value = BASE_URL_REQUEST
        await rc._get_base_url()
    assert rc.base_url == "https://sample.com"


@pytest.mark.asyncio
async def test_request_code():
    rc = RoborockClient("sample@gmail.com")
    with patch("roborock.api.RoborockClient._get_base_url") as mock_url, patch(
        "roborock.api.RoborockClient._get_header_client_id") as mock_header_client, patch(
        "roborock.api.PreparedRequest.request") as mock_request:
        mock_request.return_value = GET_CODE_RESPONSE
        await rc.request_code()


@pytest.mark.asyncio
async def test_get_home_data():
    rc = RoborockClient("sample@gmail.com")
    with patch("roborock.api.RoborockClient._get_base_url") as mock_url, patch(
        "roborock.api.RoborockClient._get_header_client_id") as mock_header_client, patch(
        "roborock.api.PreparedRequest.request") as mock_prepared_request:
        mock_prepared_request.side_effect = [{'code': 200, 'msg': 'success', 'data': {"rrHomeId": 1}},
                                             {'code': 200, 'success': True, 'result': HOME_DATA_RAW}]

        user_data = UserData(USER_DATA)
        result = await rc.get_home_data(user_data)

        assert result == HomeData(HOME_DATA_RAW)
