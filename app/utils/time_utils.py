"""Utility functions for timestamp handling."""

import re


def parse_timestamp(timestamp: str) -> int:
    """
    Parse a timestamp string (MM:SS or HH:MM:SS) to total seconds.

    Args:
        timestamp: Timestamp string in MM:SS or HH:MM:SS format

    Returns:
        Total seconds as integer

    Examples:
        >>> parse_timestamp("01:30")
        90
        >>> parse_timestamp("01:15:30")
        4530
    """
    parts = timestamp.strip().split(":")
    if len(parts) == 2:
        minutes, seconds = int(parts[0]), int(parts[1])
        return minutes * 60 + seconds
    elif len(parts) == 3:
        hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    else:
        raise ValueError(f"Invalid timestamp format: {timestamp}")


def format_timestamp(total_seconds: int) -> str:
    """
    Format total seconds to MM:SS timestamp string.

    Args:
        total_seconds: Total seconds as integer

    Returns:
        Timestamp string in MM:SS format

    Examples:
        >>> format_timestamp(90)
        '01:30'
        >>> format_timestamp(3661)
        '61:01'
    """
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


def format_timestamp_ffmpeg(total_seconds: float) -> str:
    """
    Format total seconds to HH:MM:SS.mmm timestamp for FFmpeg.

    Args:
        total_seconds: Total seconds (can be float for sub-second precision)

    Returns:
        Timestamp string in HH:MM:SS.mmm format

    Examples:
        >>> format_timestamp_ffmpeg(90.5)
        '00:01:30.500'
        >>> format_timestamp_ffmpeg(3661)
        '01:01:01.000'
    """
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"


def validate_timestamp(timestamp: str) -> bool:
    """
    Validate if a string is a valid timestamp format.

    Args:
        timestamp: String to validate

    Returns:
        True if valid timestamp format
    """
    pattern = r"^\d{1,2}:\d{2}(:\d{2})?$"
    return bool(re.match(pattern, timestamp.strip()))


def calculate_duration(start_time: str, end_time: str) -> int:
    """
    Calculate duration between two timestamps.

    Args:
        start_time: Start timestamp in MM:SS or HH:MM:SS format
        end_time: End timestamp in MM:SS or HH:MM:SS format

    Returns:
        Duration in seconds
    """
    start_seconds = parse_timestamp(start_time)
    end_seconds = parse_timestamp(end_time)
    return end_seconds - start_seconds
