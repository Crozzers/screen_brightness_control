import platform
import time
import threading


class __Cache(dict):
    '''class to cache data with a short shelf life'''
    def __init__(self):
        self.enabled = True
        super().__init__()

    def __setitem__(self, key, value, *args, expires=1, **kwargs):
        expires += time.time()
        super().__setitem__(key, (value, expires, args, kwargs))

    def __getitem__(self, key, *args, **kwargs):
        if not self.enabled:
            raise Exception
        value, expires, orig_args, orig_kwargs = super().__getitem__(key)
        if time.time() < expires and orig_args == args and orig_kwargs == kwargs:
            return value
        raise KeyError

    def get(self, *args, **kwargs):
        return self.__getitem__(*args, **kwargs)

    def store(self, *args, **kwargs):
        return self.__setitem__(*args, **kwargs)

    def expire(self, key=None, startswith=None, endswith=None):
        if key is not None:
            try:
                del(self[key])
            except Exception:
                pass
        else:
            for i in list(self.keys()):
                if (startswith, endswith) != (None, None) and i.startswith(startswith) and i.endswith(endswith):
                    del(self[i])
                elif startswith is not None and endswith is None and i.startswith(startswith):
                    del(self[i])
                elif startswith is None and endswith is not None and i.endswith(endswith):
                    del(self[i])
                else:
                    pass


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


def _monitor_brand_lookup(search):
    '''internal function to search the monitor manufacturer codes dict'''
    keys = list(MONITOR_MANUFACTURER_CODES.keys())
    keys_lower = [i.lower() for i in keys]
    values = list(MONITOR_MANUFACTURER_CODES.values())
    values_lower = [i.lower() for i in values]
    search_lower = search.lower()

    if search_lower in keys_lower:
        index = keys_lower.index(search_lower)
    elif search_lower in values_lower:
        index = values_lower.index(search_lower)
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
    def __init__(self, display):
        '''
        Args:
            display (int or str): the index/model name/serial/edid of the display you wish to control

        Raises:
            LookupError: if the given display is a string but that string does not match any known displays
            TypeError: if the given display type is not int or str

        Example:
            ```python
            import screen_brightness_control as sbc

            # create a class for the primary monitor and then a specifically named monitor
            primary = sbc.Monitor(0)
            benq_monitor = sbc.Monitor('BenQ GL2450HM')

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
        if type(display) is dict:
            if display in monitors_info:
                info = display
            else:
                raise LookupError('could not match display info to known displays')
        else:
            info = filter_monitors(display, haystack=monitors_info)[0]

        self.serial = info['serial']
        '''the serial number of the display or (if serial is not available) an ID assigned by the OS'''
        self.name = info['name']
        '''the monitors manufacturer name plus its model'''
        self.method = info['method']
        '''the method by which this monitor can be addressed'''
        self.manufacturer = info['manufacturer']
        '''the name of the brand of the monitor'''
        self.manufacturer_id = info['manufacturer_id']
        '''the 3 letter manufacturing code corresponding to the manufacturer name'''
        self.model = info['model']
        '''the general model of the display'''
        if platform.system() == 'Windows':
            self.model_name = info['model']
            '''(Windows Only) Deprecated, always equal to the model. Will be removed soon'''
        self.index = info['index']
        '''the index of the monitor FOR THE SPECIFIC METHOD THIS MONITOR USES.'''
        self.edid = info['edid']
        '''a unique string returned by the monitor that contains its DDC capabilities, serial and name'''

    def __getitem__(self, item):
        return getattr(self, item)

    def set_brightness(self, *args, **kwargs):
        '''
        Sets the brightness for this display

        Args:
            args (tuple): passed directly to this monitor's brightness method
            kwargs (dict): passed directly to this monitor's brightness method.
                            The `display` kwarg is always overwritten

        Returns:
            int: from 0 to 100

        Example:
            ```python
            import screen_brightness_control as sbc

            # set the brightness of the primary monitor to 50%
            primary = sbc.Monitor(0)
            primary.set_brightness(50)
            ```
        '''
        if self.edid is not None:
            kwargs['display'] = self.edid
        elif self.serial is not None:
            kwargs['display'] = self.serial
        else:
            kwargs['display'] = self.index
        return self.method.set_brightness(*args, **kwargs)

    def get_brightness(self, **kwargs):
        '''
        Returns the brightness of this display

        Args:
            kwargs (dict): passed directly to this monitor's brightness method (`display` kwarg is always overwritten)

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
        if self.edid is not None:
            kwargs['display'] = self.edid
        elif self.serial is not None:
            kwargs['display'] = self.serial
        else:
            kwargs['display'] = self.index
        return self.method.get_brightness(**kwargs)

    def get_info(self):
        '''
        Returns all known information about this monitor instance

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
        info = {
            'name': self.name,
            'model': self.model,
            'serial': self.serial,
            'manufacturer': self.manufacturer,
            'manufacturer_id': self.manufacturer_id,
            'method': self.method,
            'index': self.index,
            'edid': self.edid
        }
        if platform.system() == 'Windows':
            info['model_name'] = info['model']
            # deprecated, will be removed in v0.8.0. Only here for compatibility
        return info

    def is_active(self):
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


def list_monitors_info(**kwargs):
    '''
    list detailed information about all monitors that are controllable by this library

    Args:
        kwargs (dict): passed directly to OS relevant monitor list function

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

            # a unique string assigned by Windows to this display
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
    try:
        return __cache__.get('monitors_info', **kwargs)
    except Exception:
        if platform.system() == 'Windows':
            info = windows.list_monitors_info(**kwargs)
        elif platform.system() == 'Linux':
            info = linux.list_monitors_info(**kwargs)
        __cache__.store('monitors_info', info, **kwargs)
        return info


