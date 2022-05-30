import functools
import glob
import operator
import os
import platform
import subprocess
import time
import warnings
from typing import List, Optional, Tuple, Union

if platform.system() == 'Linux':
    import fcntl

from . import filter_monitors, get_methods
from .helpers import EDID, __cache__, _monitor_brand_lookup, check_output


class SysFiles:
    '''
    A way of getting display information and adjusting the brightness
    that does not rely on any 3rd party software.

    This class works with displays that show up in the `/sys/class/backlight`
    directory (so usually laptop displays).

    To set the brightness, your user will need write permissions for
    `/sys/class/backlight/*/brightness` or you will need to run the program
    as root.
    '''
    @classmethod
    def get_display_info(cls, display: Optional[Union[int, str]] = None) -> List[dict]:
        '''
        Returns information about detected displays by reading files from the
        `/sys/class/backlight` directory

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
            info = sbc.linux.SysFiles.get_display_info()
            # EG output: [{'name': 'edp-backlight', 'path': '/sys/class/backlight/edp-backlight', edid': '00ffff...'}]

            # get info about the primary monitor
            primary_info = sbc.linux.SysFiles.get_display_info(0)[0]

            # get info about a monitor called 'edp-backlight'
            edp_info = sbc.linux.SysFiles.get_display_info('edp-backlight')[0]
            ```
        '''
        subsystems = set()
        for folder in os.listdir('/sys/class/backlight'):
            if os.path.isdir(f'/sys/class/backlight/{folder}/subsystem'):
                subsystems.add(tuple(os.listdir(f'/sys/class/backlight/{folder}/subsystem')))

        all_displays = {}
        index = 0

        for subsystem in subsystems:

            device = {
                'name': subsystem[0],
                'path': f'/sys/class/backlight/{subsystem[0]}',
                'method': cls,
                'index': index,
                'model': None,
                'serial': None,
                'manufacturer': None,
                'manufacturer_id': None,
                'edid': None,
                'scale': None
            }

            for folder in subsystem:
                # subsystems like intel_backlight usually have an acpi_video0
                # counterpart, which we don't want so lets find the 'best' candidate
                try:
                    with open(os.path.join(f'/sys/class/backlight/{folder}/max_brightness')) as f:
                        scale = int(f.read().rstrip(' \n')) / 100

                    # use the display with the highest resolution scale
                    if device['scale'] is None or scale > device['scale']:
                        device['name'] = folder
                        device['path'] = f'/sys/class/backlight/{folder}'
                        device['scale'] = scale
                except (FileNotFoundError, TypeError):
                    continue

            if os.path.isfile('%s/device/edid' % device['path']):
                device['edid'] = EDID.hexdump('%s/device/edid' % device['path'])

                for key, value in zip(
                    ('manufacturer_id', 'manufacturer', 'model', 'name', 'serial'),
                    EDID.parse(device['edid'])
                ):
                    if value is None:
                        continue
                    device[key] = value

            all_displays[device['edid']] = device
            index += 1

        all_displays = list(all_displays.values())
        if display is not None:
            all_displays = filter_monitors(display=display, haystack=all_displays, include=['path'])
        return all_displays

    @classmethod
    def get_brightness(cls, display: Optional[int] = None) -> List[int]:
        '''
        Gets the brightness for a display by reading the brightness files
        stored in `/sys/class/backlight/*/brightness`

        Args:
            display (int): The specific display you wish to query.

        Returns:
            list: list of ints (0 to 100)

        Example:
            ```python
            import screen_brightness_control as sbc

            # get the current display brightness
            current_brightness = sbc.linux.SysFiles.get_brightness()

            # get the brightness of the primary display
            primary_brightness = sbc.linux.SysFiles.get_brightness(display = 0)[0]

            # get the brightness of the secondary display
            secondary_brightness = sbc.linux.SysFiles.get_brightness(display = 1)[0]
            ```
        '''
        info = cls.get_display_info()
        if display is not None:
            info = [info[display]]

        results = []
        for device in info:
            with open(os.path.join(device['path'], 'brightness'), 'r') as f:
                brightness = int(f.read().rstrip('\n'))
            results.append(int(brightness / device['scale']))

        return results

    @classmethod
    def set_brightness(cls, value: int, display: Optional[int] = None):
        '''
        Sets the brightness for a display by writing to the brightness files
        stored in `/sys/class/backlight/*/brightness`.
        This function requires permission to write to these files which is
        usually provided when it's run as root.

        Args:
            value (int): Sets the brightness to this value
            display (int): The specific display you wish to adjust.

        Example:
            ```python
            import screen_brightness_control as sbc

            # set the brightness to 50%
            sbc.linux.SysFiles.set_brightness(50)

            # set the primary display brightness to 75%
            sbc.linux.SysFiles.set_brightness(75, display = 0)

            # set the secondary display brightness to 25%
            sbc.linux.SysFiles.set_brightness(25, display = 1)
            ```
        '''
        info = cls.get_display_info()
        if display is not None:
            info = [info[display]]

        for device in info:
            with open(os.path.join(device['path'], 'brightness'), 'w') as f:
                f.write(str(int(value * device['scale'])))


