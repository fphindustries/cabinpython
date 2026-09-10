#!/usr/bin/env python3
"""
CLI: wake the Atlas PT Ultra (battery camera), optionally move it, snap a still.

Usage examples
--------------
  python3 snap.py                     # wake, snapshot.jpg
  python3 snap.py --move Right        # wake, move right 1s, snapshot.jpg
  python3 snap.py --preset 1          # wake, go to preset 1, snapshot.jpg
  python3 snap.py --presets           # wake, list configured presets
  python3 snap.py --info              # wake, print raw device/channel info
"""

import argparse
import asyncio
import configparser
import json
import os

from reolink_camera import ReolinkCamera

_config = configparser.ConfigParser()
_config.read(os.path.join(os.path.dirname(__file__), "config.ini"))
_reo = _config["Reolink"]

HOST = _reo.get("host", "192.168.1.91")
UID = _reo.get("uid", "")
PASSWORD = _reo.get("password") or os.environ.get("REOLINK_PASS")


async def run(args):
    cam = ReolinkCamera(host=args.host, password=args.password, uid=args.uid)
    await cam.login()
    print(f"Logged in to {args.host}")

    try:
        print("Waking camera …")
        await cam.wake()
        print(f"  sleeping={cam.is_sleeping()}")

        if args.info:
            print((await cam._api.get_raw_host_data())[:4000])

        if args.presets:
            for pid, name in (await cam.get_presets()).items():
                print(f"  id={pid}  name={name}")

        if args.preset is not None:
            print(f"Moving to preset {args.preset} …")
            await cam.goto_preset(args.preset)
            await asyncio.sleep(3)

        if args.move:
            print(f"Moving {args.move} for {args.duration}s …")
            await cam.move(args.move, speed=args.speed, duration=args.duration)

        if args.snap:
            print(f"Taking snapshot → {args.snap}")
            data = await cam.snapshot(path=args.snap)
            print(f"  {len(data):,} bytes written.")

    finally:
        await cam.logout()
        print("Logged out.")


def main():
    p = argparse.ArgumentParser(description="Reolink snapshot + PTZ CLI (reolink-aio)")
    p.add_argument("--host", default=HOST)
    p.add_argument("--uid", default=UID)
    p.add_argument("--password", default=PASSWORD)
    p.add_argument("--move", help="PTZ direction: Left/Right/Up/Down/LeftUp/…")
    p.add_argument("--speed", type=int, default=32, help="PTZ speed 1–64")
    p.add_argument("--duration", type=float, default=1.0, help="Move duration (s)")
    p.add_argument("--preset", type=int, help="Go to preset number before snapping")
    p.add_argument("--snap", default="snapshot.jpg", help="Output JPEG path ('' to skip)")
    p.add_argument("--info", action="store_true", help="Print device info")
    p.add_argument("--presets", action="store_true", help="List PTZ presets")
    args = p.parse_args()

    if not args.password:
        p.error("set REOLINK_PASS or pass --password")

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
