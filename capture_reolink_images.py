#!/usr/bin/env python3
"""
Capture one still image per configured PTZ preset from the Reolink Atlas
camera, at the camera's highest optical resolution (main stream).

Runs on a cron schedule; only captures between sunrise and sunset, same
as capture_image.py. Images are stored under:

  <Images.directory>/<year>/<month>/<day>/<preset name>-<YYYY-mm-dd-HH-MM>.jpg
"""

import argparse
import asyncio
import configparser
import os
import re
from datetime import date, datetime, timedelta, timezone

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from suntime import Sun

from reolink_camera import ReolinkCamera


def get_sunrise_sunset(latitude, longitude):
  """
  Get the sunrise and sunset times for a given latitude and longitude.

  Args:
    latitude (float): The latitude of the location.
    longitude (float): The longitude of the location.

  Returns:
    tuple: A tuple containing the sunrise and sunset times as datetime objects.
  """
  sun = Sun(latitude, longitude)
  today = date.today()
  sr = sun.get_sunrise_time(today)
  ss = sun.get_sunset_time(today)
  if ss < sr:
    ss = sun.get_sunset_time(today + timedelta(days=1))
  return sr, ss

def slugify(name):
  """Turn a preset name into a filesystem-safe token for use in a filename."""
  slug = re.sub(r'[^A-Za-z0-9_-]+', '_', name.strip())
  return slug.strip('_') or 'preset'

def get_r2_client(r2_config):
  """
  Build an S3-compatible client for a Cloudflare R2 bucket from the
  [CloudflareR2] config section. Returns (client, bucket, prefix), or
  (None, None, None) if R2 isn't configured.
  """
  if r2_config is None:
    return None, None, None

  account_id = r2_config.get('account_id', fallback='')
  access_key_id = r2_config.get('access_key_id', fallback='')
  secret_access_key = r2_config.get('secret_access_key', fallback='')
  bucket = r2_config.get('bucket', fallback='')

  if not (account_id and access_key_id and secret_access_key and bucket):
    print('CloudflareR2 not fully configured, skipping remote upload')
    return None, None, None

  endpoint = r2_config.get('endpoint', fallback='') or 'https://{}.r2.cloudflarestorage.com'.format(account_id)
  prefix = r2_config.get('prefix', fallback='').strip('/')

  client = boto3.client(
    's3',
    endpoint_url=endpoint,
    aws_access_key_id=access_key_id,
    aws_secret_access_key=secret_access_key,
    region_name='auto',
  )
  return client, bucket, prefix

def upload_to_r2(r2_client, bucket, prefix, local_path, key):
  """Best-effort upload of a local file to R2; failures are logged, not raised."""
  object_key = '{}/{}'.format(prefix, key) if prefix else key
  try:
    print('  Uploading -> r2://{}/{}'.format(bucket, object_key))
    r2_client.upload_file(local_path, bucket, object_key)
  except (BotoCoreError, ClientError) as e:
    print('  R2 upload failed for {}: {}'.format(local_path, e))

async def capture_all_presets(reolink_config, images_dir, r2_client, r2_bucket, r2_prefix):
  host = reolink_config.get('host')
  uid = reolink_config.get('uid', '')
  username = reolink_config.get('username', 'admin')
  password = reolink_config.get('password') or os.environ.get('REOLINK_PASS')
  timeout = reolink_config.getfloat('timeout', 30)

  if not password:
    raise SystemExit('Reolink password not set in config.ini [Reolink] or REOLINK_PASS')

  cam = ReolinkCamera(host=host, username=username, password=password, uid=uid, timeout=timeout)
  await cam.login()

  try:
    await cam.wake()

    battery = await cam.get_battery_percentage()
    print('Battery level: {}%'.format(battery))

    if battery <= 25:
      print('Battery level too low ({}%), skipping capture'.format(battery))
      return

    # ptz_presets() returns {preset name: preset id}
    presets = await cam.get_presets()
    if not presets:
      print('No PTZ presets configured on camera')
      return

    now = datetime.now()
    year, month, day = '{:%Y}'.format(now), '{:%m}'.format(now), '{:%d}'.format(now)
    day_dir = os.path.join(images_dir, year, month, day)
    os.makedirs(day_dir, exist_ok=True)

    for preset_name, preset_id in presets.items():
      print('Moving to preset {} ({}) ...'.format(preset_id, preset_name))
      await cam.goto_preset(preset_id)
      await cam.wait_until_settled()  # let the PTZ movement fully settle before snapping

      filename = '{}-{:%Y-%m-%d-%H-%M}.jpg'.format(slugify(preset_name), now)
      local_path = os.path.join(day_dir, filename)

      print('  Capturing snapshot -> {}'.format(local_path))
      await cam.snapshot(path=local_path)

      if r2_client is not None:
        object_key = '/'.join([year, month, day, filename])
        upload_to_r2(r2_client, r2_bucket, r2_prefix, local_path, object_key)
  finally:
    await cam.logout()

def main():
  config = configparser.ConfigParser()
  parser = argparse.ArgumentParser()
  parser.add_argument('--config', help='Path to the configuration file')
  parser.add_argument('--ignore-sunrise-sunset', action='store_true',
                       help='Capture regardless of whether it is currently daytime')
  args = parser.parse_args()
  config_file = args.config if args.config else 'config.ini'
  config.read(config_file)

  if args.ignore_sunrise_sunset:
    is_daytime = True
  else:
    latitude = float(config['Location']['Latitude'])
    longitude = float(config['Location']['Longitude'])
    sunrise, sunset = get_sunrise_sunset(latitude, longitude)
    now = datetime.now(timezone.utc)
    is_daytime = sunrise < now < sunset

  if is_daytime:
    images_dir = config['Images']['directory']
    r2_client, r2_bucket, r2_prefix = get_r2_client(config['CloudflareR2'] if config.has_section('CloudflareR2') else None)
    asyncio.run(capture_all_presets(config['Reolink'], images_dir, r2_client, r2_bucket, r2_prefix))
  else:
    print("it's dark out")

if __name__ == "__main__":
  main()
