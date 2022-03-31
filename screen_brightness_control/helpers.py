'''
Helper functions for the library
'''
import struct
import time
from functools import lru_cache
from typing import Any, List, Tuple, Union


class ScreenBrightnessError(Exception):
    def __init__(self, message="Cannot set/retrieve brightness level"):
        self.message = message
        super().__init__(self.message)


class EDID:
    '''
    Simple structure and method to extract monitor serial and name from an EDID string.

    The EDID parsing was created with inspiration from the [pyedid library](https://github.com/jojonas/pyedid)
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
        "10s"   # color characteristics (10 bytes)
        "H"     # supported timings (2 bytes)
        "B"     # reserved timing (1 byte)
        "16s"   # EDID supported timings (16 bytes)
        "18s"   # detailed timing block 1 (18 bytes)
        "18s"   # detailed timing block 2 (18 bytes)
        "18s"   # detailed timing block 3 (18 bytes)
        "18s"   # detailed timing block 4 (18 bytes)
        "B"     # extension flag (1 byte)
        "B"     # checksum (1 byte)
    )
    '''The byte structure for EDID strings'''

    @classmethod
    def parse_edid(cls, edid: str) -> Tuple[Union[str, None], str]:
        '''
        Takes an EDID string (as string hex, formatted as: '00ffffff00...') and
        attempts to extract the monitor's name and serial number from it

        Args:
            edid (str): the edid string

        Returns:
            tuple: First item can be None or str. Second item is always str.
                This represents the name and serial respectively.
                If the name (first item) is None then this function likely
                failed to extract the serial correctly.

        Example:
            ```python
            import screen_brightness_control as sbc

            edid = sbc.list_monitors_info()[0]['edid']
            name, serial = sbc.EDID.parse_edid(edid)
            if name is not None:
                print('Success!')
                print('Name:', name)
                print('Serial:', serial)
            else:
                print('Unable to extract the data')
            ```
        '''
        def filter_hex(st):
            st = str(st)
            while '\\x' in st:
                i = st.index('\\x')
                st = st.replace(st[i:i + 4], '')
            return st.replace('\\n', '')[2:-1]

        if ' ' in edid:
            edid = edid.replace(' ', '')
        edid = bytes.fromhex(edid)
        data = struct.unpack(cls.EDID_FORMAT, edid)
        serial = filter_hex(data[18])
        # other info can be anywhere in this range, I don't know why
        name = None
        for i in data[19:22]:
            try:
                st = str(i)[2:-1].rstrip(' ').rstrip('\t')
                if st.index(' ') < len(st) - 1:
                    name = filter_hex(i).split(' ')
                    name = name[0].lower().capitalize() + ' ' + name[1]
            except Exception:
                pass
        return name, serial.strip(' ')

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


MONITOR_MANUFACTURER_CODES = {
    "AAC": "AcerView",
    "ACR": "Acer",
    "AOC": "AOC",
    "AIC": "AG Neovo",
    "APP": "Apple Computer",
    "AST": "AST Research",
    "AUO": "Asus",
    "BNQ": "BenQ",
    "CMO": "Acer",
    "CPL": "Compal",
    "CPQ": "Compaq",
    "CPT": "Chunghwa Pciture Tubes, Ltd.",
    "CTX": "CTX",
    "DEC": "DEC",
    "DEL": "Dell",
    "DPC": "Delta",
    "DWE": "Daewoo",
    "EIZ": "EIZO",
    "ELS": "ELSA",
    "ENC": "EIZO",
    "EPI": "Envision",
    "FCM": "Funai",
    "FUJ": "Fujitsu",
    "FUS": "Fujitsu-Siemens",
    "GSM": "LG Electronics",
    "GWY": "Gateway 2000",
    "HEI": "Hyundai",
    "HIT": "Hyundai",
    "HSL": "Hansol",
    "HTC": "Hitachi/Nissei",
    "HWP": "HP",
    "IBM": "IBM",
    "ICL": "Fujitsu ICL",
    "IVM": "Iiyama",
    "KDS": "Korea Data Systems",
    "LEN": "Lenovo",
    "LGD": "Asus",
    "LPL": "Fujitsu",
    "MAX": "Belinea",
    "MEI": "Panasonic",
    "MEL": "Mitsubishi Electronics",
    "MS_": "Panasonic",
    "NAN": "Nanao",
    "NEC": "NEC",
    "NOK": "Nokia Data",
    "NVD": "Fujitsu",
    "OPT": "Optoma",
    "PHL": "Philips",
    "REL": "Relisys",
    "SAN": "Samsung",
    "SAM": "Samsung",
    "SBI": "Smarttech",
    "SGI": "SGI",
    "SNY": "Sony",
    "SRC": "Shamrock",
    "SUN": "Sun Microsystems",
    "SEC": "Hewlett-Packard",
    "TAT": "Tatung",
    "TOS": "Toshiba",
    "TSB": "Toshiba",
    "VSC": "ViewSonic",
    "ZCM": "Zenith",
    "UNK": "Unknown",
    "_YV": "Fujitsu",
}


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


def flatten_list(thick_list: List[Any]) -> List[Any]:
    '''
    Internal function I use to flatten lists, because I do that often

    Args:
        thick_list (list): The list to be flattened. Can be as deep as you wish (within recursion limits)

    Returns:
        list: one dimensional

    Example:
        ```python
        import screen_brightness_control as sbc
        thick_list = [1, [2, [3, 4, 5], 6, 7], 8, [9, 10]]
        flat_list = sbc.flatten_list(thick_list)
        # Output: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        ```
    '''
    flat_list = []
    '''
    Generic error class designed to make catching errors under one umbrella easy.
    Raised when the brightness cannot be set/retrieved.

    Example:
        ```python
        import screen_brightness_control as sbc
        try:
            sbc.set_brightness(50)
        except sbc.ScreenBrightnessError as error:
            print(error)
        ```
    '''
    for item in thick_list:
        if isinstance(item, list):
            flat_list += flatten_list(item)
        else:
            flat_list.append(item)
    return flat_list


class __Cache(dict):
    '''class to cache data with a short shelf life'''
    def __init__(self):
        self.enabled = True
        super().__init__()

    def get(self, key, *args, **kwargs):
        if not self.enabled:
            return None

        try:
            value, expires, orig_args, orig_kwargs = self[key]
            if time.time() < expires:
                if orig_args == args and orig_kwargs == kwargs:
                    return value
            else:
                del self[key]
        except KeyError:
            pass

    def store(self, key, value, *args, expires=1, **kwargs):
        self[key] = (value, expires + time.time(), args, kwargs)

    def expire(self, key=None, startswith=None):
        if key is not None:
            try:
                del self[key]
            except KeyError:
                pass
        elif startswith is not None:
            for i in tuple(self.keys()):
                if i.startswith(startswith):
                    del self[i]


__cache__ = __Cache()
