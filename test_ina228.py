#!/opt/cabinpython/env/bin/python3

"""
Test script for reading INA228 power monitor sensor via I2C.
The INA228 measures voltage, current, and power.
Uses the Adafruit CircuitPython INA228 library.
"""

import board
import time
import adafruit_ina228


def main():
    """Main test function."""
    print("INA228 Power Monitor Test (using Adafruit library)")
    print("=" * 50)

    try:
        # Initialize I2C
        i2c = board.I2C()

        # Initialize INA228 using Adafruit library
        # Adafruit INA228 board uses 0.015Ω (15mΩ) shunt resistor
        # Default address is 0x40, can be 0x41-0x4F depending on A0/A1 pins
        print("Initializing INA228 sensor...")
        ina228 = adafruit_ina228.INA228(i2c, address=0x40)

        # Configure the shunt resistor value (in ohms)
        # Adafruit INA228 board typically uses 0.015Ω (15mΩ)
        print(f"Configuring shunt resistor: 0.015Ω (15mΩ)")

        # The Adafruit library handles calibration internally
        # You can adjust max expected current if needed (default is usually good)

        # Wait for first measurement to complete (INA228 needs time to settle)
        print("Waiting for sensor to settle...")
        time.sleep(0.2)  # 200ms settling time

        print("\nStarting continuous measurements...")
        print("Press Ctrl+C to exit\n")

        # Continuous reading loop
        while True:
            # Read measurements from the sensor
            bus_voltage = ina228.bus_voltage  # in Volts
            shunt_voltage = ina228.shunt_voltage  # in Volts (convert to mV for display)
            current = ina228.current  # in Amperes (can be negative for charging)
            power = ina228.power  # in Watts

            print(f"Bus Voltage:   {bus_voltage:8.3f} V")
            print(f"Shunt Voltage: {shunt_voltage * 1000:8.3f} mV")  # Convert V to mV
            print(f"Current:       {current:8.3f} A")
            print(f"Power:         {power:8.3f} W")
            print("-" * 50)

            time.sleep(2)

    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
