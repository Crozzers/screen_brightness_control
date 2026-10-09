from ctypes import CDLL
import ctypes
import logging
from typing import List, Optional

from . import filter_monitors, get_methods, config
from .exceptions import NoValidDisplayError, format_exc
from .helpers import BrightnessMethod, BrightnessMethodAdv, _monitor_brand_lookup
from .types import DisplayIdentifier, Generator, IntPercentage

from AppKit import NSScreen


_logger = logging.getLogger(__name__)


CoreGraphicsDLL = CDLL('/System/Library/Frameworks/CoreGraphics.framework/Versions/A/CoreGraphics')
CGDirectDisplayID = ctypes.c_uint32
CoreGraphicsDLL.CGDisplayIsBuiltin.argtypes = [CGDirectDisplayID]
CoreGraphicsDLL.CGDisplayIsBuiltin.restype = ctypes.c_bool


# DisplayServices DLL works on Apple Sillicon macs
DisplayServicesDLL = CDLL('/System/Library/PrivateFrameworks/DisplayServices.framework/Versions/A/DisplayServices')
DisplayServicesDLL.DisplayServicesGetBrightness.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_float)]
DisplayServicesDLL.DisplayServicesGetBrightness.restype = ctypes.c_int
DisplayServicesDLL.DisplayServicesSetBrightness.argtypes = [ctypes.c_int, ctypes.c_float]
DisplayServicesDLL.DisplayServicesSetBrightness.restype = ctypes.c_int


class DisplayServices(BrightnessMethod):
    '''
    Brightness methods that use the private `DisplayServices` API.

    Requires `USE_PRIVATE_FRAMEWORKS` to be enabled.
    ```python
    import screen_brightness_control as sbc
    sbc.config.USE_PRIVATE_FRAMEWORKS = True
    ```
    '''
    _logger = _logger.getChild('DisplayServices')

    @classmethod
    def _gdi(cls) -> Generator[dict]:
        for index, display in enumerate(NSScreen.screens()):
            display_id = display.CGDirectDisplayID()
            name = display.localizedName()

            if name.lower().startswith('built-in'):
                mfg_lookup = _monitor_brand_lookup('APP')
            else:
                mfg_lookup = _monitor_brand_lookup(name.split(' ')[0])

            if mfg_lookup:
                manufacturer_id, manufacturer = mfg_lookup
            else:
                manufacturer_id, manufacturer = None, None

            yield {
                'index': index,
                'name': name,
                'manufacturer': manufacturer,
                'manufacturer_id': manufacturer_id,
                'model': name.split(' ', 1)[1],
                'method': cls,
                'edid': None,
                'serial': None,
                'uid': display_id,
                'unsupported': not CoreGraphicsDLL.CGDisplayIsBuiltin(display_id)
            }

    @classmethod
    def get_display_info(cls, display: Optional[DisplayIdentifier] = None) -> List[dict]:
        displays = []
        for item in cls._gdi():
            if item['unsupported']:
                continue
            del item['unsupported']
            displays.append(item)

        if display is not None:
            return filter_monitors(display=display, haystack=displays)
        return displays

    @classmethod
    def get_brightness(cls, display: Optional[int] = None) -> List[int]:
        if not config.USE_PRIVATE_FRAMEWORKS:
            cls._logger.warning('USE_PRIVATE_FRAMEWORKS is disabled')
            return []

        displays = cls.get_display_info()
        if display is not None:
            displays = [displays[display]]

        result = []
        for screen in displays:
            brightness = ctypes.c_float()
            ret = DisplayServicesDLL.DisplayServicesGetBrightness(
                ctypes.c_int(screen['uid']),
                ctypes.byref(brightness)
            )
            if ret:
                cls._logger.warning(f'DisplayServicesGetBrightness returned code {ret} for display {screen["uid"]}')
            result.append(brightness.value)

        return result


    @classmethod
    def set_brightness(cls, value: IntPercentage, display: Optional[int] = None):
        if not config.USE_PRIVATE_FRAMEWORKS:
            cls._logger.warning('USE_PRIVATE_FRAMEWORKS is disabled')
            return []

        displays = cls.get_display_info()
        if display is not None:
            displays = [displays[display]]

        for screen in displays:
            ret = DisplayServicesDLL.DisplayServicesSetBrightness(
                ctypes.c_int(screen['uid']),
                ctypes.c_float(value)
            )
            if ret:
                cls._logger.warning(f'DisplayServicesSetBrightness returned code {ret} for display {screen["uid"]}')


def list_monitors_info(
    method: Optional[str] = None, allow_duplicates: bool = False, unsupported: bool = False
) -> List[dict]:
    '''
    Lists detailed information about all detected displays

    Args:
        method: the method the display can be addressed by. See `.get_methods`
            for more info on available methods
        allow_duplicates: whether to filter out duplicate displays (displays with the same EDID) or not
        unsupported: include detected displays that are invalid or unsupported
    '''
    all_methods = get_methods(method).values()
    haystack = []
    for method_class in all_methods:
        try:
            if unsupported and issubclass(method_class, BrightnessMethodAdv):
                haystack += method_class._gdi()
            else:
                haystack += method_class.get_display_info()
        except Exception as e:
            _logger.warning(f'error grabbing display info from {method_class} - {format_exc(e)}')
            pass

    if allow_duplicates:
        return haystack

    try:
        # use filter_monitors to remove duplicates
        return filter_monitors(haystack=haystack)
    except NoValidDisplayError:
        return []


METHODS = (DisplayServices,)