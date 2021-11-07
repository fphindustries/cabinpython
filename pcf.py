import pcf8574_io

# You can use up to 8 PCF8574 boards
# the board will start in input mode
# the pins are HIGH in input mode
p1 = pcf8574_io.PCF(0x20)

# You can use multiple boards with different addresses
#p2 = pcf8574_io.PCF(0x21)

# p0 to p7 are the pins name
# INPUT or OUTPUT is the mode
p1.pin_mode("p0", "INPUT")
p1.pin_mode("p1", "INPUT")
p1.pin_mode("p2", "INPUT")
p1.pin_mode("p3", "INPUT")
p1.pin_mode("p4", "INPUT")
p1.pin_mode("p5", "INPUT")
p1.pin_mode("p6", "INPUT")
p1.pin_mode("p7", "INPUT")

while True:
	print(p1.read("p0"))
	print(p1.read("p1"))
	print(p1.read("p2"))
	print(p1.read("p3"))
	print(p1.read("p4"))
	print(p1.read("p5"))
	print(p1.read("p6"))
	print(p1.read("p7"))
