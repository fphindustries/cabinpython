"""
Reolink Atlas PT Ultra camera controller, built on reolink-aio.

reolink-aio (the library behind the Home Assistant Reolink integration)
speaks both the HTTP/HTTPS JSON API and Reolink's proprietary Baichuan
protocol (TCP port 9000). Baichuan is what the official app uses to wake
a dozing battery camera before talking to it — plain HTTP polling cannot
do this, since a sleeping camera's HTTP server is powered down entirely.

All I/O here is asyncio; wrap calls with asyncio.run() from sync code.
"""

import asyncio
import os
from typing import Optional

from reolink_aio.api import Host
from reolink_aio.enums import ConnectionEnum


class ReolinkCamera:
    def __init__(
        self,
        host: str,
        username: str = "admin",
        password: str = "",
        channel: int = 0,
        uid: str = "Unknown",
        timeout: float = 30,
    ):
        self.channel = channel
        self._api = Host(
            host,
            username,
            password,
            bc_only=True,
            bc_connection=ConnectionEnum.udp,
            uid=uid,
            timeout=timeout,
        )

    async def login(self) -> None:
        await self._api.baichuan.login()

    async def logout(self) -> None:
        await self._api.logout()

    async def __aenter__(self):
        await self.login()
        return self

    async def __aexit__(self, *_):
        await self.logout()

    # ── Wake / state ──────────────────────────────────────────────────────────

    async def wake(self) -> None:
        """
        Force the camera awake via a Baichuan wake signal, same mechanism
        the Reolink app uses. Safe to call even if already awake.
        """
        await self._api.baichuan.login()

    def is_sleeping(self) -> bool:
        return bool(self._api.sleeping(self.channel))

    async def get_battery_percentage(self) -> int:
        """Refresh and return the camera's battery percentage."""
        await self._api.baichuan.get_battery_info(self.channel)
        percentage = self._api.battery_percentage(self.channel)
        if percentage is None:
            raise RuntimeError("Camera returned no battery percentage.")
        return percentage

    # ── PTZ ──────────────────────────────────────────────────────────────────

    PTZ_COMMANDS = frozenset(
        [
            "Left", "Right", "Up", "Down",
            "LeftUp", "LeftDown", "RightUp", "RightDown",
            "ZoomInc", "ZoomDec", "Stop", "ToPos", "Auto",
        ]
    )

    async def ptz(self, command: str, speed: Optional[int] = None, preset: Optional[int] = None) -> None:
        if command not in self.PTZ_COMMANDS:
            raise ValueError(f"Unknown PTZ command '{command}'. Valid: {sorted(self.PTZ_COMMANDS)}")
        api_command: Optional[str] = command
        if command == "ToPos":
            if preset is None:
                raise ValueError("The ToPos command requires a preset ID.")
            # reolink-aio derives ToPos from the preset argument. Passing
            # command="ToPos" explicitly fails its command validation.
            api_command = None
        await self._api.set_ptz_command(self.channel, command=api_command, preset=preset, speed=speed)

    async def move(self, direction: str, speed: int = 32, duration: float = 1.0) -> None:
        """Move in direction, wait duration seconds, then stop."""
        await self.ptz(direction, speed=speed)
        await asyncio.sleep(duration)
        await self.ptz("Stop")

    async def goto_preset(self, preset_id: int) -> None:
        await self.ptz("ToPos", preset=preset_id)

    async def stop(self) -> None:
        await self.ptz("Stop")

    async def wait_until_settled(
        self,
        poll_interval: float = 0.5,
        stable_reads: int = 2,
        timeout: float = 10.0,
    ) -> None:
        """
        Block until the PTZ mechanism stops moving (pan/tilt position is
        unchanged across `stable_reads` consecutive polls), or `timeout`
        seconds have elapsed, whichever comes first. A large move (e.g.
        between distant presets) can take longer to settle than a fixed
        delay would assume, which otherwise risks motion blur in the
        snapshot taken right after.
        """
        last_position = None
        stable_count = 0
        elapsed = 0.0

        while elapsed < timeout:
            await self._api.baichuan.get_ptz_position(self.channel)
            position = (
                self._api.ptz_pan_position(self.channel),
                self._api.ptz_tilt_position(self.channel),
            )

            if position == last_position and position != (None, None):
                stable_count += 1
                if stable_count >= stable_reads:
                    return
            else:
                stable_count = 0

            last_position = position
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

    async def get_presets(self) -> dict:
        # Query only presets. A full get_states() fans out concurrent requests,
        # which can race during the initial UDP session with a battery camera.
        await self._api.baichuan.get_ptz_preset(self.channel)
        return self._api.ptz_presets(self.channel)

    # ── Snapshot ──────────────────────────────────────────────────────────────

    async def snapshot(self, path: Optional[str] = None) -> bytes:
        data = await self._api.baichuan.snapshot(self.channel, snapType="main")
        if data is None:
            raise RuntimeError("Camera returned no snapshot data.")
        if path:
            with open(path, "wb") as f:
                f.write(data)
        return data
