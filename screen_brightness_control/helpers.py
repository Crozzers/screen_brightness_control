'''
Helper functions for the library
'''
from __future__ import annotations

import logging
import struct
import subprocess
import time
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from .exceptions import (EDIDParseError, MaxRetriesExceededError,  # noqa:F401
                         ScreenBrightnessError, format_exc)
from .types import DisplayIdentifier, IntPercentage, Percentage, Generator

_logger = logging.getLogger(__name__)

MONITOR_MANUFACTURER_CODES = {
    "AAC": "AcerView",
    "ACI": "Asus (ASUSTeK Computer Inc.)",
    "ACR": "Acer",
    "ACT": "Targa",
    "ADI": "ADI Corporation",
    "AIC": "AG Neovo",
    "ALX": "Anrecson",
    "AMW": "AMW",
    "AOC": "AOC",
    "API": "Acer America Corp.",
    "APP": "Apple Computer",
    "ART": "ArtMedia",
    "AST": "AST Research",
    "AUO": "Asus",
    "BMM": "BMM",
    "BNQ": "BenQ",
    "BOE": "BOE Display Technology",
    "CMO": "Acer",
    "CPL": "Compal",
    "CPQ": "Compaq",
    "CPT": "Chunghwa Picture Tubes, Ltd.",
    "CTX": "CTX",
    "DEC": "DEC",
    "DEL": "Dell",
    "DPC": "Delta",
    "DWE": "Daewoo",
    "ECS": "ELITEGROUP Computer Systems",
    "EIZ": "EIZO",
    "ELS": "ELSA",
    "ENC": "EIZO",
    "EPI": "Envision",
    "FCM": "Funai",
    "FUJ": "Fujitsu",
    "FUS": "Fujitsu-Siemens",
    "GSM": "LG Electronics",
    "GWY": "Gateway 2000",
    "GBT": "Gigabyte",
    "HEI": "Hyundai",
    "HIQ": "Hyundai ImageQuest",
    "HIT": "Hyundai",
    "HPN": "HP",
    "HSD": "Hannspree Inc",
    "HSL": "Hansol",
    "HTC": "Hitachi/Nissei",
    "HWP": "HP",
    "IBM": "IBM",
    "ICL": "Fujitsu ICL",
    "IFS": "InFocus",
    "IQT": "Hyundai",
    "IVM": "Iiyama",
    "KDS": "Korea Data Systems",
    "KFC": "KFC Computek",
    "LEN": "Lenovo",
    "LGD": "Asus",
    "LKM": "ADLAS / AZALEA",
    "LNK": "LINK Technologies, Inc.",
    "LPL": "Fujitsu",
    "LTN": "Lite-On",
    "MAG": "MAG InnoVision",
    "MAX": "Belinea",
    "MEI": "Panasonic",
    "MEL": "Mitsubishi Electronics",
    "MIR": "miro Computer Products AG",
    "MSI": "MSI",
    "MS_": "Panasonic",
    "MTC": "MITAC",
    "NAN": "Nanao",
    "NEC": "NEC",
    "NOK": "Nokia Data",
    "NVD": "Fujitsu",
    "OPT": "Optoma",
    "OQI": "OPTIQUEST",
    "PBN": "Packard Bell",
    "PCK": "Daewoo",
    "PDC": "Polaroid",
    "PGS": "Princeton Graphic Systems",
    "PHL": "Philips",
    "PRT": "Princeton",
    "REL": "Relisys",
    "SAM": "Samsung",
    "SAN": "Samsung",
    "SBI": "Smarttech",
    "SEC": "Hewlett-Packard",
    "SGI": "SGI",
    "SMC": "Samtron",
    "SMI": "Smile",
    "SNI": "Siemens Nixdorf",
    "SNY": "Sony",
    "SPT": "Sceptre",
    "SRC": "Shamrock",
    "STN": "Samtron",
    "STP": "Sceptre",
    "SUN": "Sun Microsystems",
    "TAT": "Tatung",
    "TOS": "Toshiba",
    "TRL": "Royal Information Company",
    "TSB": "Toshiba",
    "UNK": "Unknown",
    "UNM": "Unisys Corporation",
    "VSC": "ViewSonic",
    "WTC": "Wen Technology",
    "ZCM": "Zenith",
    "_YV": "Fujitsu"
}


