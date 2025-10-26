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
Text normalization utilities for Clima Cast.

This module provides functionality to convert weather API text to
speech-friendly format, handling state abbreviations, time zones,
wind directions, and other specialized text patterns.
"""

import re
from typing import Optional

from utils.constants import ANGLES, NORMALIZE_RE, STATES


class TextNormalizer:
    """
    Converts weather text to speech-friendly format.

    This class handles various text transformations including:
    - State abbreviations
    - Time zones and meridians (AM/PM)
    - Wind directions
    - Units of measurement
    - Special weather service codes
    """

    def __init__(self):
        """Initialize the text normalizer and compile regex patterns."""
        self._compiled_pattern: Optional[re.Pattern] = None

    def _get_pattern(self) -> re.Pattern:
        """
        Get or compile the normalization regex pattern.

        Returns:
            Compiled regex pattern for text normalization
        """
        if self._compiled_pattern is None:
            self._compiled_pattern = re.compile(
                "(" + "|".join(NORMALIZE_RE) + ")", re.IGNORECASE
            )
        return self._compiled_pattern

    def normalize(self, text: str) -> str:
        """
        Normalize text for speech output.

        Identifies various text patterns and replaces them with
        easier to hear alternatives.

        Args:
            text: Input text to normalize

        Returns:
            Normalized text in lowercase
        """
        pattern = self._get_pattern()

        # Prepare text
        text = text.replace("\n", " ")

        # Process matches
        out = ""
        last = 0

        for match in pattern.finditer(text):
            # Add unmatched text before this match
            out += text[last : match.start()]
            last = match.end()

            # Process the matched group
            for name, value in match.groupdict().items():
                if value is None:
                    continue

                out += self._transform_match(name, value)
                break  # Only one group should match

        # Add remaining text and convert to lowercase
        return (out + text[last:]).lower()

    def _transform_match(self, name: str, value: str) -> str:
        """
        Transform a matched pattern to speech-friendly text.

        Args:
            name: Name of the matched regex group
            value: Matched text value

        Returns:
            Transformed text
        """
        # State abbreviations
        if name == "st":
            return self._transform_state(value)

        # Abbreviation substitutions
        elif name == "sub":
            return self._transform_abbreviation(value)

        # Nautical miles
        elif name == "nm":
            return value[:-2] + " nautical miles"

        # Knots
        elif name == "kt":
            return value[:-2] + " knots"

        # Time with AM/PM
        elif name == "meridian":
            return self._transform_meridian(value)

        # Time zones
        elif name == "tz":
            return ".".join(list(value)) + "."

        # Ignored patterns (removed from output)
        elif name == "ign":
            return ""

        # Wind directions
        elif name == "wind":
            return self._transform_wind_direction(value)

        # Singular degree
        elif name == "deg":
            return value + " degree"

        # Unknown pattern - return as-is
        return value

    def _transform_state(self, value: str) -> str:
        """
        Transform state abbreviation to full name.

        Args:
            value: State abbreviation

        Returns:
            Full state name or original value if exception states
        """
        try:
            st = value.lower()
            # Don't convert IN, NE, OR, DC as they conflict with common words
            if st in ["in", "ne", "or", "dc"]:
                return value
            # Find full name in STATES list (abbr is followed by full name)
            return STATES[STATES.index(st) - 1]
        except (ValueError, IndexError):
            return value

    def _transform_abbreviation(self, value: str) -> str:
        """
        Transform common abbreviations to full text.

        Args:
            value: Abbreviated text

        Returns:
            Full text form
        """
        abbreviations = {
            "ft": "feet",
            "nws": "national weather service",
            "mph": "miles per hour",
            "pt": "point",
            "pt.": "point",
        }
        return abbreviations.get(value.lower(), value)

    def _transform_meridian(self, value: str) -> str:
        """
        Transform time with AM/PM to speech-friendly format.

        Args:
            value: Time string like "330pm" or "10am"

        Returns:
            Formatted time like "3:30 P.M." or "10 A.M."
        """
        time_part = value[:-2].strip()
        meridian = value[-2:]

        # Add colon if time has 3+ digits
        if len(time_part) > 2:
            time_part = time_part[:-2] + ":" + time_part[-2:]

        # Format meridian with periods
        return time_part + " " + ".".join(list(meridian)) + "."

    def _transform_wind_direction(self, value: str) -> str:
        """
        Transform wind direction abbreviation to full text.

        Args:
            value: Wind direction abbreviation (N, NE, etc.)

        Returns:
            Full direction name
        """
        value = value.upper()
        for direction in ANGLES:
            if direction[1] == value:
                return direction[0]
        return value
