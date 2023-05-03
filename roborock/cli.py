from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

import click

from roborock import RoborockException
from roborock.api import RoborockApiClient
from roborock.cloud_api import RoborockMqttClient
from roborock.containers import LoginData, RoborockDeviceInfo
from roborock.util import run_sync

_LOGGER = logging.getLogger(__name__)


class RoborockContext:
    roborock_file = Path("~/.roborock").expanduser()
    _login_data: LoginData | None = None

    def __init__(self):
        self.reload()

    def reload(self):
        if self.roborock_file.is_file():
            with open(self.roborock_file, "r") as f:
                data = json.load(f)
                if data:
                    self._login_data = LoginData.from_dict(data)

    def update(self, login_data: LoginData):
        data = json.dumps(login_data.as_dict(), default=vars)
        with open(self.roborock_file, "w") as f:
            f.write(data)
        self.reload()

    def validate(self):
        if self._login_data is None:
            raise RoborockException("You must login first")

    def login_data(self):
        self.validate()
        return self._login_data


@click.option("-d", "--debug", default=False, count=True)
@click.version_option(package_name="python-roborock")
@click.group()
@click.pass_context
def cli(ctx, debug: int):
    logging_config: Dict[str, Any] = {"level": logging.DEBUG if debug > 0 else logging.INFO}
    logging.basicConfig(**logging_config)  # type: ignore
    ctx.obj = RoborockContext()


@click.command()
@click.option("--email", required=True)
@click.option("--password", required=True)
@click.pass_context
@run_sync()
async def login(ctx, email, password):
    """Login to Roborock account."""
    context: RoborockContext = ctx.obj
    try:
        context.validate()
        _LOGGER.info("Already logged in")
        return
    except RoborockException:
        pass
    client = RoborockApiClient(email)
    user_data = await client.pass_login(password)
    context.update(LoginData(user_data=user_data, email=email))


async def _discover(ctx):
    context: RoborockContext = ctx.obj
    login_data = context.login_data()
    if not login_data:
        raise Exception("You need to login first")
    client = RoborockApiClient(login_data.email)
    home_data = await client.get_home_data(login_data.user_data)
    context.update(LoginData(**login_data.as_dict(), home_data=home_data))
    click.echo(f"Discovered devices {', '.join([device.name for device in home_data.get_all_devices()])}")


@click.command()
@click.pass_context
@run_sync()
async def discover(ctx):
    await _discover(ctx)


@click.command()
@click.pass_context
@run_sync()
async def list_devices(ctx):
    context: RoborockContext = ctx.obj
    login_data = context.login_data()
    if not login_data.home_data:
        await _discover(ctx)
        login_data = context.login_data()
    home_data = login_data.home_data
    device_name_id = ", ".join(
        [f"{device.name}: {device.duid}" for device in home_data.devices + home_data.received_devices]
    )
    click.echo(f"Known devices {device_name_id}")


@click.command()
@click.option("--device_id", required=True)
@click.option("--cmd", required=True)
@click.option("--params", required=False)
@click.pass_context
@run_sync()
async def command(ctx, cmd, device_id, params):
    context: RoborockContext = ctx.obj
    login_data = context.login_data()
    if not login_data.home_data:
        await _discover(ctx)
        login_data = context.login_data()
    home_data = login_data.home_data
    devices = home_data.devices + home_data.received_devices
    device = next((device for device in devices if device.duid == device_id), None)
    if device is None:
        raise RoborockException("No device found")
    model_specification = next(
        (
            product.model_specification
            for product in home_data.products
            if device is not None and product.did == device.duid
        ),
        None,
    )
    if model_specification is None:
        raise RoborockException(f"Could not find model specifications for device {device.name}")
    device_info = RoborockDeviceInfo(device=device, model_specification=model_specification)
    mqtt_client = RoborockMqttClient(login_data.user_data, device_info)
    await mqtt_client.send_command(cmd, params)
    mqtt_client.__del__()


cli.add_command(login)
cli.add_command(discover)
cli.add_command(list_devices)
cli.add_command(command)


def main():
    return cli()


if __name__ == "__main__":
    main()
