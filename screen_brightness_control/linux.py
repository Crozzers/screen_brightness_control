import subprocess
import os
from . import flatten_list, _monitor_brand_lookup, filter_monitors, __cache__, EDID
from typing import List, Union, Optional
import warnings

# edid class used to be defined here as _EDID
_EDID = EDID


def warn_deprecated(name, alternative=None):
    '''Temporary function to warn you that things have been deprecated
    and will be removed in the next update.'''
    if alternative is None:
        alternative = name

    msg = f'screen_brightness_control.linux.{name} is deprecated.'
    if alternative:
        msg += f' Use screen_brightness_control.{alternative} instead'
    warnings.warn(msg, DeprecationWarning)


class Light:
    '''collection of screen brightness related methods using the light executable'''

    executable: str = 'light'
    '''the light executable to be called'''

    @classmethod
    def get_display_info(cls, display: Optional[Union[int, str]] = None) -> List[dict]:
        '''
        Returns information about detected displays as reported by Light

        Args:
            display (str or int): [*Optional*] The monitor to return info about.
                Pass in the serial number, name, model, interface, edid or index.
                This is passed to `filter_monitors`

        Returns:
            list: list of dicts

        Example:
            ```python
            import screen_brightness_control as sbc

            # get info about all monitors
            info = sbc.linux.Light.get_display_info()
            # EG output: [{'name': 'edp-backlight', 'path': '/sys/class/backlight/edp-backlight', edid': '00ffff...'}]

            # get info about the primary monitor
            primary_info = sbc.linux.Light.get_display_info(0)[0]

            # get info about a monitor called 'edp-backlight'
            edp_info = sbc.linux.Light.get_display_info('edp-backlight')[0]
            ```
        '''
        res = subprocess.run([cls.executable, '-L'], stdout=subprocess.PIPE).stdout.decode().split('\n')
        displays = []
        count = 0
        for r in res:
            if 'backlight' in r and 'sysfs/backlight/auto' not in r:
                r = r[r.index('backlight/') + 10:]
                if os.path.isfile(f'/sys/class/backlight/{r}/device/edid'):
                    tmp = {
                        'name': r,
                        'path': f'/sys/class/backlight/{r}',
                        'light_path': f'sysfs/backlight/{r}',
                        'method': cls,
                        'index': count,
                        'model': None,
                        'serial': None,
                        'manufacturer': None,
                        'manufacturer_id': None,
                        'edid': None
                    }
                    count += 1
                    try:
                        out = subprocess.check_output(
                            ['hexdump', tmp['path'] + '/device/edid'],
                            stderr=subprocess.DEVNULL
                        ).decode().split('\n')
                        # either the hexdump reports each hex char backwards (ff00 instead of 00ff)
                        # or both xrandr and ddcutil do. So I swap these bits around
                        edid = ''
                        for line in out:
                            for i in line.split(' '):
                                if len(i) == 4:
                                    edid += i[2:] + i[:2]
                        tmp['edid'] = edid
                        name, serial = EDID.parse_edid(edid)
                        if name is not None:
                            tmp['serial'] = serial
                            tmp['name'] = name
                        try:
                            tmp['manufacturer_id'], tmp['manufacturer'] = _monitor_brand_lookup(name.split(' ')[0])
                        except Exception:
                            tmp['manufacturer'] = name.split(' ')[0]
                            tmp['manufacturer_id'] = None
                        tmp['model'] = name.split(' ')[1]
                    except Exception:
                        pass
                    displays.append(tmp)

        if display is not None:
            displays = filter_monitors(display=display, haystack=displays, include=['path', 'light_path'])
        return displays

    @classmethod
    def get_display_names(cls) -> List[str]:
        '''
        **DEPRECATED**.
        Returns the names of each display, as reported by light

        Returns:
            list: list of strings

        Example:
            ```python
            import screen_brightness_control as sbc

            names = sbc.linux.Light.get_display_names()
            # EG output: ['edp-backlight']
            ```
        '''
        warn_deprecated('Light.get_display_names', 'list_monitors(method="light")')
        return [i['name'] for i in cls.get_display_info()]

    @classmethod
    def set_brightness(cls, value: int, display: Optional[int] = None):
        '''
        Sets the brightness for a display using the light executable

        Args:
            value (int): Sets the brightness to this value
            display (int): The specific display you wish to query.

        Example:
            ```python
            import screen_brightness_control as sbc

            # set the brightness to 50%
            sbc.linux.Light.set_brightness(50)

            # set the primary display brightness to 75%
            sbc.linux.Light.set_brightness(75, display = 0)

            # set the secondary display brightness to 25%
            sbc.linux.Light.set_brightness(75, display = 1)
            ```
        '''
        info = cls.get_display_info()
        if display is not None:
            info = [info[display]]

        for i in info:
            subprocess.call(f'{cls.executable} -S {value} -s {i["light_path"]}'.split(" "))

    @classmethod
    def get_brightness(cls, display: Optional[int] = None) -> List[int]:
        '''
        Sets the brightness for a display using the light executable

        Args:
            display (int): The specific display you wish to query.

        Returns:
            list: list of ints (0 to 100)

        Example:
            ```python
            import screen_brightness_control as sbc

            # get the current display brightness
            current_brightness = sbc.linux.Light.get_brightness()

            # get the brightness of the primary display
            primary_brightness = sbc.linux.Light.get_brightness(display = 0)[0]

            # get the brightness of the secondary display
            edp_brightness = sbc.linux.Light.get_brightness(display = 1)[0]
            ```
        '''
        info = cls.get_display_info()
        if display is not None:
            info = [info[display]]

        results = []
        for i in info:
            results.append(
                subprocess.check_output(
                    [
                        cls.executable, '-G', '-s', i['light_path']
                    ]
                )
            )
        results = [int(round(float(i.decode()), 0)) for i in results]
        return results


