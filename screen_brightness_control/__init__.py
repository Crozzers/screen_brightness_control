import platform
import struct
import threading
import time
import traceback
from functools import lru_cache
from typing import Any, List, Optional, Tuple, Union


def get_brightness(
    display: Optional[Union[int, str]] = None,
    method: Optional[str] = None,
    verbose_error: bool = False
) -> Union[List[int], int]:
    '''
    Returns the current display brightness

    Args:
        display (str or int): the specific display to query
        method (str): the way in which displays will be accessed.
            On Windows this can be 'wmi' or 'vcp'.
            On Linux it's 'light', 'xrandr', 'ddcutil' or 'xbacklight'.
        verbose_error (bool): controls the level of detail in the error messages

    Returns:
        int: an integer from 0 to 100 if only one display is detected
        list: if there a multiple displays connected it may return a list of integers (invalid monitors return `None`)

    Example:
        ```python
        import screen_brightness_control as sbc

        # get the current screen brightness (for all detected displays)
        current_brightness = sbc.get_brightness()

        # get the brightness of the primary display
        primary_brightness = sbc.get_brightness(display=0)

        # get the brightness of the secondary display (if connected)
        secondary_brightness = sbc.get_brightness(display=1)
        ```
    '''
    return __brightness(display=display, method=method, meta_method='get', verbose_error=verbose_error)


def set_brightness(
    value: Union[int, float, str],
    display: Optional[Union[str, int]] = None,
    method: Optional[str] = None,
    force: bool = False,
    verbose_error: bool = False,
    no_return: bool = False
) -> Union[List[int], int, None]:
    '''
    Sets the screen brightness

    Args:
        value (int or float or str): a value 0 to 100. This is a percentage or a string as '+5' or '-5'
        display (int or str): the specific display to adjust
        method (str): the way in which displays will be accessed.
            On Windows this can be 'wmi' or 'vcp'.
            On Linux it's 'light', 'xrandr', 'ddcutil' or 'xbacklight'.
        force (bool): [*Linux Only*] if False the brightness will never be set lower than 1.
            This is because on most displays a brightness of 0 will turn off the backlight.
            If True, this check is bypassed
        verbose_error (bool): boolean value controls the amount of detail error messages will contain
        no_return (bool): if False, this function returns new brightness (by calling `get_brightness`).
            If True, this function returns None. In the future this function will return `None` by default

    Returns:
        list: list of ints (0 to 100)
        int: if only one display is affected
        None: if the `no_return` kwarg is specified

    Example:
        ```python
        import screen_brightness_control as sbc

        # set brightness to 50%
        sbc.set_brightness(50)

        # set brightness to 0%
        sbc.set_brightness(0, force=True)

        # increase brightness by 25%
        sbc.set_brightness('+25')

        # decrease brightness by 30%
        sbc.set_brightness('-30')

        # set the brightness of display 0 to 50%
        sbc.set_brightness(50, display=0)
        ```
    '''
    if type(value) == str and ('+' in value or '-' in value):
        value = int(float(value))
        monitors = filter_monitors(display=display, method=method)
        if len(monitors) > 1:
            output = []
            for monitor in monitors:
                identifier = Monitor.get_identifier(monitor)[1]
                output.append(
                    set_brightness(
                        get_brightness(display=identifier) + value,
                        display=identifier,
                        force=force,
                        verbose_error=verbose_error,
                        no_return=no_return
                    )
                )
            output = flatten_list(output)
            return output[0] if len(output) == 1 else output
        else:
            value += get_brightness(display=Monitor.get_identifier(monitors[0])[1])
    else:
        value = int(float(str(value)))

    # make sure value is within bounds
    value = max(min(100, value), 0)

    if platform.system() == 'Linux' and not force:
        value = max(1, value)

    return __brightness(
        value, display=display, method=method,
        meta_method='set', no_return=no_return,
        verbose_error=verbose_error
    )


