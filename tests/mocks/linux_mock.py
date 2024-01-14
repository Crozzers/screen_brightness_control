import re
import textwrap
from typing import Dict, List, Tuple

from screen_brightness_control.linux import I2C
from ..helpers import fake_edid


class MockI2C:
    class MockI2CDevice:
        _fake_devices = (
            ('DEL', 'Dell ABC123', 'serial123'),
            ('BNQ', 'BenQ DEF456', 'serial456')
        )

        def __init__(self, path: str, addr: int):
            match = re.match(r'/dev/i2c-(\d+)', path)
            assert match, 'device path does not match expected format'
            self._index = int(match.group(1))
            assert addr in (I2C.HOST_ADDR_R, I2C.DDCCI_ADDR)
            self._path = path
            self._addr = addr

        def read(self, length: int) -> bytes:
            if self._addr == I2C.HOST_ADDR_R:
                edid = fake_edid(*self._fake_devices[self._index])
                assert len(edid) == 256, '128 bytes is 256 string chars'
                return bytes.fromhex(('00' * 128) + edid + ('00' * 128))
            raise NotImplementedError()

        def write(self, data: bytes) -> int:
            return len(data)

    class MockDDCInterface(MockI2CDevice):
        def __init__(self, i2c_path: str):
            super().__init__(i2c_path, I2C.DDCCI_ADDR)

            self._vcp_state: Dict[int, int] = {}

        def write(self, *args) -> int:
            raise NotImplementedError()

        def read(self, amount: int) -> bytes:
            raise NotImplementedError()

        def setvcp(self, vcp_code: int, value: int) -> int:
            self._vcp_state[vcp_code] = value
            return 0

        def getvcp(self, vcp_code: int) -> Tuple[int, int]:
            assert vcp_code == 0x10, 'should only be getting the brightness'
            # current and max brightness
            return self._vcp_state.get(vcp_code, 100), 100


def mock_xrandr_verbose_output(mfg_id: str, name: str, serial: str, index = 1):
    '''
    Mocks the output of `xrandr --verbose` for a display, including a fake edid
    '''
    edid = fake_edid(mfg_id, name, serial)
    block = textwrap.indent('\n'.join(textwrap.wrap(edid, 32)), '    ' * 6)
    return textwrap.dedent(f'''
        HDMI-{index} connected ...
                Identifier: 0x{mfg_id}
                Brightness: 1.0
                EDID:\n{block}
                non-dekstop: 0
          1920x1080 ...
                h: ...
                v: ...
          2160x1440 ...
                h: ...
                v: ...
    ''')


def mock_ddcutil_detect_output(mfg_id: str, name: str, serial: str, index = 1):
    '''
    Mocks the output of `ddcutil detect` for a display, including a fake edid
    '''
    edid = fake_edid(mfg_id, name, serial)
    block = ''
    for chunk in textwrap.wrap(edid, 32):
        block += '    ' * 2  # indent
        block += '+0000   '  # block number
        block += ' '.join(textwrap.wrap(chunk, 2))  # the edid line
        block += '   ...the_line_decoded...'
    block = textwrap.indent(block, '    ' * 5)
    return textwrap.dedent(f'''
        Display {index}
            I2C bus: /dev/i2c-{index}
            EDID synopsis:
                Mfg id: {mfg_id} - SomeBrand
                Model: {name}
                Serial number: {serial}
                Binary serial number: 123 (0x000000)
                EDID hex dump:
                        +0      +4      +8...
                    {block}
    ''')


def mock_check_output(command: List[str], max_tries: int = 1) -> bytes:
    '''
    Mocks the output of `check_output`
    '''
    if command[0] == 'xrandr':
        if command[1] == '--verbose':
            # list displays
            return (
                mock_xrandr_verbose_output('DEL', 'Dell ABC123', 'abc123', 1)
                + mock_xrandr_verbose_output('BNQ', 'BenQ DEF456', 'def456', 2)
            ).encode()
        elif '--output' in command and '--brightness' in command:
            # set brightness. output is not used. Return nothing
            return b''
    elif command[0] == 'ddcutil':
        if command[1] == 'detect':
            # list displays
            return (
                mock_ddcutil_detect_output('DEL', 'Dell ABC123', 'abc123', 1)
                + mock_ddcutil_detect_output('BNQ', 'BenQ DEF456', 'def456', 2)
            ).encode()
        elif command[1] == 'getvcp':
            return b'100 100'
        elif command[1] == 'setvcp':
            return b''

    raise NotImplementedError(f'check_output mocks not implemented for {command}')
