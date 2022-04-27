import ctypes
import platform
import threading
import time
from ctypes import POINTER, WINFUNCTYPE, Structure, WinError, byref, windll
from ctypes.wintypes import (BOOL, BYTE, DWORD, HANDLE, HDC, HMONITOR, LPARAM,
                             RECT, WCHAR)
from typing import List, Optional, Union

import pythoncom
import win32api
import win32con
import wmi

from . import filter_monitors, get_methods
from .helpers import EDID, __cache__, _monitor_brand_lookup

# a bunch of typing classes were deprecated in Python 3.9
# in favour of collections.abc (https://www.python.org/dev/peps/pep-0585/)
if int(platform.python_version_tuple()[1]) < 9:
    from typing import Generator
else:
    from collections.abc import Generator


def _wmi_init():
    '''internal function to create and return a wmi instance'''
    # WMI calls don't work in new threads so we have to run this check
    if threading.current_thread() != threading.main_thread():
        pythoncom.CoInitialize()
    return wmi.WMI(namespace='wmi')


def enum_display_devices() -> Generator[win32api.PyDISPLAY_DEVICEType, None, None]:
    '''
    Yields all display devices connected to the computer

    Yields:
        win32api.PyDISPLAY_DEVICEType
    '''
    for monitor_enum in win32api.EnumDisplayMonitors():
        pyhandle = monitor_enum[0]
        monitor_info = win32api.GetMonitorInfo(pyhandle)
        for adaptor_index in range(5):
            try:
                device = win32api.EnumDisplayDevices(monitor_info['Device'], adaptor_index, 1)
            except Exception:
                pass
            else:
                yield device
                break


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
        info = []
        try:
            # collect all monitor UIDs (derived from DeviceID)
            monitor_uids = {}
            for device in enum_display_devices():
                monitor_uids[device.DeviceID.split('#')[2]] = device

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
                        edid = ''.join(f'{char:02x}' for char in monitor.WmiGetMonitorRawEEdidV1Block(0)[0])
                    except Exception:
                        edid = None

                    # get serial, model, manufacturer and manufacturer ID
                    try:
                        if edid is None:
                            raise Exception
                        # we do the EDID parsing ourselves because calling wmi.WmiMonitorID
                        # takes too long
                        parsed = EDID.parse(edid)
                        name, serial = parsed['name'], parsed['serial']
                        if name is None:
                            raise Exception

                        # split by last space because model numbers usually are one word
                        # whereas brands can be multiple (EG: 'LG Electronics')
                        manufacturer, model = name.rsplit(' ', 1)
                        try:
                            man_id, manufacturer = _monitor_brand_lookup(manufacturer)
                        except TypeError:
                            man_id, manufacturer = None, manufacturer.lower().capitalize()
                    except Exception:
                        devid = pydevice.DeviceID.split('#')
                        serial = devid[2]
                        man_id = devid[1][:3]
                        model = devid[3]
                        del devid
                        try:
                            man_id, manufacturer = _monitor_brand_lookup(man_id)
                        except TypeError:
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

        # return info only which has correct data
        info = [i for i in info if isinstance(i, dict)]

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
        info = [i for i in get_display_info() if i['method'] == cls]
        if display is not None:
            info = filter_monitors(display=display, haystack=info)
        return info

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
        '''
        def callback(hmonitor, *_):
            monitors.append(HMONITOR(hmonitor))
            return True

        monitors = []
        if not windll.user32.EnumDisplayMonitors(None, None, cls._MONITORENUMPROC(callback), None):
            raise WinError('EnumDisplayMonitors failed')

        # user index keeps track of valid monitors
        user_index = 0
        # monitor index keeps track of valid and pseudo monitors
        monitor_index = 0
        display_devices = list(enum_display_devices())

        wmi = _wmi_init()
        try:
            laptop_displays = [
                i.InstanceName.replace('_0', '').split('\\')[2]
                for i in wmi.WmiMonitorBrightness()
            ]
        except Exception:
            laptop_displays = []

        for monitor in monitors:
            # Get physical monitor count
            count = DWORD()
            if not windll.dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR(monitor, byref(count)):
                raise WinError()
            if count.value > 0:
                # Get physical monitor handles
                physical_array = (cls._PHYSICAL_MONITOR * count.value)()
                if not windll.dxva2.GetPhysicalMonitorsFromHMONITOR(monitor, count.value, physical_array):
                    raise WinError()
                for item in physical_array:
                    # check that the monitor is not a pseudo monitor by
                    # checking it's StateFlags for the
                    # win32con DISPLAY_DEVICE_ATTACHED_TO_DESKTOP flag
                    if display_devices[monitor_index].StateFlags & win32con.DISPLAY_DEVICE_ATTACHED_TO_DESKTOP:
                        # check if monitor is actually a laptop display
                        if display_devices[monitor_index].DeviceID.split('#')[2] not in laptop_displays:
                            if user_index >= start:
                                yield item.handle
                            # increment user index as a valid monitor was found
                            user_index += 1
                    # increment monitor index
                    monitor_index += 1
                    windll.dxva2.DestroyPhysicalMonitor(item.handle)

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
        info = [i for i in get_display_info() if i['method'] == cls]
        if display is not None:
            info = filter_monitors(display=display, haystack=info)
        return info

    @classmethod
    def get_brightness(cls, display: Optional[int] = None, max_tries: int = 50) -> List[int]:
        '''
        Retrieve the brightness of all connected displays using the `ctypes.windll` API

        Args:
            display (int): The specific display you wish to query.
            max_tries (int): the maximum allowed number of attempts to
                read the VCP output from the monitor

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
                for attempt in range(max_tries):
                    if windll.dxva2.GetVCPFeatureAndVCPFeatureReply(handle, code, None, byref(cur_out), None):
                        current = cur_out.value
                        break
                    current = None
                    time.sleep(0.02 if attempt < 20 else 0.1)

            if current is not None:
                __cache__.store(f'vcp_brightness_{index}', current, expires=0.1)
                values.append(current)

            if display == index:
                # if we have just got the display we wanted then exit here
                # no point iterating through all the other ones
                break

        return values

    @classmethod
    def set_brightness(cls, value: int, display: Optional[int] = None, max_tries: int = 50):
        '''
        Sets the brightness for all connected displays using the `ctypes.windll` API

        Args:
            display (int): The specific display you wish to query.
            max_tries (int): the maximum allowed number of attempts to
                send the VCP input to the monitor

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
        value = DWORD(value)
        for index, monitor in enumerate(
            cls.iter_physical_monitors(start=display),
            start=display if display is not None else 0
        ):
            if display is None or display == index:
                handle = HANDLE(monitor)
                for attempt in range(max_tries):
                    if windll.dxva2.SetVCPFeature(handle, code, value):
                        break
                    time.sleep(0.02 if attempt < 20 else 0.1)


def list_monitors_info(method: Optional[str] = None, allow_duplicates: bool = False) -> List[dict]:
    '''
    Lists detailed information about all detected monitors

    Args:
        method (str): the method the monitor can be addressed by. See `screen_brightness_control.get_methods`
            for more info on available methods
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
    # no caching here because get_display_info caches its results
    info = get_display_info()

    all_methods = get_methods()

    if method is not None:
        method = method.lower()
        if method not in all_methods:
            raise ValueError(f'method must be one of: {list(all_methods)}')

    info_final = []
    serials = []
    # to make sure each display (with unique edid) is only reported once
    for i in info:
        if allow_duplicates or i['serial'] not in serials:
            if method is None or method == i['method'].__name__.lower():
                serials.append(i['serial'])
                info_final.append(i)

    return info_final