def fade_brightness(
    finish: Union[int, str],
    start: Optional[Union[int, str]] = None,
    interval: float = 0.01,
    increment: int = 1,
    blocking: bool = True,
    **kwargs
) -> Union[List[threading.Thread], List[int], int]:
    '''
    A function to somewhat gently fade the screen brightness from `start` to `finish`

    Args:
        finish (int or str): the brightness level to end up on
        start (int or str): where the brightness should fade from.
            If not specified the function starts from the current screen brightness
        interval (float or int): the time delay between each step in brightness
        increment (int): the amount to change the brightness by per step
        blocking (bool): whether this should occur in the main thread (`True`) or a new daemonic thread (`False`)
        kwargs (dict): passed directly to `set_brightness`.
            Any compatible kwargs are passed to `filter_monitors` as well. (eg: display, method...)

    Returns:
        list: list of `threading.Thread` objects if `blocking == False`,
            otherwise it returns the result of `get_brightness()`

    Example:
        ```python
        import screen_brightness_control as sbc

        # fade brightness from the current brightness to 50%
        sbc.fade_brightness(50)

        # fade the brightness from 25% to 75%
        sbc.fade_brightness(75, start=25)

        # fade the brightness from the current value to 100% in steps of 10%
        sbc.fade_brightness(100, increment=10)

        # fade the brightness from 100% to 90% with time intervals of 0.1 seconds
        sbc.fade_brightness(90, start=100, interval=0.1)

        # fade the brightness to 100% in a new thread
        sbc.fade_brightness(100, blocking=False)
        ```
    '''
    def fade(start, finish, increment, monitor):
        for i in range(min(start, finish), max(start, finish), increment):
            val = i
            if start > finish:
                val = start - (val - finish)
            monitor.set_brightness(val, no_return=True)
            time.sleep(interval)

        if monitor.get_brightness() != finish:
            monitor.set_brightness(finish, no_return=True)
        return

    threads = []
    if 'verbose_error' in kwargs.keys():
        del(kwargs['verbose_error'])

    try:
        # make sure only compatible kwargs are passed to filter_monitors
        available_monitors = filter_monitors(
            **{k: v for k, v in kwargs.items() if k in (
                'display', 'haystack', 'method', 'include'
            )}
        )
    except (IndexError, LookupError) as e:
        raise ScreenBrightnessError(f'\n\tfilter_monitors -> {type(e).__name__}: {e}')
    except ValueError as e:
        if platform.system() == 'Linux' and (str(kwargs.get('method', '')).lower() == 'xbacklight'):
            available_monitors = [method.XBacklight]
        else:
            raise ScreenBrightnessError(e)
    except Exception as e:
        raise ScreenBrightnessError(e)

    for i in available_monitors:
        try:
            if (
                platform.system() == 'Linux'
                and str(kwargs.get('method', '')).lower() == 'xbacklight'
            ):
                monitor = i
            else:
                monitor = Monitor(i)
            # same effect as monitor.is_active()
            current = monitor.get_brightness()
            st, fi = start, finish
            # convert strings like '+5' to an actual brightness value
            if isinstance(fi, str):
                if "+" in fi or "-" in fi:
                    fi = current + int(float(fi))
            if isinstance(st, str):
                if "+" in st or "-" in st:
                    st = current + int(float(st))

            st = current if st is None else st
            # make sure both values are within the correct range
            fi = min(max(int(float(fi)), 0), 100)
            st = min(max(int(float(st)), 0), 100)

            t1 = threading.Thread(target=fade, args=(st, fi, increment, monitor))
            t1.start()
            threads.append(t1)
        except Exception:
            pass

    if not blocking:
        return threads
    else:
        for t in threads:
            t.join()
        return get_brightness(**kwargs)


