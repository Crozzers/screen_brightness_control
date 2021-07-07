import wmi
import threading
import pythoncom
import win32api
import time
import ctypes
from ctypes import windll, byref, Structure, WinError, POINTER, WINFUNCTYPE
from ctypes.wintypes import BOOL, HMONITOR, HDC, RECT, LPARAM, DWORD, BYTE, WCHAR, HANDLE
from . import flatten_list, _monitor_brand_lookup, filter_monitors, __cache__, platform, EDID
from typing import List, Union, Optional
import warnings
# a bunch of typing classes were deprecated in Python 3.9
# in favour of collections.abc (https://www.python.org/dev/peps/pep-0585/)
if int(platform.python_version_tuple()[1]) < 9:
    from typing import Generator
else:
    from collections.abc import Generator


def warn_deprecated(name, alternative=None):
    '''Temporary function to warn you that things have been deprecated
    and will be removed in the next update.'''
    if alternative is None:
        alternative = name

    msg = f'screen_brightness_control.windows.{name} is deprecated.'
    if alternative:
        msg += f' Use screen_brightness_control.{alternative} instead'
    warnings.warn(msg, DeprecationWarning)


def _wmi_init():
    '''internal function to create and return a wmi instance'''
    # WMI calls don't work in new threads so we have to run this check
    if threading.current_thread() != threading.main_thread():
        pythoncom.CoInitialize()
    instance = wmi.WMI(namespace='wmi')
    return instance


def get_display_info() -> List[dict]:
    '''
    Gets information about all connected displays using WMI and win32api

    Returns:
        list: list of dictionaries

    Example:
        ```python
        import screen_brightness_control as s

        info = s.windows.get_display_info()
        for display in info:
            print(display['name'])
        ```
    '''
    info = __cache__.get('windows_monitors_info_raw')
    if info is None:
        try:
            # collect all monitor UIDs (derived from DeviceID)
            monitor_uids = {}
            last_good = 0
            for i in win32api.EnumDisplayMonitors():
                tmp = win32api.GetMonitorInfo(i[0])
                try:
                    # If a user has all displays plugged into display adapter 4 then
                    # this statement would be tried for each adapter (0-4) per monitor
                    # meaning 4 tries per monitor, 12 tries total.
                    # By trying the "last good" adapter first, only the first display will
                    # be tried 4 times. All the others will be tried once
                    device = win32api.EnumDisplayDevices(tmp['Device'], last_good, 1)
                    monitor_uids[device.DeviceID.split('#')[2]] = device
                except Exception:
                    # iterate up to 4 display adapters
                    for j in range(5):
                        try:
                            # last_good is tried just above here. No point trying it again
                            if j != last_good:
                                # i have no idea what this 3rd parameter does but the code doesn't work without it
                                device = win32api.EnumDisplayDevices(tmp['Device'], j, 1)
                                monitor_uids[device.DeviceID.split('#')[2]] = device
                                last_good = j
                                break
                        except Exception:
                            continue

            # gather list of laptop displays to check against later
            wmi = _wmi_init()
            try:
                laptop_displays = [
                    i.InstanceName
                    for i in wmi.WmiMonitorBrightness()
                ]
            except Exception:
                laptop_displays = []

            extras, desktop, laptop = [], 0, 0
            uid_keys = list(monitor_uids.keys())
            for monitor in wmi.WmiMonitorDescriptorMethods():
                try:
                    model, serial, manufacturer, man_id, edid = None, None, None, None, None
                    instance_name = monitor.InstanceName.replace('_0', '', 1).split('\\')[2]
                    pydevice = monitor_uids[instance_name]

                    # get the EDID
                    try:
                        edid = ''
                        for char in monitor.WmiGetMonitorRawEEdidV1Block(0)[0]:
                            char = hex(char)[2:]
                            if len(char) == 1:
                                char = '0' + char
                            edid += char
                    except Exception:
                        edid = None

                    # get serial, model, manufacturer and manufacturer ID
                    try:
                        if edid is None:
                            raise Exception
                        # we do the EDID parsing ourselves because calling wmi.WmiMonitorID
                        # takes too long
                        name, serial = EDID.parse_edid(edid)
                        if name is None:
                            raise Exception

                        # split by last space because model numbers usually are one word
                        # whereas brands can be multiple (EG: 'LG Electronics')
                        manufacturer, model = name.rsplit(' ', 1)
                        try:
                            man_id, manufacturer = _monitor_brand_lookup(manufacturer)
                        except Exception:
                            man_id, manufacturer = None, manufacturer.lower().capitalize()
                    except Exception:
                        devid = pydevice.DeviceID.split('#')
                        serial = devid[2]
                        man_id = devid[1][:3]
                        model = devid[3]
                        del(devid)
                        try:
                            man_id, manufacturer = _monitor_brand_lookup(man_id)
                        except Exception:
                            manufacturer = None

                    if (serial, model) != (None, None):
                        data = {
                            'name': f'{manufacturer} {model}',
                            'model': model,
                            'serial': serial,
                            'manufacturer': manufacturer,
                            'manufacturer_id': man_id,
                            'edid': edid
                        }
                        if monitor.InstanceName in laptop_displays:
                            data['index'] = laptop
                            data['method'] = WMI
                            laptop += 1
                        else:
                            data['method'] = VCP
                            desktop += 1

                        if instance_name in uid_keys:
                            # insert the data into the uid_keys list because
                            # uid_keys has the monitors sorted correctly. This
                            # means we don't have to re-sort the list later
                            uid_keys[uid_keys.index(instance_name)] = data
                        else:
                            extras.append(data)
                except Exception:
                    pass

            info = uid_keys + extras
            if desktop:
                # now make sure desktop monitors have the correct index
                count = 0
                for item in info:
                    if item['method'] == VCP:
                        item['index'] = count
                        count += 1
        except Exception:
            pass
        __cache__.store('windows_monitors_info_raw', info)

    return info