class BrightnessMethod(ABC):
    @classmethod
    @abstractmethod
    def get_display_info(cls, display: Optional[DisplayIdentifier] = None) -> List[dict]:
        '''
        Return information about detected displays.

        Args:
            display (.types.DisplayIdentifier): the specific display to return
                information about. This parameter is passed to `filter_monitors`

        Returns:
            A list of dictionaries, each representing a detected display.
            Each returned dictionary will have the following keys:
            - name (`str`): the name of the display
            - model (`str`): the model of the display
            - manufacturer (`str`): the name of the display manufacturer
            - manufacturer_id (`str`): the three letter manufacturer code (see `MONITOR_MANUFACTURER_CODES`)
            - serial (`str`): the serial of the display OR some other unique identifier
            - edid (`str`): the EDID string for the display
            - method (`BrightnessMethod`): the brightness method associated with this display
            - index (`int`): the index of the display, relative to the brightness method
        '''
        ...

    @classmethod
    @abstractmethod
    def get_brightness(cls, display: Optional[int] = None) -> List[IntPercentage]:
        '''
        Args:
            display: the index of the specific display to query.
                If unspecified, all detected displays are queried

        Returns:
            A list of `.types.IntPercentage` values, one for each
            queried display
        '''
        ...

    @classmethod
    @abstractmethod
    def set_brightness(cls, value: IntPercentage, display: Optional[int] = None):
        '''
        Args:
            value (.types.IntPercentage): the new brightness value
            display: the index of the specific display to adjust.
                If unspecified, all detected displays are adjusted
        '''
        ...


class BrightnessMethodAdv(BrightnessMethod):
    @classmethod
    @abstractmethod
    def _gdi(cls) -> List[dict]:
        '''
        Similar to `BrightnessMethod.get_display_info` except this method will also
        return unsupported displays, indicated by an `unsupported: bool` property
        in the returned dict
        '''
        ...


class __Cache:
    '''class to cache data with a short shelf life'''

    def __init__(self):
        self.logger = _logger.getChild(f'{self.__class__.__name__}_{id(self)}')
        self.enabled = True
        self._store: Dict[str, Tuple[Any, float]] = {}

    def expire(self, key: Optional[str] = None, startswith: Optional[str] = None):
        '''
        @private

        Runs through all keys in the cache and removes any expired items.
        Can optionally specify additional keys that should be removed.

        Args:
            key: a specific key to remove. `KeyError` exceptions are suppressed if this key doesn't exist.
            startswith: remove any keys that start with this string
        '''
        if key is not None:
            try:
                del self._store[key]
                self.logger.debug(f'delete key {key!r}')
            except KeyError:
                pass

        for k, v in tuple(self._store.items()):
            if startswith is not None and k.startswith(startswith):
                del self._store[k]
                self.logger.debug(f'delete keys {startswith=}')
                continue
            if v[1] < time.time():
                del self._store[k]
                self.logger.debug(f'delete expired key {k}')

    def get(self, key: str) -> Any:
        if not self.enabled:
            return None
        self.expire()
        if key not in self._store:
            self.logger.debug(f'{key!r} not present in cache')
            return None
        return self._store[key][0]

    def store(self, key: str, value: Any, expires: float = 1):
        if not self.enabled:
            return
        self.logger.debug(f'cache set {key!r}, {expires=}')
        self._store[key] = (value, expires + time.time())