def list_monitors_info(method: Optional[str] = None, allow_duplicates: bool = False) -> List[dict]:
    '''
    list detailed information about all monitors that are controllable by this library

    Args:
        method (str): the method to use to list the available monitors.
            On Windows this can be `'wmi'` or `'vcp'`.
            On Linux this can be `'light'`, `'xrandr'`, `'ddcutil'` or `'xbacklight'`.
        allow_duplicates (bool): whether to filter out duplicate displays or not

    Returns:
        list: list of dictionaries

    Example:
        ```python
        import screen_brightness_control as sbc
        monitors = sbc.list_monitors_info()
        for monitor in monitors:
            print('=======================')
            # the manufacturer name plus the model
            print('Name:', monitor['name'])
            # the general model of the display
            print('Model:', monitor['model'])
            # the serial of the display
            print('Serial:', monitor['serial'])
            # the name of the brand of the monitor
            print('Manufacturer:', monitor['manufacturer'])
            # the 3 letter code corresponding to the brand name, EG: BNQ -> BenQ
            print('Manufacturer ID:', monitor['manufacturer_id'])
            # the index of that display FOR THE SPECIFIC METHOD THE DISPLAY USES
            print('Index:', monitor['index'])
            # the method this monitor can be addressed by
            print('Method:', monitor['method'])
            # the EDID string associated with that monitor
            print('EDID:', monitor['edid'])
        ```
    '''
    info = __cache__.get('monitors_info', method=method, allow_duplicates=allow_duplicates)
    if info is None:
        info = globals()['method'].list_monitors_info(method=method, allow_duplicates=allow_duplicates)
        __cache__.store('monitors_info', info, method=method, allow_duplicates=allow_duplicates)
    return info


def list_monitors(method: Optional[str] = None) -> List[str]:
    '''
    List the names of all detected monitors

    Args:
        method (str): the method to use to list the available monitors.
            On Windows this can be `'wmi'` or `'vcp'`.
            On Linux this can be `'light'`, `'xrandr'`, `'ddcutil'` or `'xbacklight'`.

    Returns:
        list: list of strings

    Example:
        ```python
        import screen_brightness_control as sbc
        monitor_names = sbc.list_monitors()
        # eg: ['BenQ GL2450H', 'Dell U2211H']
        ```
    '''
    return [i['name'] for i in list_monitors_info(method=method)]


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


class ScreenBrightnessError(Exception):
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
    def __init__(self, message="Cannot set/retrieve brightness level"):
        self.message = message
        super().__init__(self.message)