class I2C:
    '''
    In the same spirit as `SysFiles`, this class serves as a way of getting
    display information and adjusting the brightness without relying on any
    3rd party software.

    Usage of this class requires read and write permission for `/dev/i2c-*`.

    This class works over the I2C bus, primarily with desktop monitors as I
    haven't tested any e-DP displays yet.

    Massive thanks to [siemer](https://github.com/siemer) for
    his work on the [ddcci.py](https://github.com/siemer/ddcci) project,
    which served as a my main reference for this.

    References:
        * [ddcci.py](https://github.com/siemer/ddcci)
        * [DDCCI Spec](https://milek7.pl/ddcbacklight/ddcci.pdf)
    '''
    # vcp commands
    GET_VCP_CMD = 0x01
    '''VCP command to get the value of a feature (eg: brightness)'''
    GET_VCP_REPLY = 0x02
    '''VCP feature reply op code'''
    SET_VCP_CMD = 0x03
    '''VCP command to set the value of a feature (eg: brightness)'''

    # addresses
    DDCCI_ADDR = 0x37
    '''DDC packets are transmittred using this I2C address'''
    HOST_ADDR_R = 0x50
    '''Packet source address (the computer) when reading data'''
    HOST_ADDR_W = 0x51
    '''Packet source address (the computer) when writing data'''
    DESTINATION_ADDR_W = 0x6e
    '''Packet destination address (the monitor) when writing data'''
    I2C_SLAVE = 0x0703
    '''The I2C slave address'''

    # timings
    WAIT_TIME = 0.05
    '''How long to wait between I2C commands'''

    _max_brightness_cache: dict = {}

    class I2CDevice():
        '''
        Class to read and write data to an I2C bus,
        based on the `I2CDev` class from [ddcci.py](https://github.com/siemer/ddcci)
        '''
        def __init__(self, fname: str, slave_addr: int):
            '''
            Args:
                fname (str): the I2C path, eg: `/dev/i2c-2`
                slave_addr (int): not entirely sure what this is meant to be
            '''
            self.device = os.open(fname, os.O_RDWR)
            # I2C_SLAVE address setup
            fcntl.ioctl(self.device, I2C.I2C_SLAVE, slave_addr)

        def read(self, length: int) -> bytes:
            '''
            Read a certain number of bytes from the I2C bus

            Args:
                length (int): the number of bytes to read

            Returns:
                bytes
            '''
            return os.read(self.device, length)

        def write(self, data: bytes) -> int:
            '''
            Writes data to the I2C bus

            Args:
                data (bytes): the data to write

            Returns:
                int: the number of bytes written
            '''
            return os.write(self.device, data)

    class DDCInterface(I2CDevice):
        '''
        Class to send DDC (Display Data Channel) commands to an I2C device,
        based on the `Ddcci` and `Mccs` classes from [ddcci.py](https://github.com/siemer/ddcci)
        '''

        PROTOCOL_FLAG = 0x80

        def __init__(self, i2c_path: str):
            '''
            Args:
                i2c_path (str): the path to the I2C device, eg: `/dev/i2c-2`
            '''
            super().__init__(i2c_path, I2C.DDCCI_ADDR)

        def write(self, *args) -> int:
            '''
            Write some data to the I2C device.

            It is recommended to use `setvcp` to set VCP values on the DDC device
            instead of using this function directly.

            Args:
                *args: variable length list of arguments. This will be put
                    into a `bytearray` and wrapped up in various flags and
                    checksums before being written to the I2C device

            Returns:
                int: the number of bytes that were written
            '''
            time.sleep(I2C.WAIT_TIME)

            ba = bytearray(args)
            ba.insert(0, len(ba) | self.PROTOCOL_FLAG)  # add length info
            ba.insert(0, I2C.HOST_ADDR_W)  # insert source address
            ba.append(functools.reduce(operator.xor, ba, I2C.DESTINATION_ADDR_W))  # checksum

            return super().write(ba)

        def setvcp(self, vcp_code: int, value: int) -> int:
            '''
            Set a VCP value on the device

            Args:
                vcp_code (int): the VCP command to send, eg: `0x10` is brightness
                value (int): what to set the value to

            Returns:
                int: the number of bytes written to the device
            '''
            return self.write(I2C.SET_VCP_CMD, vcp_code, *value.to_bytes(2, 'big'))

        def read(self, amount: int) -> bytes:
            '''
            Reads data from the DDC device.

            It is recommended to use `getvcp` to retrieve VCP values from the
            DDC device instead of using this function directly.

            Args:
                amount (int): the number of bytes to read

            Returns:
                bytes

            Raises:
                ValueError: if the read data is deemed invalid
            '''
            time.sleep(I2C.WAIT_TIME)

            ba = super().read(amount + 3)

            # check the bytes read
            checks = {
                'source address': ba[0] == I2C.DESTINATION_ADDR_W,
                'checksum': functools.reduce(operator.xor, ba) == I2C.HOST_ADDR_R,
                'length': len(ba) >= (ba[1] & ~self.PROTOCOL_FLAG) + 3
            }
            if False in checks.values():
                raise ValueError('i2c read check failed: ' + repr(checks))

            return ba[2:-1]

        def getvcp(self, vcp_code: int) -> Tuple[int, int]:
            '''
            Retrieves a VCP value from the DDC device.

            Args:
                vcp_code (int): the VCP value to read, eg: `0x10` is brightness

            Returns:
                tuple[int, int]: the current and maximum value respectively

            Raises:
                ValueError: if the read data is deemed invalid
            '''
            self.write(I2C.GET_VCP_CMD, vcp_code)
            ba = self.read(8)

            checks = {
                'is feature reply': ba[0] == I2C.GET_VCP_REPLY,
                'supported VCP opcode': ba[1] == 0,
                'answer matches request': ba[2] == vcp_code
            }
            if False in checks.values():
                raise ValueError('i2c read check failed: ' + repr(checks))

            # current and max values
            return int.from_bytes(ba[6:8], 'big'), int.from_bytes(ba[4:6], 'big')

    @classmethod
    def get_display_info(cls, display: Optional[Union[int, str]] = None) -> List[dict]:
        '''
        Returns information about detected displays by querying the various I2C buses

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
            info = sbc.linux.I2C.get_display_info()
            # EG output: [{'name': 'Benq GL2450H', 'model': 'GL2450H', 'manufacturer': 'BenQ', 'edid': '00ffff...'}]

            # get info about the primary monitor
            primary_info = sbc.linux.I2C.get_display_info(0)[0]

            # get info about a monitor called 'Benq GL2450H'
            benq_info = sbc.linux.I2C.get_display_info('Benq GL2450H')[0]
            ```
        '''
        all_displays = __cache__.get('i2c_display_info')
        if all_displays is None:
            all_displays = []
            index = 0

            for i2c_path in glob.glob('/dev/i2c-*'):
                if not os.path.exists(i2c_path):
                    continue

                try:
                    # open the I2C device using the host read address
                    device = cls.I2CDevice(i2c_path, cls.HOST_ADDR_R)
                    # read some 512 bytes from the device
                    data = device.read(512)
                except IOError:
                    continue

                # search for the EDID header within our 512 read bytes
                start = data.find(bytes.fromhex('00 FF FF FF FF FF FF 00'))
                if start < 0:
                    continue

                # grab 128 bytes of the edid
                edid = data[start: start + 128]
                # parse the EDID
                manufacturer_id, manufacturer, model, name, serial = EDID.parse(edid)
                # convert edid to hex string
                edid = ''.join(f'{i:02x}' for i in edid)

                all_displays.append(
                    {
                        'name': name,
                        'model': model,
                        'manufacturer': manufacturer,
                        'manufacturer_id': manufacturer_id,
                        'serial': serial,
                        'method': cls,
                        'index': index,
                        'edid': edid,
                        'i2c_bus': i2c_path
                    }
                )
                index += 1

            if all_displays:
                __cache__.store('i2c_display_info', all_displays, expires=2)

        if display is not None:
            return filter_monitors(display=display, haystack=all_displays, include=['i2c_bus'])
        return all_displays

    @classmethod
    def get_brightness(cls, display: Optional[int] = None) -> List[int]:
        '''
        Gets the brightness for a display by querying the I2C bus

        Args:
            display (int): The specific display you wish to query.

        Returns:
            list: list of ints (0 to 100)

        Example:
            ```python
            import screen_brightness_control as sbc

            # get the current display brightness
            current_brightness = sbc.linux.I2C.get_brightness()

            # get the brightness of the primary display
            primary_brightness = sbc.linux.I2C.get_brightness(display = 0)[0]

            # get the brightness of the secondary display
            secondary_brightness = sbc.linux.I2C.get_brightness(display = 1)[0]
            ```
        '''
        all_displays = cls.get_display_info()
        if display is not None:
            all_displays = [all_displays[display]]

        results = []
        for device in all_displays:
            interface = cls.DDCInterface(device['i2c_bus'])
            value, max_value = interface.getvcp(0x10)

            # make sure display's max brighness is cached
            cache_ident = '%s-%s-%s' % (device['name'], device['model'], device['serial'])
            if cache_ident not in cls._max_brightness_cache:
                cls._max_brightness_cache[cache_ident] = max_value

            if max_value != 100:
                # if max value is not 100 then we have to adjust the scale to be
                # a percentage
                value = int((value / max_value) * 100)

            results.append(value)

        return results

    @classmethod
    def set_brightness(cls, value: int, display: Optional[int] = None):
        '''
        Sets the brightness for a display by writing to the I2C bus

        Args:
            value (int): Set the brightness to this value
            display (int): The specific display you wish to adjust.

        Example:
            ```python
            import screen_brightness_control as sbc

            # set the brightness to 50%
            sbc.linux.I2C.set_brightness(50)

            # set the primary display brightness to 75%
            sbc.linux.I2C.set_brightness(75, display = 0)

            # set the secondary display brightness to 25%
            sbc.linux.I2C.set_brightness(25, display = 1)
            ```
        '''
        all_displays = cls.get_display_info()
        if display is not None:
            all_displays = [all_displays[display]]

        for device in all_displays:
            # make sure display brightness max value is cached
            cache_ident = '%s-%s-%s' % (device['name'], device['model'], device['serial'])
            if cache_ident not in cls._max_brightness_cache:
                cls.get_brightness(display=device['index'])

            # scale the brightness value according to the max brightness
            max_value = cls._max_brightness_cache[cache_ident]
            if max_value != 100:
                value = int((value / 100) * max_value)

            interface = cls.DDCInterface(device['i2c_bus'])
            interface.setvcp(0x10, value)