class XBacklight:
    '''collection of screen brightness related methods using the xbacklight executable'''

    executable: str = 'xbacklight'
    '''the xbacklight executable to be called'''

    @classmethod
    def set_brightness(cls, value: int, **kwargs):
        '''
        Sets the screen brightness to a supplied value

        Args:
            value (int): the value to set the brightnes to
            **kwargs: arbitrary keyword arguments. Ignored

        Example:
            ```python
            import screen_brightness_control as sbc

            # set the brightness to 100%
            sbc.linux.XBacklight.set_brightness(100)
            ```
        '''
        subprocess.call([cls.executable, '-set', str(value)])

    @classmethod
    def get_brightness(cls, **kwargs) -> int:
        '''
        Returns the screen brightness as reported by xbacklight

        Returns:
            int: from 0 to 100
            **kwargs: arbitrary keyword arguments. Ignored

        Example:
            ```python
            import screen_brightness_control as sbc

            current_brightness = sbc.linux.XBacklight.get_brightness()
            ```
        '''
        res = subprocess.run(
            [cls.executable, '-get'],
            stdout=subprocess.PIPE
        ).stdout.decode()
        return int(round(float(str(res)), 0))


class XRandr:
    '''collection of screen brightness related methods using the xrandr executable'''

    executable: str = 'xrandr'
    '''the xrandr executable to be called'''

    @classmethod
    def get_display_info(cls, display: Optional[Union[int, str]] = None, brightness: bool = False) -> List[dict]:
        '''
        Returns info about all detected monitors as reported by xrandr

        Args:
            display (str or int): [*Optional*] The monitor to return info about.
                Pass in the serial number, name, model, interface, edid or index.
                This is passed to `filter_monitors`
            brightness (bool): whether to include the current brightness
                in the returned info

        Returns:
            list: list of dicts

        Example:
            ```python
            import screen_brightness_control as sbc

            info = sbc.linux.XRandr.get_display_info()
            for i in info:
                print('================')
                for key, value in i.items():
                    print(key, ':', value)

            # get information about the first XRandr addressable monitor
            primary_info = sbc.linux.XRandr.get_display_info(0)[0]

            # get information about a monitor with a specific name
            benq_info = sbc.linux.XRandr.get_display_info('BenQ GL2450HM')[0]
            ```
        '''
        def check_tmp(tmp):
            if tmp != {}:
                if tmp['serial'] is None or '\\x' not in tmp['serial']:
                    if 'line' in tmp:
                        del(tmp['line'])
                    return True
            return False

        out = subprocess.check_output([cls.executable, '--verbose']).decode().split('\n')
        names = cls.get_display_interfaces()
        data = []
        tmp = {}
        count = 0
        for i in out:
            if i != '':
                if i.startswith(tuple(names)):
                    if check_tmp(tmp):
                        data.append(tmp)
                    tmp = {
                        'interface': i.split(' ')[0],
                        'name': i.split(' ')[0],
                        'line': i,
                        'method': cls,
                        'index': count,
                        'model': None,
                        'serial': None,
                        'manufacturer': None,
                        'manufacturer_id': None,
                        'edid': None
                    }
                    count += 1
                elif 'EDID:' in i:
                    st = out[out.index(tmp['line']):]
                    edid = []
                    for j in range(st.index(i) + 1, st.index(i) + 9):
                        edid.append(st[j].replace('\t', '').replace(' ', ''))
                    edid = ''.join(edid)
                    tmp['edid'] = edid
                    name, serial = EDID.parse_edid(edid)
                    tmp['name'] = name if name is not None else tmp['interface']
                    if name is not None:
                        tmp['manufacturer'] = name.split(' ')[0]
                        try:
                            tmp['manufacturer_id'], tmp['manufacturer'] = _monitor_brand_lookup(
                                tmp['manufacturer']
                            )
                        except Exception:
                            tmp['manufacturer_id'] = None
                        tmp['model'] = name.split(' ')[1]
                        tmp['serial'] = serial
                elif 'Brightness:' in i and brightness:
                    tmp['brightness'] = int(
                        float(i.replace('Brightness:', '').replace(' ', '').replace('\t', '')) * 100
                    )
        if check_tmp(tmp):
            data.append(tmp)

        if display is not None:
            data = filter_monitors(display=display, haystack=data, include=['interface'])
        return data

    @classmethod
    def get_display_interfaces(cls) -> List[str]:
        '''
        Returns the interfaces of each display, as reported by xrandr

        Returns:
            list: list of strings

        Example:
            ```python
            import screen_brightness_control as sbc

            names = sbc.linux.XRandr.get_display_interfaces()
            # EG output: ['eDP-1', 'HDMI1', 'HDMI2']
            ```
        '''
        out = subprocess.check_output([cls.executable, '-q']).decode().split('\n')
        return [i.split(' ')[0] for i in out if 'connected' in i and 'disconnected' not in i]

    @classmethod
    def get_display_names(cls) -> List[str]:
        '''
        **DEPRECATED**.
        Returns the names of each display, as reported by xrandr

        Returns:
            list: list of strings

        Example:
            ```python
            import screen_brightness_control as sbc

            names = sbc.linux.XRandr.get_display_names()
            # EG output: ['BenQ GL2450HM', 'Dell U2211H']
            ```
        '''
        warn_deprecated('XRandr.get_display_names', 'list_monitors(method="xrandr")')
        return [i['name'] for i in cls.get_display_info()]

    @classmethod
    def get_brightness(cls, display: Optional[int] = None) -> List[int]:
        '''
        Returns the brightness for a display using the xrandr executable

        Args:
            display (int): The specific display you wish to query.

        Returns:
            list: list of integers (from 0 to 100)

        Example:
            ```python
            import screen_brightness_control as sbc

            # get the current brightness
            current_brightness = sbc.linux.XRandr.get_brightness()

            # get the current brightness for the primary display
            primary_brightness = sbc.linux.XRandr.get_brightness(display=0)[0]
            ```
        '''
        monitors = cls.get_display_info(brightness=True)
        if display is not None:
            monitors = [monitors[display]]
        brightness = [i['brightness'] for i in monitors]

        return brightness

    @classmethod
    def set_brightness(cls, value: int, display: Optional[int] = None):
        '''
        Sets the brightness for a display using the xrandr executable

        Args:
            value (int): Sets the brightness to this value
            display (int): The specific display you wish to query.

        Example:
            ```python
            import screen_brightness_control as sbc

            # set the brightness to 50
            sbc.linux.XRandr.set_brightness(50)

            # set the brightness of the primary display to 75
            sbc.linux.XRandr.set_brightness(75, display=0)
            ```
        '''
        value = str(float(value) / 100)
        info = cls.get_display_info()
        if display is not None:
            info = [info[display]]

        for i in info:
            subprocess.run([cls.executable, '--output', i['interface'], '--brightness', value])

        # The get_brightness method takes the brightness value from get_display_info
        # The problem is that that display info is cached, meaning that the brightness
        # value is also cached. We must expire it here.