def list_monitors(**kwargs):
    '''
    list all monitors that are controllable by this library

    Args:
        kwargs (dict): passed directly to OS relevant monitor list function

    Returns:
        list: list of strings

    Example:
        ```python
        import screen_brightness_control as sbc
        monitor_names = sbc.list_monitors()
        # eg: ['BenQ GL2450H', 'Dell U2211H']
        ```
    '''
    return [i['name'] for i in list_monitors_info(**kwargs)]


def filter_monitors(display=None, haystack=None, method=None, include=[]):
    '''
    Searches through the information for all detected displays
    and attempts to return the info matching the value given.
    Will attempt to match against index, name, model, edid, method and serial

    Args:
        display (str or int): what you are searching for.
                        Can be serial number, name, model number, edid string or index of the display
        haystack (list): the information to filter from.
                        If this isn't set it defaults to the return of `list_monitors_info`
        method (str): the method the monitors use
        include (list): extra fields of information to sort by

    Raises:
        IndexError: if the display value is an int and an `IndexError` occurs when using it as a list index
        LookupError: if the display, as a str, does not have a match

    Returns:
        list

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
        raise TypeError(f'display kwarg must be int or str, not {type(display)}')

    # This loop does two things: 1. Filters out duplicate monitors and 2. Matches the display kwarg (if applicable)
    unique_identifiers = []
    monitors = []
    for monitor in monitors_with_duplicates:
        valid = False
        if type(display) is str:
            # if the display kwarg matches any of the information given (edid, serial...), add it to the list
            for field in ['edid', 'serial', 'name', 'model'] + include:
                if monitor[field] is not None and display == monitor[field]:
                    valid = True
                    break
        else:
            valid = True

        # find a valid identifier for a monitor, excluding any which are equal to None
        identifier = 'edid'
        for identifier in ('edid', 'serial', 'name', 'model'):
            if monitor[identifier] is not None:
                # if the monitor is valid and we haven't already added it
                if valid and monitor[identifier] not in unique_identifiers:
                    monitors.append(monitor)
                    unique_identifiers.append(monitor[identifier])

                    # if the display kwarg is an integer and we are currently at that index
                    if type(display) is int and len(monitors) - 1 == display:
                        return [monitor]
                break

    # if no monitors matched the query OR if display kwarg was an int
    # if the latter and we made it this far then the int was out of range
    if monitors == [] or type(display) is int:
        msg = 'no monitors found'
        if display is not None:
            msg += f' with name/serial/model/edid/index of "{display}"'
        if method is not None:
            msg += f' with method of "{method}"'
        raise LookupError(msg)

    return monitors


def flatten_list(thick_list):
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
        if type(item) is list:
            flat_list += flatten_list(item)
        else:
            flat_list.append(item)
    return flat_list


def set_brightness(value, force=False, verbose_error=False, **kwargs):
    '''
    Sets the screen brightness

    Args:
        value (int or str): a value 0 to 100. This is a percentage or a string as '+5' or '-5'
        force (bool): [Linux Only] if False the brightness will never be set lower than 1.
                    This is because on most displays a brightness of 0 will turn off the backlight.
                    If True, this check is bypassed
        verbose_error (bool): boolean value controls the amount of detail error messages will contain
        kwargs (dict): passed to the OS relevant brightness method

    Returns:
        Returns the result of `get_brightness()`

    Example:
        ```
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
    if type(value) not in (int, float, str):
        raise TypeError(f'value must be int, float or str, not {type(value)}')

    # convert values like '+5' and '-25' to integers and add/subtract them from the current brightness
    if type(value) is str and value.startswith(('+', '-')):
        if 'display' in kwargs.keys():
            current = get_brightness(display=kwargs['display'])
        else:
            current = get_brightness()
            if type(current) is list:
                # apply the offset to all displays by setting the brightness for each one individually
                out = []
                for i in range(len(current)):
                    out.append(set_brightness(current[i] + int(float(str(value))), display=i, **kwargs))
                # flatten the list output
                out = flatten_list(out)
                return out[0] if len(out) == 1 else out

        value = current + int(float(str(value)))
    else:
        value = int(float(str(value)))

    value = max(0, min(100, value))

    # decide upon the OS relevant method to run
    method = None
    if platform.system() == 'Windows':
        method = windows.set_brightness
    elif platform.system() == 'Linux':
        if not force:
            value = max(1, value)
        method = linux.set_brightness
    elif platform.system() == 'Darwin':
        error = 'MAC is not supported'
    else:
        error = f'{platform.system()} is not supported'

    if method is not None:
        try:
            return method(value, **kwargs)
        except Exception as e:
            if verbose_error:
                raise ScreenBrightnessError from e
            error = e

    # if the function has not returned by now it failed
    raise ScreenBrightnessError(f'Cannot set screen brightness: {error}')


def fade_brightness(finish, start=None, interval=0.01, increment=1, blocking=True, **kwargs):
    '''
    A function to somewhat gently fade the screen brightness from `start` to `finish`

    Args:
        finish (int or str): the brightness level to end up on
        start (int or str): where the brightness should fade from.
                            If not specified the function starts from the current screen brightness
        interval (float or int): the time delay between each step in brightness
        increment (int): the amount to change the brightness by per step
        blocking (bool): whether this should occur in the main thread (`True`) or a new daemonic thread (`False`)
        kwargs (dict): passed directly to set_brightness (see `set_brightness` docs for available kwargs)

    Returns:
        list: list of `threading.Thread` objects if blocking == False,
            otherwise it returns the result of `get_brightness()`

    Example:
        ```
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
        available_monitors = filter_monitors(**kwargs)
    except (IndexError, LookupError) as e:
        raise ScreenBrightnessError(f'{type(e).__name__} -> {e}')
    except ValueError as e:
        if platform.system() == 'Linux' and ('method' in kwargs and kwargs['method'].lower() == 'xbacklight'):
            available_monitors = [None]
        else:
            raise e

    for i in available_monitors:
        try:
            monitor = Monitor(i)
            # same effect as monitor.is_active()
            current = monitor.get_brightness()
            st, fi = start, finish
            # convert strings like '+5' to an actual brightness value
            if type(fi) == str:
                if "+" in fi or "-" in fi:
                    fi = current + int(float(fi))
            if type(st) == str:
                if "+" in st or "-" in st:
                    st = current + int(float(st))

            st = current if st is None else st
            # make sure both values are within the correct range
            fi = min(max(int(fi), 0), 100)
            st = min(max(int(st), 0), 100)

            if finish != start:
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


def get_brightness(verbose_error=False, **kwargs):
    '''
    Returns the current display brightness

    Args:
        verbose_error (bool): controls the level of detail in the error messages
        kwargs (dict): is passed directly to the OS relevant brightness method

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
    method = None
    if platform.system() == 'Windows':
        method = windows.get_brightness
    elif platform.system() == 'Linux':
        method = linux.get_brightness
    elif platform.system() == 'Darwin':
        error = 'MAC is not supported'
    else:
        error = f'{platform.system()} is not supported'

    if method is not None:
        try:
            return method(**kwargs)
        except Exception as e:
            if verbose_error:
                raise ScreenBrightnessError from e
            error = e

    # if the function has not returned by now it failed
    raise ScreenBrightnessError(f'Cannot get screen brightness: {error}')


__cache__ = __Cache()
if platform.system() == 'Windows':
    from . import windows
elif platform.system() == 'Linux':
    from . import linux

__version__ = '0.8.0-dev'
__author__ = 'Crozzers'
