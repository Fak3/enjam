# https://github.com/boadley/numify
# Copyright (c) 2020 'juwon a. boadley

import re

def numify(alphanum: str) -> float:
    r"""
    Takes an alphanumeric  `alphanum` character such as 1k and return the integer equivalent.

    Args:
        alphanum (str): String to be converted.

    Returns:
        float: The equivalent of `alphanum` as float.

    Raises:
        ValueError: Raised if alphanum does not match the pattern `^([0-9]*)(\s)?([kKmMbB])$`

    >>> numify('72')
    72.0
    >>> numify('2k')
    2000.0
    >>> numify('41 K')
    41000.0
    >>> numify('-3   M')
    -3000000.0
    """
    if re.match(r'^-?\d+(?:\.\d+)?$', alphanum):
        return float(alphanum)

    # Check if alphanum format is valid
    match = re.search(r'^(?P<num>-?[0-9.]+)(\s)*(?P<mul>[kKmMbBtT])$', alphanum)
    if match is None:
        raise ValueError("Invalid Input: correct format is 1k, 1K, 1 k, 1 K.")

    multiplier = {
        'k': 1000,
        'm': 1000_000,
        'b': 1000_000_000,
        't': 1000_000_000_000,
    }[match.group('mul').lower()]

    return float(match.group('num')) * multiplier
