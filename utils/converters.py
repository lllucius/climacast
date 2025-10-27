#!/usr/bin/python3

# =============================================================================
#
# Copyright 2017 by Leland Lucius
#
# Released under the GNU Affero GPL
# See: https://github.com/lllucius/climacast/blob/master/LICENSE
#
# =============================================================================

"""
Unit conversion utilities for Clima Cast.

This module provides utility functions for converting between different units
of measurement (temperature, pressure, distance, etc.).
"""

from typing import Optional, Tuple, Union


def to_skys(percent: Optional[float], isday: bool) -> Optional[str]:
    """
    Convert the sky cover percentage to text.

    Args:
        percent: Sky cover percentage (0-100)
        isday: True if daytime, False if nighttime

    Returns:
        Text description of sky conditions
    """
    if percent is not None:
        if 0.0 <= percent < 12.5:
            return "sunny" if isday else "clear"
        elif 12.5 <= percent < 25.0:
            return "mostly sunny" if isday else "mostly clear"
        elif 25.0 <= percent < 50.0:
            return "partly sunny" if isday else "partly cloudy"
        elif 50.0 <= percent < 87.5:
            return "mostly cloudy"
        elif 87.5 <= percent <= 100.0:
            return "cloudy"

    return None


def to_percent(percent: Optional[float]) -> Optional[int]:
    """
    Return the given value, if any, as an integer.

    Args:
        percent: Float value to convert

    Returns:
        Integer percentage or None
    """
    return None if percent is None else int(percent)


def mb_to_in(mb: Optional[float]) -> Optional[str]:
    """
    Convert millibars to inches of mercury.

    Args:
        mb: Pressure in millibars

    Returns:
        Pressure in inches (formatted string) or None
    """
    # Every so often we get back a value of 900 which seems to be
    # some sort of "low value".  So, just consider it invalid.
    if mb == 900:
        return None
    return None if mb is None else f"{mb * 0.0295301:.2f}"


def pa_to_in(pa: Optional[float]) -> Optional[str]:
    """
    Convert pascals to inches of mercury.

    Args:
        pa: Pressure in pascals

    Returns:
        Pressure in inches (formatted string) or None
    """
    return None if pa is None else f"{pa * 0.000295301:.2f}"


def mm_to_in(
    mm: Optional[float], as_text: bool = False
) -> Optional[Union[str, Tuple[float, str, str]]]:
    """
    Convert millimeters to inches, optionally as descriptive text.

    Args:
        mm: Length in millimeters
        as_text: If True, return descriptive text tuple

    Returns:
        Inches as string, or tuple of (inches, amount_text, whole_text) if as_text=True
    """
    inches = None if mm is None else f"{mm * 0.0393701:.2f}"
    if not as_text or not inches:
        return inches

    inches_float = float(inches)
    whole = int(inches_float)
    frac = inches_float - whole

    if inches_float == 0:
        return inches_float, "", ""

    if inches_float < 0.1:
        amt = "less than a tenth"
    elif 0.1 <= frac < 0.125:
        amt = "less than a quarter"
    elif 0.125 <= frac < 0.375:
        amt = "a quarter"
    elif 0.375 <= frac < 0.625:
        amt = "a half"
    elif 0.625 <= frac < 0.875:
        amt = "three quarters"
    else:
        amt = ""

    if whole == 0:
        whole_text = ""
    elif whole == 1:
        whole_text = "one"
    else:
        whole_text = str(whole)

    return inches_float, amt, whole_text


def c_to_f(celsius: Optional[float]) -> Optional[int]:
    """
    Convert Celsius to Fahrenheit.

    Args:
        celsius: Temperature in Celsius

    Returns:
        Temperature in Fahrenheit (rounded to integer) or None
    """
    return None if celsius is None else int((celsius * 9.0 / 5.0) + 32.0)


def m_to_mi(meters: Optional[float]) -> Optional[float]:
    """
    Convert meters to miles.

    Args:
        meters: Distance in meters

    Returns:
        Distance in miles or None
    """
    return None if meters is None else meters * 0.000621371


def kmh_to_mph(kmh: Optional[float]) -> Optional[int]:
    """
    Convert kilometers per hour to miles per hour.

    Args:
        kmh: Speed in km/h

    Returns:
        Speed in mph (rounded to integer) or None
    """
    return None if kmh is None else int(kmh * 0.621371)
