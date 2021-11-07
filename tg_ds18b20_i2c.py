#!/usr/bin/python3
ow_file="/mnt/1wire/28.DA82E4080000/temperature"

file = open(ow_file, "r")
celsius = float(file.read())
file.close()
fahrenheit = (9.0/5.0) * celsius + 32
print("ds18b20,addr=0 celsius={celsius},fahrenheit={fahrenheit}".format(celsius=celsius, fahrenheit=fahrenheit))