class WMI:
    '''
    A collection of screen brightness related methods using the WMI API.
    This class primarily works with laptop displays.
    '''
    @classmethod
    def get_display_info(cls, display: Optional[Union[int, str]] = None) -> List[dict]:
        '''
        Returns a list of dictionaries of info about all detected monitors

        Args:
            display (str or int): [*Optional*] the monitor to return info about.
                Pass in the serial number, name, model, edid or index

        Returns:
            list: list of dicts

        Example:
            ```python
            import screen_brightness_control as sbc

            info = sbc.windows.WMI.get_display_info()
            for i in info:
                print('================')
                for key, value in i.items():
                    print(key, ':', value)

            # get information about the first WMI addressable monitor
            primary_info = sbc.windows.WMI.get_display_info(0)

            # get information about a monitor with a specific name
            benq_info = sbc.windows.WMI.get_display_info('BenQ GL2450H')
            ```
        '''
        info = __cache__.get('wmi_monitor_info')
        if info is None:
            info = [i for i in get_display_info() if i['method'] == cls]
            __cache__.store('wmi_monitor_info', info)
        if display is not None:
            info = filter_monitors(display=display, haystack=info)
        return info

    @classmethod
    def get_display_names(cls) -> List[str]:
        '''
        **DEPRECATED**.
        Returns names of all displays that can be addressed by WMI

        Returns:
            list: list of strings

        Example:
            ```python
            import screen_brightness_control as sbc

            for name in sbc.windows.WMI.get_display_names():
                print(name)
            ```
        '''
        warn_deprecated('WMI.get_display_names', 'list_monitors(method="wmi")')
        return [i['name'] for i in cls.get_display_info()]

    @classmethod
    def set_brightness(cls, value: int, display: Optional[int] = None):
        '''
        Sets the display brightness for Windows using WMI

        Args:
            value (int): The percentage to set the brightness to
            display (int): The specific display you wish to query.

        Raises:
            LookupError: if the given display cannot be found

        Example:
            ```python
            import screen_brightness_control as sbc

            # set brightness of WMI addressable monitors to 50%
            sbc.windows.WMI.set_brightness(50)

            # set the primary display brightness to 75%
            sbc.windows.WMI.set_brightness(75, display = 0)

            # set the brightness of the secondary display to 25%
            sbc.windows.WMI.set_brightness(25, display = 1)
            ```
        '''
        brightness_method = _wmi_init().WmiMonitorBrightnessMethods()
        if display is not None:
            brightness_method = [brightness_method[display]]

        for method in brightness_method:
            method.WmiSetBrightness(value, 0)

    @classmethod
    def get_brightness(cls, display: Optional[int] = None) -> List[int]:
        '''
        Returns the current display brightness using WMI

        Args:
            display (int): The specific display you wish to query.

        Returns:
            list: list of integers (0 to 100)

        Raises:
            LookupError: if the given display cannot be found

        Example:
            ```python
            import screen_brightness_control as sbc

            # get brightness of all WMI addressable monitors
            current_brightness = sbc.windows.WMI.get_brightness()
            if type(current_brightness) is int:
                print('There is only one detected display')
            else:
                print('There are', len(current_brightness), 'detected displays')

            # get the primary display brightness
            primary_brightness = sbc.windows.WMI.get_brightness(display = 0)

            # get the brightness of the secondary monitor
            benq_brightness = sbc.windows.WMI.get_brightness(display = 1)
            ```
        '''
        brightness_method = _wmi_init().WmiMonitorBrightness()
        if display is not None:
            brightness_method = [brightness_method[display]]

        values = [i.CurrentBrightness for i in brightness_method]
        return values


