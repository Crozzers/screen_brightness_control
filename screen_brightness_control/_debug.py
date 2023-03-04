'''
A small helper module to assist with debugging the screen_brightness_control library
'''
import logging
import platform
import traceback


def info() -> dict:
    '''
    Gather and return information that may (or may not) be useful for debugging
    issues with the library.

    All of the information returned by this function has, at some point, been
    requested and used as part of the debugging process of various
    [issues](https://github.com/Crozzers/screen_brightness_control/issues).
    '''
    import screen_brightness_control as sbc

    # configure logging
    logger = logging.getLogger(__name__).getChild('info')

    debug_info = {
        'version': sbc.__version__,
        'platform': platform.system(),
        'file': sbc.__file__
    }

    logger.debug('gathering list of all monitors')

    try:
        all_monitors = sbc.list_monitors_info(allow_duplicates=True, unsupported=True)
    except Exception:
        all_monitors = traceback.format_exc()
    finally:
        debug_info['all_monitors'] = [{'info': i} for i in all_monitors]

    logger.debug('filtering the list of monitors')

    try:
        if isinstance(all_monitors, list):
            all_monitors = [i for i in all_monitors if not i.get('unsupported')]
            monitor_info = sbc.filter_monitors(haystack=all_monitors)
        else:
            monitor_info = []
    except Exception:
        monitor_info = traceback.format_exc()
    finally:
        debug_info['filtered_monitors'] = monitor_info

    if not isinstance(all_monitors, str):  # if it is not a formatted traceback error msg
        for monitor_entry in debug_info['all_monitors']:
            monitor = monitor_entry['info']

            if not isinstance(monitor_info, str):  # if it is not a formatted traceback error msg
                if monitor in monitor_info:
                    monitor_entry['global_index'] = monitor_info.index(monitor)
                else:
                    monitor_entry['global_index'] = None

            logger.debug(f'get_brightness for monitor {monitor["method"].__name__}:{monitor["index"]}')

            try:
                brightness = monitor['method'].get_brightness(display=monitor['index'])
            except Exception:
                brightness = traceback.format_exc()
            finally:
                monitor_entry['get_brightness'] = brightness

            logger.debug(f'set_brightness for monitor {monitor["method"].__name__}:{monitor["index"]}')

            try:
                output = monitor['method'].set_brightness(
                    brightness[0] if isinstance(brightness, list) else 100,
                    display=monitor['index']
                )
            except Exception:
                output = traceback.format_exc()
            finally:
                monitor_entry['set_brightness'] = output

    debug_info['methods'] = []
    for name, method in sbc.get_methods().items():
        logger.debug(f'getting display info for method: {name}')
        current = {
            'name': name,
            'class': repr(method)
        }

        try:
            displays = method.get_display_info()
        except Exception:
            displays = traceback.format_exc()
        else:
            current['displays'] = []
            for d in displays:
                current_display = {}
                if not isinstance(all_monitors, str) and d in all_monitors:
                    current_display['index'] = all_monitors.index(d)
                if not isinstance(monitor_info, str) and d in monitor_info:
                    current_display['global_index'] = monitor_info.index(d)

                if not current_display:
                    current_display = d

                current['displays'].append(current_display)

        debug_info['methods'].append(current)

    if platform.system() == 'Windows':  # windows specific debug info
        logger.debug('windows specific debug info')
        debug_info['windows'] = {
            'wmi_monitor_id_output': sbc._OS_MODULE.wmi.WMI(namespace='wmi').WmiMonitorID()
        }
        try:
            enum_displays = [
                sbc._OS_MODULE.win32api.EnumDisplayDevices(
                    sbc._OS_MODULE.win32api.GetMonitorInfo(i[0])['Device'], 0, 1
                ).DeviceID for i in sbc._OS_MODULE.win32api.EnumDisplayMonitors()
            ]
        except Exception:
            enum_displays = traceback.format_exc()
        finally:
            debug_info['windows']['win32api_enum_display_device_ids'] = enum_displays

        try:
            physical_monitors = list(map(repr, sbc._OS_MODULE.VCP.iter_physical_monitors()))
        except Exception:
            physical_monitors = traceback.format_exc()
        finally:
            debug_info['windows']['physical_monitor_handles'] = physical_monitors

    return debug_info