class DDCUtil:
    '''collection of screen brightness related methods using the ddcutil executable'''

    executable: str = 'ddcutil'
    '''the ddcutil executable to be called'''
    sleep_multiplier: float = 0.5
    '''how long ddcutil should sleep between each DDC request (lower is shorter).
    See [the ddcutil docs](https://www.ddcutil.com/performance_options/) for more info.'''

    @classmethod
    def get_display_info(cls, display: Optional[Union[int, str]] = None) -> List[dict]:
        '''
        Returns information about all DDC compatible monitors shown by DDCUtil
        Works by calling the command 'ddcutil detect' and parsing the output.

        Args:
            display (int or str): [*Optional*] The monitor to return info about.
                Pass in the serial number, name, model, i2c bus, edid or index.
                This is passed to `filter_monitors`

        Returns:
            list: list of dicts

        Example:
            ```python
            import screen_brightness_control as sbc

            info = sbc.linux.DDCUtil.get_display_info()
            for i in info:
                print('================')
                for key, value in i.items():
                    print(key, ':', value)

            # get information about the first DDCUtil addressable monitor
            primary_info = sbc.linux.DDCUtil.get_display_info(0)[0]

            # get information about a monitor with a specific name
            benq_info = sbc.linux.DDCUtil.get_display_info('BenQ GL2450HM')[0]
            ```
        '''
        def check_tmp(tmp):
            if tmp != {} and 'Invalid display' not in tmp['tmp']:
                if 'tmp' in tmp:
                    del(tmp['tmp'])
                return True
            return False

        data = __cache__.get('ddcutil_monitors_info')
        if data is None:
            out = []
            # Use -v to get EDID string but this means output cannot be decoded.
            # Or maybe it can. I don't know the encoding though, so let's assume it cannot be decoded.
            # Use str()[2:-1] workaround
            cmd_out = str(
                subprocess.check_output(
                    [
                        cls.executable,
                        'detect', '-v',
                        f'--sleep-multiplier={cls.sleep_multiplier}'
                    ], stderr=subprocess.DEVNULL
                )
            )[2:-1].split('\\n')

            for line in cmd_out:
                if line != '' and line.startswith(('Invalid display', 'Display', '\t', ' ')):
                    out.append(line)
            data = []
            tmp = {}
            count = 0
            for i in range(len(out)):
                line = out[i]
                if not line.startswith(('\t', ' ')):
                    if check_tmp(tmp):
                        data.append(tmp)
                    tmp = {
                        'tmp': line,
                        'method': cls,
                        'index': count,
                        'model': None,
                        'serial': None,
                        'manufacturer': None,
                        'manufacturer_id': None,
                        'edid': None
                    }
                    count += 1
                else:
                    if 'I2C bus' in line:
                        tmp['i2c_bus'] = line[line.index('/'):]
                        tmp['bus_number'] = int(tmp['i2c_bus'].replace('/dev/i2c-', ''))
                    elif 'Mfg id' in line:
                        tmp['manufacturer_id'] = line.replace('Mfg id:', '').replace('\t', '').replace(' ', '')
                        try:
                            tmp['manufacturer_id'], tmp['manufacturer'] = _monitor_brand_lookup(tmp['manufacturer_id'])
                        except Exception:
                            pass
                    elif 'Model' in line:
                        name = [i for i in line.replace('Model:', '').replace('\t', '').split(' ') if i != '']
                        try:
                            name[0] = name[0].lower().capitalize()
                        except IndexError:
                            pass
                        tmp['name'] = ' '.join(name)
                        try:
                            tmp['model'] = name[1]
                        except IndexError:
                            pass
                    elif 'Serial number' in line:
                        tmp['serial'] = line.replace('Serial number:', '').replace('\t', '').replace(' ', '')
                    elif 'EDID hex dump:' in line:
                        try:
                            tmp['edid'] = ''.join(
                                j[j.index('+0') + 8: j.index('+0') + 55].replace(' ', '') for j in out[i + 2: i + 10]
                            )
                        except Exception:
                            pass
            if check_tmp(tmp):
                data.append(tmp)
            __cache__.store('ddcutil_monitors_info', data)

        if display is not None:
            data = filter_monitors(display=display, haystack=data, include=['i2c_bus'])
        return data

    @classmethod
    def get_display_names(cls) -> List[str]:
        '''
        **DEPRECATED**.
        Returns the names of each display, as reported by ddcutil

        Returns:
            list: list of strings

        Example:
            ```python
            import screen_brightness_control as sbc

            names = sbc.linux.DDCUtil.get_display_names()
            # EG output: ['Dell U2211H', 'BenQ GL2450H']
            ```
        '''
        warn_deprecated('DDCUtil.get_display_names', 'list_monitors(method="ddcutil")')
        return [i['name'] for i in cls.get_display_info()]

    @classmethod
    def get_brightness(cls, display: Optional[int] = None) -> List[int]:
        '''
        Returns the brightness for a display using the ddcutil executable

        Args:
            display (int): The specific display you wish to query.

        Returns:
            list: list of ints (0 to 100)

        Example:
            ```python
            import screen_brightness_control as sbc

            # get the current brightness
            current_brightness = sbc.linux.DDCUtil.get_brightness()

            # get the current brightness for the primary display
            primary_brightness = sbc.linux.DDCUtil.get_brightness(display=0)[0]
            ```
        '''
        monitors = cls.get_display_info()
        if display is not None:
            monitors = [monitors[display]]

        res = []
        for m in monitors:
            out = __cache__.get('ddcutil_' + m['edid'] + '_brightness')
            if out is None:
                out = subprocess.check_output(
                    [
                        cls.executable,
                        'getvcp', '10', '-t',
                        '-b', str(m['bus_number']),
                        f'--sleep-multiplier={cls.sleep_multiplier}'
                    ]
                ).decode().split(' ')[-2]
                __cache__.store('ddcutil_' + m['edid'] + '_brightness', out, expires=0.5)
            try:
                res.append(int(out))
            except Exception:
                pass
        return res

    @classmethod
    def set_brightness(cls, value: int, display: Optional[int] = None):
        '''
        Sets the brightness for a display using the ddcutil executable

        Args:
            value (int): Sets the brightness to this value
            display (int): The specific display you wish to query.

        Example:
            ```python
            import screen_brightness_control as sbc

            # set the brightness to 50
            sbc.linux.DDCUtil.set_brightness(50)

            # set the brightness of the primary display to 75
            sbc.linux.DDCUtil.set_brightness(75, display=0)
            ```
        '''
        monitors = cls.get_display_info()
        if display is not None:
            monitors = [monitors[display]]

        __cache__.expire(startswith='ddcutil_', endswith='_brightness')
        for m in monitors:
            subprocess.run(
                [
                    cls.executable, 'setvcp', '10', str(value),
                    '-b', str(m['bus_number']),
                    f'--sleep-multiplier={cls.sleep_multiplier}'
                ]
            )


