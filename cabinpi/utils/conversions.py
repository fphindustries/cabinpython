"""
Unit conversion utilities for sensor measurements.

Provides functions to convert between different units of measurement.
"""


def mps_to_mph(mps: float) -> float:
    """
    Convert meters per second to miles per hour.

    Args:
        mps: Speed in meters per second

    Returns:
        Speed in miles per hour
    """
    return mps * 2.23694


def mb_to_inhg(mb: float) -> float:
    """
    Convert millibar to inches of mercury.

    Args:
        mb: Pressure in millibar

    Returns:
        Pressure in inches of mercury
    """
    return mb * 0.02953


def celsius_to_fahrenheit(celsius: float) -> float:
    """
    Convert temperature from Celsius to Fahrenheit.

    Args:
        celsius: Temperature in Celsius

    Returns:
        Temperature in Fahrenheit
    """
    return (celsius * 9/5) + 32


def mm_to_inches(mm: float) -> float:
    """
    Convert millimeters to inches.

    Args:
        mm: Length in millimeters

    Returns:
        Length in inches
    """
    return mm / 25.4


def km_to_miles(km: float) -> float:
    """
    Convert kilometers to miles.

    Args:
        km: Distance in kilometers

    Returns:
        Distance in miles
    """
    return km * 0.621371
