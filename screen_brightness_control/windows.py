import wmi
import threading
import pythoncom
import win32api
import time
import ctypes
from ctypes import windll, byref, Structure, WinError, POINTER, WINFUNCTYPE
from ctypes.wintypes import BOOL, HMONITOR, HDC, RECT, LPARAM, DWORD, BYTE, WCHAR, HANDLE
from . import flatten_list, _monitor_brand_lookup, filter_monitors, __cache__, platform
from typing import List, Union, Optional
# a bunch of typing classes were deprecated in Python 3.9
# in favour of collections.abc (https://www.python.org/dev/peps/pep-0585/)
if int(platform.python_version_tuple()[1]) < 9:
    from typing import Iterable
else:
    from collections.abc import Iterable


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
    try:
        info = __cache__.get('windows_monitors_info_raw')
    except Exception:
        info = []
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
                laptop_displays = []
                for i in wmi.WmiMonitorBrightness():
                    laptop_displays.append(
                        i.InstanceName.replace('_0', '', 1).split('\\')[2]
                    )
            except Exception:
                pass
            monitors = []
            extras = []
            uid_keys = list(monitor_uids.keys())
            for m in wmi.WmiMonitorID():
                name = m.InstanceName.replace('_0', '', 1).split('\\')[2]
                if name in uid_keys:
                    monitors.append(m)
                else:
                    extras.append(m)

            # sort the monitors in the same order as win32api reports them
            # because the first item in win32api's list is usually the primary display
            monitors = sorted(
                monitors,
                key=lambda x: uid_keys.index(x.InstanceName.replace('_0', '', 1).split('\\')[2])
            )

            monitors += extras

            # get all available edid strings
            try:
                descriptors = {
                    i.InstanceName: i.WmiGetMonitorRawEEdidV1Block(0) for i in wmi.WmiMonitorDescriptorMethods()
                }
            except Exception:
                pass
            laptop = 0
            desktop = 0
            for monitor in monitors:
                model, serial, manufacturer, man_id, edid = None, None, None, None, None
                instance_name = monitor.InstanceName.replace('_0', '', 1).split('\\')[2]
                pydevice = monitor_uids[instance_name]

                try:
                    serial = bytes(monitor.SerialNumberID).decode().replace('\x00', '')
                    manufacturer, model = bytes(monitor.UserFriendlyName).decode().replace('\x00', '').split(' ')
                    manufacturer = manufacturer.lower().capitalize()
                    try:
                        man_id, manufacturer = _monitor_brand_lookup(manufacturer)
                    except Exception:
                        man_id = None
                except Exception:
                    devid = pydevice.DeviceID.split('#')
                    serial = devid[2]
                    man_id = devid[1][:3]
                    model = devid[3:]
                    del(devid)
                    try:
                        man_id, manufacturer = _monitor_brand_lookup(man_id)
                    except Exception:
                        manufacturer = None
                try:
                    try:
                        chars = descriptors[monitor.InstanceName][0]
                    except Exception:
                        chars = descriptors[pydevice.InstanceName][0]
                    finally:
                        edid = ''
                        for char in chars:
                            char = str(hex(char)).replace('0x', '')
                            if len(char) == 1:
                                char = '0' + char
                            edid += char
                        del(chars)
                except Exception:
                    edid = None

                if (serial, model) != (None, None):
                    info.append(
                        {
                            'name': f'{manufacturer} {model}',
                            'model': model,
                            'serial': serial,
                            'manufacturer': manufacturer,
                            'manufacturer_id': man_id,
                            'edid': edid
                        }
                    )
                    if instance_name in laptop_displays:
                        info[-1]['index'] = laptop
                        info[-1]['method'] = WMI
                        laptop += 1
                    else:
                        info[-1]['index'] = desktop
                        info[-1]['method'] = VCP
                        desktop += 1
        except Exception:
            pass
        __cache__.store('windows_monitors_info_raw', info)

    return info