def list_monitors_info(method: Optional[str] = None, allow_duplicates: bool = False) -> List[dict]:
    '''
    Lists detailed information about all detected monitors

    Args:
        method (str): the method the monitor can be addressed by. Can be 'xrandr' or 'ddcutil' or 'light'
        allow_duplicates (bool): whether to filter out duplicate displays (displays with the same EDID) or not

    Returns:
        list: list of dicts

    Raises:
        ValueError: if the method kwarg is invalid

    Example:
        ```python
        import screen_brightness_control as sbc

        monitors = sbc.linux.list_monitors_info()
        for monitor in monitors:
            print('=======================')
            # the manufacturer name plus the model OR a generic name for the monitor, depending on the method
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
        ```
    '''
    info = __cache__.get('linux_monitors_info', method=method, allow_duplicates=allow_duplicates)
    if info is None:
        methods = [XRandr, DDCUtil, Light]
        if method is not None:
            method = method.lower()
            if method not in ('xrandr', 'ddcutil', 'light'):
                raise ValueError('method must be \'xrandr\' or \'ddcutil\' or \'light\' to get monitor information')

        info = []
        edids = []
        for m in methods:
            if method is None or method == m.__name__.lower():
                # to make sure each display (with unique edid) is only reported once
                try:
                    tmp = m.get_display_info()
                except Exception:
                    pass
                else:
                    for i in tmp:
                        if allow_duplicates or i['edid'] not in edids:
                            edids.append(i['edid'])
                            info.append(i)
        __cache__.store('linux_monitors_info', info, method=method, allow_duplicates=allow_duplicates)
    return info


