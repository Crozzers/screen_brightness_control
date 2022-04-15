'''
Helper functions for the library
'''
import struct
import time
from functools import lru_cache
from typing import Any, List, Tuple, Union
import warnings


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
        "18s"   # timing / display descriptor block 1 (18 bytes)
        "18s"   # timing / display descriptor block 2 (18 bytes)
        "18s"   # timing / display descriptor block 3 (18 bytes)
        "18s"   # timing / display descriptor block 4 (18 bytes)
        "B"     # extension flag (1 byte)
        "B"     # checksum (1 byte)
    )
    '''The byte structure for EDID strings'''

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
            tuple[str | None]: A tuple of 5 items representing the monitor's manufacturer ID,
                manufacturer, model, name, serial in that order.
                If any of these values are unable to be determined, they will be None.
                Otherwise, expect a string

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
        if not isinstance(edid, bytes):
            edid = bytes.fromhex(edid)

        blocks = struct.unpack(cls.EDID_FORMAT, edid)

        mfg_id_block = blocks[1]
        # split mfg_id (2 bytes) into 3 letters, 5 bits each (ignoring reserved bit)
        mfg_id = (
            mfg_id_block >> 10,             # First 6 bits (reserved bit at start is always 0)
            (mfg_id_block >> 5) & 0b11111,  # Next 5 (use bitwise AND to isolate the 5 bits we want from first 11)
            mfg_id_block & 0b11111          # Last five bits
        )
        # turn numbers into ascii
        mfg_id = ''.join(chr(i + 64) for i in mfg_id)

        # now grab the manufacturer name
        mfg_lookup = _monitor_brand_lookup(mfg_id)
        if mfg_lookup is not None:
            manufacturer = mfg_lookup[1]
        else:
            manufacturer = None

        SERIAL_DESCRIPTOR = bytes.fromhex('00 00 00 ff 00')
        serial = None
        NAME_DESCRIPTOR = bytes.fromhex('00 00 00 FC 00')
        name = None
        for descriptor_block in blocks[17:21]:
            # decode the serial
            if descriptor_block.startswith(SERIAL_DESCRIPTOR):
                # strip descriptor bytes and trailing whitespace
                serial_bytes = descriptor_block[len(SERIAL_DESCRIPTOR):].rstrip()
                serial = serial_bytes.decode()

            # decode the monitor name
            elif descriptor_block.startswith(NAME_DESCRIPTOR):
                # strip descriptor bytes and trailing whitespace
                name_bytes = descriptor_block[len(NAME_DESCRIPTOR):].rstrip()
                name = name_bytes.decode()

        # now try to figure out what model the display is
        model = None
        if name is not None:
            if manufacturer is not None and name.startswith(manufacturer):
                # eg: 'BenQ GL2450H' -> ['BenQ', 'GL2450H']
                model = name.replace(manufacturer, '', 1).strip()

            # if previous method did not work, try taking last word of name
            if not model:
                model = name.strip().rsplit(' ', 1)[1]

        return mfg_id, manufacturer, model, name, serial

    @classmethod
    def parse_edid(cls, edid: str) -> Tuple[Union[str, None], str]:
        '''
        DEPRECATED. Please use `EDID.parse` instead.

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
        warnings.warn(
            'EDID.parse_edid is deprecated and will be removed in the next release. Please use EDID.parse instead.',
            DeprecationWarning
        )

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
    "ACI": "Asus (ASUSTeK Computer Inc.)",
    "ACR": "Acer",
    "ACT": "Targa",
    "ADI": "ADI Corporation",
    "AIC": "AG Neovo",
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
    "CPT": "Chunghwa Pciture Tubes, Ltd.",
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
