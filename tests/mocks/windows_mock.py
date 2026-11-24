import re
from collections import namedtuple
from contextlib import contextmanager
from ctypes.wintypes import HMONITOR

import win32con

from ..helpers import fake_edid

FAKE_DISPLAYS = [
    {'name': 'BNQ0123', 'uid': '10000', 'longname': 'BenQ 0123', 'laptop': False},
    {'name': 'MSI4567', 'uid': '20000', 'longname': 'MSI 4567', 'laptop': False},
    {'name': 'DEL8910', 'uid': '30000', 'longname': 'Dell 8910', 'laptop': False},
    {'name': 'SEC544B', 'uid': '40000', 'longname': 'Hewlett-Packard 544B', 'laptop': True},
]

# A representative MCCS capabilities string, as reported by a real monitor
# (trimmed example from LG/Philips displays). Used by the VCP.get_capabilities tests.
FAKE_CAPABILITIES = (
    '(prot(monitor)type(LCD)model(246E7QDA)cmds(01 02 03 07 0C E3 F3)'
    'vcp(02 04 05 08 0B 0C 10 12 14(01 05 08 0B) 16 18 1A 52 54(00 01) 60(01 03 11) '
    '62 6C 6E 70 72(05 78 FB 50 64 78 8C A0) 86(02 08) 8D(01 02) AC AE B6 C0 C6 C8 C9 '
    'CA(01 02) CC D6(01 04 05) DC(00 02 05) DF E9(00 02) EB(00 01 02 03) F0(00 01) FF)'
    'mswhql(1)mccs_ver(2.2))'
)


def instance_name(fake: dict, wmi_style=False):
    name, uid, laptop = fake['name'], fake['uid'], fake['laptop']
    mid = '4&dc911b1' if laptop else '5&24bdd39e'
    if wmi_style:
        return rf'DISPLAY\{name}\{mid}&0&UID{uid}_0'
    return rf'\\?\DISPLAY#{name}#{mid}&0&UID{uid}#{{e6f07b5f-ee97-4a90-b076-33f57bf4eaa7}}'


class FakeMSMonitor:
    def __init__(self, fake: dict):
        self.InstanceName = instance_name(fake, True)
        self.__fake = fake

    def WmiGetMonitorRawEEdidV1Block(self, _index: int):
        if self.__fake['laptop']:
            raise Exception('<obscure WMI error> no edid on laptop displays')
        edid = fake_edid(self.__fake['name'][:3], self.__fake['longname'], 'serialnum')
        # split into 2 char chunks and turn into hex nums
        return [tuple(int(i, 16) for i in re.findall(r'..', edid)), 1]


class FakeWmiMonitorBrightnessMethods:
    def __init__(self, fake: dict):
        self.InstanceName = instance_name(fake, True)
        self.__fake = fake

    def WmiSetBrightness(self, value: int, timeout: int):
        return 0


class FakeWMI:
    def WmiMonitorBrightness(self):
        wmb = namedtuple('FakeWmiMonitorBrightness', ('InstanceName', 'CurrentBrightness'))
        monitors = []
        for fake in FAKE_DISPLAYS:
            if fake['laptop']:
                monitors.append(wmb(instance_name(fake, True), 100))
        return monitors

    def WmiMonitorDescriptorMethods(self):
        for fake in FAKE_DISPLAYS:
            yield FakeMSMonitor(fake)

    def WmiMonitorBrightnessMethods(self):
        monitors = []
        for fake in FAKE_DISPLAYS:
            if fake['laptop']:
                monitors.append(FakeWmiMonitorBrightnessMethods(fake))
        return monitors


class FakePyDISPLAY_DEVICE:
    DeviceID: str

    def __init__(self, fake: dict):
        self.__fake = fake
        self.DeviceID = instance_name(fake)
        self.StateFlags = win32con.DISPLAY_DEVICE_ATTACHED_TO_DESKTOP


class FakeWinDLL:
    class dxva2:
        @staticmethod
        def DestroyPhysicalMonitor(handle):
            pass

        @staticmethod
        def GetNumberOfPhysicalMonitorsFromHMONITOR(monitor: HMONITOR, count_out):
            for fake in FAKE_DISPLAYS:
                if fake['laptop']:
                    continue
                if fake['uid'].strip('0') != str(monitor):
                    continue
                count_out._obj.value = 1
                break
            else:
                count_out._obj.value = 0
            return 1

        @staticmethod
        def GetPhysicalMonitorsFromHMONITOR(monitor: HMONITOR, array_size, array_out):
            array_out[0].handle = int(monitor)
            return 1

        @staticmethod
        def GetVCPFeatureAndVCPFeatureReply(
            handle, code, code_type_out=None, current_value_out=None, max_value_out=None
        ):
            assert current_value_out is not None
            current_value_out._obj.value = 100
            if max_value_out is not None:
                max_value_out._obj.value = 100
            return 1

        @staticmethod
        def SetVCPFeature(handle, code, value_in):
            return 1

        @staticmethod
        def GetCapabilitiesStringLength(handle, length_out):
            length_out._obj.value = len(FAKE_CAPABILITIES) + 1  # include null terminator
            return 1

        @staticmethod
        def CapabilitiesRequestAndCapabilitiesReply(handle, buffer, length):
            encoded = FAKE_CAPABILITIES.encode('ascii')
            for index, byte in enumerate(encoded):
                buffer[index] = byte
            buffer[len(encoded)] = 0
            return 1


@contextmanager
def mock_wmi_init():
    yield FakeWMI()


def mock_enum_display_devices():
    for fake in FAKE_DISPLAYS:
        yield FakePyDISPLAY_DEVICE(fake)


def mock_enum_display_monitors(*args):
    ret = []
    for fake in FAKE_DISPLAYS:
        if fake['laptop']:
            continue
        ret.append((namedtuple('pyhandle', ['handle'])(int(fake['uid'].strip('0'))),))
    return ret