def list_monitors(method: Optional[str] = None) -> List[str]:
    '''
    **DEPRECATED**.
    Returns the names of all detected monitors

    Args:
        method (str): the method the monitor can be addressed by. Can be 'xrandr' or 'ddcutil' or 'light'

    Returns:
        list: list of strings

    Example:
        ```python
        import screen_brightness_control as sbc

        monitors = sbc.linux.list_monitors()
        # EG output: ['BenQ GL2450HM', 'Dell U2211H', 'edp-backlight']
        ```
    '''
    warn_deprecated('list_monitors')
    displays = [i['name'] for i in list_monitors_info(method=method)]
    return flatten_list(displays)


def get_brightness_from_sysfiles(display: int = None) -> int:
    '''
    **DEPRECATED**.
    Returns the current display brightness by reading files from `/sys/class/backlight`

    Args:
        display (int): The index of the display you wish to query

    Returns:
        int: from 0 to 100

    Raises:
        Exception: if no values could be obtained from reading `/sys/class/backlight`
        FileNotFoundError: if the `/sys/class/backlight` directory doesn't exist or it is empty

    Example:
        ```python
        import screen_brightness_control as sbc

        brightness = sbc.linux.get_brightness_from_sysfiles()
        # Eg Output: 100
        ```
    '''
    warn_deprecated('get_brightness_from_sysfiles', False)
    backlight_dir = '/sys/class/backlight/'
    error = []
    # if function has not returned yet try reading the brightness file
    if os.path.isdir(backlight_dir) and os.listdir(backlight_dir) != []:
        # if the backlight dir exists and is not empty
        folders = [dir for dir in os.listdir(backlight_dir) if os.path.isdir(os.path.join(backlight_dir, dir))]
        if display is not None:
            folders = [folders[display]]
        for folder in folders:
            try:
                # try to read the brightness value in the file
                with open(os.path.join(backlight_dir, folder, 'brightness'), 'r') as f:
                    brightness_value = int(float(str(f.read().rstrip('\n'))))

                try:
                    # try open the max_brightness file to calculate the value to set the brightness file to
                    with open(os.path.join(backlight_dir, folder, 'max_brightness'), 'r') as f:
                        max_brightness = int(float(str(f.read().rstrip('\n'))))
                except Exception:
                    # if the file does not exist we cannot calculate the brightness
                    return False
                brightness_value = int(round((brightness_value / max_brightness) * 100, 0))
                return brightness_value
            except Exception as e:
                error.append([type(Exception).__name__, e])
        # if function hasn't returned, it failed
        exc = f'Failed to get brightness from {backlight_dir}:'
        for e in error:
            exc += f'\n    {e[0]}: {e[1]}'
        raise Exception(exc)
    raise FileNotFoundError(f'Backlight directory {backlight_dir} not found')


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
                errors.append([f"{m['name']}", type(e).__name__, e])

        # use `'no_return' not in kwargs` because dict membership only checks the keys
        if output and not (all(i is None for i in output) and ('no_return' not in kwargs or not kwargs['no_return'])):
            # flatten and return any valid output (taking into account the no_return parameter)
            if 'no_return' in kwargs and kwargs['no_return']:
                return None
            output = flatten_list(output)
            return output
        else:
            try:
                return getattr(XBacklight, meta_method + '_brightness')(*args, **kwargs)
            except Exception as e:
                errors.append(['XBacklight', type(e).__name__, e])

    # if function hasn't already returned it has failed
    if (method, display) == (None, None) and meta_method == 'get':
        try:
            return get_brightness_from_sysfiles(**kwargs)
        except Exception as e:
            errors.append(['/sys/class/backlight/*', type(e).__name__, e])

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
) -> Union[List[int], int, None]:
    '''
    **DEPRECATED**.
    Sets the brightness for a display, cycles through Light, XRandr, DDCUtil and XBacklight methods until one works

    Args:
        value (int): Sets the brightness to this value
        display (int or str): The specific display you wish to adjust.
            Can be index, model, name or serial of the display.
            Can also be i2c bus (ddcutil), interface (xrandr) or path (light)
        method (str): the method to use ('light', 'xrandr', 'ddcutil' or 'xbacklight')
        kwargs (dict): passed directly to the chosen brightness method

    Returns:
        list: list of ints (0 to 100)
        int: int (0 to 100) if the method is 'XBacklight'
        None: if `no_return` is True

    Raises:
        ValueError: if you pass in an invalid value for `method`
        LookupError: if the chosen display or method is not found
        TypeError: if the value given for `display` is not int or str
        Exception: if the brightness could not be obtained by any method

    Example:
        ```python
        import screen_brightness_control as sbc

        # set brightness to 50%
        sbc.linux.set_brightness(50)

        # set brightness of the primary display to 75%
        sbc.linux.set_brightness(75, display=0)

        # set the brightness to 25% via the XRandr method
        sbc.linux.set_brightness(25, method='xrandr')
        ```
    '''
    warn_deprecated('set_brightness')
    if method is not None and method.lower() == 'xbacklight':
        return XBacklight.set_brightness(value, **kwargs)
    else:
        return __set_and_get_brightness(value, display=display, method=method, meta_method='set', **kwargs)