class VCP:
    '''Collection of screen brightness related methods using the DDC/CI commands'''
    _MONITORENUMPROC = WINFUNCTYPE(BOOL, HMONITOR, HDC, POINTER(RECT), LPARAM)

    class _PHYSICAL_MONITOR(Structure):
        '''internal class, do not call'''
        _fields_ = [('handle', HANDLE),
                    ('description', WCHAR * 128)]

    @classmethod
    def iter_physical_monitors(cls, start: int = 0) -> Generator[ctypes.wintypes.HANDLE, None, None]:
        '''
        A generator to iterate through all physical monitors
        and then close them again afterwards, yielding their handles.
        It is not recommended to use this function unless you are familiar with `ctypes` and `windll`

        Args:
            start (int): skip the first X handles

        Yields:
            ctypes.wintypes.HANDLE

        Raises:
            ctypes.WinError: upon failure to enumerate through the monitors

        Example:
            ```python
            import screen_brightness_control as sbc

            for monitor in sbc.windows.VCP.iter_physical_monitors():
                print(sbc.windows.VCP.get_monitor_caps(monitor))
            ```
        '''
        def callback(hmonitor, hdc, lprect, lparam):
            monitors.append(HMONITOR(hmonitor))
            return True

        monitors = []
        if not windll.user32.EnumDisplayMonitors(None, None, cls._MONITORENUMPROC(callback), None):
            raise WinError('EnumDisplayMonitors failed')

        index = 0

        for monitor in monitors:
            # Get physical monitor count
            count = DWORD()
            if not windll.dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR(monitor, byref(count)):
                raise WinError()
            if count.value > 0:
                if start and index + count.value < start:
                    index += count.value
                    continue
                # Get physical monitor handles
                physical_array = (cls._PHYSICAL_MONITOR * count.value)()
                if not windll.dxva2.GetPhysicalMonitorsFromHMONITOR(monitor, count.value, physical_array):
                    raise WinError()
                for item in physical_array:
                    if not (start and index != start):
                        yield item.handle
                    windll.dxva2.DestroyPhysicalMonitor(item.handle)
                    index += 1

    @classmethod
    def get_display_info(cls, display: Optional[Union[int, str]] = None) -> List[dict]:
        '''
        Returns a dictionary of info about all detected monitors or a selection of monitors

        Args:
            display (int or str): [*Optional*] the monitor to return info about.
                Pass in the serial number, name, model, edid or index

        Returns:
            list: list of dicts

        Example:
            ```python
            import screen_brightness_control as sbc

            # get the information about all monitors
            vcp_info = sbc.windows.VCP.get_display_info()
            print(vcp_info)
            # EG output: [{'name': 'BenQ GL2450H', ... }, {'name': 'Dell U2211H', ... }]

            # get information about a monitor with this specific model
            bnq_info = sbc.windows.VCP.get_display_info('GL2450H')
            # EG output: {'name': 'BenQ GL2450H', 'model': 'GL2450H', ... }
            ```
        '''
        info = __cache__.get('vcp_monitor_info')
        if info is None:
            info = [i for i in get_display_info() if i['method'] == cls]
            __cache__.store('vcp_monitor_info', info)
        if display is not None:
            info = filter_monitors(display=display, haystack=info)
        return info

    @staticmethod
    def get_monitor_caps(monitor: ctypes.wintypes.HANDLE) -> str:
        '''
        **DEPRECATED**.
        Fetches and returns the VCP capabilities string of a monitor.
        This function takes anywhere from 1-2 seconds to run

        Args:
            monitor: a monitor handle as returned by `VCP.iter_physical_monitors()`

        Returns:
            str: a string of the monitor's capabilities

        Examples:
            ```python
            import screen_brightness_control as sbc

            for monitor in sbc.windows.VCP.iter_physical_monitors():
                print(sbc.windows.VCP.get_monitor_caps(monitor))
            # EG output: '(prot(monitor)type(LCD)model(GL2450HM)cmds(01 02 03 07 0C F3)vcp(02...)'
            ```
        '''
        warn_deprecated('VCP.get_monitor_caps', False)
        caps_string_length = DWORD()
        if not windll.dxva2.GetCapabilitiesStringLength(monitor, ctypes.byref(caps_string_length)):
            return
        caps_string = (ctypes.c_char * caps_string_length.value)()
        if not windll.dxva2.CapabilitiesRequestAndCapabilitiesReply(monitor, caps_string, caps_string_length):
            return
        return caps_string.value.decode('ASCII')

    @classmethod
    def get_display_names(cls) -> List[str]:
        '''
        **DEPRECATED**.
        Return the names of each detected monitor

        Returns:
            list: list of strings

        Example:
            ```python
            import screen_brightness_control as sbc

            names = sbc.windows.VCP.get_display_names()
            print(names)
            # EG output: ['BenQ GL2450H', 'Dell U2211H']
            ```
        '''
        warn_deprecated('VCP.get_display_names', 'list_monitors(method="vcp")')
        return [i['name'] for i in cls.get_display_info()]

    @classmethod
    def get_brightness(cls, display: Optional[int] = None) -> List[int]:
        '''
        Retrieve the brightness of all connected displays using the `ctypes.windll` API

        Args:
            display (int): The specific display you wish to query.

        Returns:
            list: list of ints (0 to 100)

        Examples:
            ```python
            import screen_brightness_control as sbc

            # Get the brightness for all detected displays
            current_brightness = sbc.windows.VCP.get_brightness()
            print('There are', len(current_brightness), 'detected displays')

            # Get the brightness for the primary display
            primary_brightness = sbc.windows.VCP.get_brightness(display = 0)[0]

            # Get the brightness for a secondary display
            secondary_brightness = sbc.windows.VCP.get_brightness(display = 1)[0]
            ```
        '''
        code = BYTE(0x10)
        values = []
        for index, monitor in enumerate(
            cls.iter_physical_monitors(start=display),
            start=display if display is not None else 0
        ):
            current = __cache__.get(f'vcp_brightness_{index}')
            if current is None:
                cur_out = DWORD()
                handle = HANDLE(monitor)
                for _ in range(10):
                    if windll.dxva2.GetVCPFeatureAndVCPFeatureReply(handle, code, None, byref(cur_out), None):
                        current = cur_out.value
                        break
                    else:
                        current = None
                        time.sleep(0.02)

            if current is not None:
                __cache__.store(f'vcp_brightness_{index}', current, expires=0.1)
                values.append(current)

            if display == index:
                # if we have just got the display we wanted then exit here
                # no point iterating through all the other ones
                break

        return values

    @classmethod
    def set_brightness(cls, value: int, display: Optional[int] = None):
        '''
        Sets the brightness for all connected displays using the `ctypes.windll` API

        Args:
            display (int): The specific display you wish to query.

        Examples:
            ```python
            import screen_brightness_control as sbc

            # Set the brightness for all detected displays to 50%
            sbc.windows.VCP.set_brightness(50)

            # Set the brightness for the primary display to 75%
            sbc.windows.VCP.set_brightness(75, display = 0)

            # Set the brightness for a secondary display to 25%
            sbc.windows.VCP.set_brightness(25, display = 1)
            ```
        '''
        __cache__.expire(startswith='vcp_brightness_')
        code = BYTE(0x10)
        for index, monitor in enumerate(
            cls.iter_physical_monitors(start=display),
            start=display if display is not None else 0
        ):
            if display is None or display == index:
                handle = HANDLE(monitor)
                value = DWORD(value)
                for _ in range(10):
                    if windll.dxva2.SetVCPFeature(handle, code, value):
                        break
                    else:
                        time.sleep(0.02)


