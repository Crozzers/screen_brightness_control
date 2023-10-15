import re
from typing import Dict, Optional, Tuple
from screen_brightness_control.linux import I2C

def fake_edid(mfg_id: str, name: str, serial: str) -> str:
    def descriptor(string: str) -> str:
        return string.encode('utf-8').hex() + ('20' * (13 - len(string)))

    mfg_ords = [ord(i) - 64 for i in mfg_id]
    mfg = mfg_ords[0] << 10 | mfg_ords[1] << 5 | mfg_ords[2]

    return ''.join((
        '00ffffffffffff00',  # header
        f'{mfg:04x}',  # 'DEL' mfg id
        '00' * 44,  # product id -> edid timings
        '00' * 18,  # empty descriptor block
        f'000000fc00{descriptor(name)}',  # name descriptor
        f'000000ff00{descriptor(serial)}',  # serial descriptor
        '00' * 18,  # empty descriptor
        '00'  # extension flag
        '00'  # checksum - TODO: make this actually work
    ))


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
