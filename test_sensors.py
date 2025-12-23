#!/usr/bin/env python3
"""
Test script for SHT45, INA228, and DS18B20 sensors.

This script tests each sensor independently and reports results.
Run this before testing with the full daemon.

Usage:
    python3 test_sensors.py [--all] [--sht45] [--ina228] [--ds18b20]

    --all       Test all sensors (default)
    --sht45     Test SHT45 only
    --ina228    Test INA228 only
    --ds18b20   Test DS18B20 only
"""

import asyncio
import sys
import argparse
from datetime import datetime
from typing import Optional, Dict, Any


def print_header(title: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_reading(sensor_name: str, reading_num: int, measurements: Dict[str, Any], error: Optional[str] = None) -> None:
    """Print a formatted sensor reading."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{timestamp}] {sensor_name} - Reading #{reading_num}")

    if error:
        print(f"  ERROR: {error}")
    else:
        for key, value in measurements.items():
            if isinstance(value, float):
                print(f"  {key:20s}: {value:.4f}")
            else:
                print(f"  {key:20s}: {value}")


async def test_sht45(num_readings: int = 5) -> bool:
    """
    Test SHT45 temperature and humidity sensor.

    Args:
        num_readings: Number of readings to take

    Returns:
        True if all readings successful
    """
    print_header("Testing SHT45 Temperature/Humidity Sensor")

    try:
        # Import directly from module to avoid loading all sensors
        import sys
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "sht45",
            "/home/ckent/repos/cabinpython/cabinpi/plugins/sensors/sht45.py"
        )
        sht45_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sht45_module)
        SHT45Sensor = sht45_module.SHT45Sensor
    except ImportError as e:
        print(f"ERROR: Failed to import SHT45Sensor: {e}")
        print("Make sure smbus2 is installed: pip install smbus2")
        return False
    except Exception as e:
        print(f"ERROR: Failed to load SHT45 module: {e}")
        return False

    sensor = SHT45Sensor("test_sht45")

    config = {
        "i2c_bus": 1,
        "i2c_address": 0x44,
        "repeatability": "high"
    }

    print(f"\nConfiguration:")
    print(f"  I2C Bus: {config['i2c_bus']}")
    print(f"  I2C Address: 0x{config['i2c_address']:02X}")
    print(f"  Repeatability: {config['repeatability']}")

    # Initialize
    print("\nInitializing sensor...")
    if not await sensor.initialize(config):
        print("ERROR: Sensor initialization failed!")
        print("Check:")
        print("  - I2C is enabled (sudo raspi-config)")
        print("  - Sensor is connected properly")
        print("  - I2C address is correct (run: i2cdetect -y 1)")
        return False

    print("SUCCESS: Sensor initialized")

    # Take readings
    print(f"\nTaking {num_readings} readings (1 second interval)...")
    success_count = 0

    for i in range(num_readings):
        reading = await sensor.read()

        if reading.is_valid:
            print_reading("SHT45", i + 1, reading.measurements)
            success_count += 1
        else:
            print_reading("SHT45", i + 1, {}, reading.error)

        if i < num_readings - 1:
            await asyncio.sleep(1)

    # Cleanup
    await sensor.shutdown()

    print(f"\n{'=' * 70}")
    print(f"SHT45 Test Complete: {success_count}/{num_readings} successful")
    print(f"{'=' * 70}")

    return success_count == num_readings


async def test_ina228(num_readings: int = 5) -> bool:
    """
    Test INA228 power monitor sensor.

    Args:
        num_readings: Number of readings to take

    Returns:
        True if all readings successful
    """
    print_header("Testing INA228 Power Monitor")

    try:
        # Import directly from module to avoid loading all sensors
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "ina228",
            "/home/ckent/repos/cabinpython/cabinpi/plugins/sensors/ina228.py"
        )
        ina228_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ina228_module)
        INA228Sensor = ina228_module.INA228Sensor
    except ImportError as e:
        print(f"ERROR: Failed to import INA228Sensor: {e}")
        print("Make sure smbus2 is installed: pip install smbus2")
        return False
    except Exception as e:
        print(f"ERROR: Failed to load INA228 module: {e}")
        return False

    sensor = INA228Sensor("test_ina228")

    config = {
        "i2c_bus": 1,
        "i2c_address": 0x40,
        "shunt_resistor": 0.015,    # 15 milliohm
        "max_current": 10.0,        # 10A max
        "label": "test_battery"
    }

    print(f"\nConfiguration:")
    print(f"  I2C Bus: {config['i2c_bus']}")
    print(f"  I2C Address: 0x{config['i2c_address']:02X}")
    print(f"  Shunt Resistor: {config['shunt_resistor']}Ω ({config['shunt_resistor']*1000}mΩ)")
    print(f"  Max Current: {config['max_current']}A")
    print(f"  Label: {config['label']}")

    # Initialize
    print("\nInitializing sensor...")
    if not await sensor.initialize(config):
        print("ERROR: Sensor initialization failed!")
        print("Check:")
        print("  - I2C is enabled (sudo raspi-config)")
        print("  - Sensor is connected properly")
        print("  - I2C address is correct (run: i2cdetect -y 1)")
        print("  - No address conflict with other I2C devices")
        return False

    print("SUCCESS: Sensor initialized")

    # Take readings
    print(f"\nTaking {num_readings} readings (1 second interval)...")
    success_count = 0

    for i in range(num_readings):
        reading = await sensor.read()

        if reading.is_valid:
            print_reading("INA228", i + 1, reading.measurements)
            success_count += 1
        else:
            print_reading("INA228", i + 1, {}, reading.error)

        if i < num_readings - 1:
            await asyncio.sleep(1)

    # Cleanup
    await sensor.shutdown()

    print(f"\n{'=' * 70}")
    print(f"INA228 Test Complete: {success_count}/{num_readings} successful")
    print(f"{'=' * 70}")

    return success_count == num_readings


async def test_ds18b20(num_readings: int = 5) -> bool:
    """
    Test DS18B20 1-wire temperature sensor.

    Args:
        num_readings: Number of readings to take

    Returns:
        True if all readings successful
    """
    print_header("Testing DS18B20 1-Wire Temperature Sensor")

    try:
        # Import directly from module to avoid loading all sensors
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "ds18b20",
            "/home/ckent/repos/cabinpython/cabinpi/plugins/sensors/ds18b20.py"
        )
        ds18b20_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ds18b20_module)
        DS18B20Sensor = ds18b20_module.DS18B20Sensor
    except ImportError as e:
        print(f"ERROR: Failed to import DS18B20Sensor: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Failed to load DS18B20 module: {e}")
        return False

    sensor = DS18B20Sensor("test_ds18b20")

    config = {
        "label": "outdoor",
        # "device_id": "28-xxxxxxxxxxxx"  # Auto-detect if not specified
    }

    print(f"\nConfiguration:")
    print(f"  Label: {config['label']}")
    print(f"  Device ID: Auto-detect (will find first DS18B20)")

    # Initialize
    print("\nInitializing sensor...")
    if not await sensor.initialize(config):
        print("ERROR: Sensor initialization failed!")
        print("Check:")
        print("  - 1-wire is enabled in /boot/firmware/config.txt")
        print("    Add: dtoverlay=w1-gpio")
        print("  - Reboot after enabling 1-wire")
        print("  - DS18B20 is connected to GPIO4 (default)")
        print("  - Check for devices: ls /sys/bus/w1/devices/28-*")
        return False

    print("SUCCESS: Sensor initialized")

    # Take readings
    print(f"\nTaking {num_readings} readings (2 second interval)...")
    success_count = 0

    for i in range(num_readings):
        reading = await sensor.read()

        if reading.is_valid:
            print_reading("DS18B20", i + 1, reading.measurements)
            success_count += 1
        else:
            print_reading("DS18B20", i + 1, {}, reading.error)

        if i < num_readings - 1:
            await asyncio.sleep(2)  # DS18B20 needs more time between reads

    # Cleanup
    await sensor.shutdown()

    print(f"\n{'=' * 70}")
    print(f"DS18B20 Test Complete: {success_count}/{num_readings} successful")
    print(f"{'=' * 70}")

    return success_count == num_readings


async def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description="Test CabinPython sensors")
    parser.add_argument('--all', action='store_true', help='Test all sensors (default)')
    parser.add_argument('--sht45', action='store_true', help='Test SHT45 only')
    parser.add_argument('--ina228', action='store_true', help='Test INA228 only')
    parser.add_argument('--ds18b20', action='store_true', help='Test DS18B20 only')
    parser.add_argument('--readings', type=int, default=5, help='Number of readings per sensor (default: 5)')

    args = parser.parse_args()

    # Default to all if no specific sensor selected
    test_all = args.all or not (args.sht45 or args.ina228 or args.ds18b20)

    results = {}

    print("\n" + "=" * 70)
    print("  CabinPython Sensor Test Suite")
    print("=" * 70)
    print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Test SHT45
    if test_all or args.sht45:
        try:
            results['SHT45'] = await test_sht45(args.readings)
        except KeyboardInterrupt:
            print("\n\nTest interrupted by user")
            return 1
        except Exception as e:
            print(f"\n\nERROR during SHT45 test: {e}")
            import traceback
            traceback.print_exc()
            results['SHT45'] = False

    # Test INA228
    if test_all or args.ina228:
        try:
            results['INA228'] = await test_ina228(args.readings)
        except KeyboardInterrupt:
            print("\n\nTest interrupted by user")
            return 1
        except Exception as e:
            print(f"\n\nERROR during INA228 test: {e}")
            import traceback
            traceback.print_exc()
            results['INA228'] = False

    # Test DS18B20
    if test_all or args.ds18b20:
        try:
            results['DS18B20'] = await test_ds18b20(args.readings)
        except KeyboardInterrupt:
            print("\n\nTest interrupted by user")
            return 1
        except Exception as e:
            print(f"\n\nERROR during DS18B20 test: {e}")
            import traceback
            traceback.print_exc()
            results['DS18B20'] = False

    # Print summary
    print("\n\n" + "=" * 70)
    print("  TEST SUMMARY")
    print("=" * 70)

    for sensor_name, success in results.items():
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"  {sensor_name:15s}: {status}")

    print("=" * 70)
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Return exit code
    all_passed = all(results.values())
    return 0 if all_passed else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