def list_monitors_info(method: Optional[str] = None, allow_duplicates: bool = False) -> List[dict]:
    '''
    Lists detailed information about all detected monitors

    Args:
        method (str): the method the monitor can be addressed by. Can be 'wmi' or 'vcp'
        allow_duplicates (bool): whether to filter out duplicate displays (displays with the same EDID) or not

    Returns:
        list: list of dicts upon success, empty list upon failure

    Raises:
        ValueError: if the method kwarg is invalid

    Example:
        ```python
        import screen_brightness_control as sbc

        monitors = sbc.windows.list_monitors_info()
        for info in monitors:
            print('=======================')
            # the manufacturer name plus the model
            print('Name:', info['name'])
            # the general model of the display
            print('Model:', info['model'])
            # a unique string assigned by Windows to this display
            print('Serial:', info['serial'])
            # the name of the brand of the monitor
            print('Manufacturer:', info['manufacturer'])
            # the 3 letter code corresponding to the brand name, EG: BNQ -> BenQ
            print('Manufacturer ID:', info['manufacturer_id'])
            # the index of that display FOR THE SPECIFIC METHOD THE DISPLAY USES
            print('Index:', info['index'])
            # the method this monitor can be addressed by
            print('Method:', info['method'])
            # the EDID string of the monitor
            print('EDID:', info['edid'])
        ```
    '''
    info = __cache__.get(f'windows_monitors_info_{method}_{allow_duplicates}')
    if info is None:
        info = get_display_info()

        if method is not None:
            method = method.lower()
            if method not in ('wmi', 'vcp'):
                raise ValueError('method kwarg must be "wmi" or "vcp"')

        info_final = []
        serials = []
        # to make sure each display (with unique edid) is only reported once
        for i in info:
            if allow_duplicates or i['serial'] not in serials:
                if method is None or method == i['method'].__name__.lower():
                    serials.append(i['serial'])
                    info_final.append(i)
        __cache__.store(f'windows_monitors_info_{method}_{allow_duplicates}', info_final)
        info = info_final
    return info