class WMI:
    '''
    A collection of screen brightness related methods using the WMI API.
    This class primarily works with laptop displays.
    '''
    @staticmethod
    def get_display_info(display: Optional[Union[int, str]] = None) -> List[dict]:
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
        try:
            info = __cache__.get('wmi_monitor_info')
        except Exception:
            info = [i for i in get_display_info() if i['method'] == WMI]
            __cache__.store('wmi_monitor_info', info)
        if display is not None:
            info = filter_monitors(display=display, haystack=info)
        return info

    @staticmethod
    def get_display_names() -> List[str]:
        '''
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
        return [i['name'] for i in WMI.get_display_info()]

    @staticmethod
    def set_brightness(
        value: int,
        display: Optional[Union[int, str]] = None,
        no_return: bool = False
    ) -> Union[List[int], None]:
        '''
        Sets the display brightness for Windows using WMI

        Args:
            value (int): The percentage to set the brightness to
            display (int or str): The specific display you wish to query.
                Can be index, name, model, serial or edid string.
                `int` is faster as it isn't passed to `filter_monitors` to be matched against.
                `str` is slower as it is passed to `filter_monitors` to match to a display.
            no_return (bool): if True, this function returns None
                Otherwise it returns the result of `WMI.get_brightness()`

        Returns:
            list: list of integers (0 to 100)
            None: if `no_return` is set to `True`

        Raises:
            LookupError: if the given display cannot be found

        Example:
            ```python
            import screen_brightness_control as sbc

            # set brightness of WMI addressable monitors to 50%
            sbc.windows.WMI.set_brightness(50)

            # set the primary display brightness to 75%
            sbc.windows.WMI.set_brightness(75, display = 0)

            # set the brightness of a named monitor to 25%
            sbc.windows.WMI.set_brightness(25, display = 'BenQ GL2450H')
            ```
        '''
        brightness_method = _wmi_init().WmiMonitorBrightnessMethods()
        if display is not None:
            if type(display) == int:
                brightness_method = [brightness_method[display]]
            else:
                indexes = [i['index'] for i in filter_monitors(display=display, method='wmi')]
                brightness_method = [brightness_method[i] for i in indexes]
        for method in brightness_method:
            method.WmiSetBrightness(value, 0)
        return WMI.get_brightness(display=display) if not no_return else None

    @staticmethod
    def get_brightness(display: Optional[Union[int, str]] = None) -> List[int]:
        '''
        Returns the current display brightness using WMI

        Args:
            display (int or str): The specific display you wish to query.
                Can be index, name, model, serial or edid string.
                `int` is faster as it isn't passed to `filter_monitors` to be matched against.
                `str` is slower as it is passed to `filter_monitors` to match to a display.

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

            # get the brightness of a named monitor
            benq_brightness = sbc.windows.WMI.get_brightness(display = 'BenQ GL2450H')
            ```
        '''
        brightness_method = _wmi_init().WmiMonitorBrightness()
        if display is not None:
            if type(display) == int:
                brightness_method = [brightness_method[display]]
            else:
                displays = WMI.get_display_info(display)
                brightness_method = [brightness_method[i['index']] for i in displays]

        values = [i.CurrentBrightness for i in brightness_method]
        return values


class VCP:
    '''Collection of screen brightness related methods using the DDC/CI commands'''
    _MONITORENUMPROC = WINFUNCTYPE(BOOL, HMONITOR, HDC, POINTER(RECT), LPARAM)

    class _PHYSICAL_MONITOR(Structure):
        '''internal class, do not call'''
        _fields_ = [('handle', HANDLE),
                    ('description', WCHAR * 128)]

    @staticmethod
    def iter_physical_monitors() -> Iterable[ctypes.wintypes.HANDLE]:
        '''
        A generator to iterate through all physical monitors
        and then close them again afterwards, yielding their handles.
        It is not recommended to use this function unless you are familiar with `ctypes` and `windll`

        Returns:
            generator: generator that yields `ctypes.wintypes.HANDLE` objects

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
        if not windll.user32.EnumDisplayMonitors(None, None, VCP._MONITORENUMPROC(callback), None):
            raise WinError('EnumDisplayMonitors failed')
        for monitor in monitors:
            # Get physical monitor count
            count = DWORD()
            if not windll.dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR(monitor, byref(count)):
                raise WinError()
            if count.value > 0:
                # Get physical monitor handles
                physical_array = (VCP._PHYSICAL_MONITOR * count.value)()
                if not windll.dxva2.GetPhysicalMonitorsFromHMONITOR(monitor, count.value, physical_array):
                    raise WinError()
                for item in physical_array:
                    yield item.handle
                    windll.dxva2.DestroyPhysicalMonitor(item.handle)

    @staticmethod
    def get_display_info(display: Optional[Union[int, str]] = None) -> List[dict]:
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
        try:
            info = __cache__.get('vcp_monitor_info')
        except Exception:
            info = [i for i in get_display_info() if i['method'] == VCP]
            __cache__.store('vcp_monitor_info', info)
        if display is not None:
            info = filter_monitors(display=display, haystack=info)
        return info

    @staticmethod
    def get_monitor_caps(monitor: ctypes.wintypes.HANDLE) -> str:
        '''
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
        caps_string_length = DWORD()
        if not windll.dxva2.GetCapabilitiesStringLength(monitor, ctypes.byref(caps_string_length)):
            return
        caps_string = (ctypes.c_char * caps_string_length.value)()
        if not windll.dxva2.CapabilitiesRequestAndCapabilitiesReply(monitor, caps_string, caps_string_length):
            return
        return caps_string.value.decode('ASCII')

    @staticmethod
    def get_display_names() -> List[str]:
        '''
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
        return [i['name'] for i in VCP.get_display_info()]

    @staticmethod
    def get_brightness(display: Optional[Union[int, str]] = None) -> List[int]:
        '''
        Retrieve the brightness of all connected displays using the `ctypes.windll` API

        Args:
            display (int or str): The specific display you wish to query.
                Can be index, name, model, serial or edid string.
                `int` is faster as it isn't passed to `filter_monitors` to be matched against.
                `str` is slower as it is passed to `filter_monitors` to match to a display.

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

            # Get the brightness for a display with the model 'GL2450H'
            benq_brightness = sbc.windows.VCP.get_brightness(display = 'GL2450H')[0]
            ```
        '''
        # filter monitors even if display kwarg is not specified due to oddities surrounding issues #7 and #8
        # https://github.com/Crozzers/screen_brightness_control/issues/7
        # https://github.com/Crozzers/screen_brightness_control/issues/8
        # essentially, we get 'ghost' monitors showing up here that cannot actually
        # be adjusted (even if no error gets raised) so we use this to filter out
        # such ghost monitors by only attempting to get the brightness for valid monitors
        # (determined by VCP.get_display_info)
        # yes, it does add an unnecessary function call but that's only if you're using this module low-level.
        # Top-level functions always end up specifying the display kwarg anyway
        if type(display) == int:
            indexes = [display]
        else:
            indexes = [i['index'] for i in filter_monitors(display=display, haystack=VCP.get_display_info())]

        count = 0
        values = []
        for m in VCP.iter_physical_monitors():
            try:
                v = __cache__.get(f'vcp_brightness_{count}')
            except Exception:
                cur_out = DWORD()
                for _ in range(10):
                    if windll.dxva2.GetVCPFeatureAndVCPFeatureReply(HANDLE(m), BYTE(0x10), None, byref(cur_out), None):
                        v = cur_out.value
                        break
                    else:
                        time.sleep(0.02)
                        v = None
                del(cur_out)
            if v is not None:
                if count in indexes:
                    try:
                        __cache__.store(f'vcp_brightness_{count}', v, expires=0.1)
                    except IndexError:
                        pass
                    values.append(v)
                    if count >= max(indexes):
                        break
            count += 1

        return values

    @staticmethod
    def set_brightness(
        value: int,
        display: Optional[Union[int, str]] = None,
        no_return: bool = False
    ) -> Union[List[int], None]:
        '''
        Sets the brightness for all connected displays using the `ctypes.windll` API

        Args:
            display (int or str): The specific display you wish to query.
                Can be index, name, model, serial or edid string.
                `int` is faster as it isn't passed to `filter_monitors` to be matched against.
                `str` is slower as it is passed to `filter_monitors` to match to a display.
            no_return (bool): if set to `True` this function will return `None`

        Returns:
            list: list of ints (0 to 100) (the result of `VCP.get_brightness`) if `no_return` is False
            None: if `no_return` is True

        Examples:
            ```python
            import screen_brightness_control as sbc

            # Set the brightness for all detected displays to 50%
            sbc.windows.VCP.set_brightness(50)

            # Set the brightness for the primary display to 75%
            sbc.windows.VCP.set_brightness(75, display = 0)

            # Set the brightness for a secondary display to 25%
            sbc.windows.VCP.set_brightness(25, display = 1)

            # Set the brightness for a display with the model 'GL2450H' to 100%
            sbc.windows.VCP.set_brightness(100, display = 'GL2450H')
            ```
        '''
        if type(display) == int:
            indexes = [display]
        else:
            # see VCP.set_brightness for the explanation for why we always gather this list
            indexes = [i['index'] for i in filter_monitors(display=display, haystack=VCP.get_display_info())]

        __cache__.expire(startswith='vcp_brightness_')

        count = 0
        for m in VCP.iter_physical_monitors():
            if display is None or (count in indexes):
                for _ in range(10):
                    if windll.dxva2.SetVCPFeature(HANDLE(m), BYTE(0x10), DWORD(value)):
                        break
                    else:
                        time.sleep(0.02)
            count += 1
        return VCP.get_brightness(display=display) if not no_return else None


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
    try:
        return __cache__.get(f'windows_monitors_info_{method}_{allow_duplicates}')
    except Exception:
        info = get_display_info()

        if method is not None:
            method = method.lower()
            if method not in ('wmi', 'vcp'):
                raise ValueError('method kwarg must be \'wmi\' or \'vcp\'')

        info_final = []
        serials = []
        # to make sure each display (with unique edid) is only reported once
        for i in info:
            if allow_duplicates or i['serial'] not in serials:
                if method is None or method == i['method'].__name__.lower():
                    serials.append(i['serial'])
                    info_final.append(i)
        __cache__.store(f'windows_monitors_info_{method}_{allow_duplicates}', info_final)
        return info_final


def list_monitors(method: Optional[str] = None) -> List[str]:
    '''
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
    return [i['name'] for i in list_monitors_info(method=method)]


def __set_and_get_brightness(*args, display=None, method=None, meta_method='get', **kwargs) -> Union[List[int], None]:
    '''
    Internal function, do not call. Either sets the brightness or gets it.
    Exists because set_brightness and get_brightness only have a couple differences
    '''
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
    # this function is called because set_brightness and get_brightness only differed by 1 line of code
    # so I made another internal function to reduce the filesize
    return __set_and_get_brightness(value, display=display, method=method, meta_method='set', **kwargs)


def get_brightness(display: Optional[Union[int, str]] = None, method: Optional[str] = None, **kwargs) -> List[int]:
    '''
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
    # this function is called because set_brightness and get_brightness only differed by 1 line of code
    # so I made another internal function to reduce the filesize
    return __set_and_get_brightness(display=display, method=method, meta_method='get', **kwargs)
