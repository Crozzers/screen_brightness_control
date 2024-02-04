import logging
import threading
import time
from ctypes import POINTER, WINFUNCTYPE, Structure, WinError, byref, windll
from ctypes.wintypes import (BOOL, BYTE, DWORD, HANDLE, HDC, HMONITOR, LPARAM,
                             RECT, WCHAR)
from typing import List, Optional

import pythoncom
import pywintypes
import win32api
import win32con
import wmi

from . import filter_monitors, get_methods
from .exceptions import EDIDParseError, NoValidDisplayError, format_exc
from .helpers import EDID, BrightnessMethod, __Cache, _monitor_brand_lookup
from .types import DisplayIdentifier, Generator, IntPercentage

__cache__ = __Cache()
_logger = logging.getLogger(__name__)


def _wmi_init():
    '''internal function to create and return a wmi instance'''
    # WMI calls don't work in new threads so we have to run this check
    if threading.current_thread() != threading.main_thread():
        pythoncom.CoInitialize()
    return wmi.WMI(namespace='wmi')


def enum_display_devices() -> Generator[win32api.PyDISPLAY_DEVICEType, None, None]:
    '''
    Yields all display devices connected to the computer
    '''
    for monitor_enum in win32api.EnumDisplayMonitors():
        pyhandle = monitor_enum[0]
        monitor_info = win32api.GetMonitorInfo(pyhandle)
        for adaptor_index in range(5):
            try:
                # EDD_GET_DEVICE_INTERFACE_NAME flag to populate DeviceID field
                device = win32api.EnumDisplayDevices(
                    monitor_info['Device'], adaptor_index, 1)
            except pywintypes.error:
                _logger.debug(
                    f'failed to get display device {monitor_info["Device"]} on adaptor index {adaptor_index}')
            else:
                yield device
                break