def list_monitors(method: Optional[str] = None) -> List[str]:
    '''
    **DEPRECATED**.
    Returns a list of all addressable monitor names

    Args:
        method (str): the method the monitor can be addressed by. Can be 'wmi' or 'vcp'

    Returns:
        list: list of strings

    Example:
        ```python
        import screen_brightness_control as sbc

        monitors = sbc.windows.list_monitors()
        # EG output: ['BenQ GL2450H', 'Dell U2211H']
        ```
    '''
    warn_deprecated('list_monitors')
    return [i['name'] for i in list_monitors_info(method=method)]


def __set_and_get_brightness(*args, display=None, method=None, meta_method='get', **kwargs) -> Union[List[int], None]:
    '''
    **DEPRECATED**.
    Internal function, do not call. Either sets the brightness or gets it.
    Exists because set_brightness and get_brightness only have a couple differences
    '''
    warn_deprecated('__set_and_get_brightness', '__brightness')
    errors = []
    try:  # filter known list of monitors according to kwargs
        if type(display) == int:
            monitors = [list_monitors_info(method=method)[display]]
        else:
            monitors = filter_monitors(display=display, method=method)
    except Exception as e:
        errors.append(['', type(e).__name__, e])
    else:
        output = []
        for m in monitors:  # add the output of each brightness method to the output list
            try:
                output.append(
                    getattr(m['method'], meta_method + '_brightness')(*args, display=m['index'], **kwargs)
                )
            except Exception as e:
                output.append(None)
                errors.append([f"{m['name']} ({m['serial']})", type(e).__name__, e])

        # use `'no_return' not in kwargs` because dict membership only checks the keys
        if (
            output and not
            (all(i in (None, []) for i in output) and ('no_return' not in kwargs or not kwargs['no_return']))
        ):
            # flatten and return any output (taking into account the no_return parameter)
            if 'no_return' in kwargs and kwargs['no_return']:
                return None
            output = flatten_list(output)
            return output

    # if function hasn't already returned it has failed
    msg = '\n'
    for e in errors:
        msg += f'\t{e[0]} -> {e[1]}: {e[2]}\n'
    if msg == '\n':
        msg += '\tno valid output was received from brightness methods'
    raise Exception(msg)