class Monitor():
    '''A class to manage a single monitor and its relevant information'''
    def __init__(self, display: Union[int, str, dict]):
        '''
        Args:
            display (int or str or dict): the index/name/model name/serial/edid
                of the display you wish to control. Is passed to `filter_monitors`
                to decide which display to use.

        Raises:
            LookupError: if a matching display could not be found
            TypeError: if the given display type is not int or str

        Example:
            ```python
            import screen_brightness_control as sbc

            # create a class for the primary monitor and then a specifically named monitor
            primary = sbc.Monitor(0)
            benq_monitor = sbc.Monitor('BenQ GL2450H')

            # check if the benq monitor is the primary one
            if primary.serial == benq_monitor.serial:
                print('BenQ GL2450HM is the primary display')
            else:
                print('The primary display is', primary.name)

            # this class can also be accessed like a dictionary
            print(primary['name'])
            print(benq_monitor['name'])
            ```
        '''
        monitors_info = list_monitors_info(allow_duplicates=True)
        if isinstance(display, dict):
            if display in monitors_info:
                info = display
            else:
                info = filter_monitors(
                    display=self.get_identifier(display),
                    haystack=monitors_info
                )[0]
        else:
            info = filter_monitors(display=display, haystack=monitors_info)[0]

        # make a copy so that we don't alter the dict in-place
        info = info.copy()

        self.serial: str = info.pop('serial')
        '''the serial number of the display or (if serial is not available) an ID assigned by the OS'''
        self.name: str = info.pop('name')
        '''the monitors manufacturer name plus its model'''
        self.method = info.pop('method')
        '''the method by which this monitor can be addressed.
        This will be a class from either the windows or linux sub-module'''
        self.manufacturer: str = info.pop('manufacturer')
        '''the name of the brand of the monitor'''
        self.manufacturer_id: str = info.pop('manufacturer_id')
        '''the 3 letter manufacturing code corresponding to the manufacturer name'''
        self.model: str = info.pop('model')
        '''the general model of the display'''
        self.index: int = info.pop('index')
        '''the index of the monitor FOR THE SPECIFIC METHOD THIS MONITOR USES.'''
        self.edid: str = info.pop('edid')
        '''a unique string returned by the monitor that contains its DDC capabilities, serial and name'''

        # this assigns any extra info that is returned to this class
        # eg: the 'interface' key in XRandr monitors on Linux
        for key, value in info.items():
            if value is not None:
                setattr(self, key, value)

    def __getitem__(self, item: Any) -> Any:
        return getattr(self, item)

    def get_identifier(self, monitor: dict = None) -> Tuple[str, Union[int, str]]:
        '''
        Returns the piece of information used to identify this monitor.
        Will iterate through the EDID, serial, name and index and return the first
        value that is not equal to None

        Args:
            monitor (dict): extract an identifier from this dict instead of the monitor class

        Returns:
            tuple: the name of the property returned and the value of said property.
                EG: `('serial', '123abc...')` or `('name', 'BenQ GL2450H')`

        Example:
            ```python
            import screen_brightness_control as sbc
            primary = sbc.Monitor(0)
            print(primary.get_identifier())  # eg: ('serial', '123abc...')

            secondary = sbc.list_monitors_info()[1]
            print(primary.get_identifier(monitor=secondary))  # eg: ('serial', '456def...')

            # you can also use the class uninitialized
            print(sbc.Monitor.get_identifier(secondary))  # eg: ('serial', '456def...')
            ```
        '''
        if monitor is None:
            monitor = self

        for key in ('edid', 'serial', 'name', 'index'):
            value = monitor[key]
            if value is not None:
                return key, value

    def set_brightness(self, value: int, no_return: bool = False) -> Union[int, None]:
        '''
        Sets the brightness for this display. See `set_brightness` for the full docs

        Args:
            value (int): the brightness value to set the display to (from 0 to 100)
            no_return (bool): if true, this function returns `None`
                Otherwise it returns the result of `Monitor.get_brightness`

        Returns:
            int: from 0 to 100
            None: if `no_return==True`

        Example:
            ```python
            import screen_brightness_control as sbc

            # set the brightness of the primary monitor to 50%
            primary = sbc.Monitor(0)
            primary.set_brightness(50)
            ```
        '''
        # refresh display info, in case another display has been unplugged or something
        # which would change the index of this display
        self.get_info()
        value = max(0, min(value, 100))
        self.method.set_brightness(value, display=self.index)
        if no_return:
            return
        return self.get_brightness()

    def get_brightness(self) -> int:
        '''
        Returns the brightness of this display.

        Returns:
            int: from 0 to 100

        Example:
            ```python
            import screen_brightness_control as sbc

            # get the brightness of the primary monitor
            primary = sbc.Monitor(0)
            primary_brightness = primary.get_brightness()
            ```
        '''
        # refresh display info, in case another display has been unplugged or something
        # which would change the index of this display
        self.get_info()
        return self.method.get_brightness(display=self.index)[0]

    def fade_brightness(self, *args, **kwargs) -> Union[threading.Thread, int]:
        '''
        Fades the brightness for this display. See `fade_brightness` for the full docs

        Args:
            args (tuple): passed directly to `fade_brightness`
            kwargs (dict): passed directly to `fade_brightness`.
                The `display` and `method` kwargs are always
                overwritten.

        Returns:
            threading.Thread: if the the blocking kwarg is False
            int: if the blocking kwarg is True

        Example:
            ```python
            import screen_brightness_control as sbc

            # fade the brightness of the primary monitor to 50%
            primary = sbc.Monitor(0)
            primary.fade_brightness(50)
            ```
        '''
        # refresh display info, in case another display has been unplugged or something
        # which would change the index of this display
        self.get_info(refresh=False)
        kwargs['display'] = self.index
        # the reason we override the method kwarg here is that
        # the 'index' is method specific and `fade_brightness`
        # is a top-level function. `self.set_brightness` and `self.get_brightness`
        # call directly to the method so they don't need this step
        kwargs['method'] = self.method.__name__.lower()

        b = fade_brightness(*args, **kwargs)
        # fade_brightness will call the top-level get_brightness
        # function, which will return list OR int
        if isinstance(b, list):
            return b[0]
        return b

    def get_info(self, refresh: bool = True) -> dict:
        '''
        Returns all known information about this monitor instance

        Args:
            refresh (bool): whether to refresh the information
                or to return the cached version

        Returns:
            dict

        Example:
            ```python
            import screen_brightness_control as sbc

            # initialize class for primary monitor
            primary = sbc.Monitor(0)
            # get the info
            info = primary.get_info()
            ```
        '''
        if not refresh:
            return vars(self)

        identifier = self.get_identifier()

        if identifier is not None:
            # refresh the info we have on this monitor
            info = filter_monitors(display=identifier[1], method=self.method.__name__)[0]
            for key, value in info.items():
                if value is not None:
                    setattr(self, key, value)

        return vars(self)

    def is_active(self) -> bool:
        '''
        Attempts to retrieve the brightness for this display. If it works the display is deemed active

        Returns:
            bool: True means active, False means inactive

        Example:
            ```python
            import screen_brightness_control as sbc

            primary = sbc.Monitor(0)
            if primary.is_active():
                primary.set_brightness(50)
            ```
        '''
        try:
            self.get_brightness()
            return True
        except Exception:
            return False