class EDID:
    '''
    Simple structure and method to extract display serial and name from an EDID string.
    '''
    EDID_FORMAT: str = (
        ">"     # big-endian
        "8s"    # constant header (8 bytes)
        "H"     # manufacturer id (2 bytes)
        "H"     # product id (2 bytes)
        "I"     # serial number (4 bytes)
        "B"     # manufactoring week (1 byte)
        "B"     # manufactoring year (1 byte)
        "B"     # edid version (1 byte)
        "B"     # edid revision (1 byte)
        "B"     # video input type (1 byte)
        "B"     # horizontal size in cm (1 byte)
        "B"     # vertical size in cm (1 byte)
        "B"     # display gamma (1 byte)
        "B"     # supported features (1 byte)
        "10s"   # colour characteristics (10 bytes)
        "H"     # supported timings (2 bytes)
        "B"     # reserved timing (1 byte)
        "16s"   # EDID supported timings (16 bytes)
        "18s"   # timing / display descriptor block 1 (18 bytes)
        "18s"   # timing / display descriptor block 2 (18 bytes)
        "18s"   # timing / display descriptor block 3 (18 bytes)
        "18s"   # timing / display descriptor block 4 (18 bytes)
        "B"     # extension flag (1 byte)
        "B"     # checksum (1 byte)
    )
    '''
    The byte structure for EDID strings, taken from
    [pyedid](https://github.com/jojonas/pyedid/blob/2382910d968b2fa8de1fab495fbbdfebcdb39f19/pyedid/edid.py#L21),
    [Copyright 2019-2020 Jonas Lieb, Davydov Denis](https://github.com/jojonas/pyedid/blob/master/LICENSE).
    '''
    SERIAL_DESCRIPTOR = bytes.fromhex('00 00 00 ff 00')
    NAME_DESCRIPTOR = bytes.fromhex('00 00 00 fc 00')

    @classmethod
    def parse(cls, edid: Union[bytes, str]) -> Tuple[Union[str, None], ...]:
        '''
        Takes an EDID string and parses some relevant information from it according to the
        [EDID 1.4](https://en.wikipedia.org/wiki/Extended_Display_Identification_Data#EDID_1.4_data_format)
        specification on Wikipedia.

        Args:
            edid (bytes or str): the EDID, can either be raw bytes or
                a hex formatted string (00 ff ff ff ff...)

        Returns:
            tuple[str | None]: A tuple of 5 items representing the display's manufacturer ID,
                manufacturer, model, name, serial in that order.
                If any of these values are unable to be determined, they will be None.
                Otherwise, expect a string

        Raises:
            EDIDParseError: if the EDID info cannot be unpacked
            TypeError: if `edid` is not `str` or `bytes`

        Example:
            ```python
            import screen_brightness_control as sbc

            edid = sbc.list_monitors_info()[0]['edid']
            manufacturer_id, manufacturer, model, name, serial = sbc.EDID.parse(edid)

            print('Manufacturer:', manufacturer_id or 'Unknown')
            print('Model:', model or 'Unknown')
            print('Name:', name or 'Unknown')
            ```
        '''
        # see https://en.wikipedia.org/wiki/Extended_Display_Identification_Data#EDID_1.4_data_format
        if isinstance(edid, str):
            edid = bytes.fromhex(edid)
        elif not isinstance(edid, bytes):
            raise TypeError(f'edid must be of type bytes or str, not {type(edid)!r}')

        try:
            blocks = struct.unpack(cls.EDID_FORMAT, edid)
        except struct.error as e:
            raise EDIDParseError('cannot unpack edid') from e

        # split mfg_id (2 bytes) into 3 letters, 5 bits each (ignoring reserved bit)
        mfg_id_chars = (
            blocks[1] >> 10,             # First 6 bits (reserved bit at start is always 0)
            (blocks[1] >> 5) & 0b11111,  # isolate next 5 bits from first 11 using bitwise AND
            blocks[1] & 0b11111          # Last five bits
        )
        # turn numbers into ascii
        mfg_id = ''.join(chr(i + 64) for i in mfg_id_chars)

        # now grab the manufacturer name
        mfg_lookup = _monitor_brand_lookup(mfg_id)
        if mfg_lookup is not None:
            manufacturer = mfg_lookup[1]
        else:
            manufacturer = None

        serial = None
        name = None
        for descriptor_block in blocks[17:21]:
            # decode the serial
            if descriptor_block.startswith(cls.SERIAL_DESCRIPTOR):
                # strip descriptor bytes and trailing whitespace
                serial_bytes = descriptor_block[len(cls.SERIAL_DESCRIPTOR):].rstrip()
                serial = serial_bytes.decode()

            # decode the monitor name
            elif descriptor_block.startswith(cls.NAME_DESCRIPTOR):
                # strip descriptor bytes and trailing whitespace
                name_bytes = descriptor_block[len(cls.NAME_DESCRIPTOR):].rstrip()
                name = name_bytes.decode()

        # now try to figure out what model the display is
        model = None
        if name is not None:
            if manufacturer is not None and name.startswith(manufacturer):
                # eg: 'BenQ GL2450H' -> 'GL2450H'
                model = name.replace(manufacturer, '', 1).strip()

            # if previous method did not work (or if we don't know the manufacturer),
            # try taking last word of name
            if not model:
                try:
                    # eg: 'BenQ GL2450H' -> ['BenQ', 'GL2450H']
                    model = name.strip().rsplit(' ', 1)[1]
                except IndexError:
                    # If the name does not include model information then
                    # give it something generic
                    model = 'Generic Monitor'

        return mfg_id, manufacturer, model, name, serial

    @staticmethod
    def hexdump(file: str) -> str:
        '''
        Returns a hexadecimal string of binary data from a file

        Args:
            file (str): the file to read

        Returns:
            str: one long hex string

        Example:
            ```python
            from screen_brightness_control import EDID

            print(EDID.hexdump('/sys/class/backlight/intel_backlight/device/edid'))
            # '00ffffffffffff00...'
            ```
        '''
        with open(file, 'rb') as f:
            hex_str = ''.join(f'{char:02x}' for char in f.read())

        return hex_str


