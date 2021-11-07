#!/usr/bin/python

from io import BytesIO
from time import sleep
from picamera import PiCamera
from picamera import Color
from PIL import Image
from datetime import datetime
from paramiko import SSHClient
from scp import SCPClient


# Create the in-memory stream
stream = BytesIO()
camera = PiCamera()
camera.resolution = (3280,2464)
#camera.start_preview()
#sleep(3)

camera.annotate_foreground = Color('black')
camera.annotate_text = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
camera.awb_mode ='sunlight'
sleep(2)
camera.capture(stream, format='jpeg')
# "Rewind" the stream to the beginning so we can read its content
stream.seek(0)
image = Image.open(stream)
extrema = image.convert("L").getextrema()
if extrema[1] > 100:
  print(extrema[1])
  filename = '{:%Y-%m-%d-%H-%M}.jpg'.format(datetime.now())
  localfilename = '/opt/cabinpython/images/' + filename
  print(filename)

  image.save(localfilename, "JPEG", quality=90, optimize=True)

  ssh = SSHClient()
  ssh.load_system_host_keys()
  ssh.connect('cabinpi.fphi.us')

  # SCPCLient takes a paramiko transport as an argument
  scp = SCPClient(ssh.get_transport())

  scp.put(localfilename, '/opt/images/' + filename)
  scp.close()