class Light:
    '''collection of screen brightness related methods using the light executable'''

    executable: str = 'light'
    '''the light executable to be called'''

    @classmethod
    def get_display_info(cls, display: Optional[Union[int, str]] = None) -> List[dict]:
        '''
        Returns information about detected displays as reported by Light.

        It works by taking the output of `SysFiles.get_display_info` and
        filtering out any displays that aren't supported by Light

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
        light_output = check_output([cls.executable, '-L']).decode()
        displays = []
        index = 0
        for device in SysFiles.get_display_info():
            # SysFiles scrapes info from the same place that Light used to
            # so it makes sense to use that output
            if device['path'].replace('/sys/class', 'sysfs') in light_output:
                del device['scale']
                device['light_path'] = device['path'].replace('/sys/class', 'sysfs')
                device['method'] = cls
                device['index'] = index

                displays.append(device)
                index += 1

        if display is not None:
            displays = filter_monitors(display=display, haystack=displays, include=['path', 'light_path'])
        return displays

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
            sbc.linux.Light.set_brightness(25, display = 1)
            ```
        '''
        info = cls.get_display_info()
        if display is not None:
            info = [info[display]]

        for i in info:
            check_output(f'{cls.executable} -S {value} -s {i["light_path"]}'.split(" "))

    @classmethod
    def get_brightness(cls, display: Optional[int] = None) -> List[int]:
        '''
        Gets the brightness for a display using the light executable

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
                check_output([cls.executable, '-G', '-s', i['light_path']])
            )
        results = [int(round(float(i.decode()), 0)) for i in results]
        return results


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
        def check_display(display):
            if display:
                if 'line' in display:
                    del display['line']
                return display['serial'] is None or '\\x' not in display['serial']
            return False

        xrandr_output = check_output([cls.executable, '--verbose']).decode().split('\n')

        valid_displays = []
        display_count = 0
        tmp_display = {}

        for line_index, line in enumerate(xrandr_output):
            if line == '':
                continue

            if not line.startswith((' ', '\t')) and 'connected' in line and 'disconnected' not in line:
                if check_display(tmp_display):
                    valid_displays.append(tmp_display)

                tmp_display = {
                    'interface': line.split(' ')[0],
                    'name': line.split(' ')[0],
                    'line': line,
                    'method': cls,
                    'index': display_count,
                    'model': None,
                    'serial': None,
                    'manufacturer': None,
                    'manufacturer_id': None,
                    'edid': None
                }
                display_count += 1

            elif 'EDID:' in line:
                # extract the edid from the chunk of the output that will contain the edid
                edid = ''.join(
                    i.replace('\t', '') for i in xrandr_output[line_index + 1: line_index + 9]
                )
                tmp_display['edid'] = edid

                for key, value in zip(
                    ('manufacturer_id', 'manufacturer', 'model', 'name', 'serial'),
                    EDID.parse(tmp_display['edid'])
                ):
                    if value is None:
                        continue
                    tmp_display[key] = value

            elif 'Brightness:' in line and brightness:
                tmp_display['brightness'] = int(float(line.replace('Brightness:', '')) * 100)

        if check_display(tmp_display):
            valid_displays.append(tmp_display)

        if display is not None:
            valid_displays = filter_monitors(display=display, haystack=valid_displays, include=['interface'])
        return valid_displays

    @classmethod
    def get_display_interfaces(cls) -> List[str]:
        '''
        *DEPRECATED*  
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
        warnings.warn(
            (
                'XRandr.get_display_interfaces is deprecated and will be removed in the next release.'
                ' Please use XRandr.get_display_info instead'
            ), DeprecationWarning
        )
        out = subprocess.check_output([cls.executable, '-q']).decode().split('\n')
        return [i.split(' ')[0] for i in out if 'connected' in i and 'disconnected' not in i]

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
            check_output([cls.executable, '--output', i['interface'], '--brightness', value])