def filter_monitors(
    display: Optional[Union[int, str]] = None,
    haystack: Optional[List[dict]] = None,
    method: Optional[str] = None,
    include: List[str] = []
) -> List[dict]:
    '''
    Searches through the information for all detected displays
    and attempts to return the info matching the value given.
    Will attempt to match against index, name, model, edid, method and serial

    Args:
        display (str or int): the display you are searching for.
            Can be serial, name, model number, edid string or index of the display
        haystack (list): the information to filter from.
            If this isn't set it defaults to the return of `list_monitors_info`
        method (str): the method the monitors use
        include (list): extra fields of information to sort by

    Raises:
        TypeError: if the display kwarg is not an int, str or None
        LookupError: if the display, does not have a match

    Returns:
        list: list of dicts

    Example:
        ```python
        import screen_brightness_control as sbc

        search = 'GL2450H'
        match = sbc.filter_displays(search)
        print(match)
        # EG output: [{'name': 'BenQ GL2450H', 'model': 'GL2450H', ... }]
        ```
    '''
    # if we have been provided with a list of monitors to sift through then use that
    # otherwise, get the info ourselves
    if haystack:
        monitors_with_duplicates = haystack
        if method is not None:
            monitors_with_duplicates = [i for i in haystack if method.lower() == i['method'].__name__.lower()]
    else:
        monitors_with_duplicates = list_monitors_info(method=method, allow_duplicates=True)

    if display is not None and type(display) not in (str, int):
        raise TypeError(f'display kwarg must be int or str, not "{type(display).__name__}"')

    # This loop does two things: 1. Filters out duplicate monitors and 2. Matches the display kwarg (if applicable)
    unique_identifiers = []
    monitors = []
    for monitor in monitors_with_duplicates:
        # find a valid identifier for a monitor, excluding any which are equal to None
        added = False
        for identifier in ['edid', 'serial', 'name', 'model'] + include:
            if monitor.get(identifier, None) is not None:
                # check we haven't already added the monitor
                if monitor[identifier] not in unique_identifiers:
                    # check if the display kwarg (if str) matches this monitor
                    if type(display) != str or (type(display) == str and monitor[identifier] == display):
                        # if valid and monitor[identifier] not in unique_identifiers:
                        if not added:
                            monitors.append(monitor)
                            unique_identifiers.append(monitor[identifier])
                            added = True

                        # if the display kwarg is an integer and we are currently at that index
                        if type(display) is int and len(monitors) - 1 == display:
                            return [monitor]
                        if added:
                            break
                else:
                    # if we have already added a monitor with the same identifier
                    # then any info matching this monitor will match the other one
                    # so exit the checking now
                    break

    # if no monitors matched the query OR if display kwarg was an int
    # if the latter and we made it this far then the int was out of range
    if monitors == [] or type(display) is int:
        msg = 'no monitors found'
        if display is not None:
            msg += f' with name/serial/model/edid/index of {repr(display)}'
        if method is not None:
            msg += f' with method of "{method}"'
        raise LookupError(msg)

    return monitors


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
    for item in thick_list:
        if type(item) == list:
            flat_list += flatten_list(item)
        else:
            flat_list.append(item)
    return flat_list


