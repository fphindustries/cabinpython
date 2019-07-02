#!/usr/bin/python3
ow_file="/mnt/1wire/28.0EFE79971103/temperature"

file = open(ow_file, "r")
celsius = float(file.read())
file.close()
fahrenheit = (9.0/5.0) * celsius + 32
print(f'ds18b20,addr=0 celsius={celsius},fahrenheit={fahrenheit}')