def get_brightness(
    display: Optional[Union[int, str]] = None,
    method: Optional[str] = None,
    **kwargs
) -> Union[List[int], int]:
    '''
    **DEPRECATED**.
    Returns the brightness for a display, cycles through Light, XRandr, DDCUtil and XBacklight methods until one works

    Args:
        display (int or str): The specific display you wish to adjust.
            Can be index, model, name or serial of the display.
            Can also be i2c bus (ddcutil), interface (xrandr) or path (light)
        method (str): the method to use ('light', 'xrandr', 'ddcutil' or 'xbacklight')
        kwargs (dict): passed directly to chosen brightness method

    Returns:
        list: list of ints (0 to 100)
        int: int (0 to 100) if the method is 'XBacklight'

    Raises:
        ValueError: if you pass in an invalid value for `method`
        LookupError: if the chosen display or method is not found
        TypeError: if the value given for `display` is not int or str
        Exception: if the brightness could not be obtained by any method

    Example:
        ```python
        import screen_brightness_control as sbc

        # get the current screen brightness
        current_brightness = sbc.linux.get_brightness()

        # get the brightness of the primary display
        primary_brightness = sbc.linux.get_brightness(display=0)[0]

        # get the brightness via the XRandr method
        xrandr_brightness = sbc.linux.get_brightness(method='xrandr')

        # get the brightness of the secondary display using Light
        light_brightness = sbc.get_brightness(display=1, method='light')[0]
        ```
    '''
    warn_deprecated('get_brightness')
    if method is not None and method.lower() == 'xbacklight':
        return XBacklight.get_brightness(**kwargs)
    else:
        return __set_and_get_brightness(display=display, method=method, meta_method='get', **kwargs)