def check_output(command: List[str], max_tries: int = 1) -> bytes:
    '''
    Run a command with retry management built in.

    Args:
        command: the command to run
        max_tries: the maximum number of retries to allow before raising an error

    Returns:
        The output from the command
    '''
    tries = 1
    while True:
        try:
            output = subprocess.check_output(command, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            if tries >= max_tries:
                raise MaxRetriesExceededError(f'process failed after {tries} tries', e) from e
            tries += 1
            time.sleep(0.04 if tries < 5 else 0.5)
        else:
            if tries > 1:
                _logger.debug(f'command {command} took {tries}/{max_tries} tries')
            return output


def logarithmic_range(start: int, stop: int, step: int = 1) -> Generator[int, None, None]:
    '''
    A `range`-like function that yields a sequence of integers following
    a logarithmic curve (`y = 10 ^ (x / 50)`) from `start` (inclusive) to
    `stop` (inclusive).

    This is useful because it skips many of the higher percentages in the
    sequence where single percent brightness changes are hard to notice.

    This function is designed to deal with brightness percentages, and so
    will never return a value less than 0 or greater than 100.

    Args:
        start: the start of your percentage range
        stop: the end of your percentage range
        step: the increment per iteration through the sequence

    Yields:
        int
    '''
    start = int(max(0, start))
    stop = int(min(100, stop))

    if start == stop or abs(stop - start) <= 1:
        yield start
    else:
        value_range = stop - start

        def direction(x):
            return x if step > 0 else 100 - x

        last_yielded = None
        x: float
        for x in range(start, stop + 1, step):
            # get difference from base point
            x -= start
            # calculate progress through our range as a percentage
            x = (x / value_range) * 100
            # convert along logarithmic curve (inverse of y = 50log(x)) to another percentage
            x = 10 ** (direction(x) / 50)
            # apply this percentage to our range and add back starting offset
            x = int(((direction(x) / 100) * value_range) + start)

            if x == last_yielded:
                continue
            yield x
            last_yielded = x


@lru_cache(maxsize=None)
def _monitor_brand_lookup(search: str) -> Union[Tuple[str, str], None]:
    '''internal function to search the monitor manufacturer codes dict'''
    keys = tuple(MONITOR_MANUFACTURER_CODES.keys())
    keys_lower = tuple(map(str.lower, keys))
    values = tuple(MONITOR_MANUFACTURER_CODES.values())
    search = search.lower()

    if search in keys_lower:
        index = keys_lower.index(search)
    else:
        values_lower = tuple(map(str.lower, values))
        if search in values_lower:
            index = values_lower.index(search)
        else:
            return None
    return keys[index], values[index]


def percentage(
    value: Percentage,
    current: Optional[Union[int, Callable[[], int]]] = None,
    lower_bound: int = 0
) -> IntPercentage:
    '''
    Convenience function to convert a brightness value into a percentage. Can handle
    integers, floats and strings. Also can handle relative strings (eg: `'+10'` or `'-10'`)

    Args:
        value: the brightness value to convert
        current: the current brightness value or a function that returns the current brightness
            value. Used when dealing with relative brightness values
        lower_bound: the minimum value the brightness can be set to

    Returns:
        `.types.IntPercentage`: The new brightness percentage, between `lower_bound` and 100
    '''
    if isinstance(value, str) and ('+' in value or '-' in value):
        if callable(current):
            current = current()
        value = int(float(value)) + int(float(str(current)))
    else:
        value = int(float(str(value)))

    return min(100, max(lower_bound, value))