def __brightness(
    *args, display=None, method=None, meta_method='get', no_return=False,
    verbose_error=False, **kwargs
):
    '''Internal function used to get/set brightness'''

    def format_exc(name, e):
        errors.append((
            name, e.__class__.__name__,
            traceback.format_exc() if verbose_error else e
        ))

    output = []
    errors = []
    method = method.lower() if type(method) == str else method

    try:
        monitors = filter_monitors(display=display, method=method)
    except (LookupError, ValueError) as e:
        if platform.system() == 'Linux' and display is None and method in ('xbacklight', None):
            try:
                if meta_method == 'set':
                    linux.XBacklight.set_brightness(*args)
                output.append(linux.XBacklight.get_brightness())
            except Exception as e:
                format_exc('XBacklight', e)
        else:
            format_exc('filter_monitors', e)
    except Exception as e:
        format_exc('filter_monitors', e)
    else:
        for monitor in monitors:
            try:
                if meta_method == 'set':
                    monitor['method'].set_brightness(*args, display=monitor['index'], **kwargs)
                    if no_return:
                        continue

                output.append(monitor['method'].get_brightness(display=monitor['index'], **kwargs))
            except Exception as e:
                output.append(None)
                format_exc(monitor, e)

    output = flatten_list(output)

    if output and not set(output) == {None}:
        # if all of the outputs are None then all of the monitors failed
        output = output[0] if len(output) == 1 else output
        return output if not no_return else None
    elif meta_method == 'set' and no_return:
        return

    # if the function hasn't returned then it has failed
    msg = '\n'
    if errors:
        for monitor, exc_name, exc in errors:
            if type(monitor) == str:
                msg += f'\t{monitor}'
            else:
                msg += f'\t{monitor["name"]} ({monitor["serial"]})'
            msg += f' -> {exc_name}: '
            msg += str(exc).replace('\n', '\n\t\t') + '\n'
    else:
        msg += '\tno valid output was received from brightness methods'

    raise ScreenBrightnessError(msg)


class __Cache(dict):
    '''class to cache data with a short shelf life'''
    def __init__(self):
        self.enabled = True
        super().__init__()

    def get(self, key, *args, **kwargs):
        if not self.enabled:
            return None

        try:
            value, expires, orig_args, orig_kwargs = super().__getitem__(key)
            if time.time() < expires:
                if orig_args == args and orig_kwargs == kwargs:
                    return value
            else:
                super().__delitem__(key)
        except KeyError:
            pass

    def store(self, key, value, *args, expires=1, **kwargs):
        super().__setitem__(key, (value, expires + time.time(), args, kwargs))

    def expire(self, key=None, startswith=None, endswith=None):
        if key is not None:
            try:
                super().__delitem__(key)
            except Exception:
                pass
        else:
            for i in tuple(self.keys()):
                cond1 = startswith is not None and i.startswith(startswith)
                cond2 = endswith is not None and i.endswith(endswith)
                if cond1 and cond2:
                    super().__delitem__(i)
                elif cond1:
                    super().__delitem__(i)
                elif cond2:
                    super().__delitem__(i)
                else:
                    pass


__cache__ = __Cache()
plat = platform.system()
if plat == 'Windows':
    from . import windows
    method = windows
elif plat == 'Linux':
    from . import linux
    method = linux
elif plat == 'Darwin':
    raise NotImplementedError('MAC is not yet supported')
else:
    raise NotImplementedError(f'{plat} is not yet supported')
del(plat)

__version__ = '0.9.0'
__author__ = 'Crozzers'
