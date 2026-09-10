#!/usr/bin/env python3
"""Read battery state from a Reolink battery camera over Baichuan UDP."""

import argparse
import asyncio
import os

from reolink_aio.api import Host
from reolink_aio.enums import BatteryEnum, ConnectionEnum


async def read_battery(args: argparse.Namespace) -> None:
    password = os.environ.get("REOLINK_PASS")
    if not password:
        raise SystemExit("REOLINK_PASS is not set")

    host = Host(
        host=args.host,
        username=args.username,
        password=password,
        bc_only=True,
        bc_connection=ConnectionEnum.udp,
        uid=args.uid,
        timeout=args.timeout,
    )
    try:
        await asyncio.wait_for(
            host.baichuan.get_battery_info(args.channel),
            timeout=args.timeout,
        )
        # get_host_data() fans out concurrent Baichuan calls, which can race
        # during the initial UDP login on a sleeping battery camera. Fetch the
        # optional display metadata sequentially after the battery query.
        try:
            await asyncio.wait_for(host.baichuan.get_info(), timeout=5)
        except Exception:
            pass
        raw_status = host.battery_status(args.channel)
        try:
            status = BatteryEnum(raw_status).name
        except ValueError:
            status = f"unknown ({raw_status})"

        print(f"model: {host.model}")
        print(f"firmware: {host.sw_version}")
        print(f"connection: {host.baichuan.connection_type.value}")
        print(f"battery: {host.battery_percentage(args.channel)}%")
        print(f"temperature: {host.battery_temperature(args.channel)} C")
        print(f"status: {status}")
        print(f"sleeping: {host.sleeping(args.channel)}")
    finally:
        try:
            await asyncio.wait_for(host.logout(), timeout=5)
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="192.168.1.91")
    parser.add_argument("--uid", default="9527000KAS6O7O8R")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--channel", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=30)
    asyncio.run(read_battery(parser.parse_args()))


if __name__ == "__main__":
    main()