class DDCUtil:
    '''collection of screen brightness related methods using the ddcutil executable'''

    executable: str = 'ddcutil'
    '''the ddcutil executable to be called'''
    sleep_multiplier: float = 0.5
    '''how long ddcutil should sleep between each DDC request (lower is shorter).
    See [the ddcutil docs](https://www.ddcutil.com/performance_options/) for more info.'''
    _max_brightness_cache: dict = {}
    '''Cache for monitors and their maximum brightness values'''

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
        def check_display(tmp_display):
            if tmp_display and 'Invalid display' not in tmp_display['line']:
                del tmp_display['line']
                return True
            return False

        valid_displays = __cache__.get('ddcutil_monitors_info')
        if valid_displays is None:
            raw_ddcutil_output = str(
                check_output(
                    [
                        cls.executable, 'detect', '-v',
                        f'--sleep-multiplier={cls.sleep_multiplier}'
                    ], max_tries=10
                )
            )[2:-1].split('\\n')
            # Use -v to get EDID string but this means output cannot be decoded.
            # Or maybe it can. I don't know the encoding though, so let's assume it cannot be decoded.
            # Use str()[2:-1] workaround

            # include "Invalid display" sections because they tell us where one displays metadata ends
            # and another begins. We filter out invalid displays later on
            ddcutil_output = [i for i in raw_ddcutil_output if i.startswith(('Invalid display', 'Display', '\t', ' '))]
            valid_displays = []
            tmp_display = {}
            display_count = 0

            for line_index, line in enumerate(ddcutil_output):
                if not line.startswith(('\t', ' ')):
                    if check_display(tmp_display):
                        valid_displays.append(tmp_display)

                    tmp_display = {
                        'line': line,
                        'method': cls,
                        'index': display_count,
                        'model': None,
                        'serial': None,
                        'bin_serial': None,
                        'manufacturer': None,
                        'manufacturer_id': None,
                        'edid': None
                    }
                    display_count += 1

                elif 'I2C bus' in line:
                    tmp_display['i2c_bus'] = line[line.index('/'):]
                    tmp_display['bus_number'] = int(tmp_display['i2c_bus'].replace('/dev/i2c-', ''))

                elif 'Mfg id' in line:
                    tmp_display['manufacturer_id'] = line.replace('Mfg id:', '').replace(' ', '')
                    try:
                        (
                            tmp_display['manufacturer_id'],
                            tmp_display['manufacturer']
                        ) = _monitor_brand_lookup(tmp_display['manufacturer_id'])
                    except TypeError:
                        pass

                elif 'Model' in line:
                    # the split() removes extra spaces
                    name = line.replace('Model:', '').split()
                    try:
                        tmp_display['model'] = name[1]
                    except IndexError:
                        pass
                    tmp_display['name'] = ' '.join(name)

                elif 'Serial number' in line:
                    tmp_display['serial'] = line.replace('Serial number:', '').replace(' ', '')

                elif 'Binary serial number:' in line:
                    tmp_display['bin_serial'] = line.split(' ')[-1][3:-1]

                elif 'EDID hex dump:' in line:
                    try:
                        tmp_display['edid'] = ''.join(
                            ''.join(i.split()[1:17]) for i in ddcutil_output[line_index + 2: line_index + 10]
                        )
                    except Exception:
                        pass

            if check_display(tmp_display):
                valid_displays.append(tmp_display)
            if valid_displays:
                __cache__.store('ddcutil_monitors_info', valid_displays)

        if display is not None:
            valid_displays = filter_monitors(display=display, haystack=valid_displays, include=['i2c_bus'])
        return valid_displays

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
        for monitor in monitors:
            value = __cache__.get(f'ddcutil_brightness_{monitor["index"]}')
            if value is None:
                cmd_out = check_output(
                    [
                        cls.executable,
                        'getvcp', '10', '-t',
                        '-b', str(monitor['bus_number']),
                        f'--sleep-multiplier={cls.sleep_multiplier}'
                    ], max_tries=10
                ).decode().split(' ')

                value = int(cmd_out[-2])
                max_value = int(cmd_out[-1])
                if max_value != 100:
                    # if the max brightness is not 100 then the number is not a percentage
                    # and will need to be scaled
                    value = int((value / max_value) * 100)

                # now make sure max brightness is recorded so set_brightness can use it
                cache_ident = '%s-%s-%s' % (monitor['name'], monitor['serial'], monitor['bin_serial'])
                if cache_ident not in cls._max_brightness_cache:
                    cls._max_brightness_cache[cache_ident] = max_value

                __cache__.store(f'ddcutil_brightness_{monitor["index"]}', value, expires=0.5)
            try:
                res.append(value)
            except (TypeError, ValueError):
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

        __cache__.expire(startswith='ddcutil_brightness_')
        for monitor in monitors:
            # check if monitor has a max brightness that requires us to scale this value
            cache_ident = '%s-%s-%s' % (monitor['name'], monitor['serial'], monitor['bin_serial'])
            if cache_ident not in cls._max_brightness_cache:
                cls.get_brightness(display=monitor['index'])

            if cls._max_brightness_cache[cache_ident] != 100:
                value = int((value / 100) * cls._max_brightness_cache[cache_ident])

            check_output(
                [
                    cls.executable, 'setvcp', '10', str(value),
                    '-b', str(monitor['bus_number']),
                    f'--sleep-multiplier={cls.sleep_multiplier}'
                ], max_tries=10
            )


def list_monitors_info(method: Optional[str] = None, allow_duplicates: bool = False) -> List[dict]:
    '''
    Lists detailed information about all detected monitors

    Args:
        method (str): the method the monitor can be addressed by. See `screen_brightness_control.get_methods`
            for more info on available methods
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
    all_methods = get_methods()

    if method is not None:
        method = method.lower()
        if method not in all_methods:
            raise ValueError(f'method must be one of: {list(all_methods)}')

    info = []
    edids = []
    for method_name, method_class in all_methods.items():
        if method is None or method == method_name:
            # to make sure each display (with unique edid) is only reported once
            try:
                tmp = method_class.get_display_info()
            except Exception:
                pass
            else:
                for i in tmp:
                    if allow_duplicates or i['edid'] not in edids:
                        edids.append(i['edid'])
                        info.append(i)
    return info
