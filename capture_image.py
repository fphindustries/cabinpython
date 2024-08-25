#!/usr/bin/python

from picamera2 import Picamera2
from datetime import date,datetime,timedelta,timezone
from dateutil import tz
from suntime import Sun
import configparser

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


config = configparser.ConfigParser()
config.read('config.ini')

latitude = float(config['Location']['Latitude'])
longitude = float(config['Location']['Longitude'])
sunrise, sunset = get_sunrise_sunset(latitude, longitude)

now = datetime.now(timezone.utc)

if now > sunrise and now < sunset:
  filename = '{:%Y-%m-%d-%H-%M}.jpg'.format(datetime.now())
  localfilename = config['Images']['directory'] + filename

  picam2 = Picamera2()
  config = picam2.create_still_configuration()
  picam2.configure(config)

  picam2.start()

  picam2.capture_file(localfilename)
  picam2.stop()
else:
  print("it's dark out")