def get_display_info() -> List[dict]:
    '''
    Gets information about all connected displays using WMI and win32api

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
        except Exception as e:
            # don't do specific exception classes here because WMI does not play ball with it
            _logger.warning(
                f'get_display_info: failed to gather list of laptop displays - {format_exc(e)}')
            laptop_displays = []

        extras, desktop, laptop = [], 0, 0
        uid_keys = list(monitor_uids.keys())
        for monitor in wmi.WmiMonitorDescriptorMethods():
            model, serial, manufacturer, man_id, edid = None, None, None, None, None
            instance_name = monitor.InstanceName.replace(
                '_0', '', 1).split('\\')[2]
            try:
                pydevice = monitor_uids[instance_name]
            except KeyError:
                # if laptop display WAS connected but was later put to sleep (#33)
                if instance_name in laptop_displays:
                    laptop += 1
                else:
                    desktop += 1
                _logger.warning(
                    f'display {instance_name!r} is detected but not present in monitor_uids.'
                    ' Maybe it is asleep?'
                )
                continue

            # get the EDID
            try:
                edid = ''.join(
                    f'{char:02x}' for char in monitor.WmiGetMonitorRawEEdidV1Block(0)[0])
                # we do the EDID parsing ourselves because calling wmi.WmiMonitorID
                # takes too long
                parsed = EDID.parse(edid)
                man_id, manufacturer, model, name, serial = parsed
                if name is None:
                    raise EDIDParseError(
                        'parsed EDID returned invalid display name')
            except EDIDParseError as e:
                edid = None
                _logger.warning(
                    f'exception parsing edid str for {monitor.InstanceName} - {format_exc(e)}')
            except Exception as e:
                edid = None
                _logger.error(
                    f'failed to get EDID string for {monitor.InstanceName} - {format_exc(e)}')
            finally:
                if edid is None:
                    devid = pydevice.DeviceID.split('#')
                    serial = devid[2]
                    man_id = devid[1][:3]
                    model = devid[1][3:] or 'Generic Monitor'
                    del devid
                    if (brand := _monitor_brand_lookup(man_id)):
                        man_id, manufacturer = brand

            if (serial, model) != (None, None):
                data: dict = {
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

        info = uid_keys + extras
        if desktop:
            # now make sure desktop monitors have the correct index
            count = 0
            for item in info:
                if item['method'] == VCP:
                    item['index'] = count
                    count += 1

        # return info only which has correct data
        info = [i for i in info if isinstance(i, dict)]

        __cache__.store('windows_monitors_info_raw', info)

    return info


class WMI(BrightnessMethod):
    '''
    A collection of screen brightness related methods using the WMI API.
    This class primarily works with laptop displays.
    '''
    @classmethod
    def get_display_info(cls, display: Optional[DisplayIdentifier] = None) -> List[dict]:
        info = [i for i in get_display_info() if i['method'] == cls]
        if display is not None:
            info = filter_monitors(display=display, haystack=info)
        return info

    @classmethod
    def set_brightness(cls, value: IntPercentage, display: Optional[int] = None):
        brightness_method = _wmi_init().WmiMonitorBrightnessMethods()
        if display is not None:
            brightness_method = [brightness_method[display]]

        for method in brightness_method:
            method.WmiSetBrightness(value, 0)

    @classmethod
    def get_brightness(cls, display: Optional[int] = None) -> List[IntPercentage]:
        brightness_method = _wmi_init().WmiMonitorBrightness()
        if display is not None:
            brightness_method = [brightness_method[display]]

        values = [i.CurrentBrightness for i in brightness_method]
        return values


class VCP(BrightnessMethod):
    '''Collection of screen brightness related methods using the DDC/CI commands'''
    _MONITORENUMPROC = WINFUNCTYPE(BOOL, HMONITOR, HDC, POINTER(RECT), LPARAM)

    _logger = _logger.getChild('VCP')

    class _PHYSICAL_MONITOR(Structure):
        '''internal class, do not call'''
        _fields_ = [('handle', HANDLE),
                    ('description', WCHAR * 128)]

    @classmethod
    def iter_physical_monitors(cls, start: int = 0) -> Generator[HANDLE, None, None]:
        '''
        A generator to iterate through all physical monitors
        and then close them again afterwards, yielding their handles.
        It is not recommended to use this function unless you are familiar with `ctypes` and `windll`

        Args:
            start: skip the first X handles

        Raises:
            ctypes.WinError: upon failure to enumerate through the monitors
        '''
        def callback(hmonitor, *_):
            monitors.append(HMONITOR(hmonitor))
            return True

        monitors: List[HMONITOR] = []
        if not windll.user32.EnumDisplayMonitors(None, None, cls._MONITORENUMPROC(callback), None):
            cls._logger.error('EnumDisplayMonitors failed')
            raise WinError(None, 'EnumDisplayMonitors failed')

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
        except Exception as e:
            cls._logger.warning(
                f'failed to gather list of laptop displays - {format_exc(e)}')
            laptop_displays = []

        for monitor in monitors:
            # Get physical monitor count
            count = DWORD()
            if not windll.dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR(monitor, byref(count)):
                raise WinError(None, 'call to GetNumberOfPhysicalMonitorsFromHMONITOR returned invalid result')
            if count.value > 0:
                # Get physical monitor handles
                physical_array = (cls._PHYSICAL_MONITOR * count.value)()
                if not windll.dxva2.GetPhysicalMonitorsFromHMONITOR(monitor, count.value, physical_array):
                    raise WinError(None, 'call to GetPhysicalMonitorsFromHMONITOR returned invalid result')
                for item in physical_array:
                    # check that the monitor is not a pseudo monitor by
                    # checking its StateFlags for the
                    # win32con DISPLAY_DEVICE_ATTACHED_TO_DESKTOP flag
                    if display_devices[monitor_index].StateFlags & win32con.DISPLAY_DEVICE_ATTACHED_TO_DESKTOP:
                        # check if monitor is actually a laptop display
                        if display_devices[monitor_index].DeviceID.split('#')[2] not in laptop_displays:
                            if start is None or user_index >= start:
                                yield item.handle
                            # increment user index as a valid monitor was found
                            user_index += 1
                    # increment monitor index
                    monitor_index += 1
                    windll.dxva2.DestroyPhysicalMonitor(item.handle)

    @classmethod
    def get_display_info(cls, display: Optional[DisplayIdentifier] = None) -> List[dict]:
        info = [i for i in get_display_info() if i['method'] == cls]
        if display is not None:
            info = filter_monitors(display=display, haystack=info)
        return info

    @classmethod
    def get_brightness(cls, display: Optional[int] = None, max_tries: int = 50) -> List[IntPercentage]:
        '''
        Args:
            display: the index of the specific display to query.
                If unspecified, all detected displays are queried
            max_tries: the maximum allowed number of attempts to
                read the VCP output from the display

        Returns:
            See `BrightnessMethod.get_brightness`
        '''
        code = BYTE(0x10)
        values = []
        start = display if display is not None else 0
        for index, handle in enumerate(cls.iter_physical_monitors(start=start), start=start):
            current = __cache__.get(f'vcp_brightness_{index}')
            if current is None:
                cur_out = DWORD()
                attempt = 0  # avoid UnboundLocalError in else clause if max_tries is 0
                for attempt in range(max_tries):
                    if windll.dxva2.GetVCPFeatureAndVCPFeatureReply(handle, code, None, byref(cur_out), None):
                        current = cur_out.value
                        break
                    current = None
                    time.sleep(0.02 if attempt < 20 else 0.1)
                else:
                    cls._logger.error(
                        f'failed to get VCP feature reply for display:{index} after {attempt} tries')

            if current is not None:
                __cache__.store(
                    f'vcp_brightness_{index}', current, expires=0.1)
                values.append(current)

            if display == index:
                # if we've got the display we wanted then exit here, no point iterating through all the others.
                # Cleanup function usually called in iter_physical_monitors won't get called if we break, so call now
                windll.dxva2.DestroyPhysicalMonitor(handle)
                break

        return values

    @classmethod
    def set_brightness(cls, value: IntPercentage, display: Optional[int] = None, max_tries: int = 50):
        '''
        Args:
            value: percentage brightness to set the display to
            display: The specific display you wish to query.
            max_tries: the maximum allowed number of attempts to
                send the VCP input to the display
        '''
        __cache__.expire(startswith='vcp_brightness_')
        code = BYTE(0x10)
        value_dword = DWORD(value)
        start = display if display is not None else 0
        for index, handle in enumerate(cls.iter_physical_monitors(start=start), start=start):
            attempt = 0  # avoid UnboundLocalError in else clause if max_tries is 0
            for attempt in range(max_tries):
                if windll.dxva2.SetVCPFeature(handle, code, value_dword):
                    break
                time.sleep(0.02 if attempt < 20 else 0.1)
            else:
                cls._logger.error(
                    f'failed to set display:{index}->{value} after {attempt} tries')

            if display == index:
                # we have the display we wanted, exit and cleanup
                windll.dxva2.DestroyPhysicalMonitor(handle)
                break


def list_monitors_info(
    method: Optional[str] = None, allow_duplicates: bool = False, unsupported: bool = False
) -> List[dict]:
    '''
    Lists detailed information about all detected displays

    Args:
        method: the method the display can be addressed by. See `.get_methods`
            for more info on available methods
        allow_duplicates: whether to filter out duplicate displays (displays with the same EDID) or not
        unsupported: include detected displays that are invalid or unsupported.
            This argument does nothing on Windows
    '''
    # no caching here because get_display_info caches its results
    info = get_display_info()

    all_methods = get_methods(method).values()

    if method is not None:
        info = [i for i in info if i['method'] in all_methods]

    if allow_duplicates:
        return info

    try:
        # use filter_monitors to remove duplicates
        return filter_monitors(haystack=info)
    except NoValidDisplayError:
        return []


METHODS = (WMI, VCP)