def set_brightness(
    value: int,
    display: Optional[Union[int, str]] = None,
    method: Optional[str] = None,
    **kwargs
) -> Union[List[int], None]:
    '''
    **DEPRECATED**.
    Sets the brightness of any connected monitors

    Args:
        value (int): Sets the brightness to this value as a percentage
        display (int or str): The specific display you wish to adjust.
            Can be index, model, name or serial of the display
        method (str): the method to use ('wmi' or 'vcp')
        kwargs (dict): passed directly to the chosen brightness method

    Returns:
        list: list of ints (0 to 100) (the result of `get_brightness`)
        None: if `no_return` is True

    Raises:
        LookupError: if the chosen display (with method if applicable) is not found
        ValueError: if the chosen method is invalid
        TypeError: if the value given for `display` is not int or str
        Exception: if the brightness could not be set by any method

    Example:
        ```python
        import screen_brightness_control as sbc

        # set the current brightness to 50%
        sbc.windows.set_brightness(50)

        # set the brightness of the primary display to 75%
        sbc.windows.set_brightness(75, display = 0)

        # set the brightness of any displays using VCP to 25%
        sbc.windows.set_brightness(25, method = 'vcp')

        # set the brightness of displays with model name 'BenQ GL2450H' to 100%
        sbc.windows.set_brightness(100, display = 'BenQ GL2450H')
        ```
    '''
    warn_deprecated('set_brightness')
    # this function is called because set_brightness and get_brightness only differed by 1 line of code
    # so I made another internal function to reduce the filesize
    return __set_and_get_brightness(value, display=display, method=method, meta_method='set', **kwargs)


def get_brightness(display: Optional[Union[int, str]] = None, method: Optional[str] = None, **kwargs) -> List[int]:
    '''
    **DEPRECATED**.
    Returns the brightness of any connected monitors

    Args:
        display (int or str): The specific display you wish to adjust.
            Can be index, model, name or serial of the display
        method (str): the method to use ('wmi' or 'vcp')
        kwargs (dict): passed directly to chosen brightness method

    Returns:
        list: list of ints (0 to 100)

    Raises:
        LookupError: if the chosen display (with method if applicable) is not found
        ValueError: if the chosen method is invalid
        TypeError: if the value given for `display` is not int or str
        Exception: if the brightness could not be obtained by any method

    Example:
        ```python
        import screen_brightness_control as sbc

        # get the current brightness
        current_brightness = sbc.windows.get_brightness()
        if type(current_brightness) is int:
            print('There is only one detected display')
        else:
            print('There are', len(current_brightness), 'detected displays')

        # get the brightness of the primary display
        primary_brightness = sbc.windows.get_brightness(display=0)[0]

        # get the brightness of any displays using VCP
        vcp_brightness = sbc.windows.get_brightness(method='vcp')

        # get the brightness of displays with the model name 'BenQ GL2450H'
        benq_brightness = sbc.windows.get_brightness(display='BenQ GL2450H')[0]
        ```
    '''
    warn_deprecated('get_brightness')
    # this function is called because set_brightness and get_brightness only differed by 1 line of code
    # so I made another internal function to reduce the filesize
    return __set_and_get_brightness(display=display, method=method, meta_method='get', **kwargs)
